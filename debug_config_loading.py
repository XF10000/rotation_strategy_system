#!/usr/bin/env python3
"""
验证配置加载问题，确认价值比阈值是否正确传递
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

def verify_config_loading():
    """验证配置加载问题"""
    
    print("=" * 80)
    print("验证配置加载和价值比阈值传递")
    print("=" * 80)
    
    # 1. 检查配置文件内容
    print("1. 检查配置文件内容:")
    try:
        df = pd.read_csv('Input/Backtest_settings.csv', encoding='utf-8-sig')
        
        # 查找价值比阈值
        buy_threshold_row = df[df['Parameter'] == 'value_ratio_buy_threshold']
        sell_threshold_row = df[df['Parameter'] == 'value_ratio_sell_threshold']
        
        if not buy_threshold_row.empty:
            buy_threshold_file = float(buy_threshold_row['Value'].iloc[0])
            print(f"  配置文件中的买入阈值: {buy_threshold_file}")
        else:
            print(f"  ❌ 配置文件中没有找到value_ratio_buy_threshold")
            
        if not sell_threshold_row.empty:
            sell_threshold_file = float(sell_threshold_row['Value'].iloc[0])
            print(f"  配置文件中的卖出阈值: {sell_threshold_file}")
        else:
            print(f"  ❌ 配置文件中没有找到value_ratio_sell_threshold")
            
    except Exception as e:
        print(f"  ❌ 读取配置文件失败: {e}")
    
    # 2. 检查CSV配置加载器
    print(f"\n2. 检查CSV配置加载器:")
    config = create_csv_config()
    
    print(f"  加载的配置类型: {type(config)}")
    print(f"  配置键数量: {len(config)}")
    
    # 检查关键配置项
    key_params = [
        'value_ratio_buy_threshold',
        'value_ratio_sell_threshold',
        'total_capital',
        'start_date',
        'end_date'
    ]
    
    for param in key_params:
        value = config.get(param, 'N/A')
        print(f"  {param}: {value}")
    
    # 3. 检查回测引擎配置传递
    print(f"\n3. 检查回测引擎配置传递:")
    engine = BacktestEngine(config)
    
    print(f"  引擎配置类型: {type(engine.config)}")
    print(f"  引擎配置键数量: {len(engine.config)}")
    
    # 4. 检查信号生成器参数
    print(f"\n4. 检查信号生成器参数:")
    signal_generator = engine.signal_generator
    
    print(f"  信号生成器参数类型: {type(signal_generator.params)}")
    print(f"  信号生成器参数键数量: {len(signal_generator.params)}")
    
    # 检查价值比阈值
    buy_threshold_sg = signal_generator.params.get('value_ratio_buy_threshold', 'N/A')
    sell_threshold_sg = signal_generator.params.get('value_ratio_sell_threshold', 'N/A')
    
    print(f"  信号生成器中的买入阈值: {buy_threshold_sg}")
    print(f"  信号生成器中的卖出阈值: {sell_threshold_sg}")
    
    # 5. 对比分析
    print(f"\n5. 对比分析:")
    
    try:
        if buy_threshold_file == buy_threshold_sg:
            print(f"  ✅ 买入阈值传递正确: {buy_threshold_file}")
        else:
            print(f"  ❌ 买入阈值传递错误:")
            print(f"    配置文件: {buy_threshold_file}")
            print(f"    信号生成器: {buy_threshold_sg}")
            
        if sell_threshold_file == sell_threshold_sg:
            print(f"  ✅ 卖出阈值传递正确: {sell_threshold_file}")
        else:
            print(f"  ❌ 卖出阈值传递错误:")
            print(f"    配置文件: {sell_threshold_file}")
            print(f"    信号生成器: {sell_threshold_sg}")
            
    except:
        print(f"  无法进行对比分析")
    
    # 6. 测试神火股份的价值比判断
    print(f"\n6. 测试神火股份的价值比判断:")
    
    stock_code = '000933'
    dcf_value = 37.00
    current_price = 24.65
    value_ratio = current_price / dcf_value
    
    print(f"  股票: {stock_code}")
    print(f"  当前价格: {current_price}")
    print(f"  DCF估值: {dcf_value}")
    print(f"  价值比: {value_ratio:.3f}")
    
    print(f"\n  使用配置文件中的阈值:")
    try:
        if value_ratio > sell_threshold_file:
            print(f"    ✅ 支持卖出: {value_ratio:.3f} > {sell_threshold_file}")
        else:
            print(f"    ❌ 不支持卖出: {value_ratio:.3f} <= {sell_threshold_file}")
            
        if value_ratio < buy_threshold_file:
            print(f"    ✅ 支持买入: {value_ratio:.3f} < {buy_threshold_file}")
        else:
            print(f"    ❌ 不支持买入: {value_ratio:.3f} >= {buy_threshold_file}")
    except:
        print(f"    无法使用配置文件阈值进行判断")
    
    print(f"\n  使用信号生成器中的阈值:")
    try:
        if value_ratio > sell_threshold_sg:
            print(f"    ✅ 支持卖出: {value_ratio:.3f} > {sell_threshold_sg}")
        else:
            print(f"    ❌ 不支持卖出: {value_ratio:.3f} <= {sell_threshold_sg}")
            
        if value_ratio < buy_threshold_sg:
            print(f"    ✅ 支持买入: {value_ratio:.3f} < {buy_threshold_sg}")
        else:
            print(f"    ❌ 不支持买入: {value_ratio:.3f} >= {buy_threshold_sg}")
    except:
        print(f"    无法使用信号生成器阈值进行判断")
    
    # 7. 结论
    print(f"\n7. 结论:")
    print(f"  根据配置文件(0.65)，神火股份应该支持卖出信号")
    print(f"  如果信号生成器使用了错误的阈值，这就是问题的根源")

if __name__ == "__main__":
    verify_config_loading()
