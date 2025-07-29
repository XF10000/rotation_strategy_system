#!/usr/bin/env python3
"""
测试nan值修复效果
"""

import sys
import logging
from datetime import datetime
import pandas as pd

# 设置日志
logging.basicConfig(level=logging.INFO)

def test_signal_generator_indicators():
    """测试信号生成器的技术指标输出"""
    try:
        from strategy.signal_generator import SignalGenerator
        from data.data_fetcher import AkshareDataFetcher
        from data.data_processor import DataProcessor
        
        print("=" * 60)
        print("🧪 测试信号生成器技术指标输出")
        print("=" * 60)
        
        # 初始化组件
        config = {'ema_period': 20, 'rsi_period': 14}
        signal_gen = SignalGenerator(config)
        fetcher = AkshareDataFetcher()
        processor = DataProcessor()
        
        # 获取测试数据 - 使用更长时间范围确保有足够数据
        stock_code = '603345'
        print(f"📊 获取 {stock_code} 测试数据...")
        
        daily_data = fetcher.get_stock_data(stock_code, '2021-01-01', '2023-01-01', 'daily')
        if daily_data is None or daily_data.empty:
            print("❌ 数据获取失败")
            return False
        
        # 转换为周线并计算技术指标
        weekly_data = processor.resample_to_weekly(daily_data)
        weekly_data = processor.calculate_technical_indicators(weekly_data)
        
        print(f"✅ 获取到 {len(weekly_data)} 条周线数据")
        
        # 调试：检查技术指标计算结果
        print("\n📊 检查技术指标计算结果:")
        print("-" * 40)
        latest_row = weekly_data.iloc[-1]
        print(f"可用字段: {list(weekly_data.columns)}")
        print(f"最新数据日期: {weekly_data.index[-1]}")
        print(f"收盘价: {latest_row['close']:.2f}")
        if 'ema_20' in weekly_data.columns:
            print(f"EMA20: {latest_row['ema_20']:.2f}")
        if 'rsi' in weekly_data.columns:
            print(f"RSI: {latest_row['rsi']:.2f}")
        if 'macd' in weekly_data.columns:
            print(f"MACD: {latest_row['macd']:.4f}")
        if 'macd_signal' in weekly_data.columns:
            print(f"MACD Signal: {latest_row['macd_signal']:.4f}")
        
        # 生成信号
        print("\n🔄 生成交易信号...")
        signal_result = signal_gen.generate_signal(stock_code, weekly_data)
        
        # 检查技术指标
        print("\n📈 信号生成器返回的技术指标:")
        print("-" * 40)
        
        tech_indicators = signal_result.get('technical_indicators', {})
        has_nan = False
        
        for key, value in tech_indicators.items():
            is_nan = pd.isna(value) or str(value).lower() == 'nan'
            status = "❌ NaN" if is_nan else "✅ 正常"
            print(f"{key:15}: {value:8.4f} {status}")
            if is_nan:
                has_nan = True
        
        print(f"\n🎯 信号结果:")
        print(f"信号: {signal_result.get('signal', 'N/A')}")
        print(f"原因: {signal_result.get('reason', 'N/A')}")
        
        if has_nan:
            print("\n❌ 仍然存在NaN值！")
            return False
        else:
            print("\n✅ 所有技术指标都正常！")
            return True
            
    except Exception as e:
        print(f"❌ 测试失败: {e}")
        import traceback
        traceback.print_exc()
        return False

def test_csv_exporter():
    """测试CSV导出器使用真实技术指标数据"""
    try:
        from backtest.detailed_csv_exporter import DetailedCSVExporter
        from strategy.signal_generator import SignalGenerator
        from data.data_fetcher import AkshareDataFetcher
        from data.data_processor import DataProcessor
        
        print("\n" + "=" * 60)
        print("🧪 测试CSV导出器使用真实技术指标数据")
        print("=" * 60)
        
        # 获取真实的技术指标数据
        config = {'ema_period': 20, 'rsi_period': 14}
        signal_gen = SignalGenerator(config)
        fetcher = AkshareDataFetcher()
        processor = DataProcessor()
        
        stock_code = '603345'
        print(f"📊 获取 {stock_code} 真实数据用于CSV测试...")
        
        daily_data = fetcher.get_stock_data(stock_code, '2021-01-01', '2023-01-01', 'daily')
        if daily_data is None or daily_data.empty:
            print("❌ 数据获取失败")
            return False
        
        weekly_data = processor.resample_to_weekly(daily_data)
        weekly_data = processor.calculate_technical_indicators(weekly_data)
        
        # 生成真实的信号结果
        signal_result = signal_gen.generate_signal(stock_code, weekly_data)
        real_tech_indicators = signal_result.get('technical_indicators', {})
        
        print("📊 使用的真实技术指标:")
        print("-" * 30)
        for key, value in real_tech_indicators.items():
            print(f"{key}: {value}")
        
        # 创建使用真实技术指标的测试记录
        test_record = {
            'date': '2022-03-18',
            'type': 'BUY',
            'stock_code': '603345',
            'shares': 1100,
            'price': real_tech_indicators.get('close', 104.69),
            'gross_amount': 115159.0,
            'transaction_cost': 140.49,
            'reason': '现金买入',
            'technical_indicators': real_tech_indicators,  # 使用真实的技术指标
            'signal_details': {
                'dimension_status': {
                    'trend_filter': '✓',
                    'rsi_signal': '✓',
                    'macd_signal': '✓',
                    'bollinger_volume': '✗'
                },
                'reason': '买入信号：趋势过滤器+2个买入维度'
            }
        }
        
        exporter = DetailedCSVExporter()
        print("\n📝 格式化使用真实技术指标的交易记录...")
        formatted_row = exporter._format_trading_record(test_record)
        
        print("\n📊 格式化结果:")
        print("-" * 40)
        
        headers = exporter.csv_headers
        has_unrealistic_values = False
        
        for i, (header, value) in enumerate(zip(headers[:15], formatted_row[:15])):  # 只显示前15个字段
            is_nan = str(value).lower() == 'nan'
            
            # 检查是否是不合理的值（如EMA等于收盘价，RSI等于50，MACD等于0）
            is_unrealistic = False
            if header == 'EMA20' and abs(float(value) - real_tech_indicators.get('close', 0)) < 0.01:
                is_unrealistic = True
            elif header == 'RSI14' and abs(float(value) - 50.0) < 0.01:
                is_unrealistic = True
            elif header in ['MACD_DIF', 'MACD_DEA'] and abs(float(value)) < 0.01:
                is_unrealistic = True
            
            if is_nan:
                status = "❌ NaN"
                has_unrealistic_values = True
            elif is_unrealistic:
                status = "⚠️ 可能不合理"
                has_unrealistic_values = True
            else:
                status = "✅ 正常"
            
            print(f"{header:15}: {value:>10} {status}")
        
        if has_unrealistic_values:
            print("\n⚠️ CSV输出包含可能不合理的技术指标值！")
            return False
        else:
            print("\n✅ CSV输出的技术指标值都合理！")
            return True
            
    except Exception as e:
        print(f"❌ 测试失败: {e}")
        import traceback
        traceback.print_exc()
        return False

def main():
    """主测试函数"""
    print("🚀 NaN值修复效果测试")
    print("=" * 60)
    
    # 测试1: 信号生成器
    test1_passed = test_signal_generator_indicators()
    
    # 测试2: CSV导出器
    test2_passed = test_csv_exporter()
    
    # 总结
    print("\n" + "=" * 60)
    print("📋 测试总结")
    print("=" * 60)
    print(f"信号生成器测试: {'✅ 通过' if test1_passed else '❌ 失败'}")
    print(f"CSV导出器测试: {'✅ 通过' if test2_passed else '❌ 失败'}")
    
    if test1_passed and test2_passed:
        print("\n🎉 所有测试通过！NaN值问题已修复！")
    else:
        print("\n⚠️  部分测试失败，需要进一步修复")

if __name__ == "__main__":
    main()