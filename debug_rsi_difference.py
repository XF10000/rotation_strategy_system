#!/usr/bin/env python3
"""
调试RSI计算差异
分析我们的RSI计算与同花顺的差异原因
"""

import pandas as pd
import numpy as np
import logging
from datetime import datetime
import sys
import os

# 添加项目路径
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from data.data_fetcher import AkshareDataFetcher
from data.data_processor import DataProcessor
from indicators.momentum import calculate_rsi

# 设置日志
logging.basicConfig(level=logging.INFO)

def manual_rsi_calculation(prices, period=14):
    """
    手动计算RSI，用于对比验证
    使用标准的RSI计算方法
    """
    print(f"\n=== 手动RSI计算 (周期={period}) ===")
    
    if len(prices) < period + 1:
        print("数据不足")
        return None
    
    # 计算价格变化
    deltas = prices.diff().dropna()
    print(f"价格变化序列长度: {len(deltas)}")
    
    # 分离涨跌
    gains = deltas.where(deltas > 0, 0)
    losses = -deltas.where(deltas < 0, 0)
    
    print(f"涨幅序列: {gains.tail(5).values}")
    print(f"跌幅序列: {losses.tail(5).values}")
    
    # 计算平均涨跌幅 - 使用简单移动平均
    avg_gains = gains.rolling(window=period).mean()
    avg_losses = losses.rolling(window=period).mean()
    
    print(f"最近平均涨幅: {avg_gains.iloc[-1]:.6f}")
    print(f"最近平均跌幅: {avg_losses.iloc[-1]:.6f}")
    
    # 计算RS和RSI
    rs = avg_gains / avg_losses
    rsi = 100 - (100 / (1 + rs))
    
    print(f"RS值: {rs.iloc[-1]:.6f}")
    print(f"RSI值: {rsi.iloc[-1]:.2f}")
    
    return rsi

def wilder_rsi_calculation(prices, period=14):
    """
    使用Wilder平滑方法计算RSI
    这是更标准的RSI计算方法，可能更接近同花顺
    """
    print(f"\n=== Wilder平滑RSI计算 (周期={period}) ===")
    
    if len(prices) < period + 1:
        print("数据不足")
        return None
    
    # 计算价格变化
    deltas = prices.diff().dropna()
    
    # 分离涨跌
    gains = deltas.where(deltas > 0, 0)
    losses = -deltas.where(deltas < 0, 0)
    
    # 使用Wilder平滑方法 (类似EMA，但alpha = 1/period)
    alpha = 1.0 / period
    
    # 初始化：使用前period个数据的简单平均
    avg_gain = gains.iloc[:period].mean()
    avg_loss = losses.iloc[:period].mean()
    
    print(f"初始平均涨幅: {avg_gain:.6f}")
    print(f"初始平均跌幅: {avg_loss:.6f}")
    
    # Wilder平滑计算
    rsi_values = []
    
    for i in range(period, len(gains)):
        # Wilder平滑公式: new_avg = (old_avg * (period-1) + current_value) / period
        avg_gain = (avg_gain * (period - 1) + gains.iloc[i]) / period
        avg_loss = (avg_loss * (period - 1) + losses.iloc[i]) / period
        
        if avg_loss == 0:
            rsi_val = 100
        else:
            rs = avg_gain / avg_loss
            rsi_val = 100 - (100 / (1 + rs))
        
        rsi_values.append(rsi_val)
    
    # 最后几个值
    print(f"最终平均涨幅: {avg_gain:.6f}")
    print(f"最终平均跌幅: {avg_loss:.6f}")
    print(f"最终RS值: {avg_gain/avg_loss:.6f}")
    print(f"最终RSI值: {rsi_values[-1]:.2f}")
    
    return rsi_values[-1] if rsi_values else None

def analyze_rsi_difference():
    """分析RSI计算差异"""
    print("🔍 分析601898在2024年3月8日的RSI计算差异")
    print("=" * 60)
    
    try:
        # 获取数据
        fetcher = AkshareDataFetcher()
        processor = DataProcessor()
        
        # 获取更长时间范围的数据确保有足够的历史数据
        daily_data = fetcher.get_stock_data('601898', '2022-01-01', '2024-04-01', 'daily')
        if daily_data is None or daily_data.empty:
            print("❌ 数据获取失败")
            return
        
        print(f"✅ 获取到 {len(daily_data)} 条日线数据")
        
        # 转换为周线
        weekly_data = processor.resample_to_weekly(daily_data)
        print(f"✅ 转换为 {len(weekly_data)} 条周线数据")
        
        # 找到2024年3月8日对应的周线
        target_date = pd.to_datetime('2024-03-08')
        target_week_data = None
        target_index = None
        
        for i in range(len(weekly_data)):
            week_start = weekly_data.index[i]
            week_end = week_start + pd.Timedelta(days=6)
            
            if week_start <= target_date <= week_end:
                target_week_data = weekly_data.iloc[i]
                target_index = i
                print(f"📅 找到目标周: {week_start.strftime('%Y-%m-%d')} - {week_end.strftime('%Y-%m-%d')}")
                print(f"📊 目标周收盘价: {target_week_data['close']:.2f}")
                break
        
        if target_week_data is None:
            print("❌ 未找到目标日期对应的周线数据")
            return
        
        # 获取用于RSI计算的价格序列
        if target_index < 14:
            print("❌ 历史数据不足，无法计算14周RSI")
            return
        
        # 提取RSI计算所需的价格序列（目标周及之前的15周，共16周）
        rsi_prices = weekly_data['close'].iloc[target_index-15:target_index+1]
        print(f"📈 RSI计算使用的价格序列长度: {len(rsi_prices)}")
        
        print(f"\n📋 最近16周的收盘价:")
        for i, (date, price) in enumerate(rsi_prices.items()):
            marker = "👉" if i == len(rsi_prices) - 1 else "  "
            print(f"{marker} {date.strftime('%Y-%m-%d')}: {price:.2f}")
        
        # 1. 使用我们的TA-Lib方法计算
        print(f"\n🔧 使用TA-Lib方法计算RSI:")
        try:
            talib_rsi = calculate_rsi(rsi_prices, 14)
            our_rsi = talib_rsi.iloc[-1]
            print(f"我们的RSI值: {our_rsi:.2f}")
        except Exception as e:
            print(f"TA-Lib计算失败: {e}")
            our_rsi = None
        
        # 2. 使用简单移动平均方法
        simple_rsi = manual_rsi_calculation(rsi_prices, 14)
        
        # 3. 使用Wilder平滑方法
        wilder_rsi = wilder_rsi_calculation(rsi_prices, 14)
        
        # 4. 对比结果
        print(f"\n📊 RSI计算结果对比:")
        print(f"同花顺RSI:     73.23")
        if our_rsi is not None:
            print(f"我们的RSI:     {our_rsi:.2f} (差异: {our_rsi - 73.23:+.2f})")
        if simple_rsi is not None:
            print(f"简单平均RSI:   {simple_rsi.iloc[-1]:.2f} (差异: {simple_rsi.iloc[-1] - 73.23:+.2f})")
        if wilder_rsi is not None:
            print(f"Wilder平滑RSI: {wilder_rsi:.2f} (差异: {wilder_rsi - 73.23:+.2f})")
        
        # 5. 分析可能的差异原因
        print(f"\n🔍 可能的差异原因分析:")
        print(f"1. 数据源差异: 我们使用akshare，同花顺使用自己的数据源")
        print(f"2. 周线定义差异: 我们按自然周划分，同花顺可能按交易周划分")
        print(f"3. RSI算法差异: 简单移动平均 vs Wilder平滑 vs 其他方法")
        print(f"4. 数据精度差异: 价格数据的小数位精度可能不同")
        
        # 6. 检查数据处理器计算的RSI
        weekly_with_indicators = processor.calculate_technical_indicators(weekly_data)
        processor_rsi = weekly_with_indicators.loc[weekly_data.index[target_index], 'rsi']
        print(f"\n🔧 数据处理器计算的RSI: {processor_rsi:.2f}")
        
        return {
            'target_date': target_date,
            'our_rsi': our_rsi,
            'processor_rsi': processor_rsi,
            'tonghuashun_rsi': 73.23,
            'simple_rsi': simple_rsi.iloc[-1] if simple_rsi is not None else None,
            'wilder_rsi': wilder_rsi
        }
        
    except Exception as e:
        print(f"❌ 分析失败: {e}")
        import traceback
        traceback.print_exc()
        return None

if __name__ == "__main__":
    result = analyze_rsi_difference()
    
    if result:
        print(f"\n🎯 总结:")
        print(f"最接近同花顺的方法可能是Wilder平滑法")
        print(f"建议检查数据源和周线定义的一致性")