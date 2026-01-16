"""
调试第一天的执行流程
"""

import logging

import pandas as pd

from config.csv_config_loader import load_backtest_settings, load_portfolio_config
from services.backtest_orchestrator import BacktestOrchestrator

# 设置详细日志
logging.basicConfig(level=logging.INFO, format='%(name)s - %(levelname)s - %(message)s')

# 加载配置
backtest_settings = load_backtest_settings('Input/Backtest_settings_regression_test.csv')
initial_holdings = load_portfolio_config('Input/portfolio_config.csv')
config = {**backtest_settings}
config['initial_holdings'] = initial_holdings

print("=" * 80)
print("调试第一天执行流程")
print("=" * 80)

# 初始化Orchestrator
print("\n🔄 初始化 Orchestrator...")
orchestrator = BacktestOrchestrator(config)
orchestrator.initialize()

# 获取交易日期
trading_dates = orchestrator._get_trading_dates()
print(f"\n📅 总交易日期数: {len(trading_dates)}")
print(f"   前5个日期: {[d.strftime('%Y-%m-%d') for d in trading_dates[:5]]}")

# 手动执行第一天
first_date = trading_dates[0]
print(f"\n{'='*80}")
print(f"执行第一天: {first_date}")
print(f"{'='*80}")

# 1. 获取当前价格
current_prices = orchestrator._get_current_prices(first_date)
print(f"\n1️⃣ 当前价格:")
print(f"   价格数量: {len(current_prices)}")
for code, price in list(current_prices.items())[:3]:
    print(f"      {code}: {price:.2f}")

# 2. 更新投资组合价格
orchestrator.portfolio_service.portfolio_manager.update_prices(current_prices)
print(f"\n2️⃣ 更新投资组合价格完成")

# 3. 生成信号
print(f"\n3️⃣ 生成信号...")
signals = orchestrator.signal_service.generate_signals(orchestrator.stock_data, first_date)
print(f"   信号数量: {len(signals) if signals else 0}")
if signals:
    for code, signal in signals.items():
        print(f"      {code}: {signal}")
else:
    print(f"   ⚠️ 无信号生成")

# 4. 检查持仓状态
print(f"\n4️⃣ 当前持仓状态:")
holdings = orchestrator.portfolio_service.portfolio_manager.holdings
print(f"   持仓数量: {len([h for h in holdings.values() if h > 0])}")
print(f"   现金: {orchestrator.portfolio_service.portfolio_manager.cash:,.2f}")

# 检查前3只股票的持仓和信号条件
print(f"\n5️⃣ 检查前3只股票的信号生成条件:")
stock_codes = list(orchestrator.stock_data.keys())[:3]
for code in stock_codes:
    print(f"\n   {code}:")
    
    # 持仓
    shares = holdings.get(code, 0)
    print(f"      持仓: {shares:,}股")
    
    # 价格
    price = current_prices.get(code, 0)
    print(f"      价格: {price:.2f}")
    
    # 数据
    if code in orchestrator.stock_data:
        weekly = orchestrator.stock_data[code]['weekly']
        if first_date in weekly.index:
            row = weekly.loc[first_date]
            print(f"      RSI: {row.get('rsi', 'N/A')}")
            print(f"      MACD: {row.get('macd', 'N/A')}")
        else:
            print(f"      ⚠️ 该日期不在数据中")
    
    # DCF估值
    dcf = orchestrator.portfolio_service.dcf_values.get(code, 0)
    if dcf > 0:
        vp_ratio = price / dcf
        print(f"      DCF估值: {dcf:.2f}")
        print(f"      价值比: {vp_ratio:.3f}")

print("\n" + "=" * 80)
