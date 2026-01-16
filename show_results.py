"""
整体回测结果对比展示
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

print("\n" + "=" * 80)
print("整体回测结果对比")
print("=" * 80)

# 运行Orchestrator
print("\n🔄 运行 BacktestOrchestrator...")
orchestrator = BacktestOrchestrator(config)
orchestrator.initialize()
orchestrator.run_backtest()

# 运行BacktestEngine
print("\n🔄 运行 BacktestEngine (Baseline)...")
engine = BacktestEngine(config)
engine.run_backtest()

# 获取结果
print("\n" + "=" * 80)
print("📊 回测结果对比")
print("=" * 80)

# Orchestrator结果
orch_pm = orchestrator.portfolio_service.portfolio_manager
orch_cash = orch_pm.cash
orch_holdings_value = sum(
    orch_pm.holdings.get(code, 0) * orch_pm.current_prices.get(code, 0)
    for code in orch_pm.holdings.keys()
)
orch_total = orch_cash + orch_holdings_value
orch_return = (orch_total - 100000000) / 100000000 * 100
orch_txns = len(orch_pm.transaction_history)

# BacktestEngine结果
engine_pm = engine.portfolio_manager
engine_cash = engine_pm.cash
engine_holdings_value = sum(
    engine_pm.holdings.get(code, 0) * engine_pm.current_prices.get(code, 0)
    for code in engine_pm.holdings.keys()
)
engine_total = engine_cash + engine_holdings_value
engine_return = (engine_total - 100000000) / 100000000 * 100
engine_txns = len(engine_pm.transaction_history)

# 计算年化收益率
days = (pd.Timestamp(config['end_date']) - pd.Timestamp(config['start_date'])).days
years = days / 365.25
orch_annual = ((1 + orch_return/100) ** (1/years) - 1) * 100
engine_annual = ((1 + engine_return/100) ** (1/years) - 1) * 100

print(f"\n┌{'─' * 78}┐")
print(f"│ {'BacktestOrchestrator (修复后)':^76} │")
print(f"├{'─' * 78}┤")
print(f"│  初始资金: {100000000:>20,.2f} 元 {'':>35}│")
print(f"│  最终资金: {orch_total:>20,.2f} 元 {'':>35}│")
print(f"│  现金余额: {orch_cash:>20,.2f} 元 {'':>35}│")
print(f"│  持仓价值: {orch_holdings_value:>20,.2f} 元 {'':>35}│")
print(f"│  总收益率: {orch_return:>19.2f} % {'':>35}│")
print(f"│  年化收益率: {orch_annual:>17.2f} % {'':>35}│")
print(f"│  交易次数: {orch_txns:>20} 笔 {'':>35}│")
print(f"│  回测天数: {days:>20} 天 {'':>35}│")
print(f"└{'─' * 78}┘")

print(f"\n┌{'─' * 78}┐")
print(f"│ {'BacktestEngine (Baseline)':^76} │")
print(f"├{'─' * 78}┤")
print(f"│  初始资金: {100000000:>20,.2f} 元 {'':>35}│")
print(f"│  最终资金: {engine_total:>20,.2f} 元 {'':>35}│")
print(f"│  现金余额: {engine_cash:>20,.2f} 元 {'':>35}│")
print(f"│  持仓价值: {engine_holdings_value:>20,.2f} 元 {'':>35}│")
print(f"│  总收益率: {engine_return:>19.2f} % {'':>35}│")
print(f"│  年化收益率: {engine_annual:>17.2f} % {'':>35}│")
print(f"│  交易次数: {engine_txns:>20} 笔 {'':>35}│")
print(f"│  回测天数: {days:>20} 天 {'':>35}│")
print(f"└{'─' * 78}┘")

# 差异分析
diff_total = orch_total - engine_total
diff_return = orch_return - engine_return
diff_annual = orch_annual - engine_annual
diff_txns = orch_txns - engine_txns

print(f"\n┌{'─' * 78}┐")
print(f"│ {'差异分析':^76} │")
print(f"├{'─' * 78}┤")
print(f"│  最终资金差异: {diff_total:>18,.2f} 元 ({diff_total/engine_total*100:>6.2f}%) {'':>20}│")
print(f"│  总收益率差异: {diff_return:>18.2f} % {'':>35}│")
print(f"│  年化收益率差异: {diff_annual:>16.2f} % {'':>35}│")
print(f"│  交易次数差异: {diff_txns:>18} 笔 {'':>35}│")
print(f"└{'─' * 78}┘")

# 一致性判断
consistency_threshold = 0.01  # 0.01%的误差容忍度
is_consistent = (
    abs(diff_return) < consistency_threshold and
    abs(diff_annual) < consistency_threshold and
    diff_txns == 0
)

print(f"\n{'=' * 80}")
if is_consistent:
    print("✅ 结果一致性: 100% 一致 (差异 < 0.01%)")
else:
    consistency_pct = 100 - abs(diff_return / engine_return * 100)
    print(f"⚠️  结果一致性: {consistency_pct:.2f}%")
    print(f"   收益率差异: {abs(diff_return):.2f}%")
    print(f"   交易次数差异: {abs(diff_txns)} 笔")
print("=" * 80 + "\n")
