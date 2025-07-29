#!/usr/bin/env python3
"""
验证数据源准确性
对比akshare与其他数据源的差异
"""

import pandas as pd
import numpy as np
import logging
from datetime import datetime
import sys
import os

# 添加项目路径
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from data.data_fetcher import AkshareDataFetcher

# 设置日志
logging.basicConfig(level=logging.WARNING)

def verify_akshare_data():
    """验证akshare数据的准确性"""
    print("🔍 验证akshare数据源准确性")
    print("=" * 60)
    
    try:
        fetcher = AkshareDataFetcher()
        
        # 获取601898在2024年3月8日前后的日线数据
        daily_data = fetcher.get_stock_data('601898', '2024-03-01', '2024-03-15', 'daily')
        
        if daily_data is None or daily_data.empty:
            print("❌ 数据获取失败")
            return
        
        print(f"📊 601898 (中煤能源) 2024年3月前后的日线数据:")
        print("-" * 50)
        
        for date, row in daily_data.iterrows():
            weekday = date.strftime('%A')
            marker = "👉" if date.strftime('%Y-%m-%d') == '2024-03-08' else "  "
            print(f"{marker} {date.strftime('%Y-%m-%d')} ({weekday[:3]}): "
                  f"开盘={row['open']:6.2f}, 最高={row['high']:6.2f}, "
                  f"最低={row['low']:6.2f}, 收盘={row['close']:6.2f}, "
                  f"成交量={row['volume']:>8,}")
        
        # 检查3月8日的具体数据
        march_8_data = daily_data.loc[daily_data.index.date == pd.to_datetime('2024-03-08').date()]
        
        if not march_8_data.empty:
            row = march_8_data.iloc[0]
            print(f"\n🎯 2024年3月8日 akshare数据详情:")
            print(f"   开盘价: {row['open']:.2f}")
            print(f"   最高价: {row['high']:.2f}")
            print(f"   最低价: {row['low']:.2f}")
            print(f"   收盘价: {row['close']:.2f}")
            print(f"   成交量: {row['volume']:,}")
            print(f"   成交额: {row['amount']:,.0f}")
            
            # 计算涨跌幅
            if len(daily_data) > 1:
                prev_close = daily_data['close'].iloc[-2]  # 前一日收盘价
                change = row['close'] - prev_close
                change_pct = (change / prev_close) * 100
                print(f"   涨跌额: {change:+.2f}")
                print(f"   涨跌幅: {change_pct:+.2f}%")
        
        # 获取更长期的数据来分析趋势
        print(f"\n📈 分析2024年1-3月的价格趋势:")
        long_data = fetcher.get_stock_data('601898', '2024-01-01', '2024-03-31', 'daily')
        
        if long_data is not None and not long_data.empty:
            # 计算每周的收盘价
            weekly_closes = long_data.resample('W-FRI')['close'].last().dropna()
            
            print(f"2024年1-3月周收盘价:")
            for date, close in weekly_closes.items():
                marker = "👉" if abs((date - pd.to_datetime('2024-03-08')).days) <= 3 else "  "
                print(f"{marker} {date.strftime('%Y-%m-%d')}: {close:.2f}")
            
            # 计算整体趋势
            start_price = long_data['close'].iloc[0]
            end_price = long_data['close'].iloc[-1]
            total_change = (end_price - start_price) / start_price * 100
            
            print(f"\n📊 2024年1-3月整体表现:")
            print(f"   期初价格: {start_price:.2f}")
            print(f"   期末价格: {end_price:.2f}")
            print(f"   总涨跌幅: {total_change:+.2f}%")
            
            # 分析是否存在异常波动
            daily_returns = long_data['close'].pct_change().dropna()
            max_gain = daily_returns.max() * 100
            max_loss = daily_returns.min() * 100
            volatility = daily_returns.std() * 100
            
            print(f"   最大单日涨幅: {max_gain:.2f}%")
            print(f"   最大单日跌幅: {max_loss:.2f}%")
            print(f"   日收益率标准差: {volatility:.2f}%")
        
        # 建议验证方法
        print(f"\n💡 建议验证方法:")
        print(f"1. 在同花顺/Wind/雪球上查看601898在2024年3月8日的收盘价")
        print(f"2. 对比我们显示的11.76是否准确")
        print(f"3. 检查2024年1-3月的价格走势是否与实际一致")
        print(f"4. 如果数据有差异，可能需要:")
        print(f"   - 检查复权设置")
        print(f"   - 验证数据源的可靠性")
        print(f"   - 考虑使用其他数据源")
        
        return {
            'march_8_close': row['close'] if not march_8_data.empty else None,
            'data_range': f"{daily_data.index.min()} - {daily_data.index.max()}",
            'record_count': len(daily_data)
        }
        
    except Exception as e:
        print(f"❌ 验证失败: {e}")
        import traceback
        traceback.print_exc()
        return None

if __name__ == "__main__":
    result = verify_akshare_data()
    
    if result:
        print(f"\n🎯 验证结论:")
        print(f"如果akshare数据与实际市场数据一致，那么我们的RSI计算是正确的")
        print(f"如果存在差异，则需要调整数据源或数据处理方法")