#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
分析赣锋锂业(002460)在特定日期的买入信号条件
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

import pandas as pd
import numpy as np
from datetime import datetime, timedelta
from data.data_fetcher import DataFetcher
from data.data_processor import DataProcessor
from strategy.signal_generator import SignalGenerator
from utils.industry_classifier import IndustryClassifier

def analyze_specific_dates():
    """分析002460在2023-12-01和2024-02-02的信号条件"""
    
    # 目标日期
    target_dates = ['2023-12-01', '2024-02-02']
    stock_code = '002460'
    stock_name = '赣锋锂业'
    
    print(f"🔍 分析 {stock_name}({stock_code}) 在以下日期的买入信号条件:")
    for date in target_dates:
        print(f"   📅 {date}")
    print("=" * 80)
    
    try:
        # 初始化组件
        from data.data_fetcher import create_data_fetcher
        from config.backtest_configs import DEFAULT_STRATEGY_PARAMS
        data_fetcher = create_data_fetcher('akshare')
        data_processor = DataProcessor()
        signal_generator = SignalGenerator(DEFAULT_STRATEGY_PARAMS)
        industry_classifier = IndustryClassifier()
        
        # 获取股票数据（扩展时间范围以确保有足够的历史数据）
        start_date = '2021-01-01'
        end_date = '2024-03-01'
        
        print(f"📊 获取 {stock_name} 数据...")
        stock_data = data_fetcher.get_stock_data(stock_code, start_date, end_date)
        
        if stock_data is None or stock_data.empty:
            print(f"❌ 无法获取 {stock_name} 的数据")
            return
            
        print(f"✅ 成功获取数据，共 {len(stock_data)} 条记录")
        print(f"📅 数据时间范围: {stock_data.index[0]} 到 {stock_data.index[-1]}")
        
        # 处理数据
        print("🔄 处理技术指标...")
        processed_data = data_processor.process_stock_data(stock_data)
        
        # 获取行业信息
        industry_info = industry_classifier.get_industry_info(stock_code)
        sw2_industry = industry_info.get('sw2_industry', '其他')
        
        print(f"🏭 行业分类: {sw2_industry}")
        
        # 生成信号
        print("🎯 生成交易信号...")
        signals = signal_generator.generate_signals(processed_data, stock_code)
        
        # 分析每个目标日期
        for target_date in target_dates:
            print(f"\n{'='*60}")
            print(f"📅 分析日期: {target_date}")
            print(f"{'='*60}")
            
            # 查找最接近的交易日
            target_dt = pd.to_datetime(target_date)
            available_dates = processed_data.index
            
            # 找到最接近且不晚于目标日期的交易日
            valid_dates = available_dates[available_dates <= target_dt]
            if len(valid_dates) == 0:
                print(f"❌ 在 {target_date} 之前没有找到交易数据")
                continue
                
            closest_date = valid_dates[-1]
            print(f"🎯 最接近的交易日: {closest_date.strftime('%Y-%m-%d')}")
            
            # 获取该日期的数据
            if closest_date not in processed_data.index:
                print(f"❌ {closest_date} 的数据不存在")
                continue
                
            row_data = processed_data.loc[closest_date]
            
            # 显示基础数据
            print(f"\n📊 基础数据:")
            print(f"   收盘价: {row_data['close']:.2f}")
            print(f"   成交量: {row_data['volume']:,.0f}")
            print(f"   20周EMA: {row_data['ema_20']:.2f}")
            print(f"   RSI: {row_data['rsi']:.2f}")
            print(f"   MACD: {row_data['macd']:.4f}")
            print(f"   MACD Signal: {row_data['macd_signal']:.4f}")
            print(f"   MACD Histogram: {row_data['macd_histogram']:.4f}")
            print(f"   布林下轨: {row_data['bb_lower']:.2f}")
            
            # 计算4维度评分
            print(f"\n🎯 4维度信号分析:")
            
            # 1. 趋势过滤器
            ema_trend = "向下" if row_data['ema_20'] < processed_data.loc[processed_data.index < closest_date, 'ema_20'].iloc[-1] else "向上"
            trend_filter = row_data['close'] < row_data['ema_20']
            print(f"   1️⃣ 趋势过滤器: {'✅ 通过' if trend_filter else '❌ 未通过'}")
            print(f"      收盘价 {row_data['close']:.2f} {'<' if trend_filter else '>='} EMA20 {row_data['ema_20']:.2f}, EMA趋势{ema_trend}")
            
            if not trend_filter:
                print(f"   ❌ 趋势过滤器未通过，无法产生买入信号")
                continue
            
            # 2. 超买超卖 (RSI + 背离)
            rsi_oversold = row_data['rsi'] <= 30
            # 简化背离检测 - 检查是否有价格新低但RSI未创新低
            recent_data = processed_data.loc[processed_data.index <= closest_date].tail(10)
            price_new_low = row_data['close'] == recent_data['close'].min()
            rsi_divergence = False
            if price_new_low and len(recent_data) >= 5:
                rsi_min_idx = recent_data['rsi'].idxmin()
                rsi_divergence = rsi_min_idx != recent_data['close'].idxmin()
            
            oversold_score = rsi_oversold and rsi_divergence
            print(f"   2️⃣ 超买超卖: {'✅ 满足' if oversold_score else '❌ 不满足'}")
            print(f"      RSI {row_data['rsi']:.2f} {'<=' if rsi_oversold else '>'} 30, 背离: {'是' if rsi_divergence else '否'}")
            
            # 3. MACD动能确认
            # 检查MACD柱体是否连续缩短或金叉
            recent_macd = processed_data.loc[processed_data.index <= closest_date, 'macd_histogram'].tail(3)
            histogram_shrinking = len(recent_macd) >= 2 and recent_macd.iloc[-1] > recent_macd.iloc[-2]
            golden_cross = row_data['macd'] > row_data['macd_signal'] and len(recent_data) >= 2
            if len(recent_data) >= 2:
                prev_data = recent_data.iloc[-2]
                golden_cross = golden_cross and prev_data['macd'] <= prev_data['macd_signal']
            
            macd_score = histogram_shrinking or golden_cross
            print(f"   3️⃣ MACD动能: {'✅ 满足' if macd_score else '❌ 不满足'}")
            print(f"      柱体缩短: {'是' if histogram_shrinking else '否'}, 金叉: {'是' if golden_cross else '否'}")
            
            # 4. 极端价格+量能
            price_extreme = row_data['close'] <= row_data['bb_lower']
            # 计算4周平均成交量
            volume_avg_4w = processed_data.loc[processed_data.index <= closest_date, 'volume'].tail(20).mean()
            volume_surge = row_data['volume'] >= volume_avg_4w * 0.8
            
            extreme_score = price_extreme and volume_surge
            print(f"   4️⃣ 极端价格+量能: {'✅ 满足' if extreme_score else '❌ 不满足'}")
            print(f"      收盘价 {row_data['close']:.2f} {'<=' if price_extreme else '>'} 布林下轨 {row_data['bb_lower']:.2f}")
            print(f"      成交量 {row_data['volume']:,.0f} {'≥' if volume_surge else '<'} 4周均量×0.8 {volume_avg_4w * 0.8:,.0f}")
            
            # 总结
            other_dimensions = [oversold_score, macd_score, extreme_score]
            satisfied_count = sum(other_dimensions)
            
            print(f"\n📈 买入信号评估:")
            print(f"   趋势过滤器: {'✅' if trend_filter else '❌'}")
            print(f"   其他维度满足: {satisfied_count}/3 (需要≥2个)")
            print(f"   最终结果: {'🎉 产生买入信号!' if trend_filter and satisfied_count >= 2 else '❌ 未产生买入信号'}")
            
            # 检查信号记录
            if closest_date in signals.index:
                signal_row = signals.loc[closest_date]
                actual_signal = signal_row.get('signal', 0)
                print(f"   实际信号记录: {actual_signal} ({'买入' if actual_signal > 0 else '卖出' if actual_signal < 0 else '无信号'})")
            else:
                print(f"   实际信号记录: 未找到")
    
    except Exception as e:
        print(f"❌ 分析过程中出现错误: {str(e)}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    analyze_specific_dates()
