"""
测试优化后的Portfolio数据管理系统
"""
import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from backtest.portfolio_data_manager import PortfolioDataManager
import pandas as pd
from datetime import datetime, timedelta

def test_portfolio_data_manager():
    """测试Portfolio数据管理器的功能"""
    print("🚀 开始测试Portfolio数据管理器...")
    
    # 1. 初始化数据管理器
    total_capital = 15000000  # 1500万
    manager = PortfolioDataManager(total_capital)
    
    print(f"✅ 数据管理器初始化完成，总资金: {total_capital:,}")
    
    # 2. 设置价格数据
    test_stocks = ['601088', '601225', '600985']
    base_date = datetime(2024, 1, 1)
    
    for i, stock_code in enumerate(test_stocks):
        price_data = {}
        base_price = 10 + i * 2  # 基础价格
        
        # 生成30天的价格数据
        for day in range(30):
            date = base_date + timedelta(days=day)
            date_str = date.strftime('%Y-%m-%d')
            # 模拟价格波动
            price = base_price + (day * 0.1) + (i * 0.5)
            price_data[date_str] = price
        
        manager.set_price_data(stock_code, price_data)
        print(f"✅ 设置 {stock_code} 价格数据，共 {len(price_data)} 个交易日")
    
    # 3. 记录Portfolio状态
    positions = {
        '601088': 100000,  # 10万股
        '601225': 200000,  # 20万股
        '600985': 150000,  # 15万股
    }
    
    cash = 5000000  # 500万现金
    
    # 记录多个交易日的状态
    for day in range(0, 30, 7):  # 每周记录一次
        date = base_date + timedelta(days=day)
        date_str = date.strftime('%Y-%m-%d')
        
        # 获取当日价格
        current_prices = {}
        for stock_code in test_stocks:
            current_prices[stock_code] = manager.get_price(stock_code, date_str)
        
        # 模拟持仓变化
        if day > 0:
            positions['601088'] += 1000  # 每周增加1000股
            cash -= current_prices['601088'] * 1000  # 相应减少现金
        
        manager.record_portfolio_state(
            date=date_str,
            positions=positions.copy(),
            cash=cash,
            prices=current_prices
        )
        
        print(f"✅ 记录 {date_str} Portfolio状态")
    
    # 4. 测试数据获取功能
    print("\n📊 测试数据获取功能:")
    
    # 获取初始状态
    initial_state = manager.get_initial_portfolio_state()
    print(f"📈 初始Portfolio状态: {initial_state}")
    
    # 获取最终状态
    final_state = manager.get_final_portfolio_state()
    print(f"📈 最终Portfolio状态: {final_state}")
    
    # 获取历史记录
    history_df = manager.get_portfolio_history()
    print(f"📈 Portfolio历史记录: {len(history_df)} 条记录")
    print(history_df.head())
    
    # 5. 测试性能指标计算
    print("\n📊 测试性能指标计算:")
    performance = manager.calculate_performance_metrics()
    print(f"📈 性能指标: {performance}")
    
    # 6. 测试持仓对比
    print("\n📊 测试持仓对比:")
    comparison = manager.get_position_comparison()
    print(f"📈 持仓对比: {comparison}")
    
    # 7. 测试摘要信息
    print("\n📊 测试摘要信息:")
    summary = manager.get_summary()
    print(f"📈 数据管理器摘要: {summary}")
    
    print("\n🎉 Portfolio数据管理器测试完成！")

def test_price_data_access():
    """测试价格数据访问功能"""
    print("\n🔍 测试价格数据访问功能...")
    
    manager = PortfolioDataManager(1000000)
    
    # 设置测试价格数据
    stock_code = '000001'
    price_data = {
        '2024-01-01': 10.0,
        '2024-01-02': 10.5,
        '2024-01-03': 11.0,
        '2024-01-04': 10.8,
        '2024-01-05': 11.2
    }
    
    manager.set_price_data(stock_code, price_data)
    
    # 测试各种价格获取方法
    print(f"✅ 获取特定日期价格: {manager.get_price(stock_code, '2024-01-03')}")
    print(f"✅ 获取初始价格: {manager.get_initial_price(stock_code)}")
    print(f"✅ 获取最新价格: {manager.get_latest_price(stock_code)}")
    
    # 测试不存在的数据
    print(f"✅ 获取不存在日期: {manager.get_price(stock_code, '2024-01-10')}")
    print(f"✅ 获取不存在股票: {manager.get_price('999999', '2024-01-01')}")

if __name__ == "__main__":
    test_portfolio_data_manager()
    test_price_data_access()