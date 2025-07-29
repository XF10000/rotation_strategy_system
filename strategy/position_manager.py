"""
仓位管理器
管理股票持仓、资金分配和交易执行
"""

import pandas as pd
import numpy as np
from typing import Dict, List, Tuple, Optional
import logging
from datetime import datetime

import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from strategy.exceptions import PositionManagementError, InsufficientDataError

logger = logging.getLogger(__name__)

class PositionManager:
    """
    仓位管理器
    负责管理持仓、计算仓位大小、执行交易
    """
    
    def __init__(self, config: Dict):
        """
        初始化仓位管理器
        
        Args:
            config: 配置参数
        """
        self.config = config
        self.logger = logging.getLogger("strategy.PositionManager")
        
        # 默认参数
        self.default_params = {
            'initial_capital': 1000000,    # 初始资金
            'position_size': 0.1,          # 单只股票仓位比例 (10%)
            'max_positions': 5,            # 最大持仓数量
            'min_trade_amount': 10000,     # 最小交易金额
            'commission_rate': 0.0003,     # 手续费率
            'slippage_rate': 0.001,        # 滑点率
            'cash_reserve_ratio': 0.05     # 现金储备比例
        }
        
        # 合并配置
        self.params = {**self.default_params, **config}
        
        # 初始化状态
        self.positions = {}           # 持仓信息
        self.cash = self.params['initial_capital']  # 可用现金
        self.total_value = self.params['initial_capital']  # 总资产
        self.trade_history = []       # 交易历史
        
        self.logger.info("仓位管理器初始化完成")
    
    def calculate_position_size(self, stock_code: str, signal: str, 
                              current_price: float, signal_confidence: float) -> int:
        """
        计算仓位大小
        
        Args:
            stock_code: 股票代码
            signal: 交易信号 ('BUY', 'SELL', 'HOLD')
            current_price: 当前价格
            signal_confidence: 信号置信度
            
        Returns:
            int: 应该买入/卖出的股数 (正数买入，负数卖出，0不操作)
        """
        try:
            if signal == 'HOLD':
                return 0
            
            if signal == 'BUY':
                return self._calculate_buy_size(stock_code, current_price, signal_confidence)
            elif signal == 'SELL':
                return self._calculate_sell_size(stock_code, current_price, signal_confidence)
            else:
                return 0
                
        except Exception as e:
            raise PositionManagementError(f"计算仓位大小失败: {str(e)}") from e
    
    def _calculate_buy_size(self, stock_code: str, current_price: float, 
                           confidence: float) -> int:
        """计算买入数量"""
        try:
            # 检查是否已持仓
            if stock_code in self.positions:
                self.logger.debug(f"股票 {stock_code} 已持仓，不再买入")
                return 0
            
            # 检查持仓数量限制
            if len(self.positions) >= self.params['max_positions']:
                self.logger.debug(f"已达到最大持仓数量 {self.params['max_positions']}")
                return 0
            
            # 计算可用资金
            reserved_cash = self.total_value * self.params['cash_reserve_ratio']
            available_cash = max(0, self.cash - reserved_cash)
            
            if available_cash < self.params['min_trade_amount']:
                self.logger.debug(f"可用资金不足: {available_cash}")
                return 0
            
            # 基础仓位大小
            base_position_value = self.total_value * self.params['position_size']
            
            # 根据信号置信度调整
            adjusted_position_value = base_position_value * confidence
            
            # 限制在可用资金范围内
            position_value = min(adjusted_position_value, available_cash)
            
            # 计算股数 (考虑手续费和滑点)
            total_cost_rate = 1 + self.params['commission_rate'] + self.params['slippage_rate']
            shares = int(position_value / (current_price * total_cost_rate))
            
            # 确保最小交易金额
            if shares * current_price < self.params['min_trade_amount']:
                return 0
            
            # 调整为100股的整数倍
            shares = (shares // 100) * 100
            
            self.logger.debug(f"计算买入 {stock_code}: {shares}股 @ {current_price}")
            return shares
            
        except Exception as e:
            raise PositionManagementError(f"计算买入数量失败: {str(e)}") from e
    
    def _calculate_sell_size(self, stock_code: str, current_price: float, 
                            confidence: float) -> int:
        """计算卖出数量"""
        try:
            # 检查是否持仓
            if stock_code not in self.positions:
                self.logger.debug(f"股票 {stock_code} 未持仓，无法卖出")
                return 0
            
            current_shares = self.positions[stock_code]['shares']
            
            # 根据信号置信度决定卖出比例
            if confidence >= 0.8:
                sell_ratio = 1.0  # 全部卖出
            elif confidence >= 0.6:
                sell_ratio = 0.8  # 卖出80%
            elif confidence >= 0.4:
                sell_ratio = 0.5  # 卖出50%
            else:
                sell_ratio = 0.3  # 卖出30%
            
            sell_shares = int(current_shares * sell_ratio)
            
            # 调整为100股的整数倍
            sell_shares = (sell_shares // 100) * 100
            
            # 确保不超过持仓数量
            sell_shares = min(sell_shares, current_shares)
            
            self.logger.debug(f"计算卖出 {stock_code}: {sell_shares}股 @ {current_price}")
            return -sell_shares  # 负数表示卖出
            
        except Exception as e:
            raise PositionManagementError(f"计算卖出数量失败: {str(e)}") from e
    
    def execute_trade(self, stock_code: str, shares: int, price: float, 
                     timestamp: datetime) -> Dict:
        """
        执行交易
        
        Args:
            stock_code: 股票代码
            shares: 股数 (正数买入，负数卖出)
            price: 交易价格
            timestamp: 交易时间
            
        Returns:
            Dict: 交易结果
        """
        try:
            if shares == 0:
                return {'status': 'no_trade', 'message': '无需交易'}
            
            if shares > 0:
                return self._execute_buy(stock_code, shares, price, timestamp)
            else:
                return self._execute_sell(stock_code, abs(shares), price, timestamp)
                
        except Exception as e:
            raise PositionManagementError(f"执行交易失败: {str(e)}") from e
    
    def _execute_buy(self, stock_code: str, shares: int, price: float, 
                    timestamp: datetime) -> Dict:
        """执行买入交易"""
        try:
            # 计算交易成本
            market_value = shares * price
            commission = market_value * self.params['commission_rate']
            slippage = market_value * self.params['slippage_rate']
            total_cost = market_value + commission + slippage
            
            # 检查资金是否充足
            if total_cost > self.cash:
                return {
                    'status': 'failed',
                    'message': f'资金不足: 需要{total_cost:.2f}, 可用{self.cash:.2f}'
                }
            
            # 更新持仓
            if stock_code in self.positions:
                # 加仓
                old_position = self.positions[stock_code]
                new_shares = old_position['shares'] + shares
                new_cost = old_position['total_cost'] + total_cost
                new_avg_price = new_cost / new_shares
                
                self.positions[stock_code].update({
                    'shares': new_shares,
                    'avg_price': new_avg_price,
                    'total_cost': new_cost,
                    'last_update': timestamp
                })
            else:
                # 新建仓位
                self.positions[stock_code] = {
                    'shares': shares,
                    'avg_price': price,
                    'total_cost': total_cost,
                    'first_buy_date': timestamp,
                    'last_update': timestamp
                }
            
            # 更新现金
            self.cash -= total_cost
            
            # 记录交易
            trade_record = {
                'timestamp': timestamp,
                'stock_code': stock_code,
                'action': 'BUY',
                'shares': shares,
                'price': price,
                'market_value': market_value,
                'commission': commission,
                'slippage': slippage,
                'total_cost': total_cost,
                'cash_after': self.cash
            }
            self.trade_history.append(trade_record)
            
            self.logger.info(f"买入成功: {stock_code} {shares}股 @ {price:.2f}")
            
            return {
                'status': 'success',
                'action': 'BUY',
                'shares': shares,
                'price': price,
                'total_cost': total_cost,
                'trade_record': trade_record
            }
            
        except Exception as e:
            raise PositionManagementError(f"执行买入失败: {str(e)}") from e
    
    def _execute_sell(self, stock_code: str, shares: int, price: float, 
                     timestamp: datetime) -> Dict:
        """执行卖出交易"""
        try:
            # 检查持仓
            if stock_code not in self.positions:
                return {'status': 'failed', 'message': '未持有该股票'}
            
            current_position = self.positions[stock_code]
            if shares > current_position['shares']:
                return {
                    'status': 'failed', 
                    'message': f'卖出数量超过持仓: {shares} > {current_position["shares"]}'
                }
            
            # 计算交易收入
            market_value = shares * price
            commission = market_value * self.params['commission_rate']
            slippage = market_value * self.params['slippage_rate']
            net_proceeds = market_value - commission - slippage
            
            # 计算盈亏
            cost_per_share = current_position['total_cost'] / current_position['shares']
            cost_sold = shares * cost_per_share
            pnl = net_proceeds - cost_sold
            
            # 更新持仓
            remaining_shares = current_position['shares'] - shares
            if remaining_shares > 0:
                # 部分卖出
                remaining_cost = current_position['total_cost'] - cost_sold
                self.positions[stock_code].update({
                    'shares': remaining_shares,
                    'total_cost': remaining_cost,
                    'last_update': timestamp
                })
            else:
                # 全部卖出
                del self.positions[stock_code]
            
            # 更新现金
            self.cash += net_proceeds
            
            # 记录交易
            trade_record = {
                'timestamp': timestamp,
                'stock_code': stock_code,
                'action': 'SELL',
                'shares': shares,
                'price': price,
                'market_value': market_value,
                'commission': commission,
                'slippage': slippage,
                'net_proceeds': net_proceeds,
                'pnl': pnl,
                'cash_after': self.cash
            }
            self.trade_history.append(trade_record)
            
            self.logger.info(f"卖出成功: {stock_code} {shares}股 @ {price:.2f}, 盈亏: {pnl:.2f}")
            
            return {
                'status': 'success',
                'action': 'SELL',
                'shares': shares,
                'price': price,
                'net_proceeds': net_proceeds,
                'pnl': pnl,
                'trade_record': trade_record
            }
            
        except Exception as e:
            raise PositionManagementError(f"执行卖出失败: {str(e)}") from e
    
    def update_total_value(self, current_prices: Dict[str, float]):
        """
        更新总资产价值
        
        Args:
            current_prices: 当前价格字典 {stock_code: price}
        """
        try:
            position_value = 0
            
            for stock_code, position in self.positions.items():
                if stock_code in current_prices:
                    position_value += position['shares'] * current_prices[stock_code]
                else:
                    # 如果没有当前价格，使用平均成本价
                    position_value += position['shares'] * position['avg_price']
                    self.logger.warning(f"股票 {stock_code} 缺少当前价格，使用成本价")
            
            self.total_value = self.cash + position_value
            
            self.logger.debug(f"总资产更新: 现金{self.cash:.2f} + 持仓{position_value:.2f} = {self.total_value:.2f}")
            
        except Exception as e:
            raise PositionManagementError(f"更新总资产失败: {str(e)}") from e
    
    def get_position_summary(self, current_prices: Dict[str, float] = None) -> Dict:
        """
        获取持仓摘要
        
        Args:
            current_prices: 当前价格字典
            
        Returns:
            Dict: 持仓摘要信息
        """
        try:
            if current_prices:
                self.update_total_value(current_prices)
            
            position_details = []
            total_position_value = 0
            total_pnl = 0
            
            for stock_code, position in self.positions.items():
                current_price = current_prices.get(stock_code, position['avg_price']) if current_prices else position['avg_price']
                market_value = position['shares'] * current_price
                pnl = market_value - position['total_cost']
                pnl_ratio = pnl / position['total_cost'] if position['total_cost'] > 0 else 0
                
                position_details.append({
                    'stock_code': stock_code,
                    'shares': position['shares'],
                    'avg_price': position['avg_price'],
                    'current_price': current_price,
                    'market_value': market_value,
                    'total_cost': position['total_cost'],
                    'pnl': pnl,
                    'pnl_ratio': pnl_ratio,
                    'weight': market_value / self.total_value if self.total_value > 0 else 0
                })
                
                total_position_value += market_value
                total_pnl += pnl
            
            return {
                'cash': self.cash,
                'total_position_value': total_position_value,
                'total_value': self.total_value,
                'total_pnl': total_pnl,
                'total_return': (self.total_value - self.params['initial_capital']) / self.params['initial_capital'],
                'position_count': len(self.positions),
                'cash_ratio': self.cash / self.total_value if self.total_value > 0 else 0,
                'positions': position_details
            }
            
        except Exception as e:
            raise PositionManagementError(f"获取持仓摘要失败: {str(e)}") from e
    
    def get_trade_history(self) -> List[Dict]:
        """获取交易历史"""
        return self.trade_history.copy()
    
    def reset(self):
        """重置仓位管理器"""
        self.positions.clear()
        self.cash = self.params['initial_capital']
        self.total_value = self.params['initial_capital']
        self.trade_history.clear()
        self.logger.info("仓位管理器已重置")

if __name__ == "__main__":
    # 测试代码
    logging.basicConfig(level=logging.INFO)
    
    # 测试配置
    config = {
        'initial_capital': 1000000,
        'position_size': 0.1,
        'max_positions': 5
    }
    
    # 创建仓位管理器
    pm = PositionManager(config)
    
    print("🚀 仓位管理器测试")
    print("=" * 50)
    
    try:
        # 模拟交易
        from datetime import datetime
        
        current_time = datetime.now()
        
        # 测试买入
        print("1. 测试买入计算...")
        buy_size = pm.calculate_position_size("000001", "BUY", 10.0, 0.8)
        print(f"   建议买入数量: {buy_size}股")
        
        if buy_size > 0:
            # 执行买入
            result = pm.execute_trade("000001", buy_size, 10.0, current_time)
            print(f"   买入结果: {result['status']}")
            
            # 查看持仓
            summary = pm.get_position_summary({"000001": 10.5})
            print(f"   当前总资产: {summary['total_value']:.2f}")
            print(f"   持仓数量: {summary['position_count']}")
            print(f"   现金比例: {summary['cash_ratio']:.2%}")
        
        print("✅ 仓位管理器测试完成")
        
    except Exception as e:
        print(f"❌ 测试失败: {e}")
        import traceback
        traceback.print_exc()