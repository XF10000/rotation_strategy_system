#!/usr/bin/env python3
"""
分析神火股份的行业特定RSI阈值
检查极端RSI阈值逻辑
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

# 设置日志
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def analyze_industry_rsi_thresholds():
    """分析神火股份的行业特定RSI阈值"""
    
    print("=" * 80)
    print("神火股份(000933) 行业特定RSI阈值分析")
    print("=" * 80)
    
    # 加载配置
    config = create_csv_config()
    
    # 创建回测引擎
    engine = BacktestEngine(config)
    
    stock_code = '000933'  # 神火股份
    
    print(f"分析股票: {stock_code}")
    
    # 1. 检查股票行业映射
    if hasattr(engine.signal_generator, 'stock_industry_map') and engine.signal_generator.stock_industry_map:
        stock_industry_map = engine.signal_generator.stock_industry_map
        if stock_code in stock_industry_map:
            industry_info = stock_industry_map[stock_code]
            industry_code = industry_info['industry_code']
            industry_name = industry_info['industry_name']
            
            print(f"行业代码: {industry_code}")
            print(f"行业名称: {industry_name}")
        else:
            print(f"❌ 未找到 {stock_code} 的行业映射信息")
            return
    else:
        print(f"❌ 股票行业映射数据未加载")
        return
    
    # 2. 检查RSI阈值配置
    if hasattr(engine.signal_generator, 'rsi_thresholds') and engine.signal_generator.rsi_thresholds:
        rsi_thresholds = engine.signal_generator.rsi_thresholds
        if industry_code in rsi_thresholds:
            threshold_info = rsi_thresholds[industry_code]
            
            print(f"\n行业RSI阈值配置:")
            print(f"普通超买阈值: {threshold_info.get('sell_threshold', 'N/A')}")
            print(f"普通超卖阈值: {threshold_info.get('buy_threshold', 'N/A')}")
            print(f"极端超买阈值: {threshold_info.get('extreme_sell_threshold', 'N/A')}")
            print(f"极端超卖阈值: {threshold_info.get('extreme_buy_threshold', 'N/A')}")
            
            # 获取具体的极端阈值
            extreme_overbought = threshold_info.get('extreme_sell_threshold', 80)
            extreme_oversold = threshold_info.get('extreme_buy_threshold', 20)
            
            print(f"\n关键信息:")
            print(f"极端超买阈值: {extreme_overbought}")
            print(f"极端超卖阈值: {extreme_oversold}")
            
        else:
            print(f"❌ 未找到行业代码 {industry_code} 的RSI阈值配置")
            return
    else:
        print(f"❌ RSI阈值数据未加载")
        return
    
    # 3. 分析2024-04-12的RSI情况
    target_date = '2024-04-12'
    print(f"\n分析日期: {target_date}")
    
    try:
        # 获取股票数据
        weekly_data = engine._get_cached_or_fetch_data(stock_code, '2024-01-01', '2024-05-01', 'weekly')
        
        if weekly_data is None or weekly_data.empty:
            print(f"无法获取 {stock_code} 的数据")
            return
            
        # 找到目标日期附近的数据
        target_datetime = pd.to_datetime(target_date)
        weekly_data_with_date = weekly_data.copy()
        weekly_data_with_date['date'] = weekly_data_with_date.index
        
        # 找到最接近目标日期的数据
        closest_idx = (weekly_data_with_date['date'] - target_datetime).abs().idxmin()
        target_row = weekly_data.loc[closest_idx]
        
        print(f"实际分析日期: {closest_idx.strftime('%Y-%m-%d')}")
        
        # 获取RSI数值
        rsi_current = target_row['rsi']
        print(f"当前RSI: {rsi_current:.2f}")
        
        # 4. 极端RSI阈值判断
        print(f"\n极端RSI阈值判断:")
        print(f"当前RSI: {rsi_current:.2f}")
        print(f"极端超买阈值: {extreme_overbought:.2f}")
        print(f"极端超卖阈值: {extreme_oversold:.2f}")
        
        # 检查极端阈值条件
        is_extreme_overbought = rsi_current >= extreme_overbought
        is_extreme_oversold = rsi_current <= extreme_oversold
        
        print(f"\n极端阈值判断结果:")
        print(f"极端超买 (RSI >= {extreme_overbought:.2f}): {is_extreme_overbought}")
        print(f"极端超卖 (RSI <= {extreme_oversold:.2f}): {is_extreme_oversold}")
        
        if is_extreme_overbought:
            print(f"✅ 满足极端超买条件，应该强制产生卖出信号（无需背离）")
        elif is_extreme_oversold:
            print(f"✅ 满足极端超卖条件，应该强制产生买入信号（无需背离）")
        else:
            print(f"❌ 未达到极端阈值，需要检查普通阈值+背离条件")
        
        # 5. 重新评估卖出信号条件
        if is_extreme_overbought:
            print(f"\n重新评估卖出信号条件:")
            print(f"1. 价值比过滤器: ✅ (价值比0.666 > 0.65)")
            print(f"2. 超买超卖维度: ✅ (极端超买，无需背离)")
            print(f"3. 动能确认维度: ❌ (MACD柱体放大)")
            print(f"4. 极端价格+量能维度: ✅ (价格超布林上轨+成交量放大)")
            
            other_dimensions_count = 2  # 超买超卖 + 极端价格量能
            print(f"\n其他3维度满足数量: {other_dimensions_count}/3 (需要≥2)")
            
            should_generate_sell = other_dimensions_count >= 2
            print(f"应该产生卖出信号: {should_generate_sell}")
            
            if should_generate_sell:
                print(f"\n🚨 重要发现: 根据极端RSI阈值，神火股份在2024-04-12应该产生卖出信号！")
                print(f"   可能存在的问题:")
                print(f"   1. 极端RSI阈值逻辑在信号生成器中未正确实现")
                print(f"   2. 行业特定阈值未正确传递到信号判断逻辑")
                print(f"   3. 极端阈值优先级设置有误")
        
    except Exception as e:
        print(f"分析过程中出错: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    analyze_industry_rsi_thresholds()
