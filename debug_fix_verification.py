#!/usr/bin/env python3
"""
验证动态仓位管理器修复效果
测试神火股份在2024-04-12的SELL信号现在是否能正确执行
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

import pandas as pd
import numpy as np
from datetime import datetime
import logging

from backtest.backtest_engine import BacktestEngine
from config.csv_config_loader import create_csv_config
from strategy.dynamic_position_manager import DynamicPositionManager

# 设置详细日志
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def verify_fix():
    """验证修复效果"""
    
    print("=" * 80)
    print("验证动态仓位管理器修复效果")
    print("测试神火股份在2024-04-12的SELL信号执行")
    print("=" * 80)
    
    # 加载配置
    config = create_csv_config()
    
    # 创建回测引擎
    engine = BacktestEngine(config)
    
    target_date = '2024-04-12'
    stock_code = '000933'  # 神火股份
    
    try:
        # 1. 数据准备
        print("1. 准备数据...")
        success = engine.prepare_data()
        if not success:
            print("❌ 数据准备失败")
            return
        
        # 2. 测试信号生成
        print(f"\n2. 测试{target_date}的信号生成:")
        print("-" * 50)
        
        date = pd.to_datetime(target_date)
        stock_weekly = engine.stock_data[stock_code]['weekly']
        historical_data = stock_weekly.loc[:date]
        
        signal_result = engine.signal_generator.generate_signal(stock_code, historical_data)
        
        print(f"✅ 信号: {signal_result['signal']}")
        print(f"✅ 原因: {signal_result.get('reason', 'N/A')}")
        print(f"✅ 价值比: {signal_result.get('value_price_ratio', 'N/A'):.6f}")
        
        if signal_result['signal'] != 'SELL':
            print("❌ 信号不是SELL，无法继续测试")
            return
        
        # 3. 测试动态仓位管理器
        print(f"\n3. 测试动态仓位管理器:")
        print("-" * 50)
        
        # 创建动态仓位管理器
        position_manager = DynamicPositionManager(config)
        
        # 模拟持仓状态
        current_shares = 79900  # 从交易记录分析得出
        current_price = historical_data.iloc[-1]['close']
        value_price_ratio = signal_result.get('value_price_ratio')
        
        print(f"模拟参数:")
        print(f"  股票代码: {stock_code}")
        print(f"  当前持股: {current_shares}股")
        print(f"  当前价格: {current_price:.2f}元")
        print(f"  价值比: {value_price_ratio:.6f}")
        
        # 调用动态仓位管理器
        position_action = position_manager.get_position_action(
            signal_type='SELL',
            stock_code=stock_code,
            value_price_ratio=value_price_ratio,
            current_shares=current_shares,
            current_price=current_price,
            available_cash=1000000,  # 模拟值
            total_assets=15000000    # 模拟值
        )
        
        print(f"\n动态仓位管理器结果:")
        print(f"  操作: {position_action.get('action', 'N/A')}")
        print(f"  股数: {position_action.get('shares', 0)}")
        print(f"  原因: {position_action.get('reason', 'N/A')}")
        print(f"  应用规则: {position_action.get('rule_applied', 'N/A')}")
        
        if position_action.get('shares', 0) > 0:
            estimated_proceeds = position_action.get('estimated_proceeds', 0)
            print(f"  预计收益: {estimated_proceeds:,.2f}元")
        
        # 4. 验证修复效果
        print(f"\n4. 验证修复效果:")
        print("-" * 50)
        
        if position_action.get('action') == 'SELL' and position_action.get('shares', 0) > 0:
            print("🎉 修复成功！")
            print("✅ 信号生成器产生SELL信号")
            print("✅ 动态仓位管理器支持卖出操作")
            print("✅ 价值比0.666现在匹配到'obvious_undervalue_sell'规则")
            
            # 计算卖出比例
            sell_shares = position_action.get('shares', 0)
            sell_ratio = sell_shares / current_shares
            print(f"✅ 卖出比例: {sell_ratio:.1%} ({sell_shares}/{current_shares}股)")
            
        else:
            print("❌ 修复失败！")
            print(f"  动态仓位管理器仍然阻止卖出")
            print(f"  操作: {position_action.get('action')}")
            print(f"  原因: {position_action.get('reason')}")
        
        # 5. 检查配置加载
        print(f"\n5. 检查配置加载:")
        print("-" * 50)
        
        print("动态仓位管理器的卖出规则:")
        for rule_name, rule in position_manager.position_config['sell_rules'].items():
            min_ratio, max_ratio = rule['range']
            sell_ratio = rule['sell_ratio']
            print(f"  {rule_name}: 价值比({min_ratio:.2f}, {max_ratio:.2f}] -> 卖出{sell_ratio:.0%}")
            
            # 检查神火股份是否匹配此规则
            if min_ratio < value_price_ratio <= max_ratio:
                print(f"    🎯 神火股份价值比{value_price_ratio:.3f}匹配此规则！")
        
        # 6. 运行完整回测验证（可选）
        print(f"\n6. 建议运行完整回测验证:")
        print("-" * 50)
        print("现在可以运行 python3 main.py 来验证完整回测中的交易执行")
        print("预期结果：神火股份在2024-04-12应该会产生卖出交易记录")
        
    except Exception as e:
        print(f"验证过程中出错: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    verify_fix()
