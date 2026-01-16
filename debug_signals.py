"""
对比信号生成
"""

import logging
import pandas as pd
from services.backtest_orchestrator import BacktestOrchestrator
from backtest.backtest_engine import BacktestEngine
from config.csv_config_loader import load_backtest_settings, load_portfolio_config

logging.basicConfig(level=logging.INFO)

# 加载配置
backtest_settings = load_backtest_settings('Input/Backtest_settings_regression_test.csv')
initial_holdings = load_portfolio_config('Input/portfolio_config.csv')
config = {**backtest_settings}
config['initial_holdings'] = initial_holdings

print("=" * 80)
print("信号生成对比")
print("=" * 80)

# 运行Orchestrator
print("\n🔄 初始化 Orchestrator...")
orchestrator = BacktestOrchestrator(config)
orchestrator.initialize()

# 获取交易日期
trading_dates = orchestrator._get_trading_dates()
print(f"\n📅 交易日期数量: {len(trading_dates)}")
print(f"   开始日期: {trading_dates[0]}")
print(f"   结束日期: {trading_dates[-1]}")

# 检查前5个交易日的信号
print(f"\n🎯 检查前5个交易日的信号生成:")
for i, current_date in enumerate(trading_dates[:5]):
    print(f"\n   日期 {i+1}: {current_date}")
    
    # 生成信号
    signals = orchestrator.signal_service.generate_signals(orchestrator.stock_data, current_date)
    
    if signals:
        print(f"      信号数量: {len(signals)}")
        for code, signal in signals.items():
            print(f"         {code}: {signal}")
    else:
        print(f"      无信号")

print("\n" + "=" * 80)
