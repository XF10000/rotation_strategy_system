"""
详细调试2024-02-02的信号生成
"""

import logging

import pandas as pd

from config.csv_config_loader import load_backtest_settings, load_portfolio_config
from services.backtest_orchestrator import BacktestOrchestrator

# 设置详细日志
logging.basicConfig(
    level=logging.DEBUG,
    format='%(name)s - %(levelname)s - %(message)s'
)

# 加载配置
backtest_settings = load_backtest_settings('Input/Backtest_settings_regression_test.csv')
initial_holdings = load_portfolio_config('Input/portfolio_config.csv')
config = {**backtest_settings}
config['initial_holdings'] = initial_holdings

print("=" * 80)
print("调试2024-02-02的信号生成")
print("=" * 80)

# 初始化Orchestrator
orchestrator = BacktestOrchestrator(config)
orchestrator.initialize()

test_date = pd.Timestamp('2024-02-02')

print(f"\n测试日期: {test_date}")
print(f"\n开始生成信号...")
print("=" * 80)

# 生成信号（会输出详细的DEBUG日志）
signals = orchestrator.signal_service.generate_signals(orchestrator.stock_data, test_date)

print("=" * 80)
print(f"\n最终信号结果:")
print(f"   信号数量: {len(signals) if signals else 0}")
if signals:
    for code, signal in signals.items():
        print(f"      {code}: {signal}")

print("\n" + "=" * 80)
