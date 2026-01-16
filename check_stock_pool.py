"""
检查SignalService的stock_pool
"""

import logging

from backtest.backtest_engine import BacktestEngine
from config.csv_config_loader import load_backtest_settings, load_portfolio_config
from services.backtest_orchestrator import BacktestOrchestrator

logging.basicConfig(level=logging.WARNING)

# 加载配置
backtest_settings = load_backtest_settings('Input/Backtest_settings_regression_test.csv')
initial_holdings = load_portfolio_config('Input/portfolio_config.csv')
config = {**backtest_settings}
config['initial_holdings'] = initial_holdings

print("=" * 80)
print("检查stock_pool")
print("=" * 80)

# 初始化
orchestrator = BacktestOrchestrator(config)
orchestrator.initialize()

engine = BacktestEngine(config)
engine.prepare_data()

print(f"\n📊 Orchestrator SignalService stock_pool:")
print(f"   数量: {len(orchestrator.signal_service.stock_pool)}")
print(f"   股票: {sorted(orchestrator.signal_service.stock_pool)}")
print(f"   300346在pool中: {'300346' in orchestrator.signal_service.stock_pool}")

print(f"\n📊 BacktestEngine SignalService stock_pool:")
print(f"   数量: {len(engine.signal_service.stock_pool)}")
print(f"   股票: {sorted(engine.signal_service.stock_pool)}")
print(f"   300346在pool中: {'300346' in engine.signal_service.stock_pool}")

print(f"\n📋 stock_data对比:")
print(f"   Orchestrator: {len(orchestrator.stock_data)}只股票")
print(f"   BacktestEngine: {len(engine.stock_data)}只股票")
print(f"   300346在Orchestrator stock_data中: {'300346' in orchestrator.stock_data}")
print(f"   300346在BacktestEngine stock_data中: {'300346' in engine.stock_data}")

# 检查差异
orch_pool = set(orchestrator.signal_service.stock_pool)
engine_pool = set(engine.signal_service.stock_pool)

if orch_pool != engine_pool:
    print(f"\n⚠️ stock_pool差异:")
    only_orch = orch_pool - engine_pool
    only_engine = engine_pool - orch_pool
    if only_orch:
        print(f"   仅Orchestrator: {only_orch}")
    if only_engine:
        print(f"   仅BacktestEngine: {only_engine}")
else:
    print(f"\n✅ stock_pool完全一致")

print("\n" + "=" * 80)
