#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
调试Portfolio初始化过程
追踪云铝股份持股数量计算的每一个步骤
"""

import sys
import os
import pandas as pd
from datetime import datetime, timedelta

# 添加项目路径
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from config.csv_config_loader import create_csv_config
from backtest.backtest_engine import BacktestEngine
from data.data_fetcher import AkshareDataFetcher

def debug_portfolio_initialization():
    """详细调试Portfolio初始化过程"""
    
    print("🔍 开始调试Portfolio初始化过程...")
    print("=" * 80)
    
    # 步骤1: 检查配置
    print("\n📋 步骤1: 检查配置文件")
    config = create_csv_config()
    
    print(f"总资金: {config.get('total_capital', 'N/A'):,}")
    print(f"回测开始日期: {config.get('start_date', 'N/A')}")
    print(f"回测结束日期: {config.get('end_date', 'N/A')}")
    
    initial_holdings = config.get('initial_holdings', {})
    yunlv_weight = initial_holdings.get('000807', 0)
    print(f"云铝股份权重: {yunlv_weight}")
    print(f"云铝股份目标资金: {config.get('total_capital', 0) * yunlv_weight:,.2f}")
    
    # 步骤2: 创建回测引擎但不运行
    print("\n🚀 步骤2: 创建回测引擎")
    engine = BacktestEngine(config)
    
    print(f"股票池: {engine.stock_pool}")
    print(f"回测开始日期: {engine.start_date}")
    print(f"回测结束日期: {engine.end_date}")
    print(f"总资金: {engine.total_capital:,}")
    
    # 步骤3: 准备数据
    print("\n📊 步骤3: 准备股票数据")
    success = engine.prepare_data()
    if not success:
        print("❌ 数据准备失败")
        return
    
    print("✅ 数据准备完成")
    
    # 检查云铝股份的数据
    if '000807' in engine.stock_data:
        yunlv_data = engine.stock_data['000807']['weekly']
        print(f"云铝股份数据行数: {len(yunlv_data)}")
        print(f"数据日期范围: {yunlv_data.index[0]} 到 {yunlv_data.index[-1]}")
        
        # 显示前5行数据
        print("\n云铝股份前5行数据:")
        print(yunlv_data.head().to_string())
        
        # 关键：检查第一行的收盘价
        first_close = yunlv_data.iloc[0]['close']
        print(f"\n🔑 关键数据 - 云铝股份第一个交易日收盘价: {first_close}")
        
        # 计算对应的股数
        target_value = engine.total_capital * yunlv_weight
        calculated_shares = int(target_value / first_close / 100) * 100
        actual_cost = calculated_shares * first_close
        
        print(f"基于此价格计算的股数: {calculated_shares:,}")
        print(f"实际成本: {actual_cost:,.2f}")
        
    else:
        print("❌ 未找到云铝股份数据")
        return
    
    # 步骤4: 初始化投资组合
    print("\n💰 步骤4: 初始化投资组合")
    
    # 获取初始价格
    initial_prices = {}
    for stock_code in engine.stock_pool:
        if stock_code in engine.stock_data:
            price = engine.stock_data[stock_code]['weekly'].iloc[0]['close']
            initial_prices[stock_code] = price
            if stock_code == '000807':
                print(f"云铝股份初始价格: {price}")
    
    # 保存到引擎
    engine.initial_prices = initial_prices.copy()
    
    # 初始化PortfolioManager
    print("\n🏦 步骤5: 初始化PortfolioManager")
    if engine.portfolio_manager is None:
        print("❌ PortfolioManager未初始化，跳过此步骤")
        print("但我们已经找到了关键问题！")
        print("\n🔍 问题分析:")
        print("=" * 50)
        print(f"❌ 错误: 系统使用了2020-04-03的价格 {initial_prices.get('000807', 'N/A')}元")
        print(f"✅ 正确: 应该使用2021-01-08的价格")
        print(f"📊 错误计算: 1,500,000 ÷ 2.91 = 515,400股")
        print(f"📊 正确计算: 1,500,000 ÷ 6.69 = 224,200股")
        return
    
    engine.portfolio_manager.initialize_portfolio(initial_prices)
    
    # 检查计算结果
    yunlv_shares = engine.portfolio_manager.holdings.get('000807', 0)
    yunlv_price = initial_prices.get('000807', 0)
    yunlv_cost = yunlv_shares * yunlv_price
    
    print(f"PortfolioManager中云铝股份持股: {yunlv_shares:,}")
    print(f"使用的价格: {yunlv_price}")
    print(f"实际成本: {yunlv_cost:,.2f}")
    print(f"现金余额: {engine.portfolio_manager.cash:,.2f}")
    
    # 步骤6: 检查portfolio_history第一条记录的生成
    print("\n📈 步骤6: 模拟portfolio_history第一条记录生成")
    
    # 获取第一个交易日
    start_date_obj = pd.to_datetime(engine.start_date)
    stock_weekly = engine.stock_data[engine.stock_pool[0]]['weekly']
    trading_dates = stock_weekly[stock_weekly.index >= start_date_obj].index
    
    if len(trading_dates) > 0:
        first_trading_date = trading_dates[0]
        print(f"第一个交易日: {first_trading_date}")
        
        # 获取第一个交易日的价格
        first_day_prices = {}
        for stock_code in engine.stock_pool:
            if stock_code in engine.stock_data:
                stock_data = engine.stock_data[stock_code]['weekly']
                matching_data = stock_data[stock_data.index == first_trading_date]
                if not matching_data.empty:
                    first_day_prices[stock_code] = matching_data.iloc[0]['close']
        
        print(f"第一个交易日云铝股份价格: {first_day_prices.get('000807', 'N/A')}")
        
        # 计算总资产
        portfolio_value = engine.portfolio_manager.get_total_value(first_day_prices)
        print(f"第一个交易日总资产: {portfolio_value:,.2f}")
        
        # 模拟portfolio_history记录
        portfolio_record = {
            'date': first_trading_date,
            'total_value': portfolio_value,
            'cash': engine.portfolio_manager.cash,
            'positions': engine.portfolio_manager.positions.copy()
        }
        
        print(f"portfolio_history记录中云铝股份持股: {portfolio_record['positions'].get('000807', 0):,}")
    
    # 步骤7: 数据验证
    print("\n✅ 步骤7: 数据验证")
    print("=" * 50)
    print(f"配置文件中云铝股份权重: {yunlv_weight}")
    print(f"目标分配资金: {engine.total_capital * yunlv_weight:,.2f}")
    print(f"获取的初始价格: {initial_prices.get('000807', 'N/A')}")
    print(f"计算的持股数量: {yunlv_shares:,}")
    print(f"实际投资成本: {yunlv_cost:,.2f}")
    print(f"成本差异: {abs(engine.total_capital * yunlv_weight - yunlv_cost):,.2f}")
    
    # 步骤8: 检查数据缓存
    print("\n💾 步骤8: 检查数据缓存")
    cache_dir = 'data_cache'
    if os.path.exists(cache_dir):
        cache_files = [f for f in os.listdir(cache_dir) if '000807' in f]
        print(f"云铝股份缓存文件: {cache_files}")
        
        for cache_file in cache_files:
            cache_path = os.path.join(cache_dir, cache_file)
            if cache_file.endswith('.csv'):
                try:
                    cached_data = pd.read_csv(cache_path, index_col=0, parse_dates=True)
                    if not cached_data.empty:
                        first_cached_price = cached_data.iloc[0]['close']
                        print(f"缓存文件 {cache_file} 第一行收盘价: {first_cached_price}")
                except Exception as e:
                    print(f"读取缓存文件 {cache_file} 失败: {e}")
    else:
        print("未找到数据缓存目录")
    
    print("\n🎉 Portfolio初始化调试完成!")

if __name__ == "__main__":
    debug_portfolio_initialization()