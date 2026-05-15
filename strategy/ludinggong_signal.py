"""
鹿鼎公策略 - 区域信号生成器
基于估值区间定权限 → 价格/RSI定区域 → MACD定扳机 的三层递进信号模型
"""
import logging
from dataclasses import dataclass
from typing import Dict, Optional, Tuple

import numpy as np
import pandas as pd

from indicators.divergence import (
    detect_macd_bullish_divergence,
    detect_macd_bearish_divergence,
)

logger = logging.getLogger(__name__)

# 鹿鼎公默认参数
DEFAULT_PARAMS = {
    'zero_threshold': 0.01,       # 零轴附近：abs(DIF)/close < 1%
    'band_ratio': 0.075,          # 中轨附近：半带宽15%
    'divergence_order': 5,        # 背离检测窗口
    'urgent_buy_pct': 0.45,       # 加急买入比例（40%-50%中值）
    'normal_buy_pct': 0.30,       # 正常买入比例
    'pre_sell_pct': 1/3,          # 预减仓比例
    'first_sell_pct': 1/3,        # 首次止盈比例
    'second_sell_pct': 0.5,       # 加卖比例（剩余的一半）
    'max_single_stock_ratio': 0.20,  # 单票仓位上限
}


@dataclass
class ZoneResult:
    """区域检测结果"""
    zone: str = 'zone4_hold'
    signal: str = 'HOLD'
    buy_level: Optional[str] = None       # 'normal' | 'urgent'
    buy_pct: float = 0.0
    sell_step: Optional[str] = None       # 'pre_sell' | 'first_sell' | 'second_sell'
    sell_pct: float = 0.0
    valuation_zone: str = '合理'
    zone_max_ratio: float = 0.60
    permission: str = 'sell_only'         # 'buy_only' | 'buy_sell' | 'sell_only'
    reason: str = ''


class LudinggongSignalGenerator:
    """鹿鼎公区域信号生成器"""

    def __init__(self, dcf_values: Dict[str, float],
                 rsi_thresholds: Dict[str, Dict[str, float]],
                 stock_industry_map: Dict[str, Dict[str, str]],
                 params: Optional[Dict] = None):
        self.dcf_values = dcf_values
        self.rsi_thresholds = rsi_thresholds
        self.stock_industry_map = stock_industry_map
        self.params = {**DEFAULT_PARAMS, **(params or {})}

    def get_valuation_zone(self, value_ratio: float) -> Tuple[str, float, str]:
        """
        估值区间判定 → (名称, 仓位上限占分配上限比例, 操作权限)

        仓位上限是占单票分配上限（总资金×20%）的比例。
        """
        if value_ratio < 0.70:
            return '极度低估', 1.0, 'buy_only'
        elif value_ratio < 0.80:
            return '低估', 0.80, 'buy_sell'
        elif value_ratio < 1.10:
            return '合理', 0.60, 'sell_only'
        elif value_ratio < 1.30:
            return '合理偏高', 0.30, 'sell_only'
        else:
            return '高估', 0.10, 'sell_only'

    def _get_industry_thresholds(self, stock_code: str) -> dict:
        """获取股票所属行业的RSI阈值"""
        if stock_code not in self.stock_industry_map:
            return {'os': 30, 'ob': 70, 'ext_os': 20, 'ext_ob': 80}

        industry_code = self.stock_industry_map[stock_code].get('industry_code', '')
        if industry_code not in self.rsi_thresholds:
            return {'os': 30, 'ob': 70, 'ext_os': 20, 'ext_ob': 80}

        t = self.rsi_thresholds[industry_code]
        return {
            'os': float(t.get('buy_threshold', 30)),
            'ob': float(t.get('sell_threshold', 70)),
            'ext_os': float(t.get('extreme_buy_threshold', 20)),
            'ext_ob': float(t.get('extreme_sell_threshold', 80)),
        }

    def check_zone_and_signal(self, stock_code: str, weekly_data: pd.DataFrame,
                              current_idx: int, has_pre_sold: bool = False,
                              has_first_sold: bool = False,
                              was_oversold: bool = False,
                              was_vol_dried: bool = False,
                              was_rsi_oversold: bool = False) -> ZoneResult:
        """
        主入口：判断区域 + 检测扳机 → 返回信号结果

        Args:
            stock_code: 股票代码
            weekly_data: 完整周线数据（含技术指标列）
            current_idx: 当前周在 DataFrame 中的位置索引
            has_pre_sold: 是否已执行预减仓
            has_first_sold: 是否已执行首次止盈
        """
        try:
            if current_idx < 20:
                return ZoneResult(reason='数据不足（<20周）')

            row = weekly_data.iloc[current_idx]
            row_prev = weekly_data.iloc[current_idx - 1]
            close = float(row['close'])

            # 1. 计算价值比 → 估值区间 + 操作权限
            dcf = self.dcf_values.get(stock_code)
            if dcf is None or dcf <= 0:
                return ZoneResult(reason='缺少有效DCF估值')
            value_ratio = close / dcf
            zone_name, zone_max_ratio, permission = self.get_valuation_zone(value_ratio)

            # 2. 获取行业RSI阈值
            th = self._get_industry_thresholds(stock_code)
            os, ob = th['os'], th['ob']
            ext_os, ext_ob = th['ext_os'], th['ext_ob']

            rsi = float(row['rsi']) if not pd.isna(row.get('rsi')) else 50
            rsi_prev = float(row_prev['rsi']) if not pd.isna(row_prev.get('rsi')) else 50

            # 3. 检测区域 → 检测扳机
            result = self._check_zone_3(weekly_data, current_idx, row, row_prev,
                                        th, has_pre_sold, has_first_sold,
                                        zone_name, zone_max_ratio, permission,
                                        value_ratio)
            if result.zone != 'zone4_hold':
                return result

            result = self._check_zone_2(weekly_data, current_idx, row, row_prev,
                                        th, zone_name, zone_max_ratio, permission,
                                        value_ratio)
            if result.zone != 'zone4_hold':
                return result

            result = self._check_zone_1(weekly_data, current_idx, row, row_prev,
                                        th, zone_name, zone_max_ratio, permission,
                                        value_ratio, was_oversold, was_vol_dried,
                                        was_rsi_oversold)
            if result.zone != 'zone4_hold':
                return result

            return ZoneResult(
                zone='zone4_hold', signal='HOLD',
                valuation_zone=zone_name, zone_max_ratio=zone_max_ratio,
                permission=permission, reason='未触发任何区域信号'
            )

        except Exception as e:
            logger.error(f"区域信号检测失败 {stock_code}: {e}")
            return ZoneResult(reason=f'检测异常: {e}')

    def _check_zone_1(self, data: pd.DataFrame, idx: int,
                      row, row_prev, th: dict,
                      zone_name: str, zone_max_ratio: float, permission: str,
                      value_ratio: float, was_oversold: bool = False,
                      was_vol_dried: bool = False,
                      was_rsi_oversold: bool = False) -> ZoneResult:
        """
        止跌区（左侧买入）
        绿灯区间：曾超跌 + 曾缩量 + RSI曾超卖。扳机：MACD金叉/底背离
        """
        # 估值权限：只有 buy_only 或 buy_sell 才能买入
        if permission not in ('buy_only', 'buy_sell'):
            return ZoneResult()

        ext_os = th['ext_os']

        # 价格条件：曾跌破下轨(was_oversold) 且 本周站回下轨上方
        close = float(row['close'])
        bb_lower = float(row['bb_lower']) if not pd.isna(row.get('bb_lower')) else close
        price_ok = was_oversold and (close > bb_lower)

        # RSI条件：超跌期间曾进入超卖区
        rsi_ok = was_rsi_oversold

        # 量能条件：超跌期间曾出现MA5<MA20 且 本周量 < 近4周最大量
        volume_now = float(row['volume']) if not pd.isna(row.get('volume')) else 0
        vol_4w_max = float(row['vol_4w_max']) if not pd.isna(row.get('vol_4w_max')) else float('inf')
        vol_ok = was_vol_dried and (volume_now < vol_4w_max)

        # 买入扳机：MACD金叉 / 底背离 / 绿柱缩短
        dif = float(row.get('macd', 0)) if not pd.isna(row.get('macd')) else 0
        dea = float(row.get('macd_signal', 0)) if not pd.isna(row.get('macd_signal')) else 0
        dif_prev = float(row_prev.get('macd', 0)) if not pd.isna(row_prev.get('macd')) else 0
        dea_prev = float(row_prev.get('macd_signal', 0)) if not pd.isna(row_prev.get('macd_signal')) else 0
        golden_cross = (dif_prev < dea_prev) and (dif > dea)

        close_series = data['close'].iloc[:idx + 1]
        hist_series = data['macd_histogram'].iloc[:idx + 1]
        bull_div = detect_macd_bullish_divergence(
            close_series, hist_series, order=self.params['divergence_order']
        )

        hist = float(row.get('macd_histogram', 0)) if not pd.isna(row.get('macd_histogram')) else 0
        hist_prev = float(row_prev.get('macd_histogram', 0)) if not pd.isna(row_prev.get('macd_histogram')) else 0
        hist_shrinking = (hist < 0) and (hist > hist_prev)

        # DIF跌速放缓：DIF下降速度在减速（或已拐头向上），确认真衰竭而非反弹回撤
        dif_decel = False
        if idx >= 2:
            row_prev2 = data.iloc[idx - 2]
            dif_prev2 = float(row_prev2.get('macd', 0)) if not pd.isna(row_prev2.get('macd')) else 0
            dif_delta = dif - dif_prev
            dif_delta_prev = dif_prev - dif_prev2
            dif_decel = dif_delta > dif_delta_prev

        hist_shrinking_confirmed = hist_shrinking and dif_decel

        trigger = price_ok and rsi_ok and vol_ok and (golden_cross or bull_div or hist_shrinking_confirmed)
        if not trigger:
            return ZoneResult()

        rsi_prev = float(row_prev['rsi']) if not pd.isna(row_prev.get('rsi')) else 50
        if rsi_prev < ext_os:
            buy_level = 'urgent'
            buy_pct = self.params['urgent_buy_pct']
            reason = f'止跌区·加急买入(RSI破极端{ext_os:.0f})'
        else:
            buy_level = 'normal'
            buy_pct = self.params['normal_buy_pct']
            reason = f'止跌区·正常买入'

        if golden_cross:
            trigger_detail = '金叉'
        elif bull_div:
            trigger_detail = '底背离'
        else:
            trigger_detail = '绿柱缩短'
        reason += f'·{trigger_detail}'

        return ZoneResult(
            zone='zone1_stop_falling', signal='BUY',
            buy_level=buy_level, buy_pct=buy_pct,
            valuation_zone=zone_name, zone_max_ratio=zone_max_ratio,
            permission=permission, reason=reason,
        )

    def _check_zone_2(self, data: pd.DataFrame, idx: int,
                      row, row_prev, th: dict,
                      zone_name: str, zone_max_ratio: float, permission: str,
                      value_ratio: float) -> ZoneResult:
        """
        蓄力区（右侧加仓）
        条件：中轨附近 + RSI均衡 + 零轴附近金叉 + 红柱放出
        """
        if permission not in ('buy_only', 'buy_sell'):
            return ZoneResult()

        os = th['os']
        ob = th['ob']

        # 价格中轨附近
        close = float(row['close'])
        bb_mid = float(row['bb_middle']) if not pd.isna(row.get('bb_middle')) else close
        bandwidth = float(row['boll_bandwidth']) if not pd.isna(row.get('boll_bandwidth')) else close * 0.1
        price_mid_ok = abs(close - bb_mid) < self.params['band_ratio'] * bandwidth

        # RSI均衡区
        rsi = float(row['rsi']) if not pd.isna(row.get('rsi')) else 50
        rsi_ok = os < rsi < ob

        # 零轴附近
        dif = float(row.get('macd', 0)) if not pd.isna(row.get('macd')) else 0
        zero_near = abs(dif) / close < self.params['zero_threshold'] if close > 0 else False

        # 金叉
        dea = float(row.get('macd_signal', 0)) if not pd.isna(row.get('macd_signal')) else 0
        dif_prev = float(row_prev.get('macd', 0)) if not pd.isna(row_prev.get('macd')) else 0
        dea_prev = float(row_prev.get('macd_signal', 0)) if not pd.isna(row_prev.get('macd_signal')) else 0
        golden_cross = (dif_prev < dea_prev) and (dif > dea)

        # 红柱放出（仅要求 hist > 0，V1.1 放宽）
        hist = float(row.get('macd_histogram', 0)) if not pd.isna(row.get('macd_histogram')) else 0
        hist_ok = hist > 0

        trigger = price_mid_ok and rsi_ok and zero_near and golden_cross and hist_ok
        if not trigger:
            return ZoneResult()

        # 加仓到估值区间上限（买入剩余空间）
        buy_pct = 1.0  # 蓄力区买入到上限，实际数量由仓位管理器按剩余空间计算
        return ZoneResult(
            zone='zone2_accumulate', signal='BUY',
            buy_level='normal', buy_pct=buy_pct,
            valuation_zone=zone_name, zone_max_ratio=zone_max_ratio,
            permission=permission,
            reason=f'蓄力区·零轴金叉加仓(DIF={dif:.3f})',
        )

    def _check_zone_3(self, data: pd.DataFrame, idx: int,
                      row, row_prev, th: dict,
                      has_pre_sold: bool, has_first_sold: bool,
                      zone_name: str, zone_max_ratio: float, permission: str,
                      value_ratio: float) -> ZoneResult:
        """
        亢奋观察区（止盈卖出）
        进入条件：收盘价 > 布林上轨 或 RSI > 普通超买
        """
        # 极度低估禁止标准卖出，但允许预减仓（RSI极端超买）
        ob = th['ob']
        ext_ob = th['ext_ob']

        close = float(row['close'])
        high = float(row['high'])
        bb_upper = float(row['bb_upper']) if not pd.isna(row.get('bb_upper')) else close * 2
        rsi = float(row['rsi']) if not pd.isna(row.get('rsi')) else 50

        enter_zone = (close > bb_upper) or (high > bb_upper) or (rsi > ob)
        if not enter_zone:
            return ZoneResult()

        # 价值比>1.2时，所有卖出清仓处理
        if value_ratio > 1.2:
            clear_step, clear_pct = 'clear_all', 1.0
        else:
            clear_step, clear_pct = None, None

        # Step 1: 预减仓 — RSI > 极端超买（含极度低估）
        if rsi > ext_ob:
            if value_ratio > 1.2:
                return ZoneResult(
                    zone='zone3_excited', signal='SELL',
                    sell_step=clear_step, sell_pct=clear_pct,
                    valuation_zone=zone_name, zone_max_ratio=zone_max_ratio,
                    permission=permission,
                    reason=f'亢奋区·高估清仓(RSI={rsi:.1f}>{ext_ob:.0f})',
                )
            return ZoneResult(
                zone='zone3_excited', signal='SELL',
                sell_step='pre_sell', sell_pct=self.params['pre_sell_pct'],
                valuation_zone=zone_name, zone_max_ratio=zone_max_ratio,
                permission=permission,
                reason=f'亢奋区·预减仓1/3(RSI={rsi:.1f}>{ext_ob:.0f})',
            )

        # 极度低估：预减仓之后禁止首次止盈和加卖
        if permission == 'buy_only':
            return ZoneResult(
                zone='zone3_excited', signal='HOLD',
                valuation_zone=zone_name, zone_max_ratio=zone_max_ratio,
                permission=permission,
                reason='亢奋区·观察中(极度低估禁止常规卖出)',
            )

        # Step 2: 常规止盈扳机 — 红柱缩短、顶背离、死叉
        hist = float(row.get('macd_histogram', 0)) if not pd.isna(row.get('macd_histogram')) else 0
        hist_prev = float(row_prev.get('macd_histogram', 0)) if not pd.isna(row_prev.get('macd_histogram')) else 0
        hist_shorter = (hist > 0) and (hist < hist_prev)

        close_series = data['close'].iloc[:idx + 1]
        dif_series_for_div = data['macd'].iloc[:idx + 1]
        bear_div = detect_macd_bearish_divergence(
            close_series, dif_series_for_div, order=self.params['divergence_order']
        )

        dif = float(row.get('macd', 0)) if not pd.isna(row.get('macd')) else 0
        dea = float(row.get('macd_signal', 0)) if not pd.isna(row.get('macd_signal')) else 0
        dif_prev = float(row_prev.get('macd', 0)) if not pd.isna(row_prev.get('macd')) else 0
        dea_prev = float(row_prev.get('macd_signal', 0)) if not pd.isna(row_prev.get('macd_signal')) else 0
        death_cross = (dif_prev > dea_prev) and (dif < dea)

        first_sell_signal = hist_shorter or bear_div or death_cross

        # Step 3: 加卖 — 已预减或已首次止盈

        second_sell_signal = death_cross or bear_div or hist_shorter

        if has_pre_sold or has_first_sold:
            if second_sell_signal:
                if death_cross:
                    trigger_str = '死叉'
                elif bear_div:
                    trigger_str = '顶背离'
                else:
                    trigger_str = '红柱缩短'
                if value_ratio > 1.2:
                    return ZoneResult(
                        zone='zone3_excited', signal='SELL',
                        sell_step=clear_step, sell_pct=clear_pct,
                        valuation_zone=zone_name, zone_max_ratio=zone_max_ratio,
                        permission=permission,
                        reason=f'亢奋区·高估清仓({trigger_str})',
                    )
                return ZoneResult(
                    zone='zone3_excited', signal='SELL',
                    sell_step='second_sell', sell_pct=self.params['second_sell_pct'],
                    valuation_zone=zone_name, zone_max_ratio=zone_max_ratio,
                    permission=permission,
                    reason=f'亢奋区·加卖剩余1/2({trigger_str})',
                )
            return ZoneResult(
                zone='zone3_excited', signal='HOLD',
                valuation_zone=zone_name, zone_max_ratio=zone_max_ratio,
                permission=permission,
                reason='亢奋区·等待下一步卖出信号',
            )

        if first_sell_signal:
            if death_cross:
                trigger_str = '死叉'
            elif hist_shorter:
                trigger_str = '红柱缩短'
            else:
                trigger_str = '顶背离'
            if value_ratio > 1.2:
                return ZoneResult(
                    zone='zone3_excited', signal='SELL',
                    sell_step=clear_step, sell_pct=clear_pct,
                    valuation_zone=zone_name, zone_max_ratio=zone_max_ratio,
                    permission=permission,
                    reason=f'亢奋区·高估清仓({trigger_str})',
                )
            return ZoneResult(
                zone='zone3_excited', signal='SELL',
                sell_step='first_sell', sell_pct=self.params['first_sell_pct'],
                valuation_zone=zone_name, zone_max_ratio=zone_max_ratio,
                permission=permission,
                reason=f'亢奋区·首次止盈1/3({trigger_str})',
            )

        return ZoneResult(
            zone='zone3_excited', signal='HOLD',
            valuation_zone=zone_name, zone_max_ratio=zone_max_ratio,
            permission=permission,
            reason='亢奋区·观察中',
        )
