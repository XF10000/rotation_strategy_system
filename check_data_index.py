"""
检查第一天的数据索引
"""

import logging

import pandas as pd

from config.csv_config_loader import load_backtest_settings, load_portfolio_config
from services.backtest_orchestrator import BacktestOrchestrator

logging.basicConfig(level=logging.WARNING)

# 加载配置
backtest_settings = load_backtest_settings('Input/Backtest_settings_regression_test.csv')
initial_holdings = load_portfolio_config('Input/portfolio_config.csv')
config = {**backtest_settings}
config['initial_holdings'] = initial_holdings

# 初始化Orchestrator
orchestrator = BacktestOrchestrator(config)
orchestrator.initialize()

# 获取交易日期
trading_dates = orchestrator._get_trading_dates()
first_date = trading_dates[0]

print("=" * 80)
print(f"检查第一天数据索引: {first_date}")
print("=" * 80)

# 检查前5只股票
stock_codes = list(orchestrator.stock_data.keys())[:5]
for code in stock_codes:
    if code in orchestrator.stock_data:
        weekly = orchestrator.stock_data[code]['weekly']
        
        if first_date in weekly.index:
            current_idx = weekly.index.get_loc(first_date)
            print(f"\n{code}:")
            print(f"   总数据量: {len(weekly)}")
            print(f"   当前索引: {current_idx}")
            print(f"   历史数据量: {current_idx + 1}")
            print(f"   是否满足120条要求: {'✅ 是' if current_idx >= 120 else '❌ 否'}")
            
            # 显示数据范围
            print(f"   数据起始: {weekly.index[0]}")
            print(f"   数据结束: {weekly.index[-1]}")
            print(f"   当前日期: {first_date}")
        else:
            print(f"\n{code}: ⚠️ 第一天不在数据中")

print("\n" + "=" * 80)
