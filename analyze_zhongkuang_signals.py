"""
分析中矿资源在特定日期的信号生成情况
专门分析 2022-02-25、2022-03-04 和 2022-03-11 为什么没有给出卖出信号
"""

import pandas as pd
import numpy as np
import logging
from datetime import datetime
import sys
import os

# 添加项目路径
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from strategy.signal_generator import SignalGenerator
from data.data_processor import DataProcessor
from config.csv_config_loader import create_csv_config

# 设置日志
logging.basicConfig(level=logging.DEBUG, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def analyze_specific_dates():
    """分析中矿资源在特定日期的信号情况"""
    
    stock_code = "002738"  # 中矿资源
    target_dates = ["2022-02-25", "2022-03-04", "2022-03-11"]
    
    print("=" * 80)
    print("🔍 中矿资源信号分析")
    print("=" * 80)
    print(f"📊 股票代码: {stock_code}")
    print(f"📅 分析日期: {', '.join(target_dates)}")
    print()
    
    try:
        # 1. 读取缓存数据
        cache_file = f"data_cache/stock_data/weekly/{stock_code}.csv"
        if not os.path.exists(cache_file):
            print(f"❌ 缓存文件不存在: {cache_file}")
            return
        
        print(f"📁 读取缓存数据: {cache_file}")
        data = pd.read_csv(cache_file)
        data['date'] = pd.to_datetime(data['date'])
        data = data.set_index('date').sort_index()
        
        print(f"✅ 数据加载完成，共 {len(data)} 条记录")
        print(f"📅 数据时间范围: {data.index[0].date()} 至 {data.index[-1].date()}")
        print()
        
        # 2. 加载配置和DCF估值
        config = create_csv_config()
        dcf_values = {}
        
        # 从配置中提取DCF估值
        portfolio_df = pd.read_csv('Input/portfolio_config.csv', encoding='utf-8-sig')
        for _, row in portfolio_df.iterrows():
            if str(row['Stock_number']).strip() == stock_code:
                dcf_values[stock_code] = float(row['DCF_value_per_share'])
                break
        
        print(f"💰 DCF估值: {dcf_values.get(stock_code, '未找到')} 元/股")
        print()
        
        # 3. 创建信号生成器
        signal_config = {
            'ema_period': 20,
            'rsi_period': 14,
            'rsi_overbought': 70,
            'rsi_oversold': 30,
            'macd_fast': 12,
            'macd_slow': 26,
            'macd_signal': 9,
            'bb_period': 20,
            'bb_std': 2,
            'volume_ma_period': 4,
            'volume_buy_ratio': 0.8,
            'volume_sell_ratio': 1.3,
            'min_data_length': 60,
            'value_ratio_sell_threshold': 80.0,
            'value_ratio_buy_threshold': 70.0
        }
        
        signal_generator = SignalGenerator(signal_config, dcf_values)
        
        # 4. 分析每个目标日期
        for target_date in target_dates:
            print("=" * 60)
            print(f"📅 分析日期: {target_date}")
            print("=" * 60)
            
            # 找到目标日期或最接近的日期
            target_dt = pd.to_datetime(target_date)
            
            # 找到目标日期之前的最新数据点
            available_dates = data.index[data.index <= target_dt]
            if len(available_dates) == 0:
                print(f"❌ 没有找到 {target_date} 之前的数据")
                continue
            
            actual_date = available_dates[-1]
            print(f"🎯 实际分析日期: {actual_date.date()} (目标: {target_date})")
            
            # 获取到该日期为止的所有数据
            data_until_date = data.loc[:actual_date].copy()
            
            if len(data_until_date) < 60:
                print(f"❌ 数据不足，只有 {len(data_until_date)} 条记录")
                continue
            
            # 获取当日数据
            current_data = data_until_date.iloc[-1]
            print(f"📊 当日数据:")
            print(f"   - 收盘价: {current_data['close']:.2f} 元")
            print(f"   - 成交量: {current_data['volume']:,.0f}")
            print(f"   - 涨跌幅: {((current_data['close'] / current_data['open'] - 1) * 100):.2f}%")
            
            # 计算价值比
            dcf_value = dcf_values.get(stock_code, 0)
            if dcf_value > 0:
                price_value_ratio = (current_data['close'] / dcf_value) * 100
                print(f"   - 价值比: {price_value_ratio:.1f}% (DCF估值: {dcf_value:.2f})")
                print(f"   - 卖出阈值: 80.0%, 买入阈值: 70.0%")
            
            print()
            
            try:
                # 生成信号
                signal_result = signal_generator.generate_signal(stock_code, data_until_date)
                
                print("🎯 信号分析结果:")
                print(f"   - 信号类型: {signal_result['signal']}")
                print(f"   - 置信度: {signal_result['confidence']:.2f}")
                print(f"   - 触发原因: {signal_result['reason']}")
                
                # 详细分析4维度评分
                scores = signal_result['scores']
                print()
                print("📊 4维度评分详情:")
                print(f"   1. 价值比过滤器:")
                print(f"      - 支持卖出: {scores['trend_filter_high']} (价值比 > 80%)")
                print(f"      - 支持买入: {scores['trend_filter_low']} (价值比 < 70%)")
                
                print(f"   2. 超买超卖信号:")
                print(f"      - 支持卖出: {scores['overbought_oversold_high']} (RSI超买+背离)")
                print(f"      - 支持买入: {scores['overbought_oversold_low']} (RSI超卖+背离)")
                
                print(f"   3. 动能确认:")
                print(f"      - 支持卖出: {scores['momentum_high']} (MACD红缩短/转绿/死叉)")
                print(f"      - 支持买入: {scores['momentum_low']} (MACD绿缩短/转红/金叉)")
                
                print(f"   4. 极端价格+量能:")
                print(f"      - 支持卖出: {scores['extreme_price_volume_high']} (≥布林上轨+放量)")
                print(f"      - 支持买入: {scores['extreme_price_volume_low']} (≤布林下轨+放量)")
                
                # 技术指标详情
                if 'technical_indicators' in signal_result:
                    indicators = signal_result['technical_indicators']
                    print()
                    print("📈 技术指标详情:")
                    print(f"   - RSI(14): {indicators.get('rsi_14w', 0):.2f}")
                    print(f"   - EMA(20): {indicators.get('ema_20w', 0):.2f}")
                    print(f"   - MACD DIF: {indicators.get('macd_dif', 0):.4f}")
                    print(f"   - MACD DEA: {indicators.get('macd_dea', 0):.4f}")
                    print(f"   - MACD HIST: {indicators.get('macd_hist', 0):.4f}")
                    print(f"   - 布林上轨: {indicators.get('bb_upper', 0):.2f}")
                    print(f"   - 布林下轨: {indicators.get('bb_lower', 0):.2f}")
                    print(f"   - 成交量比率: {indicators.get('volume_ratio', 0):.2f}")
                
                # 分析为什么没有卖出信号
                print()
                print("🔍 卖出信号分析:")
                
                # 检查价值比过滤器
                if dcf_value > 0:
                    if price_value_ratio <= 80.0:
                        print(f"   ❌ 价值比过滤器不支持卖出: {price_value_ratio:.1f}% ≤ 80.0%")
                        print(f"      股价相对DCF估值仍然偏低，不满足卖出的价值比条件")
                    else:
                        print(f"   ✅ 价值比过滤器支持卖出: {price_value_ratio:.1f}% > 80.0%")
                
                # 统计其他维度
                sell_dimensions = [
                    scores['overbought_oversold_high'],
                    scores['momentum_high'], 
                    scores['extreme_price_volume_high']
                ]
                sell_count = sum(sell_dimensions)
                
                print(f"   📊 其他维度卖出信号数量: {sell_count}/3 (需要≥2个)")
                if sell_count < 2:
                    print(f"      ❌ 其他维度信号不足，无法生成卖出信号")
                    print(f"      - 超买超卖: {'✅' if scores['overbought_oversold_high'] else '❌'}")
                    print(f"      - 动能确认: {'✅' if scores['momentum_high'] else '❌'}")
                    print(f"      - 极端价格+量能: {'✅' if scores['extreme_price_volume_high'] else '❌'}")
                else:
                    print(f"      ✅ 其他维度信号充足")
                
                print()
                
            except Exception as e:
                print(f"❌ 信号生成失败: {e}")
                import traceback
                traceback.print_exc()
            
            print()
        
        print("=" * 80)
        print("📋 分析总结")
        print("=" * 80)
        print("根据4维信号系统的规则:")
        print("1. 必须先满足价值比过滤器（硬性条件）")
        print("2. 然后在其余3个维度中至少满足2个")
        print()
        print("中矿资源在这些日期没有卖出信号的可能原因:")
        print("• 价值比过滤器不支持卖出（股价/DCF估值 ≤ 80%）")
        print("• 或者其他3个维度中满足的数量 < 2个")
        print("• RSI未达到超买状态或缺乏背离确认")
        print("• MACD动能确认条件不满足")
        print("• 未触及布林带上轨或成交量不够放大")
        
    except Exception as e:
        print(f"❌ 分析失败: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    analyze_specific_dates()