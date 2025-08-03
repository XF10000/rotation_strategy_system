import pandas as pd
import json

# 读取最新生成的HTML报告，提取K线数据
html_file = "reports/integrated_backtest_report_20250803_162130.html"

print("🔍 验证蜡烛图数据和颜色逻辑...")

# 从HTML文件中提取K线数据
with open(html_file, 'r', encoding='utf-8') as f:
    content = f.read()

# 查找stockData部分
start_marker = "const stockData = "
end_marker = ";\n"

start_idx = content.find(start_marker)
if start_idx != -1:
    start_idx += len(start_marker)
    end_idx = content.find(end_marker, start_idx)
    if end_idx != -1:
        stock_data_str = content[start_idx:end_idx]
        try:
            stock_data = json.loads(stock_data_str)
            
            # 检查第一只股票的K线数据
            first_stock = list(stock_data.keys())[0]
            kline_data = stock_data[first_stock]['kline']
            
            print(f"📊 股票: {first_stock}")
            print(f"📊 K线数据点数量: {len(kline_data)}")
            
            # 分析前10个数据点的涨跌情况
            print("\n🔍 前10个K线数据点分析:")
            print("时间戳\t\t开盘\t最高\t最低\t收盘\t涨跌")
            
            up_count = 0
            down_count = 0
            
            for i, point in enumerate(kline_data[:10]):
                timestamp, open_price, high, low, close = point
                direction = "涨" if close > open_price else "跌" if close < open_price else "平"
                if close > open_price:
                    up_count += 1
                elif close < open_price:
                    down_count += 1
                    
                print(f"{timestamp}\t{open_price:.2f}\t{high:.2f}\t{low:.2f}\t{close:.2f}\t{direction}")
            
            # 统计全部数据的涨跌情况
            total_up = 0
            total_down = 0
            total_flat = 0
            
            for point in kline_data:
                timestamp, open_price, high, low, close = point
                if close > open_price:
                    total_up += 1
                elif close < open_price:
                    total_down += 1
                else:
                    total_flat += 1
            
            total_points = len(kline_data)
            print(f"\n📈 全部数据统计:")
            print(f"上涨周数: {total_up} ({total_up/total_points*100:.1f}%)")
            print(f"下跌周数: {total_down} ({total_down/total_points*100:.1f}%)")
            print(f"平盘周数: {total_flat} ({total_flat/total_points*100:.1f}%)")
            
            print(f"\n🎨 ECharts颜色逻辑:")
            print(f"color (红色 #ff4757): 用于上涨周 (close > open) - {total_up}个")
            print(f"color0 (绿色 #2ed573): 用于下跌周 (close <= open) - {total_down + total_flat}个")
            
            if total_down > 0:
                print(f"\n✅ 数据验证通过: 确实存在{total_down}个下跌周，应该显示绿色蜡烛")
            else:
                print(f"\n⚠️ 数据异常: 没有下跌周数据！")
                
        except Exception as e:
            print(f"❌ 解析股票数据失败: {e}")
else:
    print("❌ 未找到stockData")
