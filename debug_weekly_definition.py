#!/usr/bin/env python3
"""
调试周线定义差异
分析我们的周线划分与主流软件的差异
"""

import pandas as pd
import numpy as np
import logging
from datetime import datetime, timedelta
import sys
import os

# 添加项目路径
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from data.data_fetcher import AkshareDataFetcher
from data.data_processor import DataProcessor

# 设置日志
logging.basicConfig(level=logging.INFO)

def analyze_weekly_definition():
    """分析周线定义差异"""
    print("🔍 分析周线定义差异 - 601898在2024年3月8日前后")
    print("=" * 60)
    
    try:
        # 获取数据
        fetcher = AkshareDataFetcher()
        processor = DataProcessor()
        
        # 获取2024年2月-3月的日线数据
        daily_data = fetcher.get_stock_data('601898', '2024-02-01', '2024-03-31', 'daily')
        if daily_data is None or daily_data.empty:
            print("❌ 数据获取失败")
            return
        
        print(f"✅ 获取到 {len(daily_data)} 条日线数据")
        
        # 显示2024年3月8日前后的日线数据
        target_date = pd.to_datetime('2024-03-08')
        print(f"\n📅 2024年3月8日前后的日线数据:")
        
        for i in range(len(daily_data)):
            date = daily_data.index[i]
            if abs((date - target_date).days) <= 7:  # 前后一周
                row = daily_data.iloc[i]
                weekday = date.strftime('%A')
                marker = "👉" if date.date() == target_date.date() else "  "
                print(f"{marker} {date.strftime('%Y-%m-%d')} ({weekday}): 收盘={row['close']:.2f}, 成交量={row['volume']:,}")
        
        # 我们的周线划分方法
        print(f"\n🔧 我们的周线划分方法:")
        weekly_data = processor.resample_to_weekly(daily_data)
        
        # 找到包含3月8日的周线
        for i in range(len(weekly_data)):
            week_start = weekly_data.index[i]
            week_end = week_start + pd.Timedelta(days=6)
            
            if week_start <= target_date <= week_end:
                row = weekly_data.iloc[i]
                print(f"包含3月8日的周线:")
                print(f"  周期: {week_start.strftime('%Y-%m-%d')} - {week_end.strftime('%Y-%m-%d')}")
                print(f"  开盘: {row['open']:.2f}")
                print(f"  最高: {row['high']:.2f}")
                print(f"  最低: {row['low']:.2f}")
                print(f"  收盘: {row['close']:.2f}")
                print(f"  成交量: {row['volume']:,}")
                break
        
        # 尝试不同的周线划分方法
        print(f"\n🔄 尝试不同的周线划分方法:")
        
        # 方法1: 按交易周划分 (周一到周五)
        print(f"\n方法1: 按交易周划分")
        trading_weekly = daily_data.resample('W-FRI').agg({
            'open': 'first',
            'high': 'max',
            'low': 'min',
            'close': 'last',
            'volume': 'sum',
            'amount': 'sum'
        }).dropna()
        
        # 找到包含3月8日的交易周
        for i in range(len(trading_weekly)):
            week_end = trading_weekly.index[i]
            week_start = week_end - pd.Timedelta(days=4)  # 周一
            
            if week_start <= target_date <= week_end:
                row = trading_weekly.iloc[i]
                print(f"  交易周期: {week_start.strftime('%Y-%m-%d')} - {week_end.strftime('%Y-%m-%d')}")
                print(f"  收盘: {row['close']:.2f}")
                break
        
        # 方法2: 按自然周划分 (周日到周六)
        print(f"\n方法2: 按自然周划分")
        natural_weekly = daily_data.resample('W-SAT').agg({
            'open': 'first',
            'high': 'max',
            'low': 'min',
            'close': 'last',
            'volume': 'sum',
            'amount': 'sum'
        }).dropna()
        
        # 找到包含3月8日的自然周
        for i in range(len(natural_weekly)):
            week_end = natural_weekly.index[i]
            week_start = week_end - pd.Timedelta(days=6)  # 周日
            
            if week_start <= target_date <= week_end:
                row = natural_weekly.iloc[i]
                print(f"  自然周期: {week_start.strftime('%Y-%m-%d')} - {week_end.strftime('%Y-%m-%d')}")
                print(f"  收盘: {row['close']:.2f}")
                break
        
        # 检查数据源差异
        print(f"\n📊 检查akshare数据的准确性:")
        march_8_data = daily_data.loc[daily_data.index.date == target_date.date()]
        if not march_8_data.empty:
            row = march_8_data.iloc[0]
            print(f"2024-03-08 akshare数据:")
            print(f"  开盘: {row['open']:.2f}")
            print(f"  最高: {row['high']:.2f}")
            print(f"  最低: {row['low']:.2f}")
            print(f"  收盘: {row['close']:.2f}")
            print(f"  成交量: {row['volume']:,}")
        else:
            print("❌ 未找到2024-03-08的数据")
        
        # 计算不同周线方法的RSI
        print(f"\n🧮 计算不同周线方法的RSI:")
        
        # 我们的方法
        our_weekly_with_rsi = processor.calculate_technical_indicators(weekly_data)
        our_target_rsi = None
        for i in range(len(our_weekly_with_rsi)):
            week_start = our_weekly_with_rsi.index[i]
            week_end = week_start + pd.Timedelta(days=6)
            if week_start <= target_date <= week_end:
                our_target_rsi = our_weekly_with_rsi.iloc[i]['rsi']
                break
        
        # 交易周方法
        trading_weekly_with_rsi = processor.calculate_technical_indicators(trading_weekly)
        trading_target_rsi = None
        for i in range(len(trading_weekly_with_rsi)):
            week_end = trading_weekly_with_rsi.index[i]
            week_start = week_end - pd.Timedelta(days=4)
            if week_start <= target_date <= week_end:
                trading_target_rsi = trading_weekly_with_rsi.iloc[i]['rsi']
                break
        
        print(f"我们的方法RSI: {our_target_rsi:.2f}" if our_target_rsi else "我们的方法RSI: 未找到")
        print(f"交易周方法RSI: {trading_target_rsi:.2f}" if trading_target_rsi else "交易周方法RSI: 未找到")
        print(f"Wind/雪球RSI: ~73.00")
        print(f"同花顺RSI: 73.23")
        
        # 分析差异
        print(f"\n🔍 差异分析:")
        if our_target_rsi and trading_target_rsi:
            if abs(trading_target_rsi - 73.23) < abs(our_target_rsi - 73.23):
                print(f"✅ 交易周方法更接近主流软件")
            else:
                print(f"❌ 两种方法都与主流软件差异较大")
        
        return {
            'our_rsi': our_target_rsi,
            'trading_rsi': trading_target_rsi,
            'target_close': march_8_data.iloc[0]['close'] if not march_8_data.empty else None
        }
        
    except Exception as e:
        print(f"❌ 分析失败: {e}")
        import traceback
        traceback.print_exc()
        return None

if __name__ == "__main__":
    result = analyze_weekly_definition()
    
    if result:
        print(f"\n🎯 建议:")
        print(f"1. 检查是否需要调整周线划分方法")
        print(f"2. 验证akshare数据源的准确性")
        print(f"3. 考虑使用其他数据源进行对比")