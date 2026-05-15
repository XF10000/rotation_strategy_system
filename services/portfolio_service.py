"""
投资组合服务 - 鹿鼎公策略
估值定仓位上限 + 分批建仓 + 步进止盈
"""

from typing import Any, Dict, List, Optional

import pandas as pd

from backtest.portfolio_manager import PortfolioManager
from strategy.ludinggong_position import LudinggongPositionManager, TradeDecision
from strategy.ludinggong_state import LudinggongStateTracker

from .base_service import BaseService


class PortfolioService(BaseService):
    """
    投资组合服务 - 鹿鼎公仓位管理与交易执行

    职责：
    1. 持仓管理（复用 PortfolioManager）
    2. 使用 LudinggongPositionManager 计算买卖数量
    3. 使用 LudinggongStateTracker 追踪交易回合状态
    4. 分红配股处理
    """

    def __init__(self, config: Dict[str, Any], dcf_values: Dict[str, float],
                 state_tracker: LudinggongStateTracker = None,
                 signal_tracker=None):
        super().__init__(config)

        self.dcf_values = dcf_values
        self.state_tracker = state_tracker or LudinggongStateTracker()
        self.signal_tracker = signal_tracker

        self.total_capital = config.get('total_capital', 1000000)
        self.initial_holdings = config.get('initial_holdings', {})

        self.portfolio_manager = None
        self.position_manager = None

        self.transaction_history = []
        self.stock_pool = [code for code in self.initial_holdings.keys() if code != 'cash']

    def initialize(self, stock_data: Dict[str, Dict[str, pd.DataFrame]],
                   start_date: pd.Timestamp,
                   dcf_values: Dict[str, float],
                   signal_tracker=None) -> bool:
        try:
            self.dcf_values = dcf_values
            self.signal_tracker = signal_tracker

            # 创建鹿鼎公仓位管理器
            strategy_params = self.config.get('strategy_params', {})
            max_single_ratio = strategy_params.get('max_single_stock_ratio', 0.20)
            self.position_manager = LudinggongPositionManager(
                total_capital=self.total_capital,
                max_single_stock_ratio=max_single_ratio,
                params=strategy_params,
            )

            # 创建交易成本计算器
            from backtest.transaction_cost import TransactionCostCalculator
            cost_config = self.config.get('cost_config', {
                'commission_rate': 0.0003,
                'min_commission': 5.0,
                'stamp_duty_rate': 0.001,
                'transfer_fee_rate': 0.00002,
            })
            self.cost_calculator = TransactionCostCalculator(cost_config)

            return self.initialize_portfolio(stock_data, start_date)

        except Exception as e:
            self.logger.error(f"服务初始化失败: {e}")
            return False

    def initialize_portfolio(self, stock_data: Dict[str, Dict[str, pd.DataFrame]],
                             start_date: pd.Timestamp) -> bool:
        try:
            initial_prices = {}
            for stock_code in self.stock_pool:
                if stock_code in stock_data:
                    stock_weekly = stock_data[stock_code]['weekly']
                    backtest_data = stock_weekly[stock_weekly.index >= start_date]
                    if not backtest_data.empty:
                        initial_prices[stock_code] = backtest_data.iloc[0]['close']

            holdings = {}
            total_stock_value = 0.0

            for stock_code in self.stock_pool:
                if stock_code in self.initial_holdings and stock_code in initial_prices:
                    weight = self.initial_holdings[stock_code]
                    if weight <= 0:
                        continue
                    target_stock_value = self.total_capital * weight
                    price = initial_prices[stock_code]
                    shares = int(target_stock_value / price / 100) * 100
                    if shares > 0:
                        holdings[stock_code] = shares
                        total_stock_value += shares * price

            initial_cash = self.total_capital - total_stock_value

            self.portfolio_manager = PortfolioManager(
                total_capital=self.total_capital,
                initial_holdings={},
            )
            if hasattr(self, 'cost_calculator'):
                self.portfolio_manager.cost_calculator = self.cost_calculator

            self.portfolio_manager.holdings = holdings.copy()
            self.portfolio_manager.cash = initial_cash
            self.portfolio_manager.initial_prices = initial_prices.copy()

            # 初始化交易回合状态：已有持仓的股票标记为活跃回合
            for stock_code in holdings:
                if holdings[stock_code] > 0:
                    state = self.state_tracker.get_state(stock_code)
                    if not state.transaction_round_active:
                        price = initial_prices.get(stock_code, 0)
                        self.state_tracker.start_new_round(stock_code, price, start_date)

            self._initialized = True
            self.logger.info(f"PortfolioService (鹿鼎公) 初始化完成: "
                            f"总资产 {self.total_capital:,.0f}, "
                            f"{len(holdings)} 只持仓, 现金 {initial_cash:,.0f}")
            return True

        except Exception as e:
            self.logger.error(f"投资组合初始化失败: {e}")
            return False

    def execute_trades(self, signals: Dict[str, str],
                       stock_data: Dict[str, Dict[str, pd.DataFrame]],
                       current_date: pd.Timestamp,
                       signal_details: Dict = None) -> List[str]:
        """
        执行交易 — 鹿鼎公分批建仓+步进止盈

        signal_details: {stock_code: ZoneResult}
        """
        executed_trades = []

        current_prices = {}
        for stock_code in self.stock_pool:
            if stock_code in stock_data:
                stock_weekly = stock_data[stock_code]['weekly']
                if current_date in stock_weekly.index:
                    current_prices[stock_code] = stock_weekly.loc[current_date, 'close']

        # 每周更新仓位锚定点为当前总资产
        total_value = self.portfolio_manager.get_total_value(current_prices)
        self.position_manager.update_total_capital(total_value)

        # 先卖出（释放现金），再买入
        for stock_code, signal in signals.items():
            if signal == 'SELL' and stock_code in current_prices:
                trade_info = self._execute_sell(
                    stock_code, current_prices, current_date, signal_details
                )
                if trade_info:
                    executed_trades.append(trade_info)

        for stock_code, signal in signals.items():
            if signal == 'BUY' and stock_code in current_prices:
                trade_info = self._execute_buy(
                    stock_code, current_prices, current_date, signal_details
                )
                if trade_info:
                    executed_trades.append(trade_info)

        return executed_trades

    def _execute_sell(self, stock_code: str, current_prices: Dict[str, float],
                      current_date: pd.Timestamp, signal_details: Dict = None) -> Optional[str]:
        current_shares = self.portfolio_manager.holdings.get(stock_code, 0)
        if current_shares <= 0:
            return None

        price = current_prices[stock_code]
        zone_result = signal_details.get(stock_code) if signal_details else None
        if zone_result is None:
            return None

        # 鹿鼎公卖出决策
        decision = self.position_manager.calculate_sell_decision(
            stock_code, price, zone_result, current_shares
        )
        decision = self.position_manager.enforce_permission(decision, zone_result)

        if decision.action != 'SELL' or decision.shares <= 0:
            if self.signal_tracker:
                self._record_rejection(stock_code, 'SELL', current_date, price,
                                       decision.reason, signal_details)
            return None

        shares_to_sell = min(decision.shares, current_shares)
        position_before = current_shares
        total_value = self.portfolio_manager.get_total_value(current_prices)
        position_weight_before = (position_before * price / total_value) if total_value > 0 else 0.0

        # 构建技术指标快照
        technical_indicators = self._build_indicator_snapshot(stock_code, price, zone_result)

        success, trade_info = self.portfolio_manager.sell_stock(
            stock_code, shares_to_sell, price, current_date, decision.reason,
            technical_indicators, {'zone_result': zone_result}
        )

        if success:
            # 更新交易回合状态
            remaining = self.portfolio_manager.holdings.get(stock_code, 0)
            self.state_tracker.record_sell(stock_code, zone_result.sell_step or '',
                                          shares_to_sell, remaining)

            # 更新 signal_tracker
            if self.signal_tracker:
                position_after = remaining
                total_value_after = self.portfolio_manager.get_total_value(current_prices)
                weight_after = (position_after * price / total_value_after) if total_value_after > 0 else 0.0
                self._update_signal_execution(
                    stock_code, 'SELL', current_date, trade_info,
                    position_before, position_after,
                    position_weight_before, weight_after,
                    signal_details
                )

            self.transaction_history.append(trade_info)
            return f"SELL {stock_code} {shares_to_sell}股 @{price:.2f}"

        return None

    def _execute_buy(self, stock_code: str, current_prices: Dict[str, float],
                     current_date: pd.Timestamp, signal_details: Dict = None) -> Optional[str]:
        price = current_prices[stock_code]
        zone_result = signal_details.get(stock_code) if signal_details else None
        if zone_result is None:
            return None

        current_shares = self.portfolio_manager.holdings.get(stock_code, 0)
        available_cash = self.portfolio_manager.cash

        # 鹿鼎公买入决策
        decision = self.position_manager.calculate_buy_decision(
            stock_code, price, zone_result, current_shares, available_cash
        )
        decision = self.position_manager.enforce_permission(decision, zone_result)

        if decision.action != 'BUY' or decision.shares <= 0:
            if self.signal_tracker:
                self._record_rejection(stock_code, 'BUY', current_date, price,
                                       decision.reason, signal_details)
            return None

        position_before = current_shares
        total_value = self.portfolio_manager.get_total_value(current_prices)
        position_weight_before = (position_before * price / total_value) if total_value > 0 else 0.0

        # 新交易回合检测
        state = self.state_tracker.get_state(stock_code)
        if current_shares == 0 and not state.transaction_round_active:
            dcf = self.dcf_values.get(stock_code, 0)
            value_ratio = price / dcf if dcf and dcf > 0 else 1.0
            if self.state_tracker.is_new_round_allowed(stock_code, value_ratio, current_shares):
                self.state_tracker.start_new_round(stock_code, price, current_date)

        # 构建技术指标快照
        technical_indicators = self._build_indicator_snapshot(stock_code, price, zone_result)

        success, trade_info = self.portfolio_manager.buy_stock(
            stock_code, decision.shares, price, current_date, decision.reason,
            technical_indicators, {'zone_result': zone_result}
        )

        if success:
            self.state_tracker.record_buy(stock_code, decision.shares)

            if self.signal_tracker:
                position_after = self.portfolio_manager.holdings.get(stock_code, 0)
                total_value_after = self.portfolio_manager.get_total_value(current_prices)
                weight_after = (position_after * price / total_value_after) if total_value_after > 0 else 0.0
                self._update_signal_execution(
                    stock_code, 'BUY', current_date, trade_info,
                    position_before, position_after,
                    position_weight_before, weight_after,
                    signal_details
                )

            self.transaction_history.append(trade_info)
            return f"BUY {stock_code} {decision.shares}股 @{price:.2f}"

        return None

    def _build_indicator_snapshot(self, stock_code: str, price: float,
                                   zone_result) -> Dict[str, Any]:
        """构建交易记录所需的技术指标快照"""
        dcf = self.dcf_values.get(stock_code, 0)
        value_ratio = price / dcf if dcf and dcf > 0 else 1.0
        return {
            'dcf_value': dcf,
            'value_price_ratio': value_ratio,
            'zone': zone_result.zone,
            'valuation_zone': zone_result.valuation_zone,
            'permission': zone_result.permission,
            'trigger_reason': zone_result.reason,
        }

    def process_dividend_events(self, stock_data: Dict[str, Dict[str, pd.DataFrame]],
                                current_date: pd.Timestamp):
        try:
            dividend_events_today = {}
            for stock_code in self.stock_pool:
                if stock_code not in stock_data:
                    continue
                stock_weekly = stock_data[stock_code]['weekly']
                if current_date in stock_weekly.index:
                    row = stock_weekly.loc[current_date]
                    has_dividend = (
                        row.get('dividend_amount', 0) > 0
                        or row.get('bonus_ratio', 0) > 0
                        or row.get('transfer_ratio', 0) > 0
                        or row.get('allotment_ratio', 0) > 0
                    )
                    if has_dividend:
                        dividend_events_today[stock_code] = row
            if dividend_events_today:
                self.portfolio_manager.process_dividend_events(current_date, dividend_events_today)
        except Exception as e:
            self.logger.warning(f"分红事件处理失败: {e}")

    def _record_rejection(self, stock_code: str, signal_type: str,
                          current_date: pd.Timestamp, price: float,
                          reason: str, signal_details: Dict = None):
        if not self.signal_tracker:
            return
        signal_id = self.signal_tracker.get_signal_id(stock_code, current_date, signal_type)
        if signal_id:
            position_before = self.portfolio_manager.holdings.get(stock_code, 0)
            current_prices = {stock_code: price}
            total_value = self.portfolio_manager.get_total_value(current_prices)
            weight_before = (position_before * price / total_value) if total_value > 0 else 0.0
            self.signal_tracker.update_execution_status(
                signal_id=signal_id,
                execution_status='未执行',
                execution_reason=reason,
                position_before_signal=position_before,
                position_weight_before=weight_before,
                trade_shares=0,
                position_after_trade=position_before,
                position_weight_after=weight_before,
            )

    def _update_signal_execution(self, stock_code: str, signal_type: str,
                                  current_date: pd.Timestamp, trade_info: Dict,
                                  position_before: int, position_after: int,
                                  weight_before: float, weight_after: float,
                                  signal_details: Dict = None):
        if not self.signal_tracker:
            return
        signal_id = self.signal_tracker.get_signal_id(stock_code, current_date, signal_type)
        if signal_id:
            self.signal_tracker.update_execution_status(
                signal_id=signal_id,
                execution_status='已执行',
                execution_date=current_date,
                execution_price=trade_info.get('price', 0),
                position_before_signal=position_before,
                position_weight_before=weight_before,
                trade_shares=trade_info.get('shares', 0),
                position_after_trade=position_after,
                position_weight_after=weight_after,
            )

    def get_portfolio_state(self, current_prices: Dict[str, float]) -> Dict[str, Any]:
        return {
            'cash': self.portfolio_manager.cash,
            'positions': self.portfolio_manager.holdings.copy(),
            'total_value': self.portfolio_manager.get_total_value(current_prices),
            'transaction_count': len(self.transaction_history),
        }

    def get_transaction_history(self) -> List[Dict]:
        return self.transaction_history.copy()
