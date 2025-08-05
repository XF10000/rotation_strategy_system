#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from config.csv_config_loader import load_portfolio_config
from config.backtest_configs import get_config
import pandas as pd

def track_yunlv_calculation():
    """跟踪云铝股份(000807)的持股数量计算过程"""
    print("🔍 跟踪云铝股份(000807)持股数量计算过程...")
    
    # 1. 读取配置文件
    print("\n📋 步骤1: 读取配置文件")
    portfolio_config = load_portfolio_config()
    print(f"云铝股份权重配置: {portfolio_config.get('000807', '未找到')}")
    
    # 2. 获取总资金
    print("\n💰 步骤2: 获取总资金")
    config = get_config('csv')
    total_capital = config.get('total_capital', 1000000)
    print(f"总资金: {total_capital:,.2f}")
    
    # 3. 计算云铝股份应分配资金
    yunlv_weight = portfolio_config.get('000807', 0)
    yunlv_target_value = total_capital * yunlv_weight
    print(f"\n📊 步骤3: 计算目标分配")
    print(f"云铝股份权重: {yunlv_weight}")
    print(f"云铝股份目标资金: {yunlv_target_value:,.2f}")
    
    # 4. 模拟获取初始价格（从实际数据中获取）
    print("\n💹 步骤4: 获取初始价格")
    try:
        # 尝试读取实际的股票数据
        from data.data_fetcher import AkshareDataFetcher
        from datetime import datetime, timedelta
        
        fetcher = AkshareDataFetcher()
        
        # 计算回测开始日期
        start_date = config.get('start_date', '2024-01-01')
        end_date = config.get('end_date', '2024-12-31')
        
        print(f"回测期间: {start_date} 到 {end_date}")
        
        # 获取云铝股份的历史数据
        yunlv_data = fetcher.get_stock_data('000807', start_date, end_date, 'weekly')
        
        if not yunlv_data.empty:
            initial_price = yunlv_data.iloc[0]['close']
            print(f"云铝股份初始价格: {initial_price:.2f}")
            
            # 5. 计算股数
            print(f"\n🧮 步骤5: 计算股数")
            print(f"目标资金: {yunlv_target_value:,.2f}")
            print(f"初始价格: {initial_price:.2f}")
            
            # 按照PortfolioManager的逻辑计算
            raw_shares = yunlv_target_value / initial_price
            shares_rounded_to_100 = int(raw_shares / 100) * 100
            actual_cost = shares_rounded_to_100 * initial_price
            
            print(f"原始股数: {raw_shares:.2f}")
            print(f"向下取整到100股: {shares_rounded_to_100}")
            print(f"实际成本: {actual_cost:,.2f}")
            print(f"剩余资金: {yunlv_target_value - actual_cost:,.2f}")
            
            # 6. 对比HTML报告中的数据
            print(f"\n📊 步骤6: 数据对比")
            print(f"计算得出的云铝股份持股数量: {shares_rounded_to_100}")
            print(f"HTML报告中显示的数量: 224,200 (待验证)")
            
            if shares_rounded_to_100 == 224200:
                print("✅ 数据一致！")
            else:
                print("❌ 数据不一致，需要进一步调查")
                print(f"差异: {abs(shares_rounded_to_100 - 224200)} 股")
        else:
            print("❌ 无法获取云铝股份数据")
            
    except Exception as e:
        print(f"❌ 获取数据失败: {e}")
        
        # 使用假设价格进行计算
        print("\n🔄 使用假设价格进行计算")
        assumed_prices = [2.5, 2.91, 3.0, 3.5]  # 不同的假设价格
        
        for price in assumed_prices:
            raw_shares = yunlv_target_value / price
            shares_rounded = int(raw_shares / 100) * 100
            actual_cost = shares_rounded * price
            
            print(f"假设价格 {price:.2f}: {shares_rounded} 股, 成本 {actual_cost:,.2f}")
            
            if shares_rounded == 224200:
                print(f"✅ 在价格 {price:.2f} 时得到 224,200 股!")

if __name__ == "__main__":
    track_yunlv_calculation()