"""
回测配置文件 - 仅保留默认参数定义
现在主要使用CSV配置，这里只保留默认参数供参考
"""

# 默认交易成本配置
DEFAULT_COST_CONFIG = {
    'buy_commission_rate': 0.0002,    # 买入手续费率 0.02%
    'sell_commission_rate': 0.0002,   # 卖出手续费率 0.02%
    'min_commission': 5.0,            # 最低手续费 5元
    'stamp_tax_rate': 0.001,          # 印花税率 0.1%（仅卖出）
    'slippage_rate': 0.001,           # 滑点率 0.1%
    'transfer_fee_rate': 0.00002,     # 过户费率 0.002%（沪市）
}

# 默认策略参数
DEFAULT_STRATEGY_PARAMS = {
    'ema_period': 20,
    'rsi_period': 14,
    'rsi_overbought': 70,
    'rsi_oversold': 30,
    'macd_fast': 12,
    'macd_slow': 26,
    'macd_signal': 9,
    'bb_period': 20,
    'bb_std': 2,
    'volume_ma_period': 4,
    'volume_sell_ratio': 1.3,
    'volume_buy_ratio': 0.8,
    'use_industry_optimization': True,
    'rotation_percentage': 0.10,
    
    # V1.1新增：价值比过滤器阈值
    'value_ratio_sell_threshold': 80.0,  # 卖出阈值：价值比 > 80%
    'value_ratio_buy_threshold': 70.0    # 买入阈值：价值比 < 70%
}

# 注意：现在系统主要使用CSV配置文件
# 请使用 Input/portfolio_config.csv 和 Input/Backtest_settings.csv 进行配置
# 这里的参数仅作为默认值参考