#!/usr/bin/env python3
"""
调查为什么回测期间没有任何交易发生
重点分析轮动策略的信号生成和交易触发机制
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

def investigate_no_trading_issue():
    """调查为什么没有交易发生"""
    
    print("=" * 80)
    print("调查为什么回测期间没有任何交易发生")
    print("=" * 80)
    
    # 加载配置
    config = create_csv_config()
    
    stock_code = '000933'  # 神火股份
    target_date = '2024-04-12'
    
    print(f"目标股票: {stock_code}")
    print(f"目标日期: {target_date}")
    
    # 关键配置参数
    print(f"\n关键配置参数:")
    print(f"  轮动比例: {config.get('rotation_percentage', 'N/A')}")
    print(f"  价值比买入阈值: {config.get('value_ratio_buy_threshold', 'N/A')}")
    print(f"  价值比卖出阈值: {config.get('value_ratio_sell_threshold', 'N/A')}")
    print(f"  最大持仓数: {config.get('max_positions', 'N/A')}")
    print(f"  股票池: {config.get('stock_pool', [])}")
    
    # 创建回测引擎
    engine = BacktestEngine(config)
    
    try:
        # 1. 检查初始持仓是如何确定的
        print(f"\n1. 分析初始持仓的确定逻辑")
        
        # 获取初始日期的数据
        start_date = config.get('start_date', '2024-03-01')
        print(f"回测开始日期: {start_date}")
        
        # 检查初始持仓选择逻辑
        print(f"初始持仓应该基于什么逻辑选择？")
        
        # 2. 分析轮动策略的触发条件
        print(f"\n2. 分析轮动策略的触发条件")
        
        # 检查轮动策略配置
        rotation_percentage = config.get('rotation_percentage', 0.1)
        print(f"轮动比例: {rotation_percentage * 100}%")
        
        if rotation_percentage == 0:
            print(f"🚨 发现问题：轮动比例为0，这意味着不会进行任何轮动交易！")
            print(f"   - 如果轮动比例为0，系统将保持初始持仓不变")
            print(f"   - 这解释了为什么没有任何买卖交易")
            return
        
        # 3. 检查信号生成是否正常工作
        print(f"\n3. 检查信号生成机制")
        
        # 获取神火股份的数据
        weekly_data = engine._get_cached_or_fetch_data(stock_code, '2024-03-01', '2024-05-01', 'weekly')
        
        if weekly_data is not None and not weekly_data.empty:
            print(f"✅ 成功获取{stock_code}的周线数据，共{len(weekly_data)}条记录")
            
            # 找到2024-04-12附近的数据
            target_datetime = pd.to_datetime(target_date)
            weekly_data_with_date = weekly_data.copy()
            weekly_data_with_date['date'] = weekly_data_with_date.index
            
            closest_idx = (weekly_data_with_date['date'] - target_datetime).abs().idxmin()
            target_row = weekly_data.loc[closest_idx]
            
            print(f"\n2024-04-12附近的数据 ({closest_idx.strftime('%Y-%m-%d')}):")
            print(f"  收盘价: {target_row['close']:.2f}")
            print(f"  RSI: {target_row.get('rsi', 'N/A')}")
            print(f"  成交量: {target_row['volume']:,.0f}")
            
            # 4. 手动测试信号生成
            print(f"\n4. 手动测试信号生成")
            
            # 获取DCF估值
            dcf_values = engine._load_dcf_values()
            if stock_code in dcf_values:
                dcf_value = dcf_values[stock_code]
                value_ratio = target_row['close'] / dcf_value
                print(f"  DCF估值: {dcf_value:.2f}")
                print(f"  价值比: {value_ratio:.3f}")
                
                # 检查价值比过滤器
                buy_threshold = config.get('value_ratio_buy_threshold', 0.7)
                sell_threshold = config.get('value_ratio_sell_threshold', 0.65)
                
                print(f"  价值比过滤器:")
                print(f"    买入阈值: {buy_threshold}")
                print(f"    卖出阈值: {sell_threshold}")
                print(f"    当前价值比: {value_ratio:.3f}")
                
                if value_ratio < buy_threshold:
                    print(f"    ✅ 支持买入信号 ({value_ratio:.3f} < {buy_threshold})")
                else:
                    print(f"    ❌ 不支持买入信号 ({value_ratio:.3f} >= {buy_threshold})")
                
                if value_ratio > sell_threshold:
                    print(f"    ✅ 支持卖出信号 ({value_ratio:.3f} > {sell_threshold})")
                else:
                    print(f"    ❌ 不支持卖出信号 ({value_ratio:.3f} <= {sell_threshold})")
            else:
                print(f"  ❌ 没有DCF估值数据")
        
        # 5. 检查轮动策略的实际执行逻辑
        print(f"\n5. 检查轮动策略的实际执行逻辑")
        
        # 检查是否有轮动策略实例
        if hasattr(engine, 'rotation_strategy'):
            print(f"✅ 回测引擎有轮动策略实例")
            
            # 检查轮动策略的配置
            rotation_strategy = engine.rotation_strategy
            print(f"轮动策略类型: {type(rotation_strategy)}")
            
        else:
            print(f"❌ 回测引擎没有轮动策略实例")
        
        # 6. 分析可能的问题原因
        print(f"\n6. 可能的问题原因分析")
        print(f"可能的原因:")
        print(f"  1. 轮动比例设置为0或很小，导致不触发轮动")
        print(f"  2. 信号生成逻辑有问题，没有产生足够强的信号")
        print(f"  3. 轮动策略的触发条件过于严格")
        print(f"  4. 初始持仓已经是最优选择，不需要调整")
        print(f"  5. 交易成本或其他约束阻止了交易")
        
        # 7. 检查具体的轮动触发逻辑
        print(f"\n7. 检查轮动触发的具体条件")
        
        # 模拟一次轮动决策
        print(f"模拟2024-04-12的轮动决策过程...")
        
        # 这里需要深入到轮动策略的内部逻辑
        # 检查是否满足轮动的最小条件
        
    except Exception as e:
        print(f"调查过程中出错: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    investigate_no_trading_issue()
