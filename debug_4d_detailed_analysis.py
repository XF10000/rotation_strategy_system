#!/usr/bin/env python3
"""
详细分析神火股份2024-04-12的4维度评分
找出为什么没有满足至少2个维度的要求
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
logging.basicConfig(level=logging.DEBUG, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def analyze_4d_scores_detailed():
    """详细分析4维度评分"""
    
    print("=" * 80)
    print("神火股份2024-04-12的4维度详细评分分析")
    print("=" * 80)
    
    # 加载配置
    config = create_csv_config()
    
    # 创建回测引擎
    engine = BacktestEngine(config)
    
    stock_code = '000933'  # 神火股份
    target_date = '2024-04-12'
    
    try:
        # 准备数据
        engine.prepare_data()
        
        # 获取数据
        stock_weekly = engine.stock_data[stock_code]['weekly']
        target_datetime = pd.to_datetime(target_date)
        
        if target_datetime not in stock_weekly.index:
            closest_idx = (stock_weekly.index - target_datetime).abs().idxmin()
            target_datetime = closest_idx
        
        # 获取历史数据
        current_idx = stock_weekly.index.get_loc(target_datetime)
        historical_data = stock_weekly.iloc[:current_idx+1]
        
        print(f"分析日期: {target_datetime.strftime('%Y-%m-%d')}")
        print(f"历史数据长度: {len(historical_data)}")
        
        # 计算技术指标
        indicators = engine.signal_generator._calculate_indicators(historical_data)
        
        # 计算4维度评分
        scores, rsi_thresholds = engine.signal_generator._calculate_4d_scores(
            historical_data, indicators, stock_code
        )
        
        print(f"\n=== 4维度评分结果 ===")
        print(f"1. 价值比过滤器 (趋势过滤器):")
        print(f"   支持买入: {scores['trend_filter_low']}")
        print(f"   支持卖出: {scores['trend_filter_high']}")
        
        print(f"\n2. 超买超卖维度:")
        print(f"   支持买入: {scores['overbought_oversold_low']}")
        print(f"   支持卖出: {scores['overbought_oversold_high']}")
        
        print(f"\n3. 动能确认维度:")
        print(f"   支持买入: {scores['momentum_low']}")
        print(f"   支持卖出: {scores['momentum_high']}")
        
        print(f"\n4. 极端价格+量能维度:")
        print(f"   支持买入: {scores['extreme_price_volume_low']}")
        print(f"   支持卖出: {scores['extreme_price_volume_high']}")
        
        # 分析卖出信号
        print(f"\n=== 卖出信号分析 ===")
        trend_filter_high = scores['trend_filter_high']
        print(f"价值比过滤器支持卖出: {trend_filter_high}")
        
        if trend_filter_high:
            high_signals = [
                scores['overbought_oversold_high'],
                scores['momentum_high'],
                scores['extreme_price_volume_high']
            ]
            
            high_signal_count = sum(1 for signal in high_signals if signal)
            
            print(f"其他3个维度的卖出信号:")
            print(f"  - RSI超买: {scores['overbought_oversold_high']}")
            print(f"  - MACD动能: {scores['momentum_high']}")
            print(f"  - 极端价格+量能: {scores['extreme_price_volume_high']}")
            print(f"满足的维度数量: {high_signal_count}/3")
            print(f"需要满足的最低要求: 2/3")
            
            if high_signal_count >= 2:
                print(f"✅ 满足卖出条件！应该产生SELL信号")
            else:
                print(f"❌ 不满足卖出条件，缺少 {2 - high_signal_count} 个维度")
                
                # 详细分析每个不满足的维度
                print(f"\n=== 不满足维度的详细分析 ===")
                
                if not scores['overbought_oversold_high']:
                    print(f"RSI超买维度不满足:")
                    current_rsi = historical_data['rsi'].iloc[-1]
                    print(f"  当前RSI: {current_rsi:.2f}")
                    print(f"  普通超买阈值: {rsi_thresholds.get('overbought', 70):.2f}")
                    print(f"  极端超买阈值: {rsi_thresholds.get('extreme_overbought', 80):.2f}")
                    
                    if current_rsi >= rsi_thresholds.get('extreme_overbought', 80):
                        print(f"  🔥 应该满足极端超买条件！")
                    elif current_rsi >= rsi_thresholds.get('overbought', 70):
                        print(f"  应该检查背离条件")
                    else:
                        print(f"  RSI未达到超买水平")
                
                if not scores['momentum_high']:
                    print(f"\nMACD动能维度不满足:")
                    macd_hist = historical_data['macd_histogram'].iloc[-1]
                    macd_hist_prev = historical_data['macd_histogram'].iloc[-2]
                    print(f"  当前MACD柱体: {macd_hist:.4f}")
                    print(f"  前一期MACD柱体: {macd_hist_prev:.4f}")
                    print(f"  柱体变化: {macd_hist - macd_hist_prev:.4f}")
                    
                    if macd_hist > 0 and macd_hist < macd_hist_prev:
                        print(f"  红色柱体缩短: 是")
                    else:
                        print(f"  红色柱体缩短: 否")
                
                if not scores['extreme_price_volume_high']:
                    print(f"\n极端价格+量能维度不满足:")
                    current_price = historical_data['close'].iloc[-1]
                    bb_upper = historical_data['bb_upper'].iloc[-1]
                    volume_ratio = historical_data['volume_ratio'].iloc[-1]
                    print(f"  当前价格: {current_price:.2f}")
                    print(f"  布林上轨: {bb_upper:.2f}")
                    print(f"  价格突破上轨: {current_price > bb_upper}")
                    print(f"  成交量比率: {volume_ratio:.2f}")
                    print(f"  成交量放大(>1.3): {volume_ratio > 1.3}")
        else:
            print(f"❌ 价值比过滤器不支持卖出，无法产生卖出信号")
        
        # 生成最终信号进行验证
        print(f"\n=== 最终信号验证 ===")
        signal_result = engine.signal_generator._generate_final_signal(
            stock_code, scores, indicators, rsi_thresholds
        )
        
        print(f"最终信号: {signal_result['signal']}")
        print(f"信号原因: {signal_result['reason']}")
        print(f"置信度: {signal_result['confidence']}")
        
        if 'action' in signal_result:
            print(f"建议操作: {signal_result['action']}")
        
    except Exception as e:
        print(f"分析过程中出错: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    analyze_4d_scores_detailed()
