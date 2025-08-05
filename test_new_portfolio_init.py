#!/usr/bin/env python3
"""
测试新的投资组合初始化逻辑
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

import logging
from backtest.backtest_engine import BacktestEngine

# 设置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

def test_new_portfolio_initialization():
    """测试新的投资组合初始化逻辑"""
    
    # 配置参数
    config = {
        'start_date': '2021-01-08',
        'end_date': '2021-01-15',  # 短期测试
        'total_capital': 1000000,
        'initial_holdings': {
            '601088': 0.1,  # 中国神华 10%
            '000807': 0.1,  # 云铝股份 10%
            '002460': 0.0,  # 赣锋锂业 0%（测试0权重）
            'cash': 0.8     # 现金 80%（这个值将被忽略，由计算得出）
        },
        'strategy_params': {
            'rotation_percentage': 0.1
        },
        'cost_config': {
            'commission_rate': 0.0003,
            'min_commission': 5.0,
            'stamp_tax_rate': 0.001
        }
    }
    
    print("=" * 60)
    print("测试新的投资组合初始化逻辑")
    print("=" * 60)
    
    # 创建回测引擎
    engine = BacktestEngine(config)
    
    # 准备数据
    print("\n1. 准备数据...")
    if not engine.prepare_data():
        print("❌ 数据准备失败")
        return False
    
    # 初始化投资组合
    print("\n2. 初始化投资组合...")
    if not engine.initialize_portfolio():
        print("❌ 投资组合初始化失败")
        return False
    
    # 验证结果
    print("\n3. 验证初始化结果...")
    portfolio_manager = engine.portfolio_manager
    
    print(f"总资产: {config['total_capital']:,.2f}")
    print(f"现金: {portfolio_manager.cash:,.2f}")
    print(f"持仓: {portfolio_manager.holdings}")
    
    # 计算各股票市值
    total_stock_value = 0
    for stock_code, shares in portfolio_manager.holdings.items():
        if stock_code in portfolio_manager.initial_prices:
            price = portfolio_manager.initial_prices[stock_code]
            market_value = shares * price
            total_stock_value += market_value
            print(f"{stock_code}: {shares:,}股 × {price:.2f} = {market_value:,.2f}")
    
    print(f"总股票市值: {total_stock_value:,.2f}")
    print(f"现金 + 股票市值: {portfolio_manager.cash + total_stock_value:,.2f}")
    
    # 验证总价值是否等于总资产
    total_calculated = portfolio_manager.cash + total_stock_value
    difference = abs(total_calculated - config['total_capital'])
    
    print(f"\n验证结果:")
    print(f"计算总价值: {total_calculated:,.2f}")
    print(f"目标总资产: {config['total_capital']:,.2f}")
    print(f"差异: {difference:.2f}")
    print(f"验证: {'✓ 通过' if difference < 0.01 else '✗ 失败'}")
    
    # 特别检查云铝股份的持仓
    if '000807' in portfolio_manager.holdings:
        yunlv_shares = portfolio_manager.holdings['000807']
        yunlv_price = portfolio_manager.initial_prices['000807']
        yunlv_value = yunlv_shares * yunlv_price
        print(f"\n云铝股份详情:")
        print(f"持仓: {yunlv_shares:,}股")
        print(f"价格: {yunlv_price:.2f}")
        print(f"市值: {yunlv_value:,.2f}")
        print(f"预期应该是 224,200 股（如果价格是 6.69）")
    
    return True

if __name__ == "__main__":
    test_new_portfolio_initialization()