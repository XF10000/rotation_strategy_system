"""
对比RSI阈值
"""

import logging

import pandas as pd

from backtest.backtest_engine import BacktestEngine
from config.csv_config_loader import load_backtest_settings, load_portfolio_config
from services.backtest_orchestrator import BacktestOrchestrator

# 启用DEBUG日志以查看RSI阈值详情
logging.basicConfig(
    level=logging.DEBUG,
    format='%(name)s - %(message)s',
    handlers=[logging.StreamHandler()]
)

# 只显示SignalGenerator的日志
logging.getLogger('strategy.SignalGenerator').setLevel(logging.DEBUG)
logging.getLogger().setLevel(logging.WARNING)

# 加载配置
backtest_settings = load_backtest_settings('Input/Backtest_settings_regression_test.csv')
initial_holdings = load_portfolio_config('Input/portfolio_config.csv')
config = {**backtest_settings}
config['initial_holdings'] = initial_holdings

# 初始化
print("=" * 80)
print("初始化BacktestEngine...")
print("=" * 80)
engine = BacktestEngine(config)
engine.prepare_data()

print("\n" + "=" * 80)
print("初始化Orchestrator...")
print("=" * 80)
orchestrator = BacktestOrchestrator(config)
orchestrator.initialize()

test_date = pd.Timestamp('2024-02-02')
stock_code = '002738'

print("\n" + "=" * 80)
print(f"测试 {stock_code} @ {test_date}")
print("=" * 80)

# Engine信号生成（会输出DEBUG日志）
print("\n>>> BacktestEngine信号生成:")
weekly = engine.stock_data[stock_code]['weekly']
idx = weekly.index.get_loc(test_date)
hist_data = weekly.iloc[:idx+1]
result_engine = engine.signal_service.signal_generator.generate_signal(stock_code, hist_data)

print("\n>>> Orchestrator信号生成:")
orch_weekly = orchestrator.stock_data[stock_code]['weekly']
orch_idx = orch_weekly.index.get_loc(test_date)
orch_hist = orch_weekly.iloc[:orch_idx+1]
result_orch = orchestrator.signal_service.signal_generator.generate_signal(stock_code, orch_hist)

print("\n" + "=" * 80)
print("结果对比:")
print("=" * 80)
print(f"Engine信号: {result_engine.get('signal')}")
print(f"Orchestrator信号: {result_orch.get('signal')}")
