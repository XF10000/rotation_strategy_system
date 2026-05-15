"""
回测配置文件 — 默认参数
策略参数由 strategy/ludinggong_signal.py 的 DEFAULT_PARAMS 定义。
此文件只保留交易成本配置和 CSV 配置合并用的基础参数。
"""

# 默认交易成本配置
DEFAULT_COST_CONFIG = {
    'buy_commission_rate': 0.0002,
    'sell_commission_rate': 0.0002,
    'min_commission': 5.0,
    'stamp_tax_rate': 0.001,
    'slippage_rate': 0.001,
    'transfer_fee_rate': 0.00002,
}

# CSV 策略参数默认值 — 会被 Input/Backtest_settings.csv 覆盖
# 鹿鼎公策略核心参数见 strategy/ludinggong_signal.py:DEFAULT_PARAMS
DEFAULT_STRATEGY_PARAMS = {
    'rotation_percentage': 0.10,
    'max_single_stock_ratio': 0.20,
}
