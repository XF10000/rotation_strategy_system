#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
分析赣锋锂业(002460)在2023-12-01和2024-02-02的信号条件
使用现有回测系统的完整架构
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

import pandas as pd
import numpy as np
from datetime import datetime
from backtest.backtest_engine import BacktestEngine
from config.csv_config_loader import create_csv_config
import logging

# 设置日志
logging.basicConfig(level=logging.INFO, format='%(message)s')
logger = logging.getLogger(__name__)

def analyze_002460_signals():
    """分析赣锋锂业在特定日期的信号条件"""
    
    target_dates = ['2023-12-01', '2024-02-02']
    stock_code = '002460'
    stock_name = '赣锋锂业'
    
    print(f"🔍 分析 {stock_name}({stock_code}) 在以下日期的买入信号条件:")
    for date in target_dates:
        print(f"   📅 {date}")
    print("=" * 80)
    
    try:
        # 临时修改配置文件路径，使用只包含002460的配置
        original_portfolio_file = 'Input/portfolio_config.csv'
        temp_portfolio_file = 'Input/portfolio_config_002460_only.csv'
        
        # 备份原配置
        import shutil
        if os.path.exists(original_portfolio_file):
            shutil.copy(original_portfolio_file, original_portfolio_file + '.backup')
        
        # 使用临时配置
        shutil.copy(temp_portfolio_file, original_portfolio_file)
        
        # 创建配置
        config = create_csv_config()
        print(f"📊 配置加载完成: {config['name']}")
        print(f"📅 回测期间: {config['start_date']} 至 {config['end_date']}")
        
        # 创建回测引擎
        engine = BacktestEngine(config)
        
        # 运行回测
        print("🚀 运行回测以获取信号数据...")
        success = engine.run_backtest()
        
        if not success:
            print("❌ 回测运行失败")
            return
        
        # 获取回测结果
        results = engine.get_backtest_results()
        
        # 分析信号数据
        if 'signal_history' in results:
            signal_history = results['signal_history']
            print(f"\n📊 信号历史数据: {len(signal_history)} 条记录")
            
            # 分析目标日期
            for target_date in target_dates:
                print(f"\n{'='*60}")
                print(f"📅 分析日期: {target_date}")
                print(f"{'='*60}")
                
                target_dt = pd.to_datetime(target_date)
                
                # 查找最接近的交易日信号
                closest_signal = None
                min_diff = float('inf')
                
                for signal_date, signal_data in signal_history.items():
                    if stock_code in signal_data:
                        signal_dt = pd.to_datetime(signal_date)
                        diff = abs((signal_dt - target_dt).days)
                        if diff < min_diff:
                            min_diff = diff
                            closest_signal = (signal_date, signal_data[stock_code])
                
                if closest_signal and min_diff <= 7:  # 7天内的信号
                    signal_date, signal_info = closest_signal
                    print(f"🎯 最接近的信号日期: {signal_date} (相差{min_diff}天)")
                    
                    # 显示信号详情
                    signal_value = signal_info.get('signal', 0)
                    signal_type = "买入" if signal_value > 0 else "卖出" if signal_value < 0 else "无信号"
                    
                    print(f"📈 信号类型: {signal_type} (值: {signal_value})")
                    
                    # 显示4维度评分
                    if 'scores' in signal_info:
                        scores = signal_info['scores']
                        print(f"\n🎯 4维度评分详情:")
                        print(f"   1️⃣ 趋势过滤器: {scores.get('trend_filter', 'N/A')}")
                        print(f"   2️⃣ 超买超卖: {scores.get('oversold_score', 'N/A')}")
                        print(f"   3️⃣ MACD动能: {scores.get('macd_score', 'N/A')}")
                        print(f"   4️⃣ 极端价格+量能: {scores.get('extreme_score', 'N/A')}")
                        
                        # 计算满足条件的维度数
                        other_scores = [
                            scores.get('oversold_score', 0),
                            scores.get('macd_score', 0),
                            scores.get('extreme_score', 0)
                        ]
                        satisfied_count = sum(1 for score in other_scores if score > 0)
                        
                        print(f"\n📊 买入条件评估:")
                        print(f"   趋势过滤器: {'✅ 通过' if scores.get('trend_filter', 0) > 0 else '❌ 未通过'}")
                        print(f"   其他维度满足: {satisfied_count}/3 (需要≥2个)")
                        
                        should_buy = scores.get('trend_filter', 0) > 0 and satisfied_count >= 2
                        print(f"   最终结果: {'🎉 应产生买入信号!' if should_buy else '❌ 不满足买入条件'}")
                        print(f"   实际信号: {signal_type}")
                    
                    # 显示技术指标数值
                    if 'indicators' in signal_info:
                        indicators = signal_info['indicators']
                        print(f"\n📊 技术指标数值:")
                        print(f"   收盘价: {indicators.get('close', 'N/A'):.2f}")
                        print(f"   20周EMA: {indicators.get('ema_20', 'N/A'):.2f}")
                        print(f"   RSI: {indicators.get('rsi', 'N/A'):.2f}")
                        print(f"   MACD: {indicators.get('macd', 'N/A'):.4f}")
                        print(f"   MACD Signal: {indicators.get('macd_signal', 'N/A'):.4f}")
                        print(f"   MACD Histogram: {indicators.get('macd_histogram', 'N/A'):.4f}")
                        print(f"   布林下轨: {indicators.get('bb_lower', 'N/A'):.2f}")
                        print(f"   成交量: {indicators.get('volume', 'N/A'):,.0f}")
                else:
                    print(f"❌ 在 {target_date} 附近未找到信号数据")
        
        # 恢复原配置文件
        if os.path.exists(original_portfolio_file + '.backup'):
            shutil.move(original_portfolio_file + '.backup', original_portfolio_file)
        
        print(f"\n✅ 分析完成")
        
    except Exception as e:
        print(f"❌ 分析过程中出现错误: {str(e)}")
        import traceback
        traceback.print_exc()
        
        # 确保恢复原配置文件
        try:
            if os.path.exists('Input/portfolio_config.csv.backup'):
                shutil.move('Input/portfolio_config.csv.backup', 'Input/portfolio_config.csv')
        except:
            pass

if __name__ == "__main__":
    analyze_002460_signals()
