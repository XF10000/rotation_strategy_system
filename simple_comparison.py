"""
简单对比：直接获取最终持仓价值
"""

import logging
import pandas as pd
from services.backtest_orchestrator import BacktestOrchestrator
from backtest.backtest_engine import BacktestEngine
from config.csv_config_loader import load_backtest_settings, load_portfolio_config

logging.basicConfig(level=logging.WARNING)

# 加载配置
backtest_settings = load_backtest_settings('Input/Backtest_settings_regression_test.csv')
initial_holdings = load_portfolio_config('Input/portfolio_config.csv')
config = {**backtest_settings}
config['initial_holdings'] = initial_holdings

print("=" * 80)
print("简单对比")
print("=" * 80)

# 运行Orchestrator
print("\n🔄 运行 Orchestrator...")
orchestrator = BacktestOrchestrator(config)
orchestrator.initialize()
orchestrator.run_backtest()

# 获取Orchestrator最终状态
trading_dates = orchestrator._get_trading_dates()
final_date = trading_dates[-1]
final_prices_orch = orchestrator._get_current_prices(final_date)
pm_orch = orchestrator.portfolio_service.portfolio_manager
final_value_orch = pm_orch.get_total_value(final_prices_orch)

print(f"\n📊 Orchestrator:")
print(f"   最终日期: {final_date}")
print(f"   现金: ¥{pm_orch.cash:,.2f}")
print(f"   持仓数: {len(pm_orch.holdings)}")
print(f"   最终价值: ¥{final_value_orch:,.2f}")
print(f"   总收益率: {(final_value_orch/config['total_capital'] - 1):.2%}")

# 运行BacktestEngine
print("\n🔄 运行 BacktestEngine...")
engine = BacktestEngine(config)
engine.prepare_data()
engine.initialize_portfolio()
engine.run_backtest()

# 获取BacktestEngine最终状态
pm_engine = engine.portfolio_manager
# 获取最终价格
final_prices_engine = {}
for code in engine.stock_pool:
    if code in engine.stock_data:
        weekly = engine.stock_data[code]['weekly']
        if final_date in weekly.index:
            final_prices_engine[code] = weekly.loc[final_date, 'close']

final_value_engine = pm_engine.get_total_value(final_prices_engine)

print(f"\n📊 BacktestEngine:")
print(f"   最终日期: {final_date}")
print(f"   现金: ¥{pm_engine.cash:,.2f}")
print(f"   持仓数: {len(pm_engine.holdings)}")
print(f"   最终价值: ¥{final_value_engine:,.2f}")
print(f"   总收益率: {(final_value_engine/config['total_capital'] - 1):.2%}")

# 对比
print(f"\n📉 差异:")
diff = final_value_orch - final_value_engine
diff_pct = diff / final_value_engine
print(f"   最终价值差异: ¥{diff:,.2f} ({diff_pct:.2%})")

if abs(diff_pct) < 0.01:
    print(f"\n✅ 结果一致！差异在1%以内")
else:
    print(f"\n⚠️ 结果存在{abs(diff_pct):.2%}的差异")
    
    # 显示详细持仓对比
    print(f"\n📋 持仓对比（前5只）:")
    for code in list(pm_orch.holdings.keys())[:5]:
        orch_shares = pm_orch.holdings.get(code, 0)
        engine_shares = pm_engine.holdings.get(code, 0)
        price = final_prices_orch.get(code, 0)
        print(f"   {code}:")
        print(f"      Orch: {orch_shares:,}股 = ¥{orch_shares*price:,.2f}")
        print(f"      Engine: {engine_shares:,}股 = ¥{engine_shares*price:,.2f}")
        print(f"      差异: {orch_shares-engine_shares:,}股")

print("\n" + "=" * 80)
