#!/usr/bin/env python3
"""
检查600079在2024-09-13的原始股票数据
"""

import pandas as pd
from datetime import datetime

def check_raw_stock_data():
    """检查原始股票数据"""
    
    # 读取600079的原始数据
    data_file = "data_cache/stock_data/weekly/600079.csv"
    
    try:
        df = pd.read_csv(data_file)
        df['date'] = pd.to_datetime(df['date'])
        
        # 查找2024-09-13附近的数据
        target_date = pd.to_datetime('2024-09-13')
        
        # 找到最接近的日期
        df['date_diff'] = abs(df['date'] - target_date)
        closest_idx = df['date_diff'].idxmin()
        closest_row = df.loc[closest_idx]
        
        print(f"📊 600079原始股票数据:")
        print(f"   最接近日期: {closest_row['date']}")
        print(f"   开盘价: {closest_row['open']}")
        print(f"   最高价: {closest_row['high']}")
        print(f"   最低价: {closest_row['low']}")
        print(f"   收盘价: {closest_row['close']}")
        print(f"   成交量: {closest_row['volume']}")
        
        # 验证OHLC逻辑
        open_price = closest_row['open']
        high_price = closest_row['high']
        low_price = closest_row['low']
        close_price = closest_row['close']
        
        print(f"\n🔍 原始数据OHLC验证:")
        print(f"   最高价 >= 开盘价: {high_price >= open_price} ({'✅' if high_price >= open_price else '❌'})")
        print(f"   最高价 >= 收盘价: {high_price >= close_price} ({'✅' if high_price >= close_price else '❌'})")
        print(f"   最低价 <= 开盘价: {low_price <= open_price} ({'✅' if low_price <= open_price else '❌'})")
        print(f"   最低价 <= 收盘价: {low_price <= close_price} ({'✅' if low_price <= close_price else '❌'})")
        
        # 蜡烛图颜色
        print(f"\n🎨 蜡烛图颜色:")
        if close_price > open_price:
            print(f"   收盘价({close_price}) > 开盘价({open_price}): 阳线 (红色)")
        elif close_price < open_price:
            print(f"   收盘价({close_price}) < 开盘价({open_price}): 阴线 (绿色)")
        else:
            print(f"   收盘价({close_price}) = 开盘价({open_price}): 十字星")
            
        return True
        
    except Exception as e:
        print(f"❌ 检查原始数据出错: {e}")
        return False

if __name__ == "__main__":
    print("🔍 开始检查600079原始股票数据...")
    check_raw_stock_data()
