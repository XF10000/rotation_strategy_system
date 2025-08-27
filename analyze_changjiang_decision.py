#!/usr/bin/env python3
"""
长江电力仓位决策分析工具
专门分析为什么长江电力没有被买入
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from strategy.dynamic_position_manager import DynamicPositionManager
from config.csv_config_loader import create_csv_config

def analyze_changjiang_decision():
    """分析长江电力的仓位决策"""
    
    print("🔍 分析长江电力(600900)仓位决策")
    print("=" * 50)
    
    # 长江电力的基本信息
    stock_code = "600900"
    current_price = 27.63  # 2025-08-15的价格
    dcf_value = 39.00      # DCF估值
    value_ratio = current_price / dcf_value  # 价值比
    
    print(f"📊 基本信息:")
    print(f"   股票代码: {stock_code}")
    print(f"   当前价格: {current_price:.2f} 元")
    print(f"   DCF估值: {dcf_value:.2f} 元")
    print(f"   价值比: {value_ratio:.3f} ({value_ratio*100:.1f}%)")
    
    # 判断估值区间
    if value_ratio <= 0.6:
        valuation_level = "极度低估"
    elif value_ratio <= 0.7:
        valuation_level = "明显低估"
    elif value_ratio <= 0.8:
        valuation_level = "轻度低估"
    elif value_ratio <= 1.0:
        valuation_level = "合理区间"
    elif value_ratio <= 1.2:
        valuation_level = "轻度高估"
    else:
        valuation_level = "极度高估"
    
    print(f"   估值状态: {valuation_level}")
    print()
    
    # 加载动态仓位管理器配置
    config = create_csv_config()
    position_manager = DynamicPositionManager(config.get('strategy_params', config))
    
    print("📋 动态仓位管理规则:")
    print("   极度低估(≤60%): 开仓15%, 加仓50%, 上限15%")
    print("   明显低估(60-70%): 开仓10%, 加仓20%, 上限10%")
    print("   轻度低估(70-80%): 开仓5%, 加仓10%, 上限5%")
    print()
    
    # 模拟不同现金情况下的买入决策
    total_assets = 100_000_000  # 1亿总资产
    
    print("💰 不同现金比例下的买入分析:")
    
    cash_ratios = [0.8, 0.5, 0.3, 0.1, 0.05]  # 不同现金比例情况
    
    for cash_ratio in cash_ratios:
        cash = total_assets * cash_ratio
        current_positions = {}  # 假设没有持仓
        current_prices = {stock_code: current_price}
        
        # 计算买入决策
        action_info = position_manager.get_position_action(
            'BUY', stock_code, value_ratio, 0, current_price, cash, total_assets
        )
        
        can_buy = action_info['action'] == 'BUY'
        shares = action_info.get('shares', 0)
        amount = action_info.get('estimated_cost', 0)
        reason = action_info.get('reason', '')
        
        buy_value_ratio = (amount / total_assets) if total_assets > 0 else 0
        
        print(f"   现金比例 {cash_ratio:.0%} ({cash:,.0f}元):")
        print(f"     可以买入: {can_buy}")
        print(f"     买入股数: {shares:,}")
        print(f"     买入金额: {amount:,.0f} 元")
        print(f"     占总资产: {buy_value_ratio:.1%}")
        print(f"     决策原因: {reason}")
        print()
    
    # 对比其他股票的估值优势
    print("📈 对比其他股票的估值优势:")
    
    other_stocks = [
        ("中国神华", "601088", 35.38, 45.00),  # 实际交易记录中的价格
        ("陕西煤业", "601225", 18.95, 40.00),
        ("中煤能源", "601898", 10.12, 39.00),
        ("淮北矿业", "600985", 11.25, 25.00),
    ]
    
    for name, code, price, dcf in other_stocks:
        ratio = price / dcf
        if ratio <= 0.6:
            level = "极度低估"
            rule = "开仓15%"
        elif ratio <= 0.7:
            level = "明显低估" 
            rule = "开仓10%"
        elif ratio <= 0.8:
            level = "轻度低估"
            rule = "开仓5%"
        else:
            level = "其他"
            rule = "不买入"
            
        print(f"   {name}({code}): 价值比{ratio:.1%} - {level} - {rule}")
    
    print()
    print("🎯 结论分析:")
    print("   1. 长江电力价值比70.8%，属于'轻度低估'")
    print("   2. 轻度低估的开仓比例只有5%，远低于极度低估的15%")
    print("   3. 其他煤炭股多数属于极度低估，优先级更高")
    print("   4. 在资金有限的情况下，系统会优先买入估值更低的股票")
    print("   5. 这解释了为什么单独分析显示BUY信号，但实际回测没有买入")

if __name__ == "__main__":
    analyze_changjiang_decision()