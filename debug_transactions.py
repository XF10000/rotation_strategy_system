"""
详细对比交易记录，找出缺失的交易
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
print("详细交易记录对比")
print("=" * 80)

# 运行Orchestrator
print("\n🔄 运行 Orchestrator...")
orchestrator = BacktestOrchestrator(config)
orchestrator.initialize()
orchestrator.run_backtest()

# 运行BacktestEngine
print("\n🔄 运行 BacktestEngine...")
engine = BacktestEngine(config)
engine.prepare_data()
engine.initialize_portfolio()
engine.run_backtest()

# 获取交易记录
orch_txns = orchestrator.portfolio_service.portfolio_manager.transaction_history
engine_txns = engine.portfolio_manager.transaction_history

print(f"\n📊 交易数量:")
print(f"   Orchestrator: {len(orch_txns)}")
print(f"   BacktestEngine: {len(engine_txns)}")

# 创建交易记录的DataFrame便于对比
def txn_to_dict(txn):
    return {
        'date': txn.get('date'),
        'action': txn.get('action'),
        'stock_code': txn.get('stock_code'),
        'shares': txn.get('shares', 0),
        'price': txn.get('price', 0),
        'amount': txn.get('amount', 0)
    }

orch_df = pd.DataFrame([txn_to_dict(t) for t in orch_txns])
engine_df = pd.DataFrame([txn_to_dict(t) for t in engine_txns])

if len(orch_df) > 0:
    orch_df = orch_df.sort_values('date')
if len(engine_df) > 0:
    engine_df = engine_df.sort_values('date')

print(f"\n📋 Orchestrator交易记录（前10笔）:")
if len(orch_df) > 0:
    for i, row in orch_df.head(10).iterrows():
        print(f"   {row['date']} {row['action']} {row['stock_code']} {row['shares']:,}股 @{row['price']:.2f}")
else:
    print("   无交易记录")

print(f"\n📋 BacktestEngine交易记录（前10笔）:")
if len(engine_df) > 0:
    for i, row in engine_df.head(10).iterrows():
        print(f"   {row['date']} {row['action']} {row['stock_code']} {row['shares']:,}股 @{row['price']:.2f}")
else:
    print("   无交易记录")

# 找出缺失的交易日期
if len(engine_df) > 0:
    engine_dates = set(engine_df['date'].unique())
    orch_dates = set(orch_df['date'].unique()) if len(orch_df) > 0 else set()
    
    missing_dates = engine_dates - orch_dates
    if missing_dates:
        print(f"\n⚠️ Orchestrator缺失的交易日期:")
        for date in sorted(missing_dates):
            engine_on_date = engine_df[engine_df['date'] == date]
            print(f"\n   {date}:")
            for i, row in engine_on_date.iterrows():
                print(f"      {row['action']} {row['stock_code']} {row['shares']:,}股")

print("\n" + "=" * 80)
