"""检查实际的交易日期"""
import logging

import pandas as pd

from config.csv_config_loader import load_backtest_settings, load_portfolio_config
from services.backtest_orchestrator import BacktestOrchestrator

logging.basicConfig(level=logging.WARNING)

backtest_settings = load_backtest_settings('Input/Backtest_settings_regression_test.csv')
initial_holdings = load_portfolio_config('Input/portfolio_config.csv')
config = {**backtest_settings}
config['initial_holdings'] = initial_holdings

orchestrator = BacktestOrchestrator(config)
orchestrator.initialize()

print(f"配置的end_date: {config['end_date']}")
print(f"配置的start_date: {config['start_date']}")

# 检查第一只股票的实际日期范围
first_stock = list(orchestrator.stock_data.keys())[0]
weekly = orchestrator.stock_data[first_stock]['weekly']
print(f"\n{first_stock}的日期范围:")
print(f"  最早: {weekly.index[0]}")
print(f"  最晚: {weekly.index[-1]}")

# 检查end_date是否在数据中
end_date = pd.Timestamp(config['end_date'])
print(f"\nend_date在数据中: {end_date in weekly.index}")

# 找到最接近的日期
if end_date not in weekly.index:
    # 找到小于等于end_date的最大日期
    valid_dates = weekly.index[weekly.index <= end_date]
    if len(valid_dates) > 0:
        actual_end = valid_dates[-1]
        print(f"实际最后交易日: {actual_end}")
        print(f"该日收盘价: {weekly.loc[actual_end, 'close']}")
