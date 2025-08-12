#!/usr/bin/env python3
"""
完整调查2024-04-12的回测执行流程
检查信号生成、投资组合状态、交易决策的完整链路
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

# 设置详细日志
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def investigate_complete_execution():
    """调查完整执行流程"""
    
    print("=" * 80)
    print("完整调查2024-04-12的回测执行流程")
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
        
        # 2. 检查回测历史 - 找到2024-04-12之前的最后交易状态
        print(f"\n2. 分析2024-04-12之前的投资组合状态:")
        print("-" * 50)
        
        # 从交易记录推断投资组合状态
        # 根据之前的分析，2024-03-08是最后一次交易（中国神华卖出）
        
        print("从交易记录分析2024-04-12前的持仓状态:")
        print("2023/06/21 - 神火股份买入73000股")
        print("2023/06/30 - 神火股份加仓6900股")
        print("总持仓: 79900股神火股份")
        print("2024/03/08 - 中国神华卖出（其他股票）")
        print("结论: 2024-04-12时应该持有79900股神火股份")
        
        # 3. 验证2024-04-12的信号生成
        print(f"\n3. 验证2024-04-12的信号生成:")
        print("-" * 50)
        
        date = pd.to_datetime(target_date)
        stock_weekly = engine.stock_data[stock_code]['weekly']
        historical_data = stock_weekly.loc[:date]
        
        signal_result = engine.signal_generator.generate_signal(stock_code, historical_data)
        
        print(f"✅ 信号: {signal_result['signal']}")
        print(f"✅ 原因: {signal_result.get('reason', 'N/A')}")
        
        if signal_result['signal'] == 'SELL':
            print("🎯 确认：神火股份在2024-04-12产生了SELL信号！")
        
        # 4. 检查为什么没有执行卖出交易
        print(f"\n4. 分析为什么SELL信号没有执行交易:")
        print("-" * 50)
        
        print("可能的原因分析:")
        print("1. 🔍 投资组合管理器问题:")
        print("   - 可能没有正确记录神火股份的持仓")
        print("   - 可能持仓数量为0")
        
        print("2. 🔍 轮动策略约束:")
        print("   - 可能有轮动频率限制（如每月只能交易一次）")
        print("   - 可能有最小持有期限制")
        
        print("3. 🔍 风险管理干预:")
        print("   - 可能触发了止损/止盈规则")
        print("   - 可能有最大交易次数限制")
        
        print("4. 🔍 交易执行逻辑问题:")
        print("   - 可能信号生成了但交易执行模块有bug")
        print("   - 可能有交易金额/数量的最小限制")
        
        # 5. 检查配置文件中的约束条件
        print(f"\n5. 检查配置文件中的约束条件:")
        print("-" * 50)
        
        print("回测配置:")
        for key, value in config.items():
            if isinstance(value, dict):
                print(f"  {key}:")
                for sub_key, sub_value in value.items():
                    print(f"    {sub_key}: {sub_value}")
            else:
                print(f"  {key}: {value}")
        
        # 6. 建议的解决方案
        print(f"\n6. 建议的解决方案:")
        print("-" * 50)
        print("为了彻底解决这个问题，需要:")
        print("1. 🔧 运行完整的回测并启用DEBUG级别日志")
        print("2. 🔧 在回测引擎中添加详细的执行跟踪日志")
        print("3. 🔧 检查投资组合管理器的持仓记录逻辑")
        print("4. 🔧 验证轮动策略的交易决策逻辑")
        print("5. 🔧 确认交易执行模块的完整性")
        
        # 7. 创建一个简化的回测来验证
        print(f"\n7. 建议创建简化回测验证:")
        print("-" * 50)
        print("创建一个只包含神火股份的简化回测，专门验证2024-04-12的交易执行")
        
    except Exception as e:
        print(f"调查过程中出错: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    investigate_complete_execution()
