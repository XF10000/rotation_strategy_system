#!/usr/bin/env python3
"""
调试价值比过滤器逻辑
分析神火股份在2024-04-12的具体情况
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
logging.basicConfig(level=logging.DEBUG, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def analyze_value_ratio_logic():
    """分析价值比过滤器逻辑"""
    
    print("=" * 80)
    print("价值比过滤器逻辑分析")
    print("=" * 80)
    
    # 加载配置
    config = create_csv_config()
    
    print(f"配置的买入阈值: {config.get('value_ratio_buy_threshold', 'N/A')}")
    print(f"配置的卖出阈值: {config.get('value_ratio_sell_threshold', 'N/A')}")
    
    # 创建回测引擎
    engine = BacktestEngine(config)
    
    # 获取神火股份的数据
    stock_code = '000933'  # 神火股份
    target_date = '2024-04-12'
    
    print(f"\n分析股票: {stock_code} 在日期: {target_date}")
    
    try:
        # 获取股票数据
        weekly_data = engine._get_cached_or_fetch_data(stock_code, '2024-01-01', '2024-05-01', 'weekly')
        
        if weekly_data is None or weekly_data.empty:
            print(f"无法获取 {stock_code} 的数据")
            return
            
        # 检查数据列名
        print(f"数据列名: {list(weekly_data.columns)}")
        print(f"数据形状: {weekly_data.shape}")
        print(f"前几行数据:")
        print(weekly_data.head())
        
        # 找到目标日期附近的数据
        target_datetime = pd.to_datetime(target_date)
        
        # 检查日期列名（可能是'date'或其他名称）
        date_col = None
        for col in weekly_data.columns:
            if 'date' in col.lower() or weekly_data[col].dtype == 'datetime64[ns]':
                date_col = col
                break
        
        if date_col is None:
            # 如果没有找到日期列，使用索引
            if hasattr(weekly_data.index, 'to_pydatetime'):
                weekly_data['date'] = weekly_data.index
                date_col = 'date'
            else:
                print("无法找到日期列")
                return
        
        weekly_data[date_col] = pd.to_datetime(weekly_data[date_col])
        
        # 找到最接近目标日期的数据
        closest_idx = (weekly_data[date_col] - target_datetime).abs().idxmin()
        target_row = weekly_data.loc[closest_idx]
        
        print(f"\n实际分析日期: {target_row[date_col].strftime('%Y-%m-%d')}")
        print(f"收盘价: {target_row['close']:.2f}")
        
        # 获取DCF估值
        dcf_values = engine._load_dcf_values()
        if stock_code in dcf_values:
            dcf_value = dcf_values[stock_code]
            price_value_ratio = target_row['close'] / dcf_value
            
            print(f"DCF估值: {dcf_value:.2f}")
            print(f"价值比: {price_value_ratio:.3f}")
            
            # 分析价值比过滤器逻辑
            buy_threshold = config.get('value_ratio_buy_threshold', 0.8)
            sell_threshold = config.get('value_ratio_sell_threshold', 0.65)
            
            print(f"\n价值比过滤器分析:")
            print(f"买入阈值: {buy_threshold}")
            print(f"卖出阈值: {sell_threshold}")
            print(f"当前价值比: {price_value_ratio:.3f}")
            
            # 判断支持的信号类型
            supports_buy = price_value_ratio < buy_threshold
            supports_sell = price_value_ratio > sell_threshold
            
            print(f"\n逻辑判断:")
            print(f"支持买入信号 (价值比 < {buy_threshold}): {supports_buy}")
            print(f"支持卖出信号 (价值比 > {sell_threshold}): {supports_sell}")
            
            if supports_buy and supports_sell:
                print(f"⚠️  重叠区间: 价值比 {price_value_ratio:.3f} 同时支持买入和卖出信号")
            elif supports_sell:
                print(f"✅ 仅支持卖出信号")
            elif supports_buy:
                print(f"✅ 仅支持买入信号")
            else:
                print(f"❌ 不支持任何信号")
                
            # 进一步分析为什么没有产生卖出信号
            if supports_sell:
                print(f"\n🔍 深入分析: 价值比过滤器支持卖出，但可能其他维度条件不满足")
                
                # 使用信号生成器分析完整的4维度评分
                from strategy.signal_generator import SignalGenerator
                
                signal_gen = SignalGenerator(config, dcf_values)
                
                # 准备技术指标数据
                indicators = engine._calculate_indicators(weekly_data)
                
                # 获取目标日期的4维度评分
                target_idx = closest_idx
                if target_idx >= len(indicators['rsi']) - 1:
                    target_idx = len(indicators['rsi']) - 1
                    
                scores = signal_gen._calculate_4d_scores(
                    indicators, target_idx, stock_code, 
                    current_price=target_row['close']
                )
                
                print(f"\n4维度评分详情:")
                print(f"趋势过滤器(高): {scores.get('trend_filter_high', False)}")
                print(f"趋势过滤器(低): {scores.get('trend_filter_low', False)}")
                print(f"超买超卖(高): {scores.get('overbought_oversold_high', False)}")
                print(f"超买超卖(低): {scores.get('overbought_oversold_low', False)}")
                print(f"动能确认(高): {scores.get('momentum_high', False)}")
                print(f"动能确认(低): {scores.get('momentum_low', False)}")
                print(f"极端价格量能(高): {scores.get('extreme_price_volume_high', False)}")
                print(f"极端价格量能(低): {scores.get('extreme_price_volume_low', False)}")
                
                # 计算卖出信号条件
                trend_filter_ok = scores.get('trend_filter_high', False)
                other_conditions = sum([
                    scores.get('overbought_oversold_high', False),
                    scores.get('momentum_high', False),
                    scores.get('extreme_price_volume_high', False)
                ])
                
                print(f"\n卖出信号条件检查:")
                print(f"趋势过滤器(硬性前提): {trend_filter_ok}")
                print(f"其他3维度满足数量: {other_conditions}/3 (需要≥2)")
                
                if trend_filter_ok and other_conditions >= 2:
                    print(f"✅ 应该产生卖出信号")
                else:
                    print(f"❌ 不满足卖出信号条件")
                    if not trend_filter_ok:
                        print(f"   - 趋势过滤器不满足")
                    if other_conditions < 2:
                        print(f"   - 其他维度条件不足 ({other_conditions}/3 < 2)")
        else:
            print(f"未找到 {stock_code} 的DCF估值数据")
            
    except Exception as e:
        print(f"分析过程中出错: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    analyze_value_ratio_logic()
