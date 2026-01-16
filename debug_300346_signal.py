"""
调试300346在2024-01-19的信号生成差异
"""

import logging

import pandas as pd

from backtest.backtest_engine import BacktestEngine
from config.csv_config_loader import load_backtest_settings, load_portfolio_config
from services.backtest_orchestrator import BacktestOrchestrator

logging.basicConfig(level=logging.INFO, format='%(levelname)s - %(message)s')

# 加载配置
backtest_settings = load_backtest_settings('Input/Backtest_settings_regression_test.csv')
initial_holdings = load_portfolio_config('Input/portfolio_config.csv')
config = {**backtest_settings}
config['initial_holdings'] = initial_holdings

print("=" * 80)
print("调试300346在2024-01-19的信号差异")
print("=" * 80)

# 初始化
orchestrator = BacktestOrchestrator(config)
orchestrator.initialize()

engine = BacktestEngine(config)
engine.prepare_data()
engine.initialize_portfolio()

test_date = pd.Timestamp('2024-01-19')
stock_code = '300346'

print(f"\n📅 测试日期: {test_date}")
print(f"📊 股票代码: {stock_code}")

# 检查数据
print(f"\n1️⃣ 数据检查:")
if stock_code in orchestrator.stock_data:
    orch_weekly = orchestrator.stock_data[stock_code]['weekly']
    if test_date in orch_weekly.index:
        idx = orch_weekly.index.get_loc(test_date)
        print(f"   Orchestrator: 数据存在，索引={idx}")
        hist_data = orch_weekly.iloc[:idx+1]
        print(f"   历史数据量: {len(hist_data)}")
        print(f"   当前价格: {hist_data.iloc[-1]['close']:.2f}")
    else:
        print(f"   Orchestrator: 该日期不在数据中")
else:
    print(f"   Orchestrator: 股票不在stock_data中")

if stock_code in engine.stock_data:
    engine_weekly = engine.stock_data[stock_code]['weekly']
    if test_date in engine_weekly.index:
        idx = engine_weekly.index.get_loc(test_date)
        print(f"   BacktestEngine: 数据存在，索引={idx}")
        hist_data = engine_weekly.iloc[:idx+1]
        print(f"   历史数据量: {len(hist_data)}")
        print(f"   当前价格: {hist_data.iloc[-1]['close']:.2f}")
    else:
        print(f"   BacktestEngine: 该日期不在数据中")
else:
    print(f"   BacktestEngine: 股票不在stock_data中")

# 检查DCF估值
print(f"\n2️⃣ DCF估值检查:")
orch_dcf = orchestrator.portfolio_service.dcf_values.get(stock_code)
engine_dcf = engine.signal_service.signal_generator.dcf_values.get(stock_code)
print(f"   Orchestrator DCF: {orch_dcf}")
print(f"   BacktestEngine DCF: {engine_dcf}")

# 生成信号
print(f"\n3️⃣ 信号生成:")
if stock_code in orchestrator.stock_data and test_date in orchestrator.stock_data[stock_code]['weekly']:
    orch_weekly = orchestrator.stock_data[stock_code]['weekly']
    idx = orch_weekly.index.get_loc(test_date)
    hist_data = orch_weekly.iloc[:idx+1]
    
    print(f"\n   Orchestrator:")
    try:
        result = orchestrator.signal_service.signal_generator.generate_signal(stock_code, hist_data)
        print(f"      信号: {result.get('signal', 'N/A')}")
        print(f"      原因: {result.get('reason', 'N/A')}")
        print(f"      价值比: {result.get('value_price_ratio', 'N/A')}")
        print(f"      趋势过滤器高: {result.get('scores', {}).get('trend_filter_high', 'N/A')}")
        print(f"      趋势过滤器低: {result.get('scores', {}).get('trend_filter_low', 'N/A')}")
    except Exception as e:
        print(f"      错误: {e}")

if stock_code in engine.stock_data and test_date in engine.stock_data[stock_code]['weekly']:
    engine_weekly = engine.stock_data[stock_code]['weekly']
    idx = engine_weekly.index.get_loc(test_date)
    hist_data = engine_weekly.iloc[:idx+1]
    
    print(f"\n   BacktestEngine:")
    try:
        result = engine.signal_service.signal_generator.generate_signal(stock_code, hist_data)
        print(f"      信号: {result.get('signal', 'N/A')}")
        print(f"      原因: {result.get('reason', 'N/A')}")
        print(f"      价值比: {result.get('value_price_ratio', 'N/A')}")
        print(f"      趋势过滤器高: {result.get('scores', {}).get('trend_filter_high', 'N/A')}")
        print(f"      趋势过滤器低: {result.get('scores', {}).get('trend_filter_low', 'N/A')}")
    except Exception as e:
        print(f"      错误: {e}")

print("\n" + "=" * 80)
