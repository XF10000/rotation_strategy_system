#!/usr/bin/env python3
"""
深入分析4维度信号生成逻辑
专门分析神火股份在2024-04-12的各维度条件
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
from indicators.trend import calculate_ema, detect_ema_trend
from indicators.momentum import calculate_rsi, calculate_macd
from indicators.volatility import calculate_bollinger_bands
from indicators.divergence import detect_rsi_divergence, detect_macd_divergence

# 设置日志
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def analyze_4d_signals():
    """深入分析4维度信号条件"""
    
    print("=" * 80)
    print("神火股份(000933) 2024-04-12 四维度信号详细分析")
    print("=" * 80)
    
    # 加载配置
    config = create_csv_config()
    
    # 创建回测引擎
    engine = BacktestEngine(config)
    
    # 获取神火股份的数据
    stock_code = '000933'  # 神火股份
    target_date = '2024-04-12'
    
    try:
        # 获取更长时间范围的数据，确保技术指标计算准确
        weekly_data = engine._get_cached_or_fetch_data(stock_code, '2023-01-01', '2024-06-01', 'weekly')
        
        if weekly_data is None or weekly_data.empty:
            print(f"无法获取 {stock_code} 的数据")
            return
            
        print(f"获取数据范围: {weekly_data.index[0]} 到 {weekly_data.index[-1]}")
        print(f"数据条数: {len(weekly_data)}")
        
        # 找到目标日期附近的数据
        target_datetime = pd.to_datetime(target_date)
        weekly_data_with_date = weekly_data.copy()
        weekly_data_with_date['date'] = weekly_data_with_date.index
        
        # 找到最接近目标日期的数据
        closest_idx = (weekly_data_with_date['date'] - target_datetime).abs().idxmin()
        target_row = weekly_data.loc[closest_idx]
        target_idx_in_data = weekly_data.index.get_loc(closest_idx)
        
        print(f"\n目标分析日期: {closest_idx.strftime('%Y-%m-%d')}")
        print(f"数据索引位置: {target_idx_in_data}")
        print(f"收盘价: {target_row['close']:.2f}")
        
        # 获取DCF估值
        dcf_values = engine._load_dcf_values()
        if stock_code not in dcf_values:
            print(f"未找到 {stock_code} 的DCF估值数据")
            return
            
        dcf_value = dcf_values[stock_code]
        price_value_ratio = target_row['close'] / dcf_value
        
        print(f"DCF估值: {dcf_value:.2f}")
        print(f"价值比: {price_value_ratio:.3f}")
        
        # 创建信号生成器
        signal_gen = SignalGenerator(config, dcf_values)
        
        print("\n" + "="*60)
        print("四维度信号详细分析")
        print("="*60)
        
        # 1. 价值比过滤器分析
        print(f"\n1. 【价值比过滤器】")
        buy_threshold = config.get('value_ratio_buy_threshold', 0.8)
        sell_threshold = config.get('value_ratio_sell_threshold', 0.65)
        
        supports_buy = price_value_ratio < buy_threshold
        supports_sell = price_value_ratio > sell_threshold
        
        print(f"   价值比: {price_value_ratio:.3f}")
        print(f"   买入阈值: {buy_threshold}, 支持买入: {supports_buy}")
        print(f"   卖出阈值: {sell_threshold}, 支持卖出: {supports_sell}")
        
        if supports_sell:
            print(f"   ✅ 价值比过滤器支持卖出信号")
        else:
            print(f"   ❌ 价值比过滤器不支持卖出信号")
        
        # 2. 超买超卖分析
        print(f"\n2. 【超买超卖 - RSI + 背离】")
        rsi_current = target_row['rsi']
        print(f"   当前RSI: {rsi_current:.2f}")
        
        # 检查RSI超买条件
        rsi_overbought = 70  # 默认阈值
        rsi_oversold = 30
        
        print(f"   RSI超买阈值: {rsi_overbought}")
        print(f"   RSI超卖阈值: {rsi_oversold}")
        
        rsi_supports_sell = rsi_current > rsi_overbought
        rsi_supports_buy = rsi_current < rsi_oversold
        
        print(f"   RSI支持卖出(超买): {rsi_supports_sell}")
        print(f"   RSI支持买入(超卖): {rsi_supports_buy}")
        
        # 检查背离
        if target_idx_in_data >= 10:  # 确保有足够数据检查背离
            try:
                # 获取RSI和价格数据用于背离检测
                rsi_data = weekly_data['rsi'].iloc[max(0, target_idx_in_data-10):target_idx_in_data+1]
                price_data = weekly_data['close'].iloc[max(0, target_idx_in_data-10):target_idx_in_data+1]
                
                # 检测顶背离（卖出信号）
                top_divergence = detect_rsi_divergence(rsi_data, price_data, divergence_type='top')
                # 检测底背离（买入信号）
                bottom_divergence = detect_rsi_divergence(rsi_data, price_data, divergence_type='bottom')
                
                print(f"   RSI顶背离: {top_divergence}")
                print(f"   RSI底背离: {bottom_divergence}")
                
                # 综合判断超买超卖维度
                overbought_oversold_sell = rsi_supports_sell and top_divergence
                overbought_oversold_buy = rsi_supports_buy and bottom_divergence
                
                print(f"   超买超卖维度支持卖出: {overbought_oversold_sell}")
                print(f"   超买超卖维度支持买入: {overbought_oversold_buy}")
                
            except Exception as e:
                print(f"   背离检测失败: {e}")
                overbought_oversold_sell = False
                overbought_oversold_buy = False
        else:
            print(f"   数据不足，无法检测背离")
            overbought_oversold_sell = False
            overbought_oversold_buy = False
        
        # 3. 动能确认分析
        print(f"\n3. 【动能确认 - MACD】")
        macd_current = target_row['macd']
        macd_signal_current = target_row['macd_signal']
        macd_hist_current = target_row['macd_histogram']
        
        print(f"   MACD: {macd_current:.6f}")
        print(f"   MACD Signal: {macd_signal_current:.6f}")
        print(f"   MACD Histogram: {macd_hist_current:.6f}")
        
        # 检查MACD条件
        momentum_sell = False
        momentum_buy = False
        
        if target_idx_in_data >= 2:  # 需要至少3个数据点检查柱体变化
            # 获取最近3个MACD柱体数据
            hist_data = weekly_data['macd_histogram'].iloc[target_idx_in_data-2:target_idx_in_data+1]
            macd_data = weekly_data['macd'].iloc[target_idx_in_data-2:target_idx_in_data+1]
            signal_data = weekly_data['macd_signal'].iloc[target_idx_in_data-2:target_idx_in_data+1]
            
            print(f"   最近3期MACD柱体: {list(hist_data.values)}")
            
            # 检查卖出条件
            # 1. MACD红色柱体连续2根缩短
            if len(hist_data) >= 3 and all(h > 0 for h in hist_data[-3:]):  # 都是红色柱体
                if hist_data.iloc[-1] < hist_data.iloc[-2] < hist_data.iloc[-3]:
                    print(f"   ✅ MACD红色柱体连续2根缩短")
                    momentum_sell = True
            
            # 2. MACD柱体已为绿色
            if macd_hist_current < 0:
                print(f"   ✅ MACD柱体已为绿色")
                momentum_sell = True
            
            # 3. DIF死叉DEA
            if len(macd_data) >= 2 and len(signal_data) >= 2:
                if (macd_data.iloc[-2] > signal_data.iloc[-2] and 
                    macd_data.iloc[-1] < signal_data.iloc[-1]):
                    print(f"   ✅ DIF死叉DEA")
                    momentum_sell = True
            
            # 检查买入条件
            # 1. MACD绿色柱体连续2根缩短
            if len(hist_data) >= 3 and all(h < 0 for h in hist_data[-3:]):  # 都是绿色柱体
                if hist_data.iloc[-1] > hist_data.iloc[-2] > hist_data.iloc[-3]:  # 绿色柱体缩短意味着数值变大（接近0）
                    print(f"   ✅ MACD绿色柱体连续2根缩短")
                    momentum_buy = True
            
            # 2. MACD柱体已为红色
            if macd_hist_current > 0:
                print(f"   ✅ MACD柱体已为红色")
                momentum_buy = True
            
            # 3. DIF金叉DEA
            if len(macd_data) >= 2 and len(signal_data) >= 2:
                if (macd_data.iloc[-2] < signal_data.iloc[-2] and 
                    macd_data.iloc[-1] > signal_data.iloc[-1]):
                    print(f"   ✅ DIF金叉DEA")
                    momentum_buy = True
        
        print(f"   动能确认维度支持卖出: {momentum_sell}")
        print(f"   动能确认维度支持买入: {momentum_buy}")
        
        # 4. 极端价格+量能分析
        print(f"\n4. 【极端价格+量能 - 布林带+成交量】")
        bb_upper = target_row['bb_upper']
        bb_lower = target_row['bb_lower']
        current_price = target_row['close']
        current_volume = target_row['volume']
        volume_ma = target_row['volume_ma']  # 4周均量
        
        print(f"   收盘价: {current_price:.2f}")
        print(f"   布林上轨: {bb_upper:.2f}")
        print(f"   布林下轨: {bb_lower:.2f}")
        print(f"   当前成交量: {current_volume:,.0f}")
        print(f"   4周均量: {volume_ma:,.0f}")
        
        # 检查极端价格+量能条件
        # 卖出：收盘价≥布林上轨且本周量≥4周均量×1.3
        price_at_upper = current_price >= bb_upper
        volume_amplified_sell = current_volume >= volume_ma * 1.3
        extreme_price_volume_sell = price_at_upper and volume_amplified_sell
        
        # 买入：收盘价≤布林下轨且本周量≥4周均量×0.8
        price_at_lower = current_price <= bb_lower
        volume_amplified_buy = current_volume >= volume_ma * 0.8
        extreme_price_volume_buy = price_at_lower and volume_amplified_buy
        
        print(f"   价格达到布林上轨: {price_at_upper}")
        print(f"   成交量放大(≥1.3倍均量): {volume_amplified_sell} (比例: {current_volume/volume_ma:.2f})")
        print(f"   价格达到布林下轨: {price_at_lower}")
        print(f"   成交量放大(≥0.8倍均量): {volume_amplified_buy} (比例: {current_volume/volume_ma:.2f})")
        
        print(f"   极端价格+量能维度支持卖出: {extreme_price_volume_sell}")
        print(f"   极端价格+量能维度支持买入: {extreme_price_volume_buy}")
        
        # 5. 综合信号判断
        print(f"\n" + "="*60)
        print("综合信号判断")
        print("="*60)
        
        print(f"\n卖出信号条件检查:")
        print(f"1. 价值比过滤器(硬性前提): {supports_sell}")
        print(f"2. 超买超卖维度: {overbought_oversold_sell}")
        print(f"3. 动能确认维度: {momentum_sell}")
        print(f"4. 极端价格+量能维度: {extreme_price_volume_sell}")
        
        other_dimensions_sell = sum([overbought_oversold_sell, momentum_sell, extreme_price_volume_sell])
        print(f"\n其他3维度满足数量: {other_dimensions_sell}/3 (需要≥2)")
        
        should_generate_sell_signal = supports_sell and other_dimensions_sell >= 2
        print(f"\n最终判断 - 应该产生卖出信号: {should_generate_sell_signal}")
        
        if not should_generate_sell_signal:
            print(f"\n❌ 未产生卖出信号的原因:")
            if not supports_sell:
                print(f"   - 价值比过滤器不支持")
            if other_dimensions_sell < 2:
                print(f"   - 其他维度条件不足 ({other_dimensions_sell}/3 < 2)")
                if not overbought_oversold_sell:
                    print(f"     * 超买超卖维度不满足")
                if not momentum_sell:
                    print(f"     * 动能确认维度不满足")
                if not extreme_price_volume_sell:
                    print(f"     * 极端价格+量能维度不满足")
        else:
            print(f"\n✅ 满足所有卖出信号条件，应该产生卖出信号")
            
    except Exception as e:
        print(f"分析过程中出错: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    analyze_4d_signals()
