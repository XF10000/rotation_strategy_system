"""
Portfolio数据管理器 - 统一管理投资组合的所有数据
"""
import logging
from typing import Any, Dict, List, Optional

import pandas as pd

logger = logging.getLogger(__name__)

class PortfolioDataManager:
    """
    统一的Portfolio数据管理器
    负责管理价格数据、持仓数据、历史记录等所有portfolio相关数据
    """
    
    def __init__(self, total_capital: float):
        self.total_capital = total_capital
        
        # 统一的数据存储
        self._price_data: Dict[str, Dict[str, float]] = {}  # {stock_code: {date: price}}
        self._portfolio_states: List[Dict[str, Any]] = []   # 完整的portfolio状态历史
        self._current_positions: Dict[str, int] = {}        # 当前持仓数量
        self._current_cash: float = 0.0                     # 当前现金
        
        # 缓存数据，避免重复计算
        self._cached_market_values: Dict[str, Dict[str, float]] = {}  # {date: {stock: market_value}}
        self._cached_total_values: Dict[str, float] = {}              # {date: total_value}
        
        logger.info("📊 Portfolio数据管理器初始化完成")
    
    def set_price_data(self, stock_code: str, date_prices: Dict[str, float]):
        """
        设置股票的价格数据
        
        Args:
            stock_code: 股票代码
            date_prices: {date_str: price} 格式的价格数据
        """
        self._price_data[stock_code] = date_prices.copy()
        # 清除相关缓存
        self._clear_cache()
        logger.debug(f"📈 设置 {stock_code} 价格数据，包含 {len(date_prices)} 个交易日")
    
    def get_price(self, stock_code: str, date: str) -> Optional[float]:
        """
        获取指定股票在指定日期的价格
        
        Args:
            stock_code: 股票代码
            date: 日期字符串 (YYYY-MM-DD)
            
        Returns:
            价格，如果不存在返回None
        """
        if stock_code in self._price_data:
            return self._price_data[stock_code].get(date)
        return None
    
    def get_initial_price(self, stock_code: str) -> Optional[float]:
        """
        获取股票的初始价格（第一个交易日的价格）
        
        Args:
            stock_code: 股票代码
            
        Returns:
            初始价格，如果不存在返回None
        """
        if stock_code in self._price_data and self._price_data[stock_code]:
            dates = sorted(self._price_data[stock_code].keys())
            return self._price_data[stock_code][dates[0]]
        return None
    
    def get_latest_price(self, stock_code: str) -> Optional[float]:
        """
        获取股票的最新价格（最后一个交易日的价格）
        
        Args:
            stock_code: 股票代码
            
        Returns:
            最新价格，如果不存在返回None
        """
        if stock_code in self._price_data and self._price_data[stock_code]:
            dates = sorted(self._price_data[stock_code].keys())
            return self._price_data[stock_code][dates[-1]]
        return None
    
    def record_portfolio_state(self, date: str, positions: Dict[str, int], 
                             cash: float, prices: Dict[str, float]):
        """
        记录完整的portfolio状态
        
        Args:
            date: 日期字符串
            positions: 持仓数量 {stock_code: shares}
            cash: 现金余额
            prices: 当日价格 {stock_code: price}
        """
        # 计算市值信息
        market_values = {}
        stock_total_value = 0.0
        
        for stock_code, shares in positions.items():
            if stock_code != 'cash' and shares > 0:
                price = prices.get(stock_code, 0)
                market_value = shares * price
                market_values[stock_code] = {
                    'shares': shares,
                    'price': price,
                    'market_value': market_value
                }
                stock_total_value += market_value
        
        total_value = cash + stock_total_value
        
        # 构建完整的portfolio状态
        portfolio_state = {
            'date': date,
            'total_value': total_value,
            'cash': cash,
            'stock_value': stock_total_value,
            'positions': positions.copy(),
            'prices': prices.copy(),
            'market_values': market_values,
            'position_details': market_values  # 兼容性字段
        }
        
        self._portfolio_states.append(portfolio_state)
        
        # 更新当前状态
        self._current_positions = positions.copy()
        self._current_cash = cash
        
        # 更新缓存
        self._cached_market_values[date] = market_values
        self._cached_total_values[date] = total_value
        
        logger.debug(f"📝 记录 {date} portfolio状态: 总资产={total_value:,.2f}, 现金={cash:,.2f}, 股票={stock_total_value:,.2f}")
    
    def get_portfolio_state(self, date: str = None) -> Optional[Dict[str, Any]]:
        """
        获取指定日期的portfolio状态
        
        Args:
            date: 日期字符串，None表示获取最新状态
            
        Returns:
            Portfolio状态字典，如果不存在返回None
        """
        if date is None:
            # 返回最新状态
            return self._portfolio_states[-1] if self._portfolio_states else None
        
        # 查找指定日期的状态
        for state in self._portfolio_states:
            if state['date'] == date:
                return state
        
        return None
    
    def get_initial_portfolio_state(self) -> Optional[Dict[str, Any]]:
        """
        获取初始portfolio状态
        
        Returns:
            初始portfolio状态，如果不存在返回None
        """
        return self._portfolio_states[0] if self._portfolio_states else None
    
    def get_final_portfolio_state(self) -> Optional[Dict[str, Any]]:
        """
        获取最终portfolio状态
        
        Returns:
            最终portfolio状态，如果不存在返回None
        """
        return self._portfolio_states[-1] if self._portfolio_states else None
    
    def get_portfolio_history(self) -> pd.DataFrame:
        """
        获取完整的portfolio历史记录
        
        Returns:
            Portfolio历史记录的DataFrame
        """
        if not self._portfolio_states:
            return pd.DataFrame()
        
        # 转换为DataFrame格式
        df_data = []
        for state in self._portfolio_states:
            df_data.append({
                'date': state['date'],
                'total_value': state['total_value'],
                'cash': state['cash'],
                'stock_value': state['stock_value'],
                'positions': state['positions']
            })
        
        df = pd.DataFrame(df_data)
        df['date'] = pd.to_datetime(df['date'])
        df.set_index('date', inplace=True)
        
        return df
    
    def calculate_performance_metrics(self) -> Dict[str, Any]:
        """
        计算性能指标
        
        Returns:
            性能指标字典
        """
        if len(self._portfolio_states) < 2:
            return {}
        
        initial_state = self._portfolio_states[0]
        final_state = self._portfolio_states[-1]
        
        initial_value = initial_state['total_value']
        final_value = final_state['total_value']
        
        total_return = final_value - initial_value
        total_return_rate = (total_return / initial_value) * 100
        
        # 计算年化收益率
        start_date = pd.to_datetime(initial_state['date'])
        end_date = pd.to_datetime(final_state['date'])
        days = (end_date - start_date).days
        
        if days > 0:
            annual_return = (final_value / initial_value) ** (365.25 / days) - 1
        else:
            annual_return = 0
        
        # 计算日收益率序列
        daily_returns = []
        for i in range(1, len(self._portfolio_states)):
            prev_value = self._portfolio_states[i-1]['total_value']
            curr_value = self._portfolio_states[i]['total_value']
            daily_return = (curr_value - prev_value) / prev_value
            daily_returns.append(daily_return)
        
        # 计算波动率（年化）
        if daily_returns:
            daily_returns_series = pd.Series(daily_returns)
            volatility = daily_returns_series.std() * (52 ** 0.5)  # 周数据年化
        else:
            volatility = 0
        
        logger.info(f"📊 性能指标计算完成:")
        logger.info(f"  初始价值: {initial_value:,.2f}")
        logger.info(f"  最终价值: {final_value:,.2f}")
        logger.info(f"  总收益率: {total_return_rate:.2f}%")
        logger.info(f"  年化收益率: {annual_return*100:.2f}%")
        logger.info(f"  交易天数: {days}")
        
        return {
            'initial_value': initial_value,
            'final_value': final_value,
            'total_return': total_return,
            'total_return_rate': total_return_rate,
            'annual_return': annual_return,  # 添加年化收益率
            'volatility': volatility,
            'trading_days': len(self._portfolio_states)
        }
    
    def get_position_comparison(self) -> Dict[str, Any]:
        """
        获取持仓对比信息（初始 vs 最终）
        
        Returns:
            持仓对比字典
        """
        if len(self._portfolio_states) < 2:
            return {}
        
        initial_state = self._portfolio_states[0]
        final_state = self._portfolio_states[-1]
        
        # 获取所有涉及的股票
        all_stocks = set()
        all_stocks.update(initial_state['positions'].keys())
        all_stocks.update(final_state['positions'].keys())
        all_stocks.discard('cash')  # 移除现金
        
        comparison = {}
        for stock_code in all_stocks:
            initial_shares = initial_state['positions'].get(stock_code, 0)
            final_shares = final_state['positions'].get(stock_code, 0)
            
            initial_price = initial_state['prices'].get(stock_code, 0)
            final_price = final_state['prices'].get(stock_code, 0)
            
            initial_market_value = initial_shares * initial_price
            final_market_value = final_shares * final_price
            
            comparison[stock_code] = {
                'initial_shares': initial_shares,
                'final_shares': final_shares,
                'shares_change': final_shares - initial_shares,
                'initial_price': initial_price,
                'final_price': final_price,
                'initial_market_value': initial_market_value,
                'final_market_value': final_market_value,
                'market_value_change': final_market_value - initial_market_value,
                'return_rate': (final_market_value - initial_market_value) / initial_market_value * 100 if initial_market_value > 0 else 0
            }
        
        return comparison
    
    def _clear_cache(self):
        """清除缓存数据"""
        self._cached_market_values.clear()
        self._cached_total_values.clear()
    
    def get_current_positions(self) -> Dict[str, int]:
        """获取当前持仓"""
        return self._current_positions.copy()
    
    def get_current_cash(self) -> float:
        """获取当前现金"""
        return self._current_cash
    
    def get_summary(self) -> Dict[str, Any]:
        """
        获取数据管理器的摘要信息
        
        Returns:
            摘要信息字典
        """
        return {
            'total_capital': self.total_capital,
            'stocks_count': len(self._price_data),
            'trading_days': len(self._portfolio_states),
            'current_cash': self._current_cash,
            'current_positions_count': len([k for k, v in self._current_positions.items() if k != 'cash' and v > 0])
        }