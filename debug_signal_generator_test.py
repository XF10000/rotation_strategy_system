#!/usr/bin/env python3
"""
直接测试信号生成器的极端RSI逻辑
专门针对神火股份2024-04-12的情况
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
from strategy.signal_generator import SignalGenerator

# 设置详细日志
logging.basicConfig(level=logging.DEBUG, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def test_signal_generator():
    """直接测试信号生成器"""
    
    print("=" * 80)
    print("直接测试信号生成器 - 神火股份2024-04-12")
    print("=" * 80)
    
    # 加载配置
    config = create_csv_config()
    
    # 创建回测引擎
    engine = BacktestEngine(config)
    
    stock_code = '000933'  # 神火股份
    target_date = '2024-04-12'
    
    try:
        # 获取股票数据
        weekly_data = engine._get_cached_or_fetch_data(stock_code, '2023-01-01', '2024-06-01', 'weekly')
        
        if weekly_data is None or weekly_data.empty:
            print(f"无法获取 {stock_code} 的数据")
            return
            
        # 计算技术指标
        indicators = {}
        indicators['rsi'] = weekly_data['rsi']
        indicators['ema_20'] = weekly_data['ema_20']
        indicators['macd'] = weekly_data['macd']
        indicators['macd_signal'] = weekly_data['macd_signal']
        indicators['macd_histogram'] = weekly_data['macd_histogram']
        indicators['bb_upper'] = weekly_data['bb_upper']
        indicators['bb_lower'] = weekly_data['bb_lower']
        indicators['volume'] = weekly_data['volume']
        indicators['volume_ma'] = weekly_data['volume_ma']
        
        # 添加RSI背离数据（模拟）
        indicators['rsi_divergence'] = pd.Series([{
            'top_divergence': False,
            'bottom_divergence': False
        }] * len(weekly_data), index=weekly_data.index)
        
        # 找到目标日期
        target_datetime = pd.to_datetime(target_date)
        weekly_data_with_date = weekly_data.copy()
        weekly_data_with_date['date'] = weekly_data_with_date.index
        
        closest_idx = (weekly_data_with_date['date'] - target_datetime).abs().idxmin()
        target_idx_in_data = weekly_data.index.get_loc(closest_idx)
        target_row = weekly_data.loc[closest_idx]
        
        print(f"目标日期: {closest_idx.strftime('%Y-%m-%d')}")
        print(f"数据索引: {target_idx_in_data}")
        print(f"收盘价: {target_row['close']:.2f}")
        print(f"RSI: {target_row['rsi']:.2f}")
        
        # 获取DCF估值
        dcf_values = engine._load_dcf_values()
        
        # 创建信号生成器
        signal_gen = SignalGenerator(config, dcf_values, 
                                   rsi_thresholds=engine.rsi_thresholds,
                                   stock_industry_map=engine.stock_industry_map)
        
        print(f"\n开始调用信号生成器...")
        
        # 直接调用_calculate_4d_scores方法
        # 准备数据切片到目标日期
        data_slice = weekly_data.iloc[:target_idx_in_data+1]
        indicators_slice = {}
        for key, value in indicators.items():
            if isinstance(value, pd.Series):
                indicators_slice[key] = value.iloc[:target_idx_in_data+1]
            else:
                indicators_slice[key] = value
        
        scores = signal_gen._calculate_4d_scores(
            data_slice, indicators_slice, stock_code
        )
        
        print(f"\n4维度评分结果:")
        for key, value in scores.items():
            print(f"  {key}: {value}")
        
        # 检查卖出信号条件
        trend_filter_ok = scores.get('trend_filter_high', False)
        other_conditions = sum([
            scores.get('overbought_oversold_high', False),
            scores.get('momentum_high', False),
            scores.get('extreme_price_volume_high', False)
        ])
        
        print(f"\n卖出信号分析:")
        print(f"价值比过滤器(硬性前提): {trend_filter_ok}")
        print(f"超买超卖维度: {scores.get('overbought_oversold_high', False)}")
        print(f"动能确认维度: {scores.get('momentum_high', False)}")
        print(f"极端价格+量能维度: {scores.get('extreme_price_volume_high', False)}")
        print(f"其他3维度满足数量: {other_conditions}/3")
        
        should_sell = trend_filter_ok and other_conditions >= 2
        print(f"应该产生卖出信号: {should_sell}")
        
        # 进一步检查RSI相关的详细信息
        print(f"\n详细RSI信息检查:")
        
        # 检查行业映射
        if stock_code in signal_gen.stock_industry_map:
            industry_info = signal_gen.stock_industry_map[stock_code]
            industry_code = industry_info['industry_code']
            industry_name = industry_info['industry_name']
            print(f"行业: {industry_name} ({industry_code})")
            
            # 检查RSI阈值
            if industry_code in signal_gen.rsi_thresholds:
                threshold_info = signal_gen.rsi_thresholds[industry_code]
                extreme_overbought = threshold_info.get('extreme_sell_threshold', 80)
                extreme_oversold = threshold_info.get('extreme_buy_threshold', 20)
                
                print(f"极端超买阈值: {extreme_overbought}")
                print(f"极端超卖阈值: {extreme_oversold}")
                print(f"当前RSI: {target_row['rsi']:.2f}")
                print(f"极端超买条件: {target_row['rsi']:.2f} >= {extreme_overbought} = {target_row['rsi'] >= extreme_overbought}")
                
                if target_row['rsi'] >= extreme_overbought:
                    print(f"🚨 极端RSI条件满足，但超买超卖维度结果为: {scores.get('overbought_oversold_high', False)}")
                    print(f"这表明极端RSI逻辑可能存在问题！")
        
    except Exception as e:
        print(f"测试过程中出错: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    test_signal_generator()
