"""
动态仓位管理器
基于价值比(value_price_ratio)的动态仓位管理系统
"""

import pandas as pd
import numpy as np
from typing import Dict, List, Tuple, Optional
import logging
from datetime import datetime

logger = logging.getLogger(__name__)

class DynamicPositionManager:
    """
    基于价值比的动态仓位管理器
    
    根据股票的价值比(DCF估值/当前价格)动态调整买卖比例：
    - 极度低估(≤0.60): 大幅加仓/开仓
    - 明显低估(0.60-0.70): 适度加仓/开仓  
    - 轻度低估(0.70-0.80): 小幅加仓/开仓
    - 合理区间(0.80-1.00): 持有
    - 轻度高估(1.00-1.20): 减仓
    - 极度高估(>1.20): 大幅减仓/清仓
    """
    
    def __init__(self, config: Dict):
        """
        初始化动态仓位管理器
        
        Args:
            config: 包含动态仓位管理参数的配置字典
        """
        self.config = config
        self.logger = logging.getLogger("strategy.DynamicPositionManager")
        
        # 从配置中加载动态仓位管理参数
        self.position_config = self._load_position_config(config)
        
        # 风险控制参数 - 从配置中读取
        self.max_single_position_ratio = config.get('max_single_stock_ratio', 0.20)  # 单股总仓位上限20%（核心约束）
        self.cash_insufficient_ratio = config.get('cash_insufficient_ratio', 0.80)    # 现金不足时使用现金的比例80%
"""
动态仓位管理器
基于价值比(value_price_ratio)的动态仓位管理系统
"""

import pandas as pd
import numpy as np
from typing import Dict, List, Tuple, Optional
import logging
from datetime import datetime

logger = logging.getLogger(__name__)

class DynamicPositionManager:
    """
    基于价值比的动态仓位管理器
    
    根据股票的价值比(DCF估值/当前价格)动态调整买卖比例：
    - 极度低估(≤0.60): 大幅加仓/开仓
    - 明显低估(0.60-0.70): 适度加仓/开仓  
    - 轻度低估(0.70-0.80): 小幅加仓/开仓
    - 合理区间(0.80-1.00): 持有
    - 轻度高估(1.00-1.20): 减仓
    - 极度高估(>1.20): 大幅减仓/清仓
    """
    
    def __init__(self, config: Dict):
        """
        初始化动态仓位管理器
        
        Args:
            config: 包含动态仓位管理参数的配置字典
        """
        self.config = config
        self.logger = logging.getLogger("strategy.DynamicPositionManager")
        
        # 从配置中加载动态仓位管理参数
        self.position_config = self._load_position_config(config)
        
"""
动态仓位管理器
基于价值比(value_price_ratio)的动态仓位管理系统
"""

import pandas as pd
import numpy as np
from typing import Dict, List, Tuple, Optional
import logging
from datetime import datetime

logger = logging.getLogger(__name__)

class DynamicPositionManager:
    """
    基于价值比的动态仓位管理器
    
    根据股票的价值比(DCF估值/当前价格)动态调整买卖比例：
    - 极度低估(≤0.60): 大幅加仓/开仓
    - 明显低估(0.60-0.70): 适度加仓/开仓  
    - 轻度低估(0.70-0.80): 小幅加仓/开仓
    - 合理区间(0.80-1.00): 持有
    - 轻度高估(1.00-1.20): 减仓
    - 极度高估(>1.20): 大幅减仓/清仓
    """
    
    def __init__(self, config: Dict):
        """
        初始化动态仓位管理器
        
        Args:
            config: 包含动态仓位管理参数的配置字典
        """
        self.config = config
        self.logger = logging.getLogger("strategy.DynamicPositionManager")
        
        # 从配置中加载动态仓位管理参数
        self.position_config = self._load_position_config(config)
        
        # 风险控制参数 - 从配置中读取
        self.max_single_position_ratio = config.get('max_single_stock_ratio', 0.20)  # 单股总仓位上限20%（核心约束）
        self.cash_insufficient_ratio = config.get('cash_insufficient_ratio', 0.80)    # 现金不足时使用现金的比例80%
        
        self.logger.info("动态仓位管理器初始化完成")
        self.logger.info(f"配置参数: {self.position_config}")
        self.logger.info(f"风险控制: 单股上限{float(self.max_single_position_ratio):.0%}, 现金不足比例{float(self.cash_insufficient_ratio):.0%}")
    
    def _load_position_config(self, config: Dict) -> Dict:
        """
        从配置中加载仓位管理参数
        
        Args:
            config: 配置字典
            
        Returns:
            Dict: 仓位管理配置
        """
        position_config = {
            # 买入配置
            'buy_rules': {
                'extreme_undervalue': {
                    'range': (0.0, 0.60),
                    'add_ratio': config.get('extreme_undervalue_add_ratio', 0.50),
                    'new_ratio': config.get('extreme_undervalue_new_ratio', 0.15),  # 修正：15%总资产
                    'asset_limit': config.get('extreme_undervalue_asset_limit', 0.15)
                },
                'obvious_undervalue': {
                    'range': (0.60, 0.70),
                    'add_ratio': config.get('obvious_undervalue_add_ratio', 0.20),
                    'new_ratio': config.get('obvious_undervalue_new_ratio', 0.10),  # 修正：10%总资产
                    'asset_limit': config.get('obvious_undervalue_asset_limit', 0.10)
                },
                'slight_undervalue': {
                    'range': (0.70, 0.80),
                    'add_ratio': config.get('slight_undervalue_add_ratio', 0.10),
                    'new_ratio': config.get('slight_undervalue_new_ratio', 0.05),  # 修正：5%总资产
                    'asset_limit': config.get('slight_undervalue_asset_limit', 0.05)
                }
            },
            # 卖出配置
            'sell_rules': {
                'extreme_overvalue': {
                    'range': (1.20, float('inf')),
                    'sell_ratio': config.get('extreme_overvalue_sell_ratio', 1.00)
                },
                'slight_overvalue': {
                    'range': (1.00, 1.20),
                    'sell_ratio': config.get('slight_overvalue_sell_ratio', 0.80)
                },
                'fair_value': {
                    'range': (0.80, 1.00),
                    'sell_ratio': config.get('fair_value_sell_ratio', 0.50)
                },
                'slight_undervalue_sell': {
                    'range': (0.70, 0.80),
                    'sell_ratio': config.get('slight_undervalue_sell_ratio', 0.20)
                }
            }
        }
        
        return position_config
    
    def get_position_action(self, signal_type: str, stock_code: str, value_price_ratio: float, 
                           current_shares: int, current_price: float, 
                           available_cash: float, total_assets: float) -> Dict:
        """
        根据信号类型和价值比确定仓位操作
        
        Args:
            signal_type: 信号类型 ('BUY', 'SELL', 'HOLD')
            stock_code: 股票代码
            value_price_ratio: 价值比 (当前价格/DCF估值)
            current_shares: 当前持股数量
            current_price: 当前价格
            available_cash: 可用现金
            total_assets: 总资产
            
        Returns:
            Dict: 仓位操作信息
        """
        try:
            # 根据4D信号类型决定操作方向
            if signal_type == 'BUY':
                # 买入信号：根据价值比决定买入强度
                return self._calculate_buy_action(
                    stock_code, value_price_ratio, current_shares, 
                    current_price, available_cash, total_assets
                )
            elif signal_type == 'SELL':
                # 卖出信号：根据价值比决定卖出比例
                return self._calculate_sell_action(
                    stock_code, value_price_ratio, current_shares, current_price
                )
            else:
                # HOLD信号或其他情况
                return {
                    'action': 'HOLD',
                    'shares': 0,
                    'reason': f'信号类型为 {signal_type}，无需交易'
                }
                
        except Exception as e:
            self.logger.error(f"计算仓位操作失败 {stock_code}: {str(e)}")
            return {
                'action': 'HOLD',
                'shares': 0,
                'reason': f'计算失败: {str(e)}'
            }
    
    def _calculate_buy_action(self, stock_code: str, value_price_ratio: float,
                             current_shares: int, current_price: float,
                             available_cash: float, total_assets: float) -> Dict:
        """
        计算买入操作
        
        Args:
            stock_code: 股票代码
            value_price_ratio: 价值比
            current_shares: 当前持股数量
            current_price: 当前价格
            available_cash: 可用现金
            total_assets: 总资产
            
        Returns:
            Dict: 买入操作信息
        """
        # 确定买入档位
        buy_rule = None
        rule_name = ""
        
        for rule_name, rule in self.position_config['buy_rules'].items():
            min_ratio, max_ratio = rule['range']
            if min_ratio <= value_price_ratio <= max_ratio:
                buy_rule = rule
                break
        
        if not buy_rule:
            return {
                'action': 'HOLD',
                'shares': 0,
                'reason': f'价值比 {value_price_ratio:.3f} 不在买入范围内'
            }
        
        # 第一步：基于估值水平和现金情况确定基础买入金额
        if current_shares > 0:
            # 已持有：现金充足性检查
            current_position_value = current_shares * current_price
            required_cash = current_position_value * buy_rule['add_ratio']
            
            if available_cash >= required_cash:
                # 现金充足：按比例加仓
                base_cash_amount = required_cash
                reason = f"加仓 {buy_rule['add_ratio']:.0%}持仓价值 ({rule_name})"
            else:
                # 现金不足：使用配置的现金比例
                base_cash_amount = available_cash * self.cash_insufficient_ratio
                reason = f"现金不足，加仓{self.cash_insufficient_ratio:.0%}现金 ({rule_name})"
        else:
            # 未持有：现金充足性检查
            target_asset_amount = total_assets * buy_rule['new_ratio']
            
            if available_cash >= target_asset_amount:
                # 现金充足：按总资产比例开仓
                base_cash_amount = target_asset_amount
                reason = f"开仓 {buy_rule['new_ratio']:.0%}总资产 ({rule_name})"
            else:
                # 现金不足：使用配置的现金比例
                base_cash_amount = available_cash * self.cash_insufficient_ratio
                reason = f"现金不足，开仓{self.cash_insufficient_ratio:.0%}现金 ({rule_name})"
        
        # 检查单笔交易上限
        max_asset_amount = total_assets * buy_rule['asset_limit']
        base_cash_amount = min(base_cash_amount, max_asset_amount)
        
        # 转换为股数
        base_shares = int(base_cash_amount / current_price)
        
        # 调整为100股整数倍
        base_shares = (base_shares // 100) * 100
        
        # 第二步：应用总仓位限制（硬性约束）
        current_position_value = current_shares * current_price
        max_total_position_value = total_assets * self.max_single_position_ratio  # 20%总资产上限
        
        # 计算剩余可买入空间
        remaining_capacity_value = max_total_position_value - current_position_value
        
        # 如果当前持仓已达到或超过20%，则不执行买入
        if remaining_capacity_value <= 0:
            return {
                'action': 'HOLD',
                'shares': 0,
                'reason': f'已达到单股总仓位上限20% (当前{current_position_value/total_assets:.1%})'
            }
        
        # 计算剩余空间对应的股数
        max_additional_shares = int(remaining_capacity_value / current_price)
        max_additional_shares = (max_additional_shares // 100) * 100  # 调整为100股整数倍
        
        # 最终买入股数 = min(基础买入股数, 剩余空间股数)
        target_shares = min(base_shares, max_additional_shares)
        
        # 检查最小交易量和资金充足性
        if target_shares < 100:
            return {
                'action': 'HOLD',
                'shares': 0,
                'reason': f'计算股数 {target_shares} 少于100股最小交易单位 (基础{base_shares}, 空间{max_additional_shares})'
            }
        
        required_cash = target_shares * current_price
        if required_cash > available_cash:
            return {
                'action': 'HOLD',
                'shares': 0,
                'reason': f'资金不足: 需要 {required_cash:,.0f}, 可用 {available_cash:,.0f}'
            }
        
        # 更新原因说明，包含总仓位限制信息
        if target_shares < base_shares:
            reason += f" (受20%总仓位上限约束，实际买入{target_shares}股)"
        
        return {
            'action': 'BUY',
            'shares': target_shares,
            'estimated_cost': required_cash,
            'reason': reason,
            'value_ratio': value_price_ratio,
            'rule_applied': rule_name
        }
    
    def _calculate_sell_action(self, stock_code: str, value_price_ratio: float,
                              current_shares: int, current_price: float) -> Dict:
        """
        计算卖出操作
        
        Args:
            stock_code: 股票代码
            value_price_ratio: 价值比
            current_shares: 当前持股数量
            current_price: 当前价格
            
        Returns:
            Dict: 卖出操作信息
        """
        # 如果没有持仓，无法卖出
        if current_shares <= 0:
            return {
                'action': 'HOLD',
                'shares': 0,
                'reason': '无持仓，无法卖出'
            }
        
        # 确定卖出档位
        sell_rule = None
        rule_name = ""
        
        for rule_name, rule in self.position_config['sell_rules'].items():
            min_ratio, max_ratio = rule['range']
            if min_ratio < value_price_ratio <= max_ratio:
                sell_rule = rule
                break
        
        if not sell_rule:
            return {
                'action': 'HOLD',
                'shares': 0,
                'reason': f'价值比 {value_price_ratio:.3f} 不在卖出范围内'
            }
        
        # 计算卖出股数
        target_shares = int(current_shares * sell_rule['sell_ratio'])
        
        # 调整为100股整数倍
        target_shares = (target_shares // 100) * 100
        
        # 确保不超过持仓数量
        target_shares = min(target_shares, current_shares)
        
        # 检查最小交易量
        if target_shares < 100:
            return {
                'action': 'HOLD',
                'shares': 0,
                'reason': f'计算股数 {target_shares} 少于100股最小交易单位'
            }
        
        estimated_proceeds = target_shares * current_price
        reason = f"减仓 {sell_rule['sell_ratio']:.0%} ({rule_name})"
        
        return {
            'action': 'SELL',
            'shares': target_shares,
            'estimated_proceeds': estimated_proceeds,
            'reason': reason,
            'value_ratio': value_price_ratio,
            'rule_applied': rule_name
        }
    
    def validate_trade_constraints(self, action_info: Dict, current_shares: int,
                                 available_cash: float, current_price: float = None,
                                 total_assets: float = None) -> Tuple[bool, str]:
        """
        验证交易约束条件
        
        Args:
            action_info: 交易操作信息
            current_shares: 当前持股数量
            available_cash: 可用现金
            current_price: 当前价格（用于总仓位检查）
            total_assets: 总资产（用于总仓位检查）
            
        Returns:
            Tuple[bool, str]: (是否通过验证, 验证信息)
        """
        try:
            if action_info['action'] == 'HOLD':
                return True, "无需交易"
            
            if action_info['action'] == 'BUY':
                # 验证买入约束
                required_cash = action_info.get('estimated_cost', 0)
                if required_cash > available_cash:
                    return False, f"现金不足: 需要 {required_cash:,.0f}, 可用 {available_cash:,.0f}"
                
                if action_info['shares'] < 100:
                    return False, "买入股数少于100股最小交易单位"
                
                # 验证总仓位限制（如果提供了价格和总资产信息）
                if current_price and total_assets:
                    current_position_value = current_shares * current_price
                    new_position_value = (current_shares + action_info['shares']) * current_price
                    new_position_ratio = new_position_value / total_assets
                    
                    if new_position_ratio > self.max_single_position_ratio:
                        return False, f"超出单股总仓位上限{self.max_single_position_ratio:.0%}: 交易后将达到{new_position_ratio:.1%}"
                
                
                return True, f"买入验证通过: {action_info['shares']}股"
            
            elif action_info['action'] == 'SELL':
                # 验证卖出约束
                if action_info['shares'] > current_shares:
                    return False, f"卖出股数超过持仓: {action_info['shares']} > {current_shares}"
                
                if action_info['shares'] < 100:
                    return False, "卖出股数少于100股最小交易单位"
                
                return True, f"卖出验证通过: {action_info['shares']}股"
            
            return False, f"未知操作类型: {action_info['action']}"
            
        except Exception as e:
            return False, f"验证失败: {str(e)}"
    
    def get_position_summary(self) -> Dict:
        """
        获取仓位管理配置摘要
        
        Returns:
            Dict: 配置摘要
        """
        summary = {
            'buy_rules_count': len(self.position_config['buy_rules']),
            'sell_rules_count': len(self.position_config['sell_rules']),
            'buy_rules': {},
            'sell_rules': {}
        }
        
        # 买入规则摘要
        for rule_name, rule in self.position_config['buy_rules'].items():
            summary['buy_rules'][rule_name] = {
                'range': f"{rule['range'][0]:.2f}-{rule['range'][1]:.2f}",
                'add_ratio': f"{rule['add_ratio']:.0%}",
                'new_ratio': f"{rule['new_ratio']:.0%}",
                'asset_limit': f"{rule['asset_limit']:.0%}"
            }
        
        # 卖出规则摘要
        for rule_name, rule in self.position_config['sell_rules'].items():
            range_max = "∞" if rule['range'][1] == float('inf') else f"{rule['range'][1]:.2f}"
            summary['sell_rules'][rule_name] = {
                'range': f"{rule['range'][0]:.2f}-{range_max}",
                'sell_ratio': f"{rule['sell_ratio']:.0%}"
            }
        
        return summary

if __name__ == "__main__":
    # 测试代码
    logging.basicConfig(level=logging.INFO)
    
    # 测试配置
    test_config = {
        'extreme_undervalue_add_ratio': 0.50,
        'extreme_undervalue_new_ratio': 0.40,
        'extreme_undervalue_asset_limit': 0.15,
        'obvious_undervalue_add_ratio': 0.20,
        'obvious_undervalue_new_ratio': 0.20,
        'obvious_undervalue_asset_limit': 0.10,
        'slight_undervalue_add_ratio': 0.10,
        'slight_undervalue_new_ratio': 0.10,
        'slight_undervalue_asset_limit': 0.05,
        'extreme_overvalue_sell_ratio': 1.00,
        'slight_overvalue_sell_ratio': 0.80,
        'fair_value_sell_ratio': 0.50,
        'slight_undervalue_sell_ratio': 0.20
    }
    
    # 创建动态仓位管理器
    dpm = DynamicPositionManager(test_config)
    
    print("🚀 动态仓位管理器测试")
    print("=" * 50)
    
    try:
        # 测试买入场景
        print("1. 测试极度低估买入...")
        action = dpm.get_position_action(
            stock_code="000001",
            value_price_ratio=0.55,  # 极度低估
            current_shares=0,        # 无持仓
            current_price=10.0,
            available_cash=500000,
            total_assets=1000000
        )
        print(f"   操作: {action['action']}")
        print(f"   股数: {action['shares']}")
        print(f"   原因: {action['reason']}")
        
        # 测试加仓场景
        print("\n2. 测试明显低估加仓...")
        action = dpm.get_position_action(
            stock_code="000002",
            value_price_ratio=0.65,  # 明显低估
            current_shares=10000,    # 已持仓
            current_price=15.0,
            available_cash=300000,
            total_assets=1000000
        )
        print(f"   操作: {action['action']}")
        print(f"   股数: {action['shares']}")
        print(f"   原因: {action['reason']}")
        
        # 测试卖出场景
        print("\n3. 测试极度高估卖出...")
        action = dpm.get_position_action(
            stock_code="000003",
            value_price_ratio=1.35,  # 极度高估
            current_shares=5000,     # 已持仓
            current_price=20.0,
            available_cash=200000,
            total_assets=1000000
        )
        print(f"   操作: {action['action']}")
        print(f"   股数: {action['shares']}")
        print(f"   原因: {action['reason']}")
        
        # 显示配置摘要
        print("\n4. 配置摘要:")
        summary = dpm.get_position_summary()
        print(f"   买入规则数: {summary['buy_rules_count']}")
        print(f"   卖出规则数: {summary['sell_rules_count']}")
        
        print("\n✅ 动态仓位管理器测试完成")
        
    except Exception as e:
        print(f"❌ 测试失败: {e}")
        import traceback
        traceback.print_exc()