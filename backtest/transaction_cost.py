"""
交易成本计算器
计算各种交易费用：手续费、印花税、滑点等
"""

from typing import Dict, Tuple
import logging

logger = logging.getLogger(__name__)

class TransactionCostCalculator:
    """
    交易成本计算器
    
    支持的费用类型：
    1. 买入手续费
    2. 卖出手续费  
    3. 印花税（仅卖出）
    4. 滑点成本
    """
    
    def __init__(self, cost_config: Dict = None):
        """
        初始化交易成本计算器
        
        Args:
            cost_config: 费用配置字典
        """
        # 默认费用配置（基于A股市场）
        default_config = {
            'buy_commission_rate': 0.0003,    # 买入手续费率 0.03%
            'sell_commission_rate': 0.0003,   # 卖出手续费率 0.03%
            'min_commission': 5.0,            # 最低手续费 5元
            'stamp_tax_rate': 0.001,          # 印花税率 0.1%（仅卖出）
            'slippage_rate': 0.001,           # 滑点率 0.1%
            'transfer_fee_rate': 0.00002,     # 过户费率 0.002%（沪市）
        }
        
        self.config = default_config
        if cost_config:
            self.config.update(cost_config)
        
        logger.info("交易成本计算器初始化完成")
        logger.info(f"买入手续费率: {self.config['buy_commission_rate']:.4f}")
        logger.info(f"卖出手续费率: {self.config['sell_commission_rate']:.4f}")
        logger.info(f"印花税率: {self.config['stamp_tax_rate']:.4f}")
        logger.info(f"滑点率: {self.config['slippage_rate']:.4f}")
    
    def calculate_buy_cost(self, stock_code: str, shares: int, price: float) -> Dict[str, float]:
        """
        计算买入交易成本
        
        Args:
            stock_code: 股票代码
            shares: 买入股数
            price: 买入价格
            
        Returns:
            成本明细字典
        """
        gross_amount = shares * price
        
        # 手续费
        commission = max(
            gross_amount * self.config['buy_commission_rate'],
            self.config['min_commission']
        )
        
        # 过户费（仅沪市股票）
        transfer_fee = 0.0
        if stock_code.startswith('60'):  # 沪市股票
            transfer_fee = gross_amount * self.config['transfer_fee_rate']
        
        # 滑点成本
        slippage = gross_amount * self.config['slippage_rate']
        
        # 总成本
        total_cost = commission + transfer_fee + slippage
        
        cost_detail = {
            'gross_amount': gross_amount,
            'commission': commission,
            'transfer_fee': transfer_fee,
            'slippage': slippage,
            'total_cost': total_cost,
            'cost_rate': total_cost / gross_amount if gross_amount > 0 else 0
        }
        
        return cost_detail
    
    def calculate_sell_cost(self, stock_code: str, shares: int, price: float) -> Dict[str, float]:
        """
        计算卖出交易成本
        
        Args:
            stock_code: 股票代码
            shares: 卖出股数
            price: 卖出价格
            
        Returns:
            成本明细字典
        """
        gross_amount = shares * price
        
        # 手续费
        commission = max(
            gross_amount * self.config['sell_commission_rate'],
            self.config['min_commission']
        )
        
        # 印花税
        stamp_tax = gross_amount * self.config['stamp_tax_rate']
        
        # 过户费（仅沪市股票）
        transfer_fee = 0.0
        if stock_code.startswith('60'):  # 沪市股票
            transfer_fee = gross_amount * self.config['transfer_fee_rate']
        
        # 滑点成本
        slippage = gross_amount * self.config['slippage_rate']
        
        # 总成本
        total_cost = commission + stamp_tax + transfer_fee + slippage
        
        cost_detail = {
            'gross_amount': gross_amount,
            'commission': commission,
            'stamp_tax': stamp_tax,
            'transfer_fee': transfer_fee,
            'slippage': slippage,
            'total_cost': total_cost,
            'cost_rate': total_cost / gross_amount if gross_amount > 0 else 0
        }
        
        return cost_detail
    
    def calculate_rotation_cost(self, sell_stock: str, sell_shares: int, sell_price: float,
                              buy_stock: str, buy_shares: int, buy_price: float) -> Dict[str, float]:
        """
        计算轮动交易的总成本
        
        Args:
            sell_stock: 卖出股票代码
            sell_shares: 卖出股数
            sell_price: 卖出价格
            buy_stock: 买入股票代码
            buy_shares: 买入股数
            buy_price: 买入价格
            
        Returns:
            轮动成本明细
        """
        sell_cost = self.calculate_sell_cost(sell_stock, sell_shares, sell_price)
        buy_cost = self.calculate_buy_cost(buy_stock, buy_shares, buy_price)
        
        total_amount = sell_cost['gross_amount'] + buy_cost['gross_amount']
        total_cost = sell_cost['total_cost'] + buy_cost['total_cost']
        
        rotation_detail = {
            'sell_detail': sell_cost,
            'buy_detail': buy_cost,
            'total_amount': total_amount,
            'total_cost': total_cost,
            'total_cost_rate': total_cost / total_amount if total_amount > 0 else 0
        }
        
        return rotation_detail
    
    def get_cost_summary(self, transactions: list) -> Dict[str, float]:
        """
        计算交易成本汇总
        
        Args:
            transactions: 交易记录列表
            
        Returns:
            成本汇总
        """
        total_commission = 0.0
        total_stamp_tax = 0.0
        total_transfer_fee = 0.0
        total_slippage = 0.0
        total_amount = 0.0
        
        for transaction in transactions:
            if 'transaction_cost' in transaction:
                total_cost = transaction['transaction_cost']
                total_amount += transaction.get('gross_amount', 0)
                
                # 这里简化处理，实际应该从详细记录中获取
                if transaction['type'] == 'SELL':
                    # 估算各项费用（基于比例）
                    gross = transaction['gross_amount']
                    total_commission += max(gross * self.config['sell_commission_rate'], 
                                          self.config['min_commission'])
                    total_stamp_tax += gross * self.config['stamp_tax_rate']
                    total_slippage += gross * self.config['slippage_rate']
                else:  # BUY
                    gross = transaction['gross_amount']
                    total_commission += max(gross * self.config['buy_commission_rate'],
                                          self.config['min_commission'])
                    total_slippage += gross * self.config['slippage_rate']
        
        summary = {
            'total_commission': total_commission,
            'total_stamp_tax': total_stamp_tax,
            'total_transfer_fee': total_transfer_fee,
            'total_slippage': total_slippage,
            'total_cost': total_commission + total_stamp_tax + total_transfer_fee + total_slippage,
            'total_amount': total_amount,
            'average_cost_rate': (total_commission + total_stamp_tax + total_transfer_fee + total_slippage) / total_amount if total_amount > 0 else 0
        }
        
        return summary
    
    def update_config(self, new_config: Dict):
        """
        更新费用配置
        
        Args:
            new_config: 新的配置字典
        """
        self.config.update(new_config)
        logger.info("交易成本配置已更新")

if __name__ == "__main__":
    # 测试代码
    logging.basicConfig(level=logging.INFO)
    
    calculator = TransactionCostCalculator()
    
    # 测试买入成本计算
    buy_cost = calculator.calculate_buy_cost("601088", 1000, 30.0)
    print("买入成本明细:")
    for key, value in buy_cost.items():
        print(f"  {key}: {value:.2f}")
    
    print()
    
    # 测试卖出成本计算
    sell_cost = calculator.calculate_sell_cost("601088", 1000, 32.0)
    print("卖出成本明细:")
    for key, value in sell_cost.items():
        print(f"  {key}: {value:.2f}")
    
    print()
    
    # 测试轮动成本计算
    rotation_cost = calculator.calculate_rotation_cost(
        "601088", 1000, 32.0,  # 卖出
        "000807", 2000, 16.0   # 买入
    )
    print("轮动成本明细:")
    print(f"  总交易金额: {rotation_cost['total_amount']:.2f}")
    print(f"  总交易成本: {rotation_cost['total_cost']:.2f}")
    print(f"  成本率: {rotation_cost['total_cost_rate']:.4f}")