"""
检查行业映射加载情况
"""

import logging
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
print("检查行业映射加载")
print("=" * 80)

# 初始化Orchestrator
orchestrator = BacktestOrchestrator(config)
orchestrator.initialize()

# 初始化Engine
engine = BacktestEngine(config)
engine.prepare_data()

print(f"\n📊 Orchestrator:")
print(f"   DataService.stock_industry_map: {len(orchestrator.data_service.stock_industry_map)} 条记录")
print(f"   SignalService.stock_industry_map: {len(orchestrator.signal_service.stock_industry_map)} 条记录")
print(f"   SignalGenerator.stock_industry_map: {len(orchestrator.signal_service.signal_generator.stock_industry_map)} 条记录")

print(f"\n📊 BacktestEngine:")
print(f"   engine.stock_industry_map: {len(engine.stock_industry_map)} 条记录")
print(f"   engine.signal_service.stock_industry_map: {len(engine.signal_service.stock_industry_map)} 条记录")
print(f"   engine.signal_service.signal_generator.stock_industry_map: {len(engine.signal_service.signal_generator.stock_industry_map)} 条记录")

# 检查002738
stock_code = '002738'
print(f"\n🔍 检查 {stock_code}:")
print(f"   Orchestrator DataService: {orchestrator.data_service.stock_industry_map.get(stock_code, '未找到')}")
print(f"   Orchestrator SignalGenerator: {orchestrator.signal_service.signal_generator.stock_industry_map.get(stock_code, '未找到')}")
print(f"   Engine: {engine.stock_industry_map.get(stock_code, '未找到')}")
print(f"   Engine SignalGenerator: {engine.signal_service.signal_generator.stock_industry_map.get(stock_code, '未找到')}")

print("\n" + "=" * 80)
