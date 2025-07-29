"""
策略基类
定义策略的基本接口和通用功能
"""

from abc import ABC, abstractmethod
from typing import Dict, List, Optional, Tuple
import pandas as pd
import logging
from datetime import datetime

from .exceptions import StrategyError, StrategyConfigError

logger = logging.getLogger(__name__)

class BaseStrategy(ABC):
    """策略基类"""
    
    def __init__(self, config: Dict):
        """
        初始化策略
        
        Args:
            config: 策略配置参数
        """
        self.config = config
        self.name = config.get('name', 'BaseStrategy')
        self.logger = logging.getLogger(f"strategy.{self.name}")
        
        # 验证配置
        self._validate_config()
        
        # 初始化状态
        self.positions = {}  # 当前持仓
        self.signals = {}    # 最新信号
        self.performance = {
            'total_return': 0.0,
            'max_drawdown': 0.0,
            'win_rate': 0.0,
            'trades_count': 0
        }
        
        self.logger.info(f"策略 {self.name} 初始化完成")
    
    @abstractmethod
    def generate_signals(self, data: Dict[str, pd.DataFrame]) -> Dict[str, str]:
        """
        生成交易信号
        
        Args:
            data: 股票数据字典 {stock_code: DataFrame}
            
        Returns:
            Dict[str, str]: 信号字典 {stock_code: signal}
        """
        pass
    
    @abstractmethod
    def calculate_position_size(self, stock_code: str, signal: str, 
                              current_price: float, account_value: float) -> float:
        """
        计算仓位大小
        
        Args:
            stock_code: 股票代码
            signal: 交易信号
            current_price: 当前价格
            account_value: 账户总值
            
        Returns:
            float: 仓位大小（股数）
        """
        pass
    
    @abstractmethod
    def should_exit_position(self, stock_code: str, data: pd.DataFrame) -> bool:
        """
        判断是否应该退出仓位
        
        Args:
            stock_code: 股票代码
            data: 股票数据
            
        Returns:
            bool: 是否退出
        """
        pass
    
    def update_positions(self, stock_code: str, action: str, 
                        quantity: float, price: float, timestamp: datetime):
        """
        更新持仓信息
        
        Args:
            stock_code: 股票代码
            action: 操作类型 ('buy', 'sell')
            quantity: 数量
            price: 价格
            timestamp: 时间戳
        """
        try:
            if stock_code not in self.positions:
                self.positions[stock_code] = {
                    'quantity': 0,
                    'avg_price': 0,
                    'total_cost': 0,
                    'last_update': timestamp
                }
            
            position = self.positions[stock_code]
            
            if action == 'buy':
                # 买入
                new_quantity = position['quantity'] + quantity
                new_cost = position['total_cost'] + quantity * price
                position['quantity'] = new_quantity
                position['total_cost'] = new_cost
                position['avg_price'] = new_cost / new_quantity if new_quantity > 0 else 0
                
            elif action == 'sell':
                # 卖出
                if position['quantity'] >= quantity:
                    position['quantity'] -= quantity
                    if position['quantity'] > 0:
                        # 按比例减少成本
                        cost_ratio = quantity / (position['quantity'] + quantity)
                        position['total_cost'] *= (1 - cost_ratio)
                    else:
                        # 全部卖出
                        position['total_cost'] = 0
                        position['avg_price'] = 0
                else:
                    raise StrategyError(f"卖出数量({quantity})超过持仓数量({position['quantity']})")
            
            position['last_update'] = timestamp
            
            # 清理空仓位
            if position['quantity'] <= 0:
                del self.positions[stock_code]
            
            self.logger.debug(f"更新持仓: {stock_code} {action} {quantity}@{price}")
            
        except Exception as e:
            raise StrategyError(f"更新持仓失败: {str(e)}") from e
    
    def get_current_positions(self) -> Dict:
        """获取当前持仓"""
        return self.positions.copy()
    
    def get_position_value(self, stock_code: str, current_price: float) -> float:
        """
        获取持仓市值
        
        Args:
            stock_code: 股票代码
            current_price: 当前价格
            
        Returns:
            float: 持仓市值
        """
        if stock_code not in self.positions:
            return 0.0
        
        return self.positions[stock_code]['quantity'] * current_price
    
    def get_position_pnl(self, stock_code: str, current_price: float) -> Tuple[float, float]:
        """
        获取持仓盈亏
        
        Args:
            stock_code: 股票代码
            current_price: 当前价格
            
        Returns:
            Tuple[float, float]: (绝对盈亏, 盈亏比例)
        """
        if stock_code not in self.positions:
            return 0.0, 0.0
        
        position = self.positions[stock_code]
        current_value = position['quantity'] * current_price
        cost = position['total_cost']
        
        pnl = current_value - cost
        pnl_ratio = pnl / cost if cost > 0 else 0.0
        
        return pnl, pnl_ratio
    
    def calculate_total_value(self, current_prices: Dict[str, float], 
                            cash: float = 0.0) -> float:
        """
        计算总资产价值
        
        Args:
            current_prices: 当前价格字典
            cash: 现金
            
        Returns:
            float: 总资产价值
        """
        total_value = cash
        
        for stock_code, position in self.positions.items():
            if stock_code in current_prices:
                total_value += position['quantity'] * current_prices[stock_code]
        
        return total_value
    
    def update_performance(self, **metrics):
        """更新策略表现指标"""
        self.performance.update(metrics)
    
    def get_performance(self) -> Dict:
        """获取策略表现"""
        return self.performance.copy()
    
    def _validate_config(self):
        """验证策略配置"""
        required_keys = ['name']
        
        for key in required_keys:
            if key not in self.config:
                raise StrategyConfigError(f"缺少必要配置项: {key}")
        
        # 验证数值参数
        numeric_params = ['max_position_ratio', 'stop_loss_ratio', 'take_profit_ratio']
        for param in numeric_params:
            if param in self.config:
                value = self.config[param]
                if not isinstance(value, (int, float)) or value <= 0:
                    raise StrategyConfigError(f"配置项 {param} 必须是正数")
    
    def reset(self):
        """重置策略状态"""
        self.positions.clear()
        self.signals.clear()
        self.performance = {
            'total_return': 0.0,
            'max_drawdown': 0.0,
            'win_rate': 0.0,
            'trades_count': 0
        }
        self.logger.info(f"策略 {self.name} 状态已重置")
    
    def get_config(self) -> Dict:
        """获取策略配置"""
        return self.config.copy()
    
    def update_config(self, new_config: Dict):
        """更新策略配置"""
        self.config.update(new_config)
        self._validate_config()
        self.logger.info(f"策略 {self.name} 配置已更新")

if __name__ == "__main__":
    # 测试代码
    logging.basicConfig(level=logging.INFO)
    
    # 创建测试配置
    test_config = {
        'name': 'TestStrategy',
        'max_position_ratio': 0.2,
        'stop_loss_ratio': 0.1
    }
    
    # 由于BaseStrategy是抽象类，这里只能测试配置验证
    try:
        # 测试配置验证
        BaseStrategy._validate_config(None, test_config)
        print("✅ 配置验证通过")
    except Exception as e:
        print(f"❌ 配置验证失败: {e}")