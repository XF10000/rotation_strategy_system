"""
测试 000807 在 2025-12-05 的 RSI 顶背离判断
"""
import pandas as pd
import sys
from pathlib import Path

# 添加项目路径
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

from data.data_storage import DataStorage
from indicators.momentum import calculate_rsi
from indicators.divergence import detect_rsi_divergence

def main():
    # 初始化数据存储
    storage = DataStorage()
    
    # 获取 000807 的数据
    stock_code = "000807"
    data = storage.load_data(stock_code, "weekly")
    
    if data is None or data.empty:
        print(f"❌ 无法加载 {stock_code} 的数据")
        return
    
    # 筛选到 2025-12-05 之前的数据
    target_date = pd.to_datetime("2025-12-05")
    data = data[data.index <= target_date].copy()
    
    print(f"📊 {stock_code} 数据范围: {data.index[0]} 到 {data.index[-1]}")
    print(f"📊 总共 {len(data)} 条记录\n")
    
    # 计算 RSI
    rsi = calculate_rsi(data['close'], period=14)
    
    # 获取最近 14 周的数据（回溯期 13 + 当前 1）
    lookback = 13
    recent_data = data.tail(lookback + 1).copy()
    recent_data['rsi'] = rsi.tail(lookback + 1)
    
    print("=" * 80)
    print(f"📈 最近 {lookback + 1} 周的价格和 RSI 数据:")
    print("=" * 80)
    print(f"{'日期':<12} {'收盘价':>8} {'RSI':>8}")
    print("-" * 80)
    
    for idx, row in recent_data.iterrows():
        print(f"{idx.strftime('%Y-%m-%d'):<12} {row['close']:>8.2f} {row['rsi']:>8.2f}")
    
    print("\n" + "=" * 80)
    print("🔍 顶背离分析:")
    print("=" * 80)
    
    # 当前值
    current_price = recent_data['close'].iloc[-1]
    current_rsi = recent_data['rsi'].iloc[-1]
    
    # 回溯期内的最大值
    max_price = recent_data['close'].max()
    max_rsi = recent_data['rsi'].max()
    
    # 找到最高价和最高 RSI 的日期
    max_price_date = recent_data['close'].idxmax()
    max_rsi_date = recent_data['rsi'].idxmax()
    
    print(f"当前日期: {recent_data.index[-1].strftime('%Y-%m-%d')}")
    print(f"当前价格: {current_price:.2f}")
    print(f"当前 RSI: {current_rsi:.2f}")
    print()
    print(f"回溯期内最高价: {max_price:.2f} (日期: {max_price_date.strftime('%Y-%m-%d')})")
    print(f"回溯期内最高 RSI: {max_rsi:.2f} (日期: {max_rsi_date.strftime('%Y-%m-%d')})")
    print()
    
    # 代码的判断逻辑
    price_at_high = abs(current_price - max_price) < 0.01
    indicator_below_high = current_rsi < max_rsi * 0.98
    
    print(f"代码判断:")
    print(f"  price_at_high = abs({current_price:.2f} - {max_price:.2f}) < 0.01 = {price_at_high}")
    print(f"  indicator_below_high = {current_rsi:.2f} < {max_rsi:.2f} * 0.98 = {current_rsi:.2f} < {max_rsi * 0.98:.2f} = {indicator_below_high}")
    print(f"  顶背离 = {price_at_high} AND {indicator_below_high} = {price_at_high and indicator_below_high}")
    print()
    
    # 使用代码检测
    divergence = detect_rsi_divergence(
        recent_data['close'], 
        recent_data['rsi'], 
        lookback=lookback
    )
    
    print(f"代码检测结果: {divergence}")
    print()
    
    # 人工分析：找局部高点
    print("=" * 80)
    print("🧠 人工分析 - 寻找局部高点:")
    print("=" * 80)
    
    # 简单的局部高点检测：比前后都高
    local_highs = []
    for i in range(1, len(recent_data) - 1):
        if (recent_data['close'].iloc[i] > recent_data['close'].iloc[i-1] and 
            recent_data['close'].iloc[i] > recent_data['close'].iloc[i+1]):
            local_highs.append({
                'date': recent_data.index[i],
                'price': recent_data['close'].iloc[i],
                'rsi': recent_data['rsi'].iloc[i]
            })
    
    # 加上当前点（如果是新高）
    if current_price >= recent_data['close'].iloc[-2]:
        local_highs.append({
            'date': recent_data.index[-1],
            'price': current_price,
            'rsi': current_rsi
        })
    
    if len(local_highs) >= 2:
        print(f"找到 {len(local_highs)} 个局部高点:")
        for i, high in enumerate(local_highs):
            print(f"  高点 {i+1}: {high['date'].strftime('%Y-%m-%d')} - 价格: {high['price']:.2f}, RSI: {high['rsi']:.2f}")
        
        # 比较最后两个高点
        if len(local_highs) >= 2:
            prev_high = local_highs[-2]
            curr_high = local_highs[-1]
            
            print()
            print("比较最后两个高点:")
            print(f"  前一个高点: 价格 {prev_high['price']:.2f}, RSI {prev_high['rsi']:.2f}")
            print(f"  当前高点:   价格 {curr_high['price']:.2f}, RSI {curr_high['rsi']:.2f}")
            print()
            
            price_higher = curr_high['price'] > prev_high['price']
            rsi_lower = curr_high['rsi'] < prev_high['rsi']
            
            print(f"  价格更高? {price_higher} ({curr_high['price']:.2f} > {prev_high['price']:.2f})")
            print(f"  RSI 更低? {rsi_lower} ({curr_high['rsi']:.2f} < {prev_high['rsi']:.2f})")
            print()
            
            if price_higher and rsi_lower:
                print("  ✅ 符合顶背离特征：价格创新高，RSI 未创新高")
            else:
                print("  ❌ 不符合顶背离特征")
    else:
        print(f"局部高点不足（只有 {len(local_highs)} 个），无法判断背离")

if __name__ == "__main__":
    main()
