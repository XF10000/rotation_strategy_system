"""
投资组合管理器
负责管理持仓、现金、执行交易等核心功能
"""

import logging
from datetime import datetime
from typing import Dict, Tuple

import pandas as pd

logger = logging.getLogger(__name__)

class PortfolioManager:
    """
    投资组合管理器
    
    功能：
    1. 管理股票持仓和现金
    2. 执行轮动交易
    3. 计算投资组合价值
    4. 记录交易历史
    """
    
    def __init__(self, total_capital: float, initial_holdings: Dict[str, float]):
        """
        初始化投资组合
        
        Args:
            total_capital: 总资金
            initial_holdings: 初始持仓配置 {'股票代码': 占比, 'cash': 现金占比}
        """
        self.total_capital = total_capital
        self.initial_holdings = initial_holdings.copy()
        
        # 初始化持仓
        self.holdings = {}  # {股票代码: 股数}
        self.cash = 0.0
        self.initial_prices = {}  # 记录初始价格用于计算
        
        # 交易记录
        self.transaction_history = []
        self.portfolio_history = []
        self.dividend_events = []  # 分红配股事件记录
        
        logger.info(f"投资组合管理器初始化完成，总资金: {total_capital:,.2f}")
    
    def initialize_portfolio(self, initial_prices: Dict[str, float]):
        """
        根据初始价格初始化投资组合
        
        Args:
            initial_prices: 初始价格字典 {股票代码: 价格}
        """
        self.initial_prices = initial_prices.copy()
        
        # 计算现金
        cash_ratio = self.initial_holdings.get('cash', 0.0)
        self.cash = self.total_capital * cash_ratio
        
        # 计算股票持仓
        for stock_code, ratio in self.initial_holdings.items():
            if stock_code != 'cash' and ratio > 0:
                if stock_code not in initial_prices:
                    logger.warning(f"股票 {stock_code} 缺少初始价格，跳过")
                    continue
                
                # 计算股数（向下取整到100股的整数倍）
                stock_value = self.total_capital * ratio
                shares = int(stock_value / initial_prices[stock_code] / 100) * 100
                
                if shares > 0:
                    self.holdings[stock_code] = shares
                    actual_cost = shares * initial_prices[stock_code]
                    logger.info(f"初始持仓 {stock_code}: {shares}股, 成本: {actual_cost:,.2f}")
        
        logger.info(f"初始现金: {self.cash:,.2f}")
        logger.info(f"初始化完成，总价值: {self.get_total_value(initial_prices):,.2f}")
    
    def get_total_value(self, current_prices: Dict[str, float]) -> float:
        """
        计算投资组合总价值
        
        Args:
            current_prices: 当前价格字典
            
        Returns:
            总价值
        """
        total_value = self.cash
        
        for stock_code, shares in self.holdings.items():
            if stock_code in current_prices:
                total_value += shares * current_prices[stock_code]
            else:
                logger.warning(f"股票 {stock_code} 缺少当前价格")
        
        return total_value
    
    def get_stock_value(self, stock_code: str, current_price: float) -> float:
        """
        获取某股票的当前市值
        
        Args:
            stock_code: 股票代码
            current_price: 当前价格
            
        Returns:
            股票市值
        """
        shares = self.holdings.get(stock_code, 0)
        return shares * current_price
    
    def get_stock_weight(self, stock_code: str, current_prices: Dict[str, float]) -> float:
        """
        获取某股票在投资组合中的权重
        
        Args:
            stock_code: 股票代码
            current_prices: 当前价格字典
            
        Returns:
            权重（0-1之间）
        """
        if stock_code not in current_prices:
            return 0.0
        
        stock_value = self.get_stock_value(stock_code, current_prices[stock_code])
        total_value = self.get_total_value(current_prices)
        
        return stock_value / total_value if total_value > 0 else 0.0
    
    def can_sell_dynamic(self, stock_code: str, value_price_ratio: float, current_price: float, 
                        dynamic_position_manager=None, all_current_prices: Dict[str, float] = None) -> Tuple[bool, int, float, str]:
        """
        基于价值比的动态卖出检查（新逻辑）
        
        Args:
            stock_code: 股票代码
            value_price_ratio: 价值比 (当前价格/DCF估值)
            current_price: 当前价格
            dynamic_position_manager: 动态仓位管理器实例
            all_current_prices: 所有股票的当前价格字典
            
        Returns:
            (是否可以卖出, 卖出股数, 卖出金额, 操作原因)
        """
        current_shares = self.holdings.get(stock_code, 0)
        
        if dynamic_position_manager is None:
            # 回退到原有逻辑
            return self.can_sell(stock_code, 0.20, current_price) + ("回退到固定20%逻辑",)
        
        # 计算总资产
        if all_current_prices:
            total_assets = self.get_total_value(all_current_prices)
        else:
            total_assets = self.get_total_value({stock_code: current_price})
        
        # 使用动态仓位管理器
        action_info = dynamic_position_manager.get_position_action(
            signal_type='SELL',
            stock_code=stock_code,
            value_price_ratio=value_price_ratio,
            current_shares=current_shares,
            current_price=current_price,
            available_cash=self.cash,
            total_assets=total_assets
        )
        
        if action_info['action'] == 'SELL':
            # 验证交易约束
            is_valid, validation_msg = dynamic_position_manager.validate_trade_constraints(
                action_info, current_shares, self.cash, current_price, total_assets
            )
            
            if is_valid:
                sell_value = action_info['shares'] * current_price
                return True, action_info['shares'], sell_value, action_info['reason']
            else:
                return False, 0, 0.0, f"验证失败: {validation_msg}"
        else:
            return False, 0, 0.0, action_info['reason']
    
    def can_sell(self, stock_code: str, sell_ratio: float, current_price: float) -> Tuple[bool, int, float]:
        """
        检查是否可以卖出股票（原有逻辑：卖出当前持仓市值的20%）
        保留此方法用于向后兼容
        
        Args:
            stock_code: 股票代码
            sell_ratio: 卖出比例（这个参数保留兼容性，实际使用20%）
            current_price: 当前价格
            
        Returns:
            (是否可以卖出, 卖出股数, 卖出金额)
        """
        # 如果持仓数量为0，忽略卖出信号
        current_shares = self.holdings.get(stock_code, 0)
        if current_shares <= 0:
            return False, 0, 0.0
        
        # 计算当前持仓市值
        current_holding_value = current_shares * current_price
        
        # 卖出当前持仓市值的20%
        target_sell_value = current_holding_value * 0.20
        
        # 计算卖出股数（向下取整到100股的整数倍）
        target_shares = int(target_sell_value / current_price / 100) * 100
        
        # 确保不超过当前持仓
        actual_shares = min(target_shares, current_shares)
        
        # 最小交易检查：少于100股不交易
        if actual_shares < 100:
            return False, 0, 0.0
        
        actual_value = actual_shares * current_price
        return True, actual_shares, actual_value
    
    def can_buy_dynamic(self, stock_code: str, value_price_ratio: float, current_price: float,
                       dynamic_position_manager=None, all_current_prices: Dict[str, float] = None) -> Tuple[bool, int, float, str]:
        """
        基于价值比的动态买入检查（新逻辑）
        
        Args:
            stock_code: 股票代码
            value_price_ratio: 价值比 (当前价格/DCF估值)
            current_price: 当前价格
            dynamic_position_manager: 动态仓位管理器实例
            all_current_prices: 所有股票的当前价格字典
            
        Returns:
            (是否可以买入, 买入股数, 买入金额, 操作原因)
        """
        current_shares = self.holdings.get(stock_code, 0)
        
        if dynamic_position_manager is None:
            # 回退到原有逻辑
            return self.can_buy(stock_code, 0.20, current_price) + ("回退到固定20%逻辑",)
        
        # 计算总资产（用于资产上限检查）
        if all_current_prices:
            # 使用传入的完整价格字典
            total_assets = self.get_total_value(all_current_prices)
        else:
            # 回退到原有逻辑（不推荐）
            current_prices = {stock_code: current_price}
            for other_code, shares in self.holdings.items():
                if other_code != stock_code and other_code not in current_prices:
                    # 对于其他股票，如果没有价格信息，使用一个估算值
                    current_prices[other_code] = current_price  # 简化处理
            total_assets = self.get_total_value(current_prices)
        
        # 使用动态仓位管理器
        action_info = dynamic_position_manager.get_position_action(
            signal_type='BUY',
            stock_code=stock_code,
            value_price_ratio=value_price_ratio,
            current_shares=current_shares,
            current_price=current_price,
            available_cash=self.cash,
            total_assets=total_assets
        )
        
        if action_info['action'] == 'BUY':
            # 验证交易约束
            is_valid, validation_msg = dynamic_position_manager.validate_trade_constraints(
                action_info, current_shares, self.cash, current_price, total_assets
            )
            
            if is_valid:
                buy_value = action_info['shares'] * current_price
                return True, action_info['shares'], buy_value, action_info['reason']
            else:
                return False, 0, 0.0, f"验证失败: {validation_msg}"
        else:
            return False, 0, 0.0, action_info['reason']
    
    def can_buy(self, stock_code: str, buy_ratio: float, current_price: float) -> Tuple[bool, int, float]:
        """
        检查是否可以买入股票（原有逻辑：根据持仓状态决定买入金额）
        保留此方法用于向后兼容
        
        Args:
            stock_code: 股票代码
            buy_ratio: 买入比例（这个参数保留兼容性，实际使用20%）
            current_price: 当前价格
            
        Returns:
            (是否可以买入, 买入股数, 买入金额)
        """
        current_shares = self.holdings.get(stock_code, 0)
        
        if current_shares == 0:
            # 如果持仓数量为0，则买入持有现金的20%金额
            target_buy_value = self.cash * 0.20
        else:
            # 如果持仓数量非0，则买入当前持仓市值的20%金额
            current_holding_value = current_shares * current_price
            target_buy_value = current_holding_value * 0.20
        
        # 检查现金是否足够
        if self.cash < target_buy_value:
            target_buy_value = self.cash
        
        # 计算买入股数（向下取整到100股的整数倍）
        target_shares = int(target_buy_value / current_price / 100) * 100
        
        # 最小交易检查：少于100股不交易
        if target_shares < 100:
            return False, 0, 0.0
        
        actual_value = target_shares * current_price
        
        # 最终检查现金是否足够
        if actual_value > self.cash:
            return False, 0, 0.0
        
        return True, target_shares, actual_value
    
    def execute_sell(self, stock_code: str, shares: int, price: float, 
                    transaction_cost: float, date: datetime, reason: str = "",
                    technical_indicators: dict = None, signal_details: dict = None) -> bool:
        """
        执行卖出交易
        
        Args:
            stock_code: 股票代码
            shares: 卖出股数
            price: 卖出价格
            transaction_cost: 交易成本
            date: 交易日期
            reason: 交易原因
            technical_indicators: 技术指标数值
            signal_details: 信号判断详情
            
        Returns:
            是否成功执行
        """
        if stock_code not in self.holdings or self.holdings[stock_code] < shares:
            logger.error(f"卖出失败：{stock_code} 持仓不足")
            return False
        
        # 执行卖出
        gross_proceeds = shares * price
        net_proceeds = gross_proceeds - transaction_cost
        
        self.holdings[stock_code] -= shares
        if self.holdings[stock_code] == 0:
            del self.holdings[stock_code]
        
        self.cash += net_proceeds
        
        # 记录交易（包含技术指标和信号详情）
        transaction = {
            'date': date,
            'type': 'SELL',
            'stock_code': stock_code,
            'shares': shares,
            'price': price,
            'gross_amount': gross_proceeds,
            'transaction_cost': transaction_cost,
            'net_amount': net_proceeds,
            'reason': reason,
            'technical_indicators': technical_indicators or {},
            'signal_details': signal_details or {}
        }
        self.transaction_history.append(transaction)
        
        logger.info(f"卖出 {stock_code}: {shares}股 @ {price:.2f}, 净收入: {net_proceeds:.2f}")
        return True
    
    def execute_buy(self, stock_code: str, shares: int, price: float,
                   transaction_cost: float, date: datetime, reason: str = "",
                   technical_indicators: dict = None, signal_details: dict = None) -> bool:
        """
        执行买入交易
        
        Args:
            stock_code: 股票代码
            shares: 买入股数
            price: 买入价格
            transaction_cost: 交易成本
            date: 交易日期
            reason: 交易原因
            technical_indicators: 技术指标数值
            signal_details: 信号判断详情
            
        Returns:
            是否成功执行
        """
        total_cost = shares * price + transaction_cost
        
        if self.cash < total_cost:
            logger.error(f"买入失败：现金不足，需要 {total_cost:.2f}，可用 {self.cash:.2f}")
            return False
        
        # 执行买入
        if stock_code not in self.holdings:
            self.holdings[stock_code] = 0
        
        self.holdings[stock_code] += shares
        self.cash -= total_cost
        
        # 记录交易（包含技术指标和信号详情）
        transaction = {
            'date': date,
            'type': 'BUY',
            'stock_code': stock_code,
            'shares': shares,
            'price': price,
            'gross_amount': shares * price,
            'transaction_cost': transaction_cost,
            'net_amount': total_cost,
            'reason': reason,
            'technical_indicators': technical_indicators or {},
            'signal_details': signal_details or {}
        }
        self.transaction_history.append(transaction)
        
        logger.info(f"买入 {stock_code}: {shares}股 @ {price:.2f}, 总成本: {total_cost:.2f}")
        return True
    
    def execute_rotation(self, sell_stock: str, buy_stock: str, rotation_ratio: float,
                        prices: Dict[str, float], transaction_costs: Dict[str, float],
                        date: datetime) -> Tuple[bool, str]:
        """
        执行轮动交易（A股 -> B股）
        
        Args:
            sell_stock: 卖出股票代码
            buy_stock: 买入股票代码
            rotation_ratio: 轮动比例
            prices: 价格字典
            transaction_costs: 交易成本字典
            date: 交易日期
            
        Returns:
            (是否成功, 执行信息)
        """
        # 检查卖出条件
        can_sell, sell_shares, sell_value = self.can_sell(
            sell_stock, rotation_ratio, prices[sell_stock]
        )
        
        if not can_sell:
            return False, f"无法卖出 {sell_stock}：持仓不足或金额太小"
        
        # 执行卖出
        sell_success = self.execute_sell(
            sell_stock, sell_shares, prices[sell_stock],
            transaction_costs.get(f"{sell_stock}_sell", 0),
            date, f"轮动卖出 -> {buy_stock}"
        )
        
        if not sell_success:
            return False, f"卖出 {sell_stock} 失败"
        
        # 检查买入条件（使用卖出后的现金）
        can_buy, buy_shares, buy_value = self.can_buy(
            buy_stock, rotation_ratio, prices[buy_stock]
        )
        
        if not can_buy:
            return False, f"无法买入 {buy_stock}：现金不足或价格太高"
        
        # 执行买入
        buy_success = self.execute_buy(
            buy_stock, buy_shares, prices[buy_stock],
            transaction_costs.get(f"{buy_stock}_buy", 0),
            date, f"轮动买入 <- {sell_stock}"
        )
        
        if not buy_success:
            return False, f"买入 {buy_stock} 失败"
        
        return True, f"轮动成功: {sell_stock}({sell_shares}股) -> {buy_stock}({buy_shares}股)"
    
    def execute_rotation_with_indicators(self, sell_stock: str, buy_stock: str, rotation_ratio: float,
                                       prices: Dict[str, float], transaction_costs: Dict[str, float],
                                       date: datetime, sell_indicators: dict = None, sell_signal_details: dict = None,
                                       buy_indicators: dict = None, buy_signal_details: dict = None) -> Tuple[bool, str]:
        """
        执行带技术指标记录的轮动交易（A股 -> B股）
        
        Args:
            sell_stock: 卖出股票代码
            buy_stock: 买入股票代码
            rotation_ratio: 轮动比例
            prices: 价格字典
            transaction_costs: 交易成本字典
            date: 交易日期
            sell_indicators: 卖出股票的技术指标
            sell_signal_details: 卖出信号详情
            buy_indicators: 买入股票的技术指标
            buy_signal_details: 买入信号详情
            
        Returns:
            (是否成功, 执行信息)
        """
        # 检查卖出条件
        can_sell, sell_shares, sell_value = self.can_sell(
            sell_stock, rotation_ratio, prices[sell_stock]
        )
        
        if not can_sell:
            return False, f"无法卖出 {sell_stock}：持仓不足或金额太小"
        
        # 执行卖出（带技术指标）
        sell_success = self.execute_sell(
            sell_stock, sell_shares, prices[sell_stock],
            transaction_costs.get(f"{sell_stock}_sell", 0),
            date, f"轮动卖出 -> {buy_stock}",
            sell_indicators, sell_signal_details
        )
        
        if not sell_success:
            return False, f"卖出 {sell_stock} 失败"
        
        # 检查买入条件（使用卖出后的现金）
        can_buy, buy_shares, buy_value = self.can_buy(
            buy_stock, rotation_ratio, prices[buy_stock]
        )
        
        if not can_buy:
            return False, f"无法买入 {buy_stock}：现金不足或价格太高"
        
        # 执行买入（带技术指标）
        buy_success = self.execute_buy(
            buy_stock, buy_shares, prices[buy_stock],
            transaction_costs.get(f"{buy_stock}_buy", 0),
            date, f"轮动买入 <- {sell_stock}",
            buy_indicators, buy_signal_details
        )
        
        if not buy_success:
            return False, f"买入 {buy_stock} 失败"
        
        return True, f"轮动成功: {sell_stock}({sell_shares}股) -> {buy_stock}({buy_shares}股)"
    
    def record_portfolio_snapshot(self, date: datetime, prices: Dict[str, float]):
        """
        记录投资组合快照
        
        Args:
            date: 日期
            prices: 价格字典
        """
        snapshot = {
            'date': date,
            'cash': self.cash,
            'holdings': self.holdings.copy(),
            'total_value': self.get_total_value(prices),
            'stock_values': {}
        }
        
        # 记录各股票市值
        for stock_code, shares in self.holdings.items():
            if stock_code in prices:
                snapshot['stock_values'][stock_code] = shares * prices[stock_code]
        
        self.portfolio_history.append(snapshot)
    
    def get_transaction_summary(self) -> pd.DataFrame:
        """
        获取交易汇总
        
        Returns:
            交易记录DataFrame
        """
        if not self.transaction_history:
            return pd.DataFrame()
        
        df = pd.DataFrame(self.transaction_history)
        df['date'] = pd.to_datetime(df['date'])
        return df
    
    def get_portfolio_summary(self) -> pd.DataFrame:
        """
        获取投资组合历史
        
        Returns:
            投资组合历史DataFrame
        """
        if not self.portfolio_history:
            return pd.DataFrame()
        
        df = pd.DataFrame(self.portfolio_history)
        df['date'] = pd.to_datetime(df['date'])
        return df
    
    def get_current_allocation(self, current_prices: Dict[str, float]) -> Dict[str, float]:
        """
        获取当前资产配置
        
        Args:
            current_prices: 当前价格字典
            
        Returns:
            资产配置字典 {资产: 权重}
        """
        total_value = self.get_total_value(current_prices)
        allocation = {}
        
        # 现金权重
        allocation['cash'] = self.cash / total_value if total_value > 0 else 0
        
        # 股票权重
        for stock_code, shares in self.holdings.items():
            if stock_code in current_prices:
                stock_value = shares * current_prices[stock_code]
                allocation[stock_code] = stock_value / total_value if total_value > 0 else 0
        
        return allocation
    
    def update_prices(self, current_prices: Dict[str, float]):
        """
        更新当前价格（用于计算投资组合价值）
        
        Args:
            current_prices: 当前价格字典
        """
        # 这个方法主要用于兼容性，实际价格更新在get_total_value中处理
    
    @property
    def positions(self) -> Dict[str, int]:
        """
        获取当前持仓
        
        Returns:
            持仓字典 {股票代码: 股数}
        """
        return self.holdings.copy()
    
    def sell_stock(self, stock_code: str, shares: int, price: float, date, reason: str) -> Tuple[bool, Dict]:
        """
        卖出股票的简化接口
        
        Args:
            stock_code: 股票代码
            shares: 卖出股数
            price: 卖出价格
            date: 交易日期
            reason: 交易原因
            
        Returns:
            (是否成功, 交易信息)
        """
        # 计算交易成本
        transaction_cost = 0
        if hasattr(self, 'cost_calculator') and self.cost_calculator:
            cost_detail = self.cost_calculator.calculate_sell_cost(stock_code, shares, price)
            transaction_cost = cost_detail.get('total_cost', 0)
        
        success = self.execute_sell(stock_code, shares, price, transaction_cost, date, reason)
        
        trade_info = {
            'type': 'SELL',
            'stock_code': stock_code,
            'shares': shares,
            'price': price,
            'gross_amount': shares * price,
            'transaction_cost': transaction_cost,
            'net_amount': shares * price - transaction_cost,
            'reason': reason
        }
        
        return success, trade_info
    
    def buy_stock(self, stock_code: str, shares: int, price: float, date, reason: str) -> Tuple[bool, Dict]:
        """
        买入股票的简化接口
        
        Args:
            stock_code: 股票代码
            shares: 买入股数
            price: 买入价格
            date: 交易日期
            reason: 交易原因
            
        Returns:
            (是否成功, 交易信息)
        """
        # 计算交易成本
        transaction_cost = 0
        if hasattr(self, 'cost_calculator') and self.cost_calculator:
            cost_detail = self.cost_calculator.calculate_buy_cost(stock_code, shares, price)
            transaction_cost = cost_detail.get('total_cost', 0)
        
        success = self.execute_buy(stock_code, shares, price, transaction_cost, date, reason)
        
        trade_info = {
            'type': 'BUY',
            'stock_code': stock_code,
            'shares': shares,
            'price': price,
            'gross_amount': shares * price,
            'transaction_cost': transaction_cost,
            'net_amount': shares * price + transaction_cost,
            'reason': reason
        }
        
        return success, trade_info
    
    def process_dividend_events(self, date, dividend_data):
        """
        处理分红配股事件
        
        Args:
            date: 处理日期
            dividend_data: 分红配股数据字典 {stock_code: dividend_info}
        """
        try:
            if not dividend_data:
                return
            
            for stock_code, dividend_info in dividend_data.items():
                # 检查是否持有该股票
                if stock_code not in self.holdings or self.holdings[stock_code] <= 0:
                    continue
                
                current_shares = self.holdings[stock_code]
                shares_before = current_shares
                cash_before = self.cash
                
                # 获取分红配股信息
                dividend_amount = dividend_info.get('dividend_amount', 0)  # 每股分红金额
                bonus_ratio = dividend_info.get('bonus_ratio', 0)  # 10送X股
                transfer_ratio = dividend_info.get('transfer_ratio', 0)  # 10转X股
                allotment_ratio = dividend_info.get('allotment_ratio', 0)  # 10配X股
                allotment_price = dividend_info.get('allotment_price', 0)  # 配股价格
                
                cash_change = 0
                shares_change = 0
                
                # 1. 处理分红（现金分红）
                if dividend_amount > 0:
                    dividend_cash = current_shares * dividend_amount
                    self.cash += dividend_cash
                    cash_change += dividend_cash
                    
                    # 记录分红交易
                    self.transaction_history.append({
                        'date': date,
                        'type': 'DIVIDEND',
                        'stock_code': stock_code,
                        'shares': 0,
                        'price': 0,
                        'amount': dividend_cash,
                        'commission': 0,
                        'reason': f'分红: 每股{dividend_amount:.3f}元'
                    })
                
                # 2. 处理送股（股票分红）
                if bonus_ratio > 0:
                    bonus_shares = int(current_shares * bonus_ratio / 10)
                    if bonus_shares > 0:
                        self.holdings[stock_code] += bonus_shares
                        shares_change += bonus_shares
                        
                        # 记录送股交易
                        self.transaction_history.append({
                            'date': date,
                            'type': 'BONUS',
                            'stock_code': stock_code,
                            'shares': bonus_shares,
                            'price': 0,
                            'amount': 0,
                            'commission': 0,
                            'reason': f'送股: 10送{bonus_ratio}'
                        })
                
                # 3. 处理转增（资本公积金转股本）
                if transfer_ratio > 0:
                    transfer_shares = int(current_shares * transfer_ratio / 10)
                    if transfer_shares > 0:
                        self.holdings[stock_code] += transfer_shares
                        shares_change += transfer_shares
                        
                        # 记录转增交易
                        self.transaction_history.append({
                            'date': date,
                            'type': 'TRANSFER',
                            'stock_code': stock_code,
                            'shares': transfer_shares,
                            'price': 0,
                            'amount': 0,
                            'commission': 0,
                            'reason': f'转增: 10转{transfer_ratio}'
                        })
                
                # 4. 处理配股（有偿增发）
                if allotment_ratio > 0 and allotment_price > 0:
                    allotment_shares = int(current_shares * allotment_ratio / 10)
                    if allotment_shares > 0:
                        allotment_cost = allotment_shares * allotment_price
                        
                        # 检查现金是否足够
                        if self.cash >= allotment_cost:
                            self.holdings[stock_code] += allotment_shares
                            self.cash -= allotment_cost
                            shares_change += allotment_shares
                            cash_change -= allotment_cost
                            
                            # 记录配股交易
                            self.transaction_history.append({
                                'date': date,
                                'type': 'ALLOTMENT',
                                'stock_code': stock_code,
                                'shares': allotment_shares,
                                'price': allotment_price,
                                'amount': allotment_cost,
                                'commission': 0,
                                'reason': f'配股: 10配{allotment_ratio}, 价格{allotment_price:.2f}'
                            })
                        else:
                            logger.warning(f"现金不足，无法参与配股: {stock_code}, 需要{allotment_cost:.2f}, 剩余{self.cash:.2f}")
                
                # 记录分红配股事件
                if dividend_amount > 0 or bonus_ratio > 0 or transfer_ratio > 0 or allotment_ratio > 0:
                    event_record = {
                        'date': str(date.date()) if hasattr(date, 'date') else str(date),
                        'stock_code': stock_code,
                        'mapped_date': str(date.date()) if hasattr(date, 'date') else str(date),
                        'dividend_amount': dividend_amount,
                        'bonus_ratio': bonus_ratio,
                        'transfer_ratio': transfer_ratio,
                        'allotment_ratio': allotment_ratio,
                        'allotment_price': allotment_price,
                        'shares_before': shares_before,
                        'shares_after': self.holdings[stock_code],
                        'cash_change': cash_change
                    }
                    
                    self.dividend_events.append(event_record)
                    
                    logger.info(f"处理分红配股事件: {stock_code} 在 {date.date()}, "
                               f"持股数: {shares_before} -> {self.holdings[stock_code]}, "
                               f"现金变化: {cash_change:.2f}")
        
        except Exception as e:
            logger.error(f"处理分红配股事件失败: {str(e)}")
    
    def get_dividend_events(self):
        """
        获取分红配股事件列表
        
        Returns:
            list: 分红配股事件列表
        """
        return self.dividend_events.copy()

if __name__ == "__main__":
    # 测试代码
    logging.basicConfig(level=logging.INFO)
    
    # 测试投资组合管理器
    initial_holdings = {
        "601088": 0.20,  # 中国神华 20%
        "000807": 0.15,  # 云铝股份 15%
        "002460": 0.25,  # 赣锋锂业 25%
        "cash": 0.40     # 现金 40%
    }
    
    portfolio = PortfolioManager(1000000, initial_holdings)
    
    # 模拟初始价格
    initial_prices = {
        "601088": 30.0,
        "000807": 15.0,
        "002460": 50.0
    }
    
    portfolio.initialize_portfolio(initial_prices)
    
    print("初始投资组合:")
    print(f"总价值: {portfolio.get_total_value(initial_prices):,.2f}")
    print(f"现金: {portfolio.cash:,.2f}")
    print(f"持仓: {portfolio.holdings}")