#!/usr/bin/env python3
"""
鹿鼎公信号分析工具
逐层展示：估值区间定权限 → 价格/RSI定区域 → MACD定扳机
用于诊断某只股票在某一天为什么出现/没出现买卖信号
"""

import argparse
import logging
import sys
import os
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple

import numpy as np
import pandas as pd

sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from services.data_service import DataService
from strategy.ludinggong_signal import LudinggongSignalGenerator, DEFAULT_PARAMS
from config.csv_config_loader import create_csv_config
from config.path_manager import get_path_manager


class LudinggongSignalAnalyzer:
    """鹿鼎公信号诊断器 — 逐条件打印决策过程"""

    def __init__(self):
        self.config = None
        self.data_service = None
        self.signal_generator = None
        self.dcf_values = {}
        self.logger = self._setup_logging()

    def _setup_logging(self):
        logging.basicConfig(
            level=logging.WARNING,
            format='%(message)s',
            handlers=[logging.StreamHandler(sys.stdout)]
        )
        return logging.getLogger(__name__)

    def load_config(self) -> bool:
        self.config = create_csv_config()
        pm = get_path_manager()
        portfolio_df = pd.read_csv(pm.get_portfolio_config_path(), encoding='utf-8-sig')
        for _, row in portfolio_df.iterrows():
            code = str(row['Stock_number']).strip()
            if code.upper() == 'CASH':
                continue
            if len(code) < 6:
                code = code.zfill(6)
            self.dcf_values[code] = float(row['DCF_value_per_share'])
        self.logger.info(f"✅ 加载 {len(self.dcf_values)} 只股票的DCF估值")
        return True

    def initialize(self) -> bool:
        self.data_service = DataService(self.config)
        if not self.data_service.initialize():
            return False
        self.signal_generator = LudinggongSignalGenerator(
            dcf_values=self.data_service.dcf_values,
            rsi_thresholds=self.data_service.rsi_thresholds,
            stock_industry_map=self.data_service.stock_industry_map,
            params=DEFAULT_PARAMS,
        )
        return True

    def get_data(self, stock_code: str, target_date: str) -> Optional[pd.DataFrame]:
        """获取到目标日期为止的周线数据"""
        end = pd.to_datetime(target_date)
        start = (end - timedelta(days=730)).strftime('%Y-%m-%d')
        end_str = end.strftime('%Y-%m-%d')

        stock_data = self.data_service._get_cached_or_fetch_data(
            stock_code=stock_code, start_date=start, end_date=end_str, freq='weekly'
        )
        if stock_data is None or stock_data.empty:
            return None
        return stock_data

    def analyze(self, stock_code: str, target_date: str) -> Optional[dict]:
        """完整诊断"""
        data = self.get_data(stock_code, target_date)
        if data is None:
            self.logger.error(f"❌ 无法获取 {stock_code} 数据")
            return None

        target = pd.to_datetime(target_date)
        available = data[data.index <= target].index
        if available.empty:
            self.logger.error(f"❌ {target_date} 之前无数据")
            return None

        analysis_date = available.max()
        idx = data.index.get_loc(analysis_date)
        row = data.iloc[idx]
        close = float(row['close'])

        # DCF & 估值
        dcf = self.dcf_values.get(stock_code)
        if dcf is None or dcf <= 0:
            self.logger.error(f"❌ 缺少 {stock_code} DCF估值")
            return None
        value_ratio = close / dcf

        # 行业RSI阈值
        th = self.signal_generator._get_industry_thresholds(stock_code)

        # 估值区间
        zone_name, zone_max_ratio, permission = self.signal_generator.get_valuation_zone(value_ratio)

        # 技术指标
        rsi = float(row.get('rsi', np.nan))
        rsi = rsi if not pd.isna(rsi) else 50
        macd_dif = float(row.get('macd', np.nan))
        macd_dif = macd_dif if not pd.isna(macd_dif) else 0
        macd_dea = float(row.get('macd_signal', np.nan))
        macd_dea = macd_dea if not pd.isna(macd_dea) else 0
        macd_histogram = float(row.get('macd_histogram', np.nan))
        macd_histogram = macd_histogram if not pd.isna(macd_histogram) else 0
        bb_upper = float(row.get('bb_upper', np.nan))
        bb_upper = bb_upper if not pd.isna(bb_upper) else close
        bb_mid = float(row.get('bb_middle', np.nan))
        bb_mid = bb_mid if not pd.isna(bb_mid) else close
        bb_lower = float(row.get('bb_lower', np.nan))
        bb_lower = bb_lower if not pd.isna(bb_lower) else close
        volume = float(row.get('volume', np.nan))
        volume = volume if not pd.isna(volume) else 0
        bandwidth = float(row.get('boll_bandwidth', np.nan))
        bandwidth = bandwidth if not pd.isna(bandwidth) else 0.1 * close

        # 前一周期指标
        prev_row = None
        if idx > 0:
            prev_row = data.iloc[idx - 1]

        # 回看计算底部状态（模拟状态追踪器）
        was_oversold = False
        was_vol_dried = False
        was_rsi_oversold = False
        for i in range(idx - 1, max(0, idx - 20), -1):
            prev_rw = data.iloc[i]
            pc = float(prev_rw['close'])
            pl = float(prev_rw['bb_lower']) if not pd.isna(prev_rw.get('bb_lower')) else pc
            if pc <= pl:
                # 从第一次跌破下轨的位置继续回看，找量能和RSI信号
                for j in range(i, max(0, idx - 20), -1):
                    pr = data.iloc[j]
                    pv5 = float(pr.get('vol_ma5', 0)) if not pd.isna(pr.get('vol_ma5')) else 0
                    pv20 = float(pr.get('vol_ma20', 0)) if not pd.isna(pr.get('vol_ma20')) else 0
                    if pv5 < pv20:
                        was_vol_dried = True
                    prsi = float(pr.get('rsi', np.nan))
                    prsi = prsi if not pd.isna(prsi) else 50
                    if prsi < th['os']:
                        was_rsi_oversold = True
                was_oversold = True
                break

        # 运行真实检测
        result = self.signal_generator.check_zone_and_signal(
            stock_code, data, idx,
            was_oversold=was_oversold,
            was_vol_dried=was_vol_dried,
            was_rsi_oversold=was_rsi_oversold,
        )

        return {
            'stock_code': stock_code,
            'analysis_date': analysis_date.strftime('%Y-%m-%d'),
            'target_date': target_date,
            'close': close, 'dcf': dcf, 'value_ratio': value_ratio,
            'was_oversold': was_oversold, 'was_vol_dried': was_vol_dried,
            'was_rsi_oversold': was_rsi_oversold,
            'zone_name': zone_name, 'zone_max_ratio': zone_max_ratio,
            'permission': permission,
            'th': th, 'rsi': rsi, 'macd_dif': macd_dif, 'macd_dea': macd_dea,
            'macd_histogram': macd_histogram, 'bb_upper': bb_upper, 'bb_mid': bb_mid,
            'bb_lower': bb_lower, 'volume': volume, 'bandwidth': bandwidth,
            'result': result, 'row': row, 'prev_row': prev_row,
            'data': data, 'idx': idx,
        }

    def print_report(self, r: dict):
        """打印完整诊断报告"""
        result = r['result']
        symbol = r['stock_code']
        print()
        print("╔" + "═" * 68 + "╗")
        print(f"║  鹿鼎公信号诊断 — {symbol} @ {r['analysis_date']} (目标: {r['target_date']})")
        print("╚" + "═" * 68 + "╝")

        # ── 第一层：估值区间 ──
        print(f"\n{'─'*60}")
        print("第一层：估值区间 → 定操作权限")
        print(f"{'─'*60}")
        print(f"  当前价格:   {r['close']:.2f} 元")
        print(f"  DCF估值:    {r['dcf']:.2f} 元")
        print(f"  价值比:     {r['value_ratio']:.2%}")
        print(f"  估值区间:   {r['zone_name']}  (仓位上限={r['zone_max_ratio']:.0%} × 单票分配额)")
        print(f"  操作权限:   {r['permission']}  ", end='')
        perm_desc = {
            'buy_only': '⚠️ 只允许买入（极度低估，禁止卖出）',
            'buy_sell': '✅ 允许买卖',
            'sell_only': '⚠️ 只允许卖出（合理偏高/高估，禁止买入）',
        }
        print(perm_desc.get(r['permission'], ''))

        # ── 行业RSI阈值 ──
        print(f"\n{'─'*60}")
        print("行业RSI阈值")
        print(f"{'─'*60}")
        print(f"  超卖/超买:  {r['th']['os']:.1f} / {r['th']['ob']:.1f}")
        print(f"  极端阈值:   {r['th']['ext_os']:.1f} / {r['th']['ext_ob']:.1f}")

        # ── 第二层：区域判定 ──
        print(f"\n{'─'*60}")
        print("第二层：价格+RSI → 定区域（按 Zone3→2→1 顺序检测）")
        print(f"{'─'*60}")

        self._print_zone3_check(r)
        self._print_zone2_check(r)
        self._print_zone1_check(r)

        # ── 综合结论 ──
        print(f"\n{'─'*60}")
        print("综合结论")
        print(f"{'─'*60}")
        signal = result.signal
        icon = {'BUY': '🟢', 'SELL': '🔴', 'HOLD': '⚪'}.get(signal, '❓')
        print(f"  信号:       {icon} {signal}")
        print(f"  区域:       {result.zone}")
        print(f"  原因:       {result.reason}")

        if signal == 'BUY':
            print(f"  买入级别:   {result.buy_level} (买入系数={result.buy_pct:.0%})")
        elif signal == 'SELL':
            print(f"  卖出步骤:   {result.sell_step} (卖出比例={result.sell_pct:.0%})")
        else:
            print(f"  → 无交易触发")

        # ── 技术指标快照 ──
        print(f"\n{'─'*60}")
        print("技术指标快照 (当前周)")
        print(f"{'─'*60}")
        print(f"  RSI(14):         {r['rsi']:.1f}")
        print(f"  MACD DIF/DEA:    {r['macd_dif']:.4f} / {r['macd_dea']:.4f}")
        print(f"  MACD 柱:         {r['macd_histogram']:.4f}  ", end='')
        if r['macd_histogram'] > 0:
            print("(红柱)")
        elif r['macd_histogram'] < 0:
            print("(绿柱)")
        else:
            print("(零)")
        print(f"  布林上/中/下:    {r['bb_upper']:.2f} / {r['bb_mid']:.2f} / {r['bb_lower']:.2f}")
        print(f"  成交量:          {r['volume']:,.0f}")

        # ── 最近几周数据 ──
        self._print_recent_bars(r['data'], r['idx'], r['close'])

        print(f"\n{'═'*70}")
        print()

    def _check(self, label: str, ok: bool, detail: str = ""):
        mark = "✅" if ok else "❌"
        return f"    {mark} {label}: {detail}"

    def _print_zone3_check(self, r: dict):
        """打印亢奋区检测详情"""
        idx = r['idx']
        data = r['data']
        row = data.iloc[idx]
        result = r['result']

        is_zone3 = result.zone == 'zone3_excited'
        print(f"\n  [Zone3 亢奋区] {'← 命中!' if is_zone3 else ''}")
        permission = r['permission']

        # 估值卖出权限：极度低估 禁止卖出
        if permission == 'buy_only':
            print(self._check('卖出权限', False, '估值极度低估，禁止卖出（buy_only）'))
            print(f"    → Zone3 跳过（估值权限不足）")
            return

        print(self._check('卖出权限', True, f'permission={permission}'))

        # 价格条件
        close = float(row['close'])
        bb_upper = float(row['bb_upper']) if not pd.isna(row.get('bb_upper')) else close
        price_near = close >= bb_upper * 0.95
        print(self._check('价格接近上轨', price_near,
                          f'close={close:.2f} >= 0.95×bb_upper={bb_upper*0.95:.2f}'))

        # RSI超买
        rsi = float(row.get('rsi', np.nan))
        rsi = rsi if not pd.isna(rsi) else 50
        ob = r['th']['ob']
        ext_ob = r['th']['ext_ob']
        rsi_over = rsi >= ob
        rsi_ext = rsi >= ext_ob
        print(self._check('RSI超买', rsi_over,
                          f'RSI={rsi:.1f} >= ob={ob:.0f} (极端={ext_ob:.0f}){" ⚡极端!" if rsi_ext else ""}'))

        # MACD卖出扳机
        if idx > 0:
            prev = data.iloc[idx - 1]
            macd_dif = float(row.get('macd', np.nan))
            macd_dif = macd_dif if not pd.isna(macd_dif) else 0
            macd_dea = float(row.get('macd_signal', np.nan))
            macd_dea = macd_dea if not pd.isna(macd_dea) else 0
            prev_dif = float(prev.get('macd', np.nan))
            prev_dif = prev_dif if not pd.isna(prev_dif) else 0
            prev_dea = float(prev.get('macd_signal', np.nan))
            prev_dea = prev_dea if not pd.isna(prev_dea) else 0
            death_cross = (prev_dif >= prev_dea) and (macd_dif < macd_dea)

            from indicators.divergence import detect_macd_bearish_divergence
            close_series = data['close'].iloc[:idx + 1]
            dif_series = data['macd'].iloc[:idx + 1]
            bear_div = detect_macd_bearish_divergence(close_series, dif_series, order=5)

            hist_shrink = False
            if idx >= 2:
                hist_0 = float(data.iloc[idx].get('macd_histogram', np.nan))
                hist_0 = hist_0 if not pd.isna(hist_0) else 0
                hist_1 = float(data.iloc[idx - 1].get('macd_histogram', np.nan))
                hist_1 = hist_1 if not pd.isna(hist_1) else 0
                hist_2 = float(data.iloc[idx - 2].get('macd_histogram', np.nan))
                hist_2 = hist_2 if not pd.isna(hist_2) else 0
                if hist_2 > 0 and hist_1 > 0 and hist_0 > 0:
                    hist_shrink = hist_0 < hist_1

            trigger = any([
                rsi_ext,
                death_cross,
                bear_div,
                hist_shrink,
                (price_near and rsi_over and (macd_dif > 0 and macd_dif < macd_dea)),
            ])

            print(self._check('MACD死叉', death_cross,
                              f'prev DIF={prev_dif:.4f}>{prev_dea:.4f} → DIF={macd_dif:.4f}<DEA={macd_dea:.4f}'))
            print(self._check('MACD顶背离', bear_div, ''))
            print(self._check('红柱缩短', hist_shrink, ''))
            print(f"    → Zone3 综合触发: {'✅' if trigger else '❌'}")

            if not is_zone3 and rsi_over and trigger:
                print(f"    ⚠️ 注意: 条件满足但结果不是zone3，检查 has_pre_sold/has_first_sold 状态")

    def _print_zone2_check(self, r: dict):
        """打印蓄力区检测详情"""
        idx = r['idx']
        data = r['data']
        row = data.iloc[idx]
        result = r['result']
        permission = r['permission']

        is_zone2 = result.zone == 'zone2_accumulate'
        print(f"\n  [Zone2 蓄力区] {'← 命中!' if is_zone2 else ''}")

        if permission not in ('buy_only', 'buy_sell'):
            print(self._check('买入权限', False, f'permission={permission} (只有 buy_only/buy_sell 可买入)'))
            print(f"    → Zone2 跳过（估值权限不足）")
            return

        print(self._check('买入权限', True, f'permission={permission}'))

        close = float(row['close'])
        bb_mid = r['bb_mid']
        bandwidth = r['bandwidth']
        price_mid = abs(close - bb_mid) < 0.075 * bandwidth if bandwidth > 0 else False
        print(self._check('价格中轨附近', price_mid,
                          f'|close-中轨|={abs(close-bb_mid):.2f} < {0.075*bandwidth:.2f}'))

        rsi = r['rsi']
        os, ob = r['th']['os'], r['th']['ob']
        rsi_ok = os < rsi < ob
        print(self._check('RSI均衡区', rsi_ok, f'RSI={rsi:.1f} ∈ ({os:.0f}, {ob:.0f})'))

        macd_dif = r['macd_dif']
        zero_near = abs(macd_dif) / close < 0.01 if close > 0 else False
        print(self._check('零轴附近', zero_near, f'|DIF|/close={abs(macd_dif)/close:.4f} < 1%'))

        if idx > 0:
            prev = data.iloc[idx - 1]
            prev_dif = float(prev.get('macd', np.nan))
            prev_dif = prev_dif if not pd.isna(prev_dif) else 0
            prev_dea = float(prev.get('macd_signal', np.nan))
            prev_dea = prev_dea if not pd.isna(prev_dea) else 0
            golden = (prev_dif <= prev_dea) and (macd_dif > r['macd_dea'])
            print(self._check('MACD金叉', golden,
                              f'prev DIF={prev_dif:.4f}<={prev_dea:.4f} → DIF={macd_dif:.4f}>DEA={r["macd_dea"]:.4f}'))

            trigger = price_mid and rsi_ok and zero_near and golden
            print(f"    → Zone2 综合触发: {'✅' if trigger else '❌'}")

    def _print_zone1_check(self, r: dict):
        """打印止跌区检测详情"""
        idx = r['idx']
        data = r['data']
        row = data.iloc[idx]
        result = r['result']
        permission = r['permission']

        is_zone1 = result.zone == 'zone1_stop_falling'
        print(f"\n  [Zone1 止跌区] {'← 命中!' if is_zone1 else ''}")

        if permission not in ('buy_only', 'buy_sell'):
            print(self._check('买入权限', False, f'permission={permission}'))
            print(f"    → Zone1 跳过（估值权限不足）")
            return

        print(self._check('买入权限', True, f'permission={permission}'))

        close = float(row['close'])
        bb_lower = r['bb_lower']
        os = r['th']['os']
        ext_os = r['th']['ext_os']

        price_ok = False
        rsi_ok = False
        vol_ok = False
        rsi_extreme = False

        if idx > 0:
            prev = data.iloc[idx - 1]
            # 查找最近一次跌破下轨的周，判断是否处于曾超跌状态
            was_oversold = False
            for i in range(idx - 1, max(0, idx - 20), -1):
                prev_rw = data.iloc[i]
                pc = float(prev_rw['close'])
                pl = float(prev_rw['bb_lower']) if not pd.isna(prev_rw.get('bb_lower')) else pc
                if pc <= pl:
                    was_oversold = True
                    break
            price_ok = was_oversold and (close > bb_lower)
            print(self._check('价格站回下轨', price_ok,
                              f'曾超跌={was_oversold} 且 close={close:.2f}>lower={bb_lower:.2f}'))

            rsi_ok = r.get('was_rsi_oversold', False)
            print(self._check('RSI曾超卖', rsi_ok,
                              f'曾进入超卖区(RSI<{os:.1f})={rsi_ok}'))

            # 量能：超跌期间曾出现MA5<MA20 且 本周量<近4周最大量
            was_vol_dried = r.get('was_vol_dried', False)
            vol_4w_max = float(row.get('vol_4w_max', np.nan))
            vol_4w_max = vol_4w_max if not pd.isna(vol_4w_max) else float('inf')
            volume_now = r['volume']
            vol_ok = was_vol_dried and (volume_now < vol_4w_max)
            print(self._check('量能枯竭', vol_ok,
                              f'曾枯竭={was_vol_dried} 且 vol={volume_now:.0f}<4W_max={vol_4w_max:.0f}'))

            # MACD扳机
            prev_dif = float(prev.get('macd', np.nan))
            prev_dif = prev_dif if not pd.isna(prev_dif) else 0
            prev_dea = float(prev.get('macd_signal', np.nan))
            prev_dea = prev_dea if not pd.isna(prev_dea) else 0
            golden = (prev_dif < prev_dea) and (r['macd_dif'] > r['macd_dea'])

            from indicators.divergence import detect_macd_bullish_divergence
            close_series = data['close'].iloc[:idx + 1]
            hist_series = data['macd_histogram'].iloc[:idx + 1]
            bull_div = detect_macd_bullish_divergence(close_series, hist_series, order=5)

            hist_now = float(row.get('macd_histogram', np.nan))
            hist_now = hist_now if not pd.isna(hist_now) else 0
            hist_prev = float(prev.get('macd_histogram', np.nan))
            hist_prev = hist_prev if not pd.isna(hist_prev) else 0
            hist_shrinking = (hist_now < 0) and (hist_now > hist_prev)

            dif_decel = False
            if idx >= 2:
                prev2 = data.iloc[idx - 2]
                dif_prev2 = float(prev2.get('macd', np.nan))
                dif_prev2 = dif_prev2 if not pd.isna(dif_prev2) else 0
                dif_delta = r['macd_dif'] - prev_dif
                dif_delta_prev = prev_dif - dif_prev2
                dif_decel = dif_delta > dif_delta_prev

            hist_confirmed = hist_shrinking and dif_decel

            print(self._check('MACD金叉', golden,
                              f'prev DIF={prev_dif:.4f}<{prev_dea:.4f} → DIF={r["macd_dif"]:.4f}>DEA={r["macd_dea"]:.4f}'))
            print(self._check('MACD底背离', bull_div, ''))
            print(self._check('绿柱缩短', hist_shrinking,
                              f'hist={hist_now:.4f} > 前周={hist_prev:.4f}'))
            print(self._check('DIF跌速放缓', dif_decel,
                              f'ΔDIF={r["macd_dif"]-prev_dif:.4f} > 前周ΔDIF={prev_dif-dif_prev2:.4f}'))
            print(self._check('绿柱缩短+DIF减速', hist_confirmed, ''))

            trigger = price_ok and rsi_ok and vol_ok and (golden or bull_div or hist_confirmed)
            print(f"    → Zone1 综合触发: {'✅' if trigger else '❌'}")

            if trigger and not is_zone1:
                print(f"    ⚠️ Zone1条件满足但结果不是zone1，可能是Zone3/Zone2优先命中了")

    def _print_recent_bars(self, data: pd.DataFrame, idx: int, current_close: float):
        """打印最近几周的K线和指标摘要"""
        print(f"\n{'─'*60}")
        print("最近几周数据")
        print(f"{'─'*60}")
        start_i = max(0, idx - 4)
        header = f"  {'周':<12} {'收盘':>8} {'RSI':>6} {'DIF':>8} {'DEA':>8} {'HIST':>8} {'布林下':>8} {'布林中':>8} {'布林上':>8}"
        print(header)
        print("  " + "-" * len(header))
        for i in range(start_i, idx + 1):
            rw = data.iloc[i]
            c = float(rw['close'])
            marker = " ←" if i == idx else ""
            rsi_v = float(rw.get('rsi', np.nan))
            rsi_v = rsi_v if not pd.isna(rsi_v) else 0
            dif = float(rw.get('macd', np.nan))
            dif = dif if not pd.isna(dif) else 0
            dea = float(rw.get('macd_signal', np.nan))
            dea = dea if not pd.isna(dea) else 0
            hist = float(rw.get('macd_histogram', np.nan))
            hist = hist if not pd.isna(hist) else 0
            bl = float(rw.get('bb_lower', np.nan))
            bl = bl if not pd.isna(bl) else 0
            bm = float(rw.get('bb_middle', np.nan))
            bm = bm if not pd.isna(bm) else 0
            bu = float(rw.get('bb_upper', np.nan))
            bu = bu if not pd.isna(bu) else 0
            date_s = str(data.index[i])[:10]
            print(f"  {date_s:<12} {c:>8.2f} {rsi_v:>6.1f} {dif:>8.4f} {dea:>8.4f} {hist:>8.4f} {bl:>8.2f} {bm:>8.2f} {bu:>8.2f}{marker}")
        print()


def parse_args():
    p = argparse.ArgumentParser(
        description='鹿鼎公信号诊断工具 — 逐层展示信号决策过程',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
示例:
  python3 analyze_ludinggong_signal.py -s 601225 -d 2025-02-28
  python3 analyze_ludinggong_signal.py --stock 002555 --date 2025-01-15
        """
    )
    p.add_argument('-s', '--stock', required=True, help='股票代码')
    p.add_argument('-d', '--date', required=True, help='分析日期 YYYY-MM-DD')
    return p.parse_args()


def main():
    args = parse_args()
    try:
        pd.to_datetime(args.date)
    except Exception:
        print(f"❌ 无效日期: {args.date}")
        return 1

    a = LudinggongSignalAnalyzer()
    if not a.load_config():
        return 1
    if not a.initialize():
        return 1

    r = a.analyze(args.stock, args.date)
    if r is None:
        return 1
    a.print_report(r)
    return 0


if __name__ == '__main__':
    exit(main())
