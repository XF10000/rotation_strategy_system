"""
信号服务 - 鹿鼎公策略
负责基于估值区间→价格/RSI→MACD的三层递进信号生成
"""

from typing import Any, Dict, List, Optional

import pandas as pd

from strategy.ludinggong_signal import DEFAULT_PARAMS, LudinggongSignalGenerator, ZoneResult

from .base_service import BaseService


class SignalService(BaseService):
    """
    信号服务 - 鹿鼎公区域信号生成

    职责：
    1. 对每只股票进行区域判定和扳机检测
    2. 记录信号详情供交易执行和报告使用
    """

    def __init__(self, config: Dict[str, Any], dcf_values: Dict[str, float],
                 rsi_thresholds: Dict[str, Dict[str, float]],
                 stock_industry_map: Dict[str, Dict[str, str]],
                 stock_pool: List[str],
                 state_tracker=None,
                 signal_tracker=None):
        super().__init__(config)

        self.dcf_values = dcf_values
        self.rsi_thresholds = rsi_thresholds
        self.stock_industry_map = stock_industry_map
        self.stock_pool = stock_pool
        self.state_tracker = state_tracker
        self.signal_tracker = signal_tracker

        self.signal_generator = None
        self.signal_details = {}

    def initialize(self) -> bool:
        try:
            strategy_params = self.config.get('strategy_params', {})
            params = {**DEFAULT_PARAMS, **strategy_params}

            self.signal_generator = LudinggongSignalGenerator(
                self.dcf_values,
                self.rsi_thresholds,
                self.stock_industry_map,
                params
            )

            self._initialized = True
            self.logger.info("SignalService (鹿鼎公) 初始化成功")
            return True
        except Exception as e:
            self.logger.error(f"SignalService 初始化失败: {e}")
            return False

    def generate_signals(self, stock_data: Dict[str, Dict[str, pd.DataFrame]],
                         current_date: pd.Timestamp) -> Dict[str, str]:
        """
        生成交易信号 — 鹿鼎公区域状态机

        对每只股票调用 check_zone_and_signal()，返回 BUY/SELL/HOLD。
        """
        signals = {}

        for stock_code in self.stock_pool:
            if stock_code not in stock_data:
                continue

            stock_weekly = stock_data[stock_code]['weekly']
            if current_date not in stock_weekly.index:
                continue

            current_idx = stock_weekly.index.get_loc(current_date)
            if current_idx < 20:
                continue

            # 获取该股票的交易回合状态
            has_pre_sold = False
            has_first_sold = False
            was_oversold = False
            was_vol_dried = False
            was_rsi_oversold = False
            if self.state_tracker:
                state = self.state_tracker.get_state(stock_code)
                has_pre_sold = state.has_pre_sold
                has_first_sold = state.has_first_sold
                was_oversold = state.was_oversold
                was_vol_dried = state.vol_dried_up
                was_rsi_oversold = state.was_rsi_oversold

            try:
                zone_result = self.signal_generator.check_zone_and_signal(
                    stock_code,
                    stock_weekly,
                    current_idx,
                    has_pre_sold=has_pre_sold,
                    has_first_sold=has_first_sold,
                    was_oversold=was_oversold,
                    was_vol_dried=was_vol_dried,
                    was_rsi_oversold=was_rsi_oversold,
                )

                # 更新超跌状态
                if self.state_tracker:
                    row = stock_weekly.iloc[current_idx]
                    close_val = float(row['close'])
                    bb_lower_val = float(row['bb_lower']) if not pd.isna(row.get('bb_lower')) else close_val
                    bb_mid_val = float(row['bb_middle']) if not pd.isna(row.get('bb_middle')) else close_val
                    rsi_val = float(row['rsi']) if not pd.isna(row.get('rsi')) else 50

                    # 进入超跌：价格跌破下轨
                    if close_val <= bb_lower_val:
                        self.state_tracker.set_oversold(stock_code)

                    # 退出超跌窗口：价格回到中轨上方
                    if close_val >= bb_mid_val:
                        self.state_tracker.reset_bottom_window(stock_code)
                    else:
                        current_state = self.state_tracker.get_state(stock_code)
                        if current_state.was_oversold:
                            # 超跌期间检测量能枯竭
                            vol_ma5 = float(row.get('vol_ma5', 0)) if not pd.isna(row.get('vol_ma5')) else 0
                            vol_ma20 = float(row.get('vol_ma20', 0)) if not pd.isna(row.get('vol_ma20')) else 0
                            if vol_ma5 < vol_ma20:
                                self.state_tracker.set_vol_dried_up(stock_code)

                            # 超跌期间检测RSI超卖
                            th = self.signal_generator._get_industry_thresholds(stock_code)
                            if rsi_val < th['os']:
                                self.state_tracker.set_rsi_oversold(stock_code)

                if zone_result.signal in ('BUY', 'SELL'):
                    signals[stock_code] = zone_result.signal

                    # 记录到 signal_tracker（简化格式）
                    if self.signal_tracker:
                        self._record_to_tracker(stock_code, current_date, zone_result,
                                                stock_weekly, current_idx)

                # 始终存储详情供 portfolio_service 使用
                key = f"{stock_code}_{current_date.strftime('%Y-%m-%d')}"
                self.signal_details[key] = zone_result

            except Exception as e:
                self.logger.error(f"{stock_code} 信号生成失败: {e}")

        return signals

    def _record_to_tracker(self, stock_code: str, current_date: pd.Timestamp,
                           zone_result: ZoneResult, weekly_data: pd.DataFrame,
                           current_idx: int):
        """将 ZoneResult 转为 signal_tracker 兼容格式并记录"""
        try:
            row = weekly_data.iloc[current_idx]
            close = float(row['close'])
            dcf = self.dcf_values.get(stock_code, 0)
            value_ratio = close / dcf if dcf and dcf > 0 else 1.0
            rsi = float(row['rsi']) if not pd.isna(row.get('rsi')) else 50

            signal_result = {
                'signal': zone_result.signal,
                'zone': zone_result.zone,
                'buy_level': zone_result.buy_level,
                'sell_step': zone_result.sell_step,
                'valuation_zone': zone_result.valuation_zone,
                'permission': zone_result.permission,
                'reason': zone_result.reason,
                'confidence': 3,  # 鹿鼎公信号强度固定为3（区域确认）
                'dcf_value': dcf,
                'value_price_ratio': value_ratio,
                'current_price': close,
                'scores': {
                    'trend_filter_low': zone_result.signal == 'BUY',
                    'trend_filter_high': zone_result.signal == 'SELL',
                    'overbought_oversold_low': zone_result.signal == 'BUY',
                    'momentum_low': zone_result.signal == 'BUY',
                    'extreme_price_volume_low': zone_result.signal == 'BUY',
                    'overbought_oversold_high': zone_result.signal == 'SELL',
                    'momentum_high': zone_result.signal == 'SELL',
                    'extreme_price_volume_high': zone_result.signal == 'SELL',
                },
                'technical_indicators': {
                    'rsi_14w': rsi,
                    'close': close,
                    'macd_dif': float(row.get('macd', 0)) if not pd.isna(row.get('macd')) else 0,
                    'macd_dea': float(row.get('macd_signal', 0)) if not pd.isna(row.get('macd_signal')) else 0,
                    'macd_hist': float(row.get('macd_histogram', 0)) if not pd.isna(row.get('macd_histogram')) else 0,
                    'bb_upper': float(row.get('bb_upper', close)) if not pd.isna(row.get('bb_upper')) else close,
                    'bb_middle': float(row.get('bb_middle', close)) if not pd.isna(row.get('bb_middle')) else close,
                    'bb_lower': float(row.get('bb_lower', close)) if not pd.isna(row.get('bb_lower')) else close,
                    'volume': float(row.get('volume', 0)) if not pd.isna(row.get('volume')) else 0,
                },
                'detailed_info': {
                    'industry_name': self.stock_industry_map.get(stock_code, {}).get('industry_name', ''),
                },
                'rsi_thresholds': self.rsi_thresholds.get(
                    self.stock_industry_map.get(stock_code, {}).get('industry_code', ''), {}
                ),
            }

            self.signal_tracker.record_signal({
                'date': current_date,
                'stock_code': stock_code,
                'signal_result': signal_result,
            })
        except Exception as e:
            self.logger.debug(f"记录signal_tracker失败 {stock_code}: {e}")

    def get_signal_details(self, stock_code: str, stock_data: pd.DataFrame,
                           current_date: pd.Timestamp) -> Optional[Dict]:
        """获取指定日期的信号详情"""
        try:
            key = f"{stock_code}_{current_date.strftime('%Y-%m-%d')}"
            zone_result = self.signal_details.get(key)
            if zone_result is None:
                return None

            return {
                'signal_type': zone_result.signal,
                'zone': zone_result.zone,
                'valuation_zone': zone_result.valuation_zone,
                'permission': zone_result.permission,
                'buy_level': zone_result.buy_level,
                'sell_step': zone_result.sell_step,
                'trigger_reason': zone_result.reason,
            }
        except Exception as e:
            self.logger.error(f"获取信号详情失败: {e}")
            return None

    def get_signal_statistics(self, transaction_history: pd.DataFrame) -> Dict[str, Any]:
        """获取信号统计"""
        try:
            buy_signals = transaction_history[transaction_history['trade_type'] == 'buy'] if 'trade_type' in transaction_history.columns else pd.DataFrame()
            sell_signals = transaction_history[transaction_history['trade_type'] == 'sell'] if 'trade_type' in transaction_history.columns else pd.DataFrame()

            stock_signals = {}
            for _, row in transaction_history.iterrows():
                code = row.get('stock_code', '')
                if code:
                    if code not in stock_signals:
                        stock_signals[code] = {'buy_count': 0, 'sell_count': 0}
                    action = row.get('action', row.get('type', ''))
                    if action in ('buy', 'BUY'):
                        stock_signals[code]['buy_count'] += 1
                    elif action in ('sell', 'SELL'):
                        stock_signals[code]['sell_count'] += 1

            return {
                'global_stats': {
                    'total_buy_signals': len(buy_signals),
                    'total_sell_signals': len(sell_signals),
                    'total_signals': len(transaction_history),
                },
                'stock_signals': stock_signals,
            }
        except Exception as e:
            self.logger.error(f"信号统计分析失败: {e}")
            return {}
