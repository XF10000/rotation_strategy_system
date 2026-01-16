"""
详细对比Orchestrator和BacktestEngine的结果
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

print("=" * 80)
print("详细对比 Orchestrator vs BacktestEngine")
print("=" * 80)

# 运行Orchestrator
print("\n🔄 运行 Orchestrator...")
orchestrator = BacktestOrchestrator(config)
orchestrator.initialize()
orchestrator.run_backtest()
orch_results = orchestrator.get_results()['backtest_results']

# 运行BacktestEngine
print("\n🔄 运行 BacktestEngine...")
engine = BacktestEngine(config)
engine.prepare_data()
engine.initialize_portfolio()
engine.run_backtest()

# 对比结果
print("\n" + "=" * 80)
print("📊 结果对比")
print("=" * 80)

print(f"\n初始资金:")
print(f"  Orchestrator: ¥{orch_results['initial_value']:,.2f}")
print(f"  BacktestEngine: ¥{config['total_capital']:,.2f}")

perf = engine.portfolio_data_manager.calculate_performance_metrics()

print(f"\n最终资金:")
print(f"  Orchestrator: ¥{orch_results['final_value']:,.2f}")
engine_final = config['total_capital'] * (1 + perf['total_return'])
print(f"  BacktestEngine: ¥{engine_final:,.2f}")

print(f"\n总收益率:")
print(f"  Orchestrator: {orch_results['total_return']:.2%}")
print(f"  BacktestEngine: {perf['total_return']:.2%}")

print(f"\n年化收益率:")
print(f"  Orchestrator: {orch_results['annual_return']:.2%}")
print(f"  BacktestEngine: {perf['annual_return']:.2%}")

print(f"\n交易次数:")
print(f"  Orchestrator: {orch_results['transaction_count']}")
print(f"  BacktestEngine: {len(engine.portfolio_manager.transaction_history)}")

# 计算差异
diff_final = orch_results['final_value'] - engine_final
diff_return = orch_results['total_return'] - perf['total_return']
diff_annual = orch_results['annual_return'] - perf['annual_return']

print(f"\n📉 差异:")
print(f"  最终资金差异: ¥{diff_final:,.2f}")
print(f"  总收益率差异: {diff_return:.2%}")
print(f"  年化收益率差异: {diff_annual:.2%}")

if abs(diff_return) < 0.001:
    print(f"\n✅ 结果基本一致！差异在0.1%以内")
else:
    print(f"\n⚠️ 结果存在差异，需要进一步调查")

print("\n" + "=" * 80)
