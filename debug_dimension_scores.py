"""
详细对比维度评分
"""

import logging

import pandas as pd

from backtest.backtest_engine import BacktestEngine
from config.csv_config_loader import load_backtest_settings, load_portfolio_config
from services.backtest_orchestrator import BacktestOrchestrator

logging.basicConfig(level=logging.WARNING)

# 加载配置
backtest_settings = load_backtest_settings('Input/Backtest_settings_regression_test.csv')
initial_holdings = load_portfolio_config('Input/portfolio_config.csv')
config = {**backtest_settings}
config['initial_holdings'] = initial_holdings

# 初始化
orchestrator = BacktestOrchestrator(config)
orchestrator.initialize()

engine = BacktestEngine(config)
engine.prepare_data()

test_date = pd.Timestamp('2024-02-02')
stock_code = '002738'

print("=" * 80)
print(f"详细对比维度评分 - {stock_code} @ {test_date}")
print("=" * 80)

# Engine信号
weekly = engine.stock_data[stock_code]['weekly']
idx = weekly.index.get_loc(test_date)
hist_data = weekly.iloc[:idx+1]

result_engine = engine.signal_service.signal_generator.generate_signal(stock_code, hist_data)
print(f"\n📊 BacktestEngine:")
print(f"   信号: {result_engine.get('signal')}")
print(f"   原因: {result_engine.get('reason')}")
print(f"   价值比: {result_engine.get('value_price_ratio', 0):.3f}")
print(f"\n   维度评分:")
scores_engine = result_engine.get('scores', {})
for key, value in scores_engine.items():
    print(f"      {key}: {value}")

# Orchestrator信号
orch_weekly = orchestrator.stock_data[stock_code]['weekly']
orch_idx = orch_weekly.index.get_loc(test_date)
orch_hist = orch_weekly.iloc[:orch_idx+1]

result_orch = orchestrator.signal_service.signal_generator.generate_signal(stock_code, orch_hist)
print(f"\n📊 Orchestrator:")
print(f"   信号: {result_orch.get('signal')}")
print(f"   原因: {result_orch.get('reason')}")
print(f"   价值比: {result_orch.get('value_price_ratio', 0):.3f}")
print(f"\n   维度评分:")
scores_orch = result_orch.get('scores', {})
for key, value in scores_orch.items():
    print(f"      {key}: {value}")

# 对比差异
print(f"\n⚠️ 维度评分差异:")
all_keys = set(scores_engine.keys()) | set(scores_orch.keys())
for key in sorted(all_keys):
    engine_val = scores_engine.get(key, None)
    orch_val = scores_orch.get(key, None)
    if engine_val != orch_val:
        print(f"   ❌ {key}: Engine={engine_val}, Orch={orch_val}")

# 对比技术指标
print(f"\n📈 技术指标对比:")
details_engine = result_engine.get('details', {})
details_orch = result_orch.get('details', {})

key_indicators = ['ema', 'rsi', 'macd_dif', 'macd_dea', 'macd_hist', 'bb_upper', 'bb_lower', 'volume_ma']
for key in key_indicators:
    engine_val = details_engine.get(key, 'N/A')
    orch_val = details_orch.get(key, 'N/A')
    if engine_val != orch_val:
        print(f"   ❌ {key}: Engine={engine_val}, Orch={orch_val}")
    else:
        print(f"   ✅ {key}: {engine_val}")

print("\n" + "=" * 80)
