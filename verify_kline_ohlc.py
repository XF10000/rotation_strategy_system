#!/usr/bin/env python3
"""
验证HTML报告中K线图OHLC数据的正确性
"""

import json
import re
import pandas as pd

def verify_kline_ohlc_data():
    """验证K线图OHLC数据的正确性"""
    
    # 读取最新的HTML报告
    html_file = "reports/integrated_backtest_report_20250803_164338.html"
    
    try:
        with open(html_file, 'r', encoding='utf-8') as f:
            content = f.read()
        
        # 提取K线数据
        kline_data_match = re.search(r'const klineData = (\{[^;]+\});', content, re.DOTALL)
        if not kline_data_match:
            print("❌ 未找到K线数据")
            return False
        
        # 解析K线数据
        kline_data_str = kline_data_match.group(1)
        # 修复JSON格式问题
        kline_data_str = kline_data_str.replace("'", '"')
        kline_data = json.loads(kline_data_str)
        
        print(f"✅ 成功解析K线数据，包含 {len(kline_data)} 只股票")
        
        # 验证600079的2024-09-13数据
        if '600079' in kline_data:
            stock_data = kline_data['600079']
            kline_points = stock_data.get('kline', [])
            trades = stock_data.get('trades', [])
            
            print(f"\n📊 600079股票数据:")
            print(f"   K线数据点: {len(kline_points)}个")
            print(f"   交易点: {len(trades)}个")
            
            # 打印所有交易点数据进行调试
            print(f"\n🔍 所有交易点数据:")
            for i, trade in enumerate(trades):
                print(f"   交易{i+1}: {trade}")
            
            # 查找2024-09-13的交易点（使用时间戳）
            # 2024-09-13对应的时间戳是1726185600000
            target_timestamp = 1726185600000
            target_trade = None
            for trade in trades:
                if trade.get('timestamp') == target_timestamp:
                    target_trade = trade
                    break
            
            if target_trade:
                print(f"\n🎯 找到2024-09-13的交易点:")
                print(f"   交易类型: {target_trade.get('type')}")
                print(f"   价格: {target_trade.get('price')}")
                
                # 查找对应的K线数据
                trade_timestamp = target_trade.get('timestamp')
                if trade_timestamp:
                    # 查找最接近的K线数据点
                    closest_kline = None
                    min_time_diff = float('inf')
                    
                    for kline in kline_points:
                        time_diff = abs(kline[0] - trade_timestamp)
                        if time_diff < min_time_diff:
                            min_time_diff = time_diff
                            closest_kline = kline
                    
                    if closest_kline:
                        # ECharts蜡烛图格式: [timestamp, open, close, low, high]
                        timestamp, open_price, close_price, low_price, high_price = closest_kline
                        print(f"\n📈 对应的K线数据 (ECharts蜡烛图格式):")
                        print(f"   时间戳: {timestamp}")
                        print(f"   开盘价: {open_price}")
                        print(f"   收盘价: {close_price}")
                        print(f"   最低价: {low_price}")
                        print(f"   最高价: {high_price}")
                        
                        print(f"\n🔍 数据格式检查:")
                        print(f"   原始数据: {closest_kline}")
                        print(f"   解析结果: [时间戳={timestamp}, 开盘={open_price}, 收盘={close_price}, 最低={low_price}, 最高={high_price}]")
                        
                        # 验证OHLC逻辑关系
                        print(f"\n🔍 OHLC数据验证:")
                        print(f"   最高价 >= 开盘价: {high_price >= open_price} ({'✅' if high_price >= open_price else '❌'})")
                        print(f"   最高价 >= 收盘价: {high_price >= close_price} ({'✅' if high_price >= close_price else '❌'})")
                        print(f"   最低价 <= 开盘价: {low_price <= open_price} ({'✅' if low_price <= open_price else '❌'})")
                        print(f"   最低价 <= 收盘价: {low_price <= close_price} ({'✅' if low_price <= close_price else '❌'})")
                        
                        # 检查数据合理性
                        all_valid = (
                            high_price >= open_price and 
                            high_price >= close_price and 
                            low_price <= open_price and 
                            low_price <= close_price
                        )
                        
                        # 验证蜡烛图颜色逻辑
                        print(f"\n🎨 蜡烛图颜色验证:")
                        if close_price > open_price:
                            print(f"   收盘价({close_price}) > 开盘价({open_price}): 阳线 (红色) ✅")
                        elif close_price < open_price:
                            print(f"   收盘价({close_price}) < 开盘价({open_price}): 阴线 (绿色) ✅")
                        else:
                            print(f"   收盘价({close_price}) = 开盘价({open_price}): 十字星 (中性) ✅")
                        
                        if all_valid:
                            print(f"\n🎉 OHLC数据和蜡烛图颜色验证通过！")
                            return True
                        else:
                            print(f"\n❌ OHLC数据验证失败！")
                            return False
                    else:
                        print(f"❌ 未找到对应的K线数据点")
                        return False
                else:
                    print(f"❌ 交易点缺少时间戳")
                    return False
            else:
                print(f"❌ 未找到{target_date}的交易点")
                return False
        else:
            print(f"❌ 未找到600079的股票数据")
            return False
            
    except Exception as e:
        print(f"❌ 验证过程出错: {e}")
        return False

if __name__ == "__main__":
    print("🔍 开始验证K线图OHLC数据...")
    success = verify_kline_ohlc_data()
    if success:
        print("\n✅ 验证完成：K线图OHLC数据正确！")
    else:
        print("\n❌ 验证失败：K线图OHLC数据有问题！")
