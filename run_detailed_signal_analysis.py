#!/usr/bin/env python3
"""
详细分析601225在2025-02-28和2025-03-07的信号状态
获取具体的技术指标数值和4维度评分
"""

import sys
import os
import pandas as pd
import numpy as np
import logging
from datetime import datetime, timedelta

# 添加项目路径
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

try:
    from data.data_fetcher import AkshareDataFetcher
    from data.data_processor import DataProcessor
    from strategy.signal_generator import SignalGenerator
    from config.csv_config_loader import create_csv_config
    from indicators.trend import detect_ema_trend
except ImportError as e:
    print(f"❌ 导入模块失败: {e}")
    print("请确保在项目根目录运行此脚本")
    sys.exit(1)

# 设置日志
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

def get_week_date(target_date_str):
    """获取指定日期所在周的周五日期（或最接近的交易日）"""
    target_date = pd.to_datetime(target_date_str)
    # 找到该周的周五
    days_to_friday = (4 - target_date.weekday()) % 7
    if days_to_friday == 0 and target_date.weekday() != 4:  # 如果不是周五
        days_to_friday = 7  # 下一个周五
    friday = target_date + timedelta(days=days_to_friday)
    return friday

def analyze_detailed_signals():
    """详细分析601225的信号状态"""
    
    stock_code = "601225"
    target_dates = ["2025-02-28", "2025-03-07"]
    
    print("🚀 开始详细分析601225买入信号")
    print("="*80)
    
    try:
        # 初始化组件
        config = create_csv_config()
        
        data_fetcher = AkshareDataFetcher()
        data_processor = DataProcessor()
        signal_generator = SignalGenerator(config)
        
        # 获取数据时间范围
        start_date = '2024-01-01'  # 提前获取更多数据用于技术指标计算
        end_date = '2025-12-31'
        
        print(f"📊 正在获取股票 {stock_code} 的数据...")
        print(f"📅 数据时间范围: {start_date} 到 {end_date}")
        
        # 获取日线数据
        daily_data = data_fetcher.get_stock_data(stock_code, start_date, end_date, 'daily')
        if daily_data is None or daily_data.empty:
            print(f"❌ 无法获取股票 {stock_code} 的日线数据")
            return False
        
        # 转换为周线数据
        weekly_data = data_processor.resample_to_weekly(daily_data)
        if weekly_data is None or weekly_data.empty:
            print(f"❌ 无法转换股票 {stock_code} 的周线数据")
            return False
        
        # 计算技术指标
        weekly_data_with_indicators = data_processor.calculate_technical_indicators(weekly_data)
        
        print(f"✅ 数据获取成功:")
        print(f"   - 日线数据: {len(daily_data)} 条")
        print(f"   - 周线数据: {len(weekly_data_with_indicators)} 条")
        print(f"   - 数据时间范围: {weekly_data_with_indicators.index.min().strftime('%Y-%m-%d')} 到 {weekly_data_with_indicators.index.max().strftime('%Y-%m-%d')}")
        
        # 分析每个目标日期
        for target_date_str in target_dates:
            print(f"\n{'='*80}")
            print(f"🎯 分析日期: {target_date_str}")
            print(f"{'='*80}")
            
            # 获取该周的周五日期
            week_friday = get_week_date(target_date_str)
            print(f"📅 对应周线日期: {week_friday.strftime('%Y-%m-%d')}")
            
            # 找到最接近的周线数据点
            available_dates = weekly_data_with_indicators.index
            closest_date = None
            min_diff = float('inf')
            
            for date in available_dates:
                diff = abs((date - week_friday).days)
                if diff < min_diff:
                    min_diff = diff
                    closest_date = date
            
            if closest_date is None:
                print(f"⚠️ 找不到 {target_date_str} 附近的周线数据")
                continue
            
            print(f"📊 使用数据日期: {closest_date.strftime('%Y-%m-%d')} (相差{min_diff}天)")
            
            # 获取到该日期为止的所有数据
            data_up_to_date = weekly_data_with_indicators[weekly_data_with_indicators.index <= closest_date]
            
            if len(data_up_to_date) < 60:
                print(f"⚠️ 数据不足，只有 {len(data_up_to_date)} 条记录，可能影响技术指标准确性")
            
            # 获取当前数据点
            current_data = data_up_to_date.iloc[-1]
            
            print(f"\n📈 基础数据:")
            print(f"   - 收盘价: {current_data['close']:.2f}")
            print(f"   - 成交量: {current_data['volume']:,.0f}")
            print(f"   - 开盘价: {current_data['open']:.2f}")
            print(f"   - 最高价: {current_data['high']:.2f}")
            print(f"   - 最低价: {current_data['low']:.2f}")
            
            # 计算技术指标
            try:
                # 生成信号（这会计算所有技术指标）
                signal_result = signal_generator.generate_signal(stock_code, data_up_to_date)
                
                print(f"\n📊 技术指标详情:")
                
                # EMA分析
                ema_20 = current_data.get('ema_20', np.nan)
                print(f"   📈 EMA20: {ema_20:.2f}")
                print(f"   📊 收盘价 vs EMA20: {current_data['close']:.2f} {'<' if current_data['close'] < ema_20 else '>='} {ema_20:.2f}")
                
                # EMA趋势分析
                if len(data_up_to_date) >= 8:
                    ema_series = data_up_to_date['ema_20'].dropna()
                    if len(ema_series) >= 8:
                        try:
                            ema_trend = detect_ema_trend(ema_series, 8, 0.003)
                            recent_ema = ema_series.iloc[-8:].values
                            x = np.arange(len(recent_ema))
                            slope, _ = np.polyfit(x, recent_ema, 1)
                            relative_slope = slope / np.mean(recent_ema)
                            
                            print(f"   📈 EMA趋势: {ema_trend}")
                            print(f"   📊 EMA斜率: {slope:.6f} (相对斜率: {relative_slope:.6f})")
                            print(f"   🎯 趋势判断阈值: ±0.003")
                        except Exception as e:
                            print(f"   ⚠️ EMA趋势计算失败: {e}")
                
                # RSI分析
                rsi = current_data.get('rsi', np.nan)
                print(f"   📊 RSI: {rsi:.2f}")
                print(f"   🎯 RSI超卖阈值: 30 (当前 {'≤' if rsi <= 30 else '>'} 30)")
                
                # MACD分析
                macd = current_data.get('macd', np.nan)
                macd_signal = current_data.get('macd_signal', np.nan)
                macd_hist = current_data.get('macd_histogram', np.nan)
                print(f"   📊 MACD DIF: {macd:.4f}")
                print(f"   📊 MACD DEA: {macd_signal:.4f}")
                print(f"   📊 MACD HIST: {macd_hist:.4f}")
                
                # 布林带分析
                bb_upper = current_data.get('bb_upper', np.nan)
                bb_middle = current_data.get('bb_middle', np.nan)
                bb_lower = current_data.get('bb_lower', np.nan)
                print(f"   📊 布林上轨: {bb_upper:.2f}")
                print(f"   📊 布林中轨: {bb_middle:.2f}")
                print(f"   📊 布林下轨: {bb_lower:.2f}")
                print(f"   🎯 收盘价 vs 布林下轨: {current_data['close']:.2f} {'≤' if current_data['close'] <= bb_lower else '>'} {bb_lower:.2f}")
                
                # 成交量分析
                volume_ma = current_data.get('volume_ma_4', np.nan)
                if not pd.isna(volume_ma):
                    volume_ratio = current_data['volume'] / volume_ma
                    print(f"   📊 4周均量: {volume_ma:,.0f}")
                    print(f"   📊 成交量比率: {volume_ratio:.2f}")
                    print(f"   🎯 成交量要求: ≥ {volume_ma * 0.8:,.0f} (4周均量×0.8)")
                
                # 信号分析结果
                print(f"\n🚦 信号分析结果:")
                print(f"   - 信号类型: {signal_result['signal']}")
                print(f"   - 置信度: {signal_result['confidence']}")
                print(f"   - 原因: {signal_result['reason']}")
                
                # 4维度评分详情
                if 'scores' in signal_result:
                    scores = signal_result['scores']
                    print(f"\n🔍 4维度评分详情:")
                    
                    print(f"   1️⃣ 趋势过滤器:")
                    print(f"      - 支持卖出: {'✅' if scores.get('trend_filter_high', False) else '❌'}")
                    print(f"      - 支持买入: {'✅' if scores.get('trend_filter_low', False) else '❌'}")
                    
                    print(f"   2️⃣ 超买超卖:")
                    print(f"      - 卖出信号: {'✅' if scores.get('overbought_oversold_high', False) else '❌'}")
                    print(f"      - 买入信号: {'✅' if scores.get('overbought_oversold_low', False) else '❌'}")
                    
                    print(f"   3️⃣ 动能确认:")
                    print(f"      - 卖出信号: {'✅' if scores.get('momentum_high', False) else '❌'} (红色缩短/转绿色/死叉)")
                    print(f"      - 买入信号: {'✅' if scores.get('momentum_low', False) else '❌'} (绿色缩短/转红色/金叉)")
                    
                    print(f"   4️⃣ 极端价格+量能:")
                    print(f"      - 卖出信号: {'✅' if scores.get('extreme_price_volume_high', False) else '❌'}")
                    print(f"      - 买入信号: {'✅' if scores.get('extreme_price_volume_low', False) else '❌'}")
                    
                    # 买入信号失败分析
                    print(f"\n💡 买入信号失败分析:")
                    trend_filter_ok = scores.get('trend_filter_low', False)
                    print(f"   🔒 趋势过滤器(硬性): {'✅ 通过' if trend_filter_ok else '❌ 未通过'}")
                    
                    if not trend_filter_ok:
                        print(f"   📋 失败原因: 趋势过滤器是买入信号的硬性前提")
                        if current_data['close'] >= ema_20:
                            print(f"      - 收盘价({current_data['close']:.2f}) ≥ EMA20({ema_20:.2f})")
                        if 'ema_trend' in locals() and ema_trend != "向下":
                            print(f"      - EMA趋势({ema_trend}) 不是向下")
                    else:
                        buy_signals = [
                            scores.get('overbought_oversold_low', False),
                            scores.get('momentum_low', False),
                            scores.get('extreme_price_volume_low', False)
                        ]
                        buy_count = sum(buy_signals)
                        print(f"   📊 其他维度满足数量: {buy_count}/3 (需要≥2)")
                        print(f"      - 超买超卖维度: {'✅' if buy_signals[0] else '❌'}")
                        print(f"      - 动能确认维度: {'✅' if buy_signals[1] else '❌'}")
                        print(f"      - 极端价格量能维度: {'✅' if buy_signals[2] else '❌'}")
                        
                        if buy_count < 2:
                            print(f"   📋 失败原因: 其他维度满足数量不足 ({buy_count} < 2)")
                
            except Exception as e:
                print(f"❌ 信号分析失败: {e}")
                import traceback
                traceback.print_exc()
                continue
        
        print(f"\n✅ 分析完成")
        return True
        
    except Exception as e:
        print(f"❌ 分析过程出错: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    success = analyze_detailed_signals()
    if success:
        print("\n🎉 分析成功完成！")
    else:
        print("\n💥 分析失败，请检查错误信息")
        sys.exit(1)
