"""
最终结果对比
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
print("最终结果对比")
print("=" * 80)

# 运行Orchestrator
print("\n🔄 运行 Orchestrator...")
orchestrator = BacktestOrchestrator(config)
orchestrator.initialize()
orchestrator.run_backtest()

# 运行BacktestEngine
print("\n🔄 运行 BacktestEngine...")
engine = BacktestEngine(config)
engine.run_backtest()

# 获取结果
print("\n" + "=" * 80)
print("结果对比")
print("=" * 80)

orch_txns = len(orchestrator.portfolio_service.portfolio_manager.transaction_history)
engine_txns = len(engine.portfolio_manager.transaction_history)

orch_final = orchestrator.portfolio_service.portfolio_manager.get_total_value()
engine_final = engine.portfolio_manager.get_total_value()

orch_return = (orch_final - 100000000) / 100000000 * 100
engine_return = (engine_final - 100000000) / 100000000 * 100

print(f"\n📊 Orchestrator:")
print(f"   最终资金: ¥{orch_final:,.2f}")
print(f"   总收益率: {orch_return:.2f}%")
print(f"   交易次数: {orch_txns}")

print(f"\n📊 BacktestEngine:")
print(f"   最终资金: ¥{engine_final:,.2f}")
print(f"   总收益率: {engine_return:.2f}%")
print(f"   交易次数: {engine_txns}")

print(f"\n📉 差异:")
print(f"   最终资金差异: ¥{orch_final - engine_final:,.2f}")
print(f"   总收益率差异: {orch_return - engine_return:.2f}%")
print(f"   交易次数差异: {orch_txns - engine_txns}")

if abs(orch_return - engine_return) < 0.01 and orch_txns == engine_txns:
    print(f"\n✅ 结果一致！达到100%一致性目标")
else:
    print(f"\n⚠️ 结果存在差异")
    
    # 对比交易记录
    print(f"\n🔍 交易记录对比:")
    orch_dates = set([t['date'] for t in orchestrator.portfolio_service.portfolio_manager.transaction_history])
    engine_dates = set([t['date'] for t in engine.portfolio_manager.transaction_history])
    
    only_orch = orch_dates - engine_dates
    only_engine = engine_dates - orch_dates
    
    if only_orch:
        print(f"   仅Orchestrator有交易的日期: {sorted(only_orch)}")
    if only_engine:
        print(f"   仅BacktestEngine有交易的日期: {sorted(only_engine)}")

print("\n" + "=" * 80)
