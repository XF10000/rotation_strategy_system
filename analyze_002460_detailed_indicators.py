#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
使用回测系统相同的计算模块获取赣锋锂业(002460)在特定日期的详细技术指标
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

import pandas as pd
import numpy as np
from datetime import datetime
import logging

# 导入回测系统的计算模块
from data.data_fetcher import create_data_fetcher
from data.data_processor import DataProcessor
from indicators.trend import calculate_ema
from indicators.momentum import calculate_rsi, calculate_macd
from indicators.volatility import calculate_bollinger_bands
from indicators.divergence import detect_rsi_divergence
from config.enhanced_industry_rsi_loader import get_enhanced_rsi_loader
from utils.industry_classifier import IndustryClassifier
from strategy.signal_generator import SignalGenerator
from config.backtest_configs import DEFAULT_STRATEGY_PARAMS

# 设置日志
logging.basicConfig(level=logging.INFO, format='%(message)s')
logger = logging.getLogger(__name__)

def get_detailed_indicators():
    """获取002460在特定日期的详细技术指标"""
    
    target_dates = ['2023-12-01', '2024-02-02']
    stock_code = '002460'
    stock_name = '赣锋锂业'
    
    print(f"🔍 使用回测系统相同计算模块分析 {stock_name}({stock_code})")
    print(f"📅 目标日期: {', '.join(target_dates)}")
    print("=" * 80)
    
    try:
        # 1. 获取原始数据
        print("📊 步骤1: 获取原始股票数据...")
        data_fetcher = create_data_fetcher('akshare')
        
        # 获取足够的历史数据用于技术指标计算
        start_date = '2020-01-01'
        end_date = '2024-03-01'
        
        stock_data = data_fetcher.get_stock_data(stock_code, start_date, end_date, 'weekly')
        print(f"✅ 获取到 {len(stock_data)} 条周线数据")
        print(f"📅 数据范围: {stock_data.index[0]} 到 {stock_data.index[-1]}")
        
        # 2. 计算技术指标
        print("\n📊 步骤2: 计算技术指标...")
        
        # EMA
        stock_data['ema_20'] = calculate_ema(stock_data['close'], 20)
        stock_data['ema_60'] = calculate_ema(stock_data['close'], 60)
        
        # RSI
        stock_data['rsi'] = calculate_rsi(stock_data['close'], 14)
        
        # MACD
        macd_data = calculate_macd(stock_data['close'], 12, 26, 9)
        stock_data['macd'] = macd_data['dif']  # DIF线
        stock_data['macd_signal'] = macd_data['dea']  # DEA线
        stock_data['macd_histogram'] = macd_data['hist']  # 柱状图
        
        # 布林带
        bb_data = calculate_bollinger_bands(stock_data['close'], 20, 2)
        stock_data['bb_upper'] = bb_data['upper']
        stock_data['bb_middle'] = bb_data['middle']
        stock_data['bb_lower'] = bb_data['lower']
        
        # 成交量均线
        stock_data['volume_4w_avg'] = stock_data['volume'].rolling(window=4).mean()
        
        print("✅ 技术指标计算完成")
        
        # 3. 获取行业信息和动态阈值
        print("\n📊 步骤3: 获取行业信息和动态阈值...")
        
        industry_classifier = IndustryClassifier()
        sw2_industry = industry_classifier.get_stock_industry_auto(stock_code)
        if not sw2_industry:
            sw2_industry = '其他'
        print(f"🏭 申万二级行业: {sw2_industry}")
        
        # 获取行业RSI阈值
        rsi_loader = get_enhanced_rsi_loader()
        industry_thresholds = rsi_loader.get_rsi_thresholds(sw2_industry)
        
        if industry_thresholds:
            print(f"📊 行业RSI阈值:")
            print(f"   超买阈值: {industry_thresholds.get('overbought', 70):.1f}")
            print(f"   超卖阈值: {industry_thresholds.get('oversold', 30):.1f}")
            print(f"   极端超买阈值: {industry_thresholds.get('extreme_overbought', 80):.1f}")
            print(f"   极端超卖阈值: {industry_thresholds.get('extreme_oversold', 20):.1f}")
        else:
            print(f"⚠️  未找到 {sw2_industry} 的动态阈值，使用默认值")
            industry_thresholds = {'overbought': 70, 'oversold': 30, 'extreme_overbought': 80, 'extreme_oversold': 20}
        
        # 4. DCF估值信息
        dcf_value = 50.0  # 从配置文件中获取
        print(f"💰 DCF估值: {dcf_value} 元/股")
        
        # 5. 分析目标日期
        for target_date in target_dates:
            print(f"\n{'='*60}")
            print(f"📅 分析日期: {target_date}")
            print(f"{'='*60}")
            
            # 找到最接近的交易日
            target_dt = pd.to_datetime(target_date)
            available_dates = stock_data.index
            
            # 找到最接近且不晚于目标日期的交易日
            valid_dates = available_dates[available_dates <= target_dt]
            if len(valid_dates) == 0:
                print(f"❌ 在 {target_date} 之前没有找到交易数据")
                continue
                
            closest_date = valid_dates[-1]
            print(f"🎯 最接近的交易日: {closest_date.strftime('%Y-%m-%d')}")
            
            # 获取该日期的数据
            row = stock_data.loc[closest_date]
            
            # 显示基础数据
            print(f"\n📊 基础技术指标:")
            print(f"   收盘价: {row['close']:.2f}")
            print(f"   成交量: {row['volume']:,.0f}")
            print(f"   20周EMA: {row['ema_20']:.2f}")
            print(f"   60周EMA: {row['ema_60']:.2f}")
            print(f"   RSI: {row['rsi']:.2f}")
            print(f"   MACD: {row['macd']:.4f}")
            print(f"   MACD Signal: {row['macd_signal']:.4f}")
            print(f"   MACD Histogram: {row['macd_histogram']:.4f}")
            print(f"   布林上轨: {row['bb_upper']:.2f}")
            print(f"   布林中轨: {row['bb_middle']:.2f}")
            print(f"   布林下轨: {row['bb_lower']:.2f}")
            print(f"   4周平均成交量: {row['volume_4w_avg']:,.0f}")
            
            # 计算价值比
            price_value_ratio = (row['close'] / dcf_value) * 100
            print(f"   价值比: {price_value_ratio:.1f}% (当前价格/DCF估值)")
            
            # 分析4维度条件
            print(f"\n🎯 4维度买入信号分析:")
            
            # 1. 价值比过滤器 (替代趋势过滤器) - 使用MRD文档规定的80%阈值
            buy_threshold = 80.0  # MRD V4.0规定的买入阈值
            value_filter_pass = price_value_ratio < buy_threshold
            print(f"   1️⃣ 价值比过滤器: {'✅ 通过' if value_filter_pass else '❌ 未通过'}")
            print(f"      价值比 {price_value_ratio:.1f}% {'<' if value_filter_pass else '>='} 买入阈值 {buy_threshold}%")
            
            if not value_filter_pass:
                print(f"   ❌ 价值比过滤器未通过，无法产生买入信号")
                continue
            
            # 2. 超买超卖 (使用行业动态阈值)
            oversold_threshold = industry_thresholds.get('oversold', 30)
            extreme_oversold_threshold = industry_thresholds.get('extreme_oversold', 20)
            
            rsi_oversold = row['rsi'] <= oversold_threshold
            rsi_extreme_oversold = row['rsi'] <= extreme_oversold_threshold
            
            # 检测RSI底背离
            recent_data = stock_data.loc[stock_data.index <= closest_date].tail(15)  # 增加数据量
            try:
                divergence_result = detect_rsi_divergence(recent_data['close'], recent_data['rsi'], 10)
                rsi_divergence = divergence_result.get('bottom_divergence', False)
            except Exception as e:
                print(f"      ⚠️  背离检测失败: {e}")
                rsi_divergence = False
            
            # 极端RSI优先级更高
            if rsi_extreme_oversold:
                oversold_score = True
                oversold_reason = f"极端超卖 (RSI {row['rsi']:.2f} ≤ {extreme_oversold_threshold})"
            elif rsi_oversold and rsi_divergence:
                oversold_score = True
                oversold_reason = f"超卖+底背离 (RSI {row['rsi']:.2f} ≤ {oversold_threshold} 且有底背离)"
            else:
                oversold_score = False
                oversold_reason = f"不满足 (RSI {row['rsi']:.2f}, 阈值{oversold_threshold}, 背离{'有' if rsi_divergence else '无'})"
            
            print(f"   2️⃣ 超买超卖: {'✅ 满足' if oversold_score else '❌ 不满足'}")
            print(f"      {oversold_reason}")
            
            # 3. MACD动能确认
            # 检查MACD柱体是否连续缩短或金叉
            recent_macd = stock_data.loc[stock_data.index <= closest_date].tail(3)
            
            # 柱体缩短检查
            histogram_shrinking = False
            if len(recent_macd) >= 2:
                current_hist = recent_macd['macd_histogram'].iloc[-1]
                prev_hist = recent_macd['macd_histogram'].iloc[-2]
                if current_hist < 0 and prev_hist < 0:  # 都是负值（绿柱）
                    histogram_shrinking = abs(current_hist) < abs(prev_hist)  # 绿柱缩短
            
            # 金叉检查
            golden_cross = False
            if len(recent_macd) >= 2:
                current_macd = row['macd']
                current_signal = row['macd_signal']
                prev_macd = recent_macd['macd'].iloc[-2]
                prev_signal = recent_macd['macd_signal'].iloc[-2]
                
                golden_cross = (current_macd > current_signal) and (prev_macd <= prev_signal)
            
            macd_score = histogram_shrinking or golden_cross
            macd_reason = []
            if histogram_shrinking:
                macd_reason.append("绿柱缩短")
            if golden_cross:
                macd_reason.append("DIF金叉DEA")
            
            print(f"   3️⃣ MACD动能: {'✅ 满足' if macd_score else '❌ 不满足'}")
            if macd_reason:
                print(f"      满足条件: {', '.join(macd_reason)}")
            else:
                print(f"      MACD {row['macd']:.4f}, Signal {row['macd_signal']:.4f}, Hist {row['macd_histogram']:.4f}")
                print(f"      无柱体缩短或金叉信号")
            
            # 4. 极端价格+量能
            price_extreme = row['close'] <= row['bb_lower']
            volume_surge = row['volume'] >= row['volume_4w_avg'] * 0.8
            
            extreme_score = price_extreme and volume_surge
            print(f"   4️⃣ 极端价格+量能: {'✅ 满足' if extreme_score else '❌ 不满足'}")
            print(f"      价格条件: 收盘价 {row['close']:.2f} {'≤' if price_extreme else '>'} 布林下轨 {row['bb_lower']:.2f} {'✅' if price_extreme else '❌'}")
            print(f"      量能条件: 成交量 {row['volume']:,.0f} {'≥' if volume_surge else '<'} 4周均量×0.8 {row['volume_4w_avg'] * 0.8:,.0f} {'✅' if volume_surge else '❌'}")
            
            # 总结
            other_dimensions = [oversold_score, macd_score, extreme_score]
            satisfied_count = sum(other_dimensions)
            
            print(f"\n📈 最终买入信号评估:")
            print(f"   价值比过滤器: {'✅' if value_filter_pass else '❌'}")
            print(f"   其他维度满足: {satisfied_count}/3 (需要≥2个)")
            print(f"   - 超买超卖: {'✅' if oversold_score else '❌'}")
            print(f"   - MACD动能: {'✅' if macd_score else '❌'}")
            print(f"   - 极端价格+量能: {'✅' if extreme_score else '❌'}")
            
            final_signal = value_filter_pass and satisfied_count >= 2
            print(f"   🎯 最终结果: {'🎉 应产生买入信号!' if final_signal else '❌ 不满足买入条件'}")
            
            if not final_signal:
                print(f"\n💡 失败原因分析:")
                if not value_filter_pass:
                    print(f"   - 价值比过滤器未通过: {price_value_ratio:.1f}% ≥ {buy_threshold}%")
                if satisfied_count < 2:
                    print(f"   - 其他维度不足: 只满足{satisfied_count}个，需要至少2个")
    
    except Exception as e:
        print(f"❌ 分析过程中出现错误: {str(e)}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    get_detailed_indicators()
