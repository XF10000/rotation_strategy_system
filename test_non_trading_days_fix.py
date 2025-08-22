#!/usr/bin/env python3
"""
测试非交易日期间数据获取修复效果
"""

import sys
import os
import pandas as pd
import logging
from datetime import datetime

# 添加项目路径
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from backtest.backtest_engine import BacktestEngine
from config.backtest_configs import DEFAULT_COST_CONFIG, DEFAULT_STRATEGY_PARAMS

# 设置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

def test_non_trading_days_fix():
    """测试非交易日期间的修复效果"""
    
    print("=" * 80)
    print("🧪 测试非交易日期间数据获取修复效果")
    print("=" * 80)
    
    # 测试场景1：国庆长假期间 (2024年10月1日-7日)
    print("\n📅 测试场景1：国庆长假期间回测 (2024-10-01 到 2024-10-07)")
    print("-" * 60)
    
    try:
        # 创建测试配置
        config = {
            'start_date': '2024-10-01',
            'end_date': '2024-10-07',
            'total_capital': 100000,
            'initial_holdings': {
                '000001': 0.5,  # 平安银行
                '600036': 0.3,  # 招商银行
                '000002': 0.2,  # 万科A
                'cash': 0.0
            },
            'cost_config': DEFAULT_COST_CONFIG,
            'strategy_params': DEFAULT_STRATEGY_PARAMS
        }
        
        # 创建回测引擎
        engine = BacktestEngine(config)
        
        print(f"✅ 回测引擎创建成功")
        print(f"📊 股票池: {engine.stock_pool}")
        
        # 测试数据准备阶段
        print(f"\n🔄 开始数据准备...")
        engine.prepare_data()
        
        print(f"✅ 数据准备完成")
        print(f"📈 成功加载的股票数据: {len(engine.stock_data)}")
        
        # 显示每只股票的数据情况
        for stock_code, data in engine.stock_data.items():
            if data is not None and not data.empty:
                print(f"  📊 {stock_code}: {len(data)} 条记录 "
                      f"({data.index.min().strftime('%Y-%m-%d')} 到 "
                      f"{data.index.max().strftime('%Y-%m-%d')})")
            else:
                print(f"  ❌ {stock_code}: 无数据")
        
        # 如果有数据，尝试运行回测
        if len(engine.stock_data) > 0:
            print(f"\n🚀 尝试运行回测...")
            results = engine.run_backtest()
            
            if results:
                print(f"✅ 回测成功完成")
                print(f"📈 最终资产价值: ¥{results.get('final_value', 0):,.2f}")
                print(f"📊 总收益率: {results.get('total_return', 0)*100:.2f}%")
            else:
                print(f"⚠️ 回测运行但无结果返回")
        else:
            print(f"❌ 无可用数据，无法进行回测")
            
    except Exception as e:
        print(f"❌ 测试失败: {e}")
        import traceback
        traceback.print_exc()
    
    # 测试场景2：春节假期期间
    print(f"\n" + "=" * 80)
    print("📅 测试场景2：春节假期期间回测 (2024-02-10 到 2024-02-17)")
    print("-" * 60)
    
    try:
        config2 = {
            'start_date': '2024-02-10',
            'end_date': '2024-02-17',
            'total_capital': 100000,
            'initial_holdings': {
                '000001': 1.0,  # 只测试一只股票
                'cash': 0.0
            },
            'cost_config': DEFAULT_COST_CONFIG,
            'strategy_params': DEFAULT_STRATEGY_PARAMS
        }
        
        engine2 = BacktestEngine(config2)
        print(f"✅ 春节测试引擎创建成功")
        
        engine2.prepare_data()
        print(f"✅ 春节期间数据准备完成")
        print(f"📈 成功加载的股票数据: {len(engine2.stock_data)}")
        
        for stock_code, data in engine2.stock_data.items():
            if data is not None and not data.empty:
                print(f"  📊 {stock_code}: {len(data)} 条记录")
            else:
                print(f"  ❌ {stock_code}: 无数据")
                
    except Exception as e:
        print(f"❌ 春节测试失败: {e}")
    
    print(f"\n" + "=" * 80)
    print("🎯 测试总结")
    print("=" * 80)
    print("✅ 修复后的系统应该能够:")
    print("   1. 自动检测纯非交易日期间")
    print("   2. 智能扩展日期范围获取数据")
    print("   3. 避免因假期而完全跳过股票")
    print("   4. 提供详细的处理日志")

if __name__ == "__main__":
    test_non_trading_days_fix()
