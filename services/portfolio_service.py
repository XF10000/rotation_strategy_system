"""
投资组合服务
负责持仓管理、交易执行和投资组合状态跟踪
"""

from typing import Any, Dict, List, Optional

import pandas as pd

from backtest.portfolio_manager import PortfolioManager

from .base_service import BaseService


class PortfolioService(BaseService):
    """
    投资组合服务 - 持仓和交易管理
    
    职责：
    1. 持仓管理
    2. 交易执行（买入/卖出）
    3. 分红配股处理
    4. 投资组合状态跟踪
    """
    
    def __init__(self, config: Dict[str, Any], dcf_values: Dict[str, float],
                 signal_tracker=None):
        """
        初始化投资组合服务
        
        Args:
            config: 配置字典
            dcf_values: DCF估值数据
            signal_tracker: 信号跟踪器（可选）
        """
        super().__init__(config)
        
        self.dcf_values = dcf_values
        self.signal_tracker = signal_tracker
        
        # 配置参数
        self.total_capital = config.get('total_capital', 1000000)
        self.initial_holdings = config.get('initial_holdings', {})
        
        # 组件
        self.portfolio_manager = None
        self.portfolio_data_manager = None
        self.dynamic_position_manager = None
        
        # 交易历史
        self.transaction_history = []
        
        # 股票池
        self.stock_pool = [code for code in self.initial_holdings.keys() if code != 'cash']
    
    def initialize(self, stock_data: Dict[str, Dict[str, pd.DataFrame]], 
                  start_date: pd.Timestamp, 
                  dcf_values: Dict[str, float],
                  signal_tracker=None) -> bool:
        """
        初始化服务
        
        Args:
            stock_data: 股票数据
            start_date: 回测开始日期
            dcf_values: DCF估值数据
            signal_tracker: 信号跟踪器（可选）
            
        Returns:
            bool: 初始化是否成功
        """
        try:
            self.dcf_values = dcf_values
            self.signal_tracker = signal_tracker
            
            # 创建动态仓位管理器
            from strategy.dynamic_position_manager import DynamicPositionManager
            strategy_params = self.config.get('strategy_params', self.config)
            self.dynamic_position_manager = DynamicPositionManager(strategy_params)
            
            # 创建交易成本计算器（关键！BacktestEngine有这个）
            from backtest.transaction_cost import TransactionCostCalculator
            cost_config = self.config.get('cost_config', {
                'commission_rate': 0.0003,
                'min_commission': 5.0,
                'stamp_duty_rate': 0.001,
                'transfer_fee_rate': 0.00002
            })
            self.cost_calculator = TransactionCostCalculator(cost_config)
            
            # 初始化投资组合
            return self.initialize_portfolio(stock_data, start_date)
        
        except Exception as e:
            self.logger.error(f"服务初始化失败: {e}")
            return False
    
    def initialize_portfolio(self, stock_data: Dict[str, Dict[str, pd.DataFrame]],
                           start_date: pd.Timestamp) -> bool:
        """
        初始化投资组合
        
        Args:
            stock_data: 股票数据
            start_date: 回测开始日期
            
        Returns:
            bool: 初始化是否成功
        """
        try:
            # 获取初始价格
            initial_prices = {}
            for stock_code in self.stock_pool:
                if stock_code in stock_data:
                    stock_weekly = stock_data[stock_code]['weekly']
                    if start_date in stock_weekly.index:
                        initial_prices[stock_code] = stock_weekly.loc[start_date, 'close']
            
            # 计算持仓（与BacktestEngine保持一致）
            holdings = {}
            total_stock_value = 0.0
            
            for stock_code in self.stock_pool:
                if stock_code in self.initial_holdings and stock_code in initial_prices:
                    weight = self.initial_holdings[stock_code]
                    if weight <= 0:
                        continue
                    
                    # 计算目标股票价值
                    target_stock_value = self.total_capital * weight
                    price = initial_prices[stock_code]
                    
                    # 计算股数（向下取整到100股的整数倍）
                    shares = int(target_stock_value / price / 100) * 100
                    
                    if shares > 0:
                        holdings[stock_code] = shares
                        actual_market_value = shares * price
                        total_stock_value += actual_market_value
            
            # 计算现金
            initial_cash = self.total_capital - total_stock_value
            
            # 创建PortfolioManager（空的initial_holdings）
            self.portfolio_manager = PortfolioManager(
                total_capital=self.total_capital,
                initial_holdings={}  # 空字典，我们将直接设置计算结果
            )
            
            # 设置成本计算器（如果有）
            if hasattr(self, 'cost_calculator'):
                self.portfolio_manager.cost_calculator = self.cost_calculator
            
            # 直接设置计算得出的持仓和现金（与BacktestEngine完全一致）
            self.portfolio_manager.holdings = holdings.copy()
            self.portfolio_manager.cash = initial_cash
            self.portfolio_manager.initial_prices = initial_prices.copy()
            
            # 验证总价值
            calculated_total_value = self.portfolio_manager.get_total_value(initial_prices)
            
            self.logger.info(f"✅ 投资组合初始化完成")
            self.logger.info(f"💰 总资产: {self.total_capital:,.2f}")
            self.logger.info(f"📈 股票市值: {total_stock_value:,.2f}")
            self.logger.info(f"💵 现金: {initial_cash:,.2f}")
            self.logger.info(f"🔍 计算总价值: {calculated_total_value:,.2f}")
            self.logger.info(f"📊 初始持仓: {len(self.portfolio_manager.holdings)} 只股票")
            
            return True
            
        except Exception as e:
            self.logger.error(f"投资组合初始化失败: {e}")
            return False
    
    def execute_trades(self, signals: Dict[str, str], stock_data: Dict[str, Dict[str, pd.DataFrame]],
                      current_date: pd.Timestamp, signal_details: Dict = None) -> List[str]:
        """
        执行交易
        
        Args:
            signals: 交易信号
            stock_data: 股票数据
            current_date: 当前日期
            signal_details: 信号详情（可选）
            
        Returns:
            执行的交易记录列表
        """
        executed_trades = []
        
        # 获取当前价格
        current_prices = {}
        for stock_code in self.stock_pool:
            if stock_code in stock_data:
                stock_weekly = stock_data[stock_code]['weekly']
                if current_date in stock_weekly.index:
                    current_prices[stock_code] = stock_weekly.loc[current_date, 'close']
        
        # 计算总资产
        total_assets = self.portfolio_manager.get_total_value(current_prices)
        
        # 执行卖出信号
        for stock_code, signal in signals.items():
            if signal == 'SELL' and stock_code in current_prices:
                trade_info = self._execute_sell(
                    stock_code, current_prices, current_date, signal_details
                )
                if trade_info:
                    executed_trades.append(trade_info)
        
        # 执行买入信号
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
        """执行卖出交易"""
        current_position = self.portfolio_manager.holdings.get(stock_code, 0)
        if current_position <= 0:
            return None
        
        price = current_prices[stock_code]
        
        # 获取DCF估值计算价值比
        dcf_value = self.dcf_values.get(stock_code)
        if not dcf_value or dcf_value <= 0:
            return None
        
        value_price_ratio = price / dcf_value
        
        # 使用动态仓位管理器计算卖出数量
        can_sell, sell_shares, sell_value, reason = self.portfolio_manager.can_sell_dynamic(
            stock_code, value_price_ratio, price, self.dynamic_position_manager, current_prices
        )
        
        if not can_sell or sell_shares <= 0:
            # 记录未执行原因
            if self.signal_tracker:
                self._record_rejection(
                    stock_code, 'SELL', current_date, price, reason, signal_details
                )
            return None
        
        # 记录交易前的仓位信息
        position_before = current_position
        total_value = self.portfolio_manager.get_total_value(current_prices)
        position_weight_before = (position_before * price / total_value) if total_value > 0 else 0.0
        
        # 执行卖出
        success, trade_info = self.portfolio_manager.sell_stock(
            stock_code, sell_shares, price, current_date, reason
        )
        
        if success:
            # 记录交易后的仓位信息
            position_after = self.portfolio_manager.holdings.get(stock_code, 0)
            total_value_after = self.portfolio_manager.get_total_value(current_prices)
            position_weight_after = (position_after * price / total_value_after) if total_value_after > 0 else 0.0
            
            # 更新信号跟踪器
            if self.signal_tracker:
                self._update_signal_execution(
                    stock_code, 'SELL', current_date, trade_info,
                    position_before, position_after,
                    position_weight_before, position_weight_after,
                    signal_details
                )
            
            # 记录到交易历史
            self.transaction_history.append(trade_info)
            
            return f"SELL {stock_code} {sell_shares}股 @{price:.2f}"
        
        return None
    
    def _execute_buy(self, stock_code: str, current_prices: Dict[str, float],
                    current_date: pd.Timestamp, signal_details: Dict = None) -> Optional[str]:
        """执行买入交易"""
        price = current_prices[stock_code]
        
        # 获取DCF估值计算价值比
        dcf_value = self.dcf_values.get(stock_code)
        if not dcf_value or dcf_value <= 0:
            return None
        
        value_price_ratio = price / dcf_value
        
        # 使用动态仓位管理器计算买入数量
        can_buy, buy_shares, buy_value, reason = self.portfolio_manager.can_buy_dynamic(
            stock_code, value_price_ratio, price, self.dynamic_position_manager, current_prices
        )
        
        if not can_buy or buy_shares <= 0:
            # 记录未执行原因
            if self.signal_tracker:
                self._record_rejection(
                    stock_code, 'BUY', current_date, price, reason, signal_details
                )
            return None
        
        # 记录交易前的仓位信息
        position_before = self.portfolio_manager.holdings.get(stock_code, 0)
        total_value = self.portfolio_manager.get_total_value(current_prices)
        position_weight_before = (position_before * price / total_value) if total_value > 0 else 0.0
        
        # 执行买入
        success, trade_info = self.portfolio_manager.buy_stock(
            stock_code, buy_shares, price, current_date, reason
        )
        
        if success:
            # 记录交易后的仓位信息
            position_after = self.portfolio_manager.holdings.get(stock_code, 0)
            total_value_after = self.portfolio_manager.get_total_value(current_prices)
            position_weight_after = (position_after * price / total_value_after) if total_value_after > 0 else 0.0
            
            # 更新信号跟踪器
            if self.signal_tracker:
                self._update_signal_execution(
                    stock_code, 'BUY', current_date, trade_info,
                    position_before, position_after,
                    position_weight_before, position_weight_after,
                    signal_details
                )
            
            # 记录到交易历史
            self.transaction_history.append(trade_info)
            
            return f"BUY {stock_code} {buy_shares}股 @{price:.2f}"
        
        return None
    
    def process_dividend_events(self, stock_data: Dict[str, Dict[str, pd.DataFrame]],
                               current_date: pd.Timestamp):
        """
        处理分红配股事件
        
        Args:
            stock_data: 股票数据
            current_date: 当前日期
        """
        try:
            dividend_events_today = {}
            
            for stock_code in self.stock_pool:
                if stock_code not in stock_data:
                    continue
                
                stock_weekly = stock_data[stock_code]['weekly']
                
                if current_date in stock_weekly.index:
                    row = stock_weekly.loc[current_date]
                    
                    # 检查是否有分红配股事件
                    has_dividend = (
                        row.get('dividend_amount', 0) > 0 or
                        row.get('bonus_ratio', 0) > 0 or
                        row.get('transfer_ratio', 0) > 0 or
                        row.get('allotment_ratio', 0) > 0
                    )
                    
                    if has_dividend:
                        dividend_events_today[stock_code] = row
                        self.logger.info(
                            f"💰 {current_date.strftime('%Y-%m-%d')} 发现 {stock_code} "
                            f"分红事件: 派息{row.get('dividend_amount', 0)}元"
                        )
            
            # 如果有分红事件，则处理
            if dividend_events_today:
                self.portfolio_manager.process_dividend_events(current_date, dividend_events_today)
                self.logger.info(
                    f"✅ {current_date.strftime('%Y-%m-%d')} 分红事件处理完成，"
                    f"共 {len(dividend_events_today)} 个事件"
                )
                
        except Exception as e:
            self.logger.warning(f"⚠️ {current_date.strftime('%Y-%m-%d')} 分红事件处理失败: {e}")
    
    def _record_rejection(self, stock_code: str, signal_type: str, current_date: pd.Timestamp,
                         price: float, reason: str, signal_details: Dict = None):
        """记录信号未执行原因"""
        if not self.signal_tracker:
            return
        
        signal_id = self.signal_tracker.get_signal_id(stock_code, current_date, signal_type)
        if signal_id:
            # 获取当前仓位信息
            position_before = self.portfolio_manager.holdings.get(stock_code, 0)
            current_prices = {stock_code: price}
            total_value = self.portfolio_manager.get_total_value(current_prices)
            position_weight_before = (position_before * price / total_value) if total_value > 0 else 0.0
            
            self.signal_tracker.update_execution_status(
                signal_id=signal_id,
                execution_status='未执行',
                execution_reason=reason,
                position_before_signal=position_before,
                position_weight_before=position_weight_before,
                trade_shares=0,
                position_after_trade=position_before,
                position_weight_after=position_weight_before
            )
    
    def _update_signal_execution(self, stock_code: str, signal_type: str,
                                current_date: pd.Timestamp, trade_info: Dict,
                                position_before: int, position_after: int,
                                weight_before: float, weight_after: float,
                                signal_details: Dict = None):
        """更新信号执行状态"""
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
                position_weight_after=weight_after
            )
    
    def get_portfolio_state(self, current_prices: Dict[str, float]) -> Dict[str, Any]:
        """
        获取投资组合当前状态
        
        Args:
            current_prices: 当前价格
            
        Returns:
            投资组合状态字典
        """
        return {
            'cash': self.portfolio_manager.cash,
            'positions': self.portfolio_manager.holdings.copy(),
            'total_value': self.portfolio_manager.get_total_value(current_prices),
            'transaction_count': len(self.transaction_history)
        }
    
    def get_transaction_history(self) -> List[Dict]:
        """获取交易历史"""
        return self.transaction_history.copy()
