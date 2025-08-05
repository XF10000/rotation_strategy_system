#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from config.csv_config_loader import load_portfolio_config
from config.backtest_configs import get_config
from data.data_fetcher import AkshareDataFetcher
import pandas as pd

def debug_yunlv_config():
    """调试云铝股份持股数量计算的不一致问题"""
    print("🔍 调试云铝股份持股数量不一致问题...")
    
    # 1. 检查配置文件
    print("\n📋 步骤1: 检查配置文件")
    portfolio_config = load_portfolio_config()
    yunlv_weight = portfolio_config.get('000807', 0)
    print(f"云铝股份权重配置: {yunlv_weight}")
    
    # 2. 检查总资金配置
    print("\n💰 步骤2: 检查总资金配置")
    config = get_config('csv')
    total_capital = config.get('total_capital', 1000000)
    print(f"总资金: {total_capital:,.2f}")
    
    # 3. 计算目标资金
    yunlv_target_value = total_capital * yunlv_weight
    print(f"\n📊 步骤3: 计算目标资金")
    print(f"云铝股份目标资金: {yunlv_target_value:,.2f}")
    
    # 4. 检查初始价格
    print("\n💹 步骤4: 检查初始价格")
    try:
        # 获取回测开始日期
        start_date = config.get('start_date', '2024-01-01')
        end_date = config.get('end_date', '2024-12-31')
        print(f"回测期间: {start_date} 到 {end_date}")
        
        # 获取云铝股份的历史数据
        fetcher = AkshareDataFetcher()
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
            
            # 6. 检查不同价格下的股数
            print(f"\n🔍 步骤6: 检查不同价格下的股数")
            test_prices = [2.91, 6.69]
            for price in test_prices:
                raw_shares = yunlv_target_value / price
                shares_rounded = int(raw_shares / 100) * 100
                actual_cost = shares_rounded * price
                
                print(f"价格 {price:.2f}: {shares_rounded:,}股, 成本 {actual_cost:,.2f}")
                
                if shares_rounded == 224200:
                    print(f"  ✅ 匹配224,200股")
                if shares_rounded == 515400:
                    print(f"  ✅ 匹配515,400股")
            
            # 7. 反向计算价格
            print(f"\n🔄 步骤7: 反向计算价格")
            for shares in [224200, 515400]:
                implied_price = yunlv_target_value / shares
                print(f"持股 {shares:,}股 对应的价格: {implied_price:.2f}")
        else:
            print("❌ 无法获取云铝股份数据")
    except Exception as e:
        print(f"❌ 获取数据失败: {e}")
    
    # 8. 检查日志文件中的记录
    print(f"\n📝 步骤8: 检查日志文件")
    try:
        log_files = [f for f in os.listdir('.') if f.endswith('.log')]
        for log_file in log_files[:3]:  # 只检查前3个日志文件
            print(f"检查日志文件: {log_file}")
            with open(log_file, 'r', encoding='utf-8') as f:
                for line in f:
                    if '000807' in line or '云铝股份' in line:
                        if '初始持仓' in line:
                            print(f"  找到记录: {line.strip()}")
    except Exception as e:
        print(f"❌ 检查日志失败: {e}")

if __name__ == "__main__":
    debug_yunlv_config()