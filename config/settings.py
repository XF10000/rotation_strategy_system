"""
系统配置文件
"""

# 数据源配置
DATA_SOURCE = {
    'primary': 'akshare',  # 主要数据源
    'backup': None,        # 备用数据源
    'cache_enabled': True, # 是否启用缓存
    'cache_days': 7        # 缓存天数
}

# 策略参数配置
STRATEGY_PARAMS = {
    'timeframe': 'weekly',     # 时间周期：周线
    'position_size': 0.10,     # 单次轮动仓位：10%
    'lookback_period': 13,     # 背离检测回溯周期
    
    # 技术指标参数
    'ema_period': 20,          # EMA周期
    'rsi_period': 14,          # RSI周期
    'rsi_overbought': 70,      # RSI超买阈值
    'rsi_oversold': 30,        # RSI超卖阈值
    'macd_fast': 12,           # MACD快线
    'macd_slow': 26,           # MACD慢线
    'macd_signal': 9,          # MACD信号线
    'bb_period': 20,           # 布林带周期
    'bb_std': 2.0,             # 布林带标准差
    'volume_multiplier_high': 1.3,  # 高量能倍数
    'volume_multiplier_low': 0.8,   # 低量能倍数
    'volume_ma_period': 4      # 量能均线周期
}

# 回测配置
BACKTEST_CONFIG = {
    'start_date': '2020-01-01',    # 回测开始日期
    'end_date': None,              # 回测结束日期（None为当前日期）
    'initial_capital': 1000000,    # 初始资金：100万
    'commission_rate': 0.0003,     # 手续费率：万3
    'stamp_tax_rate': 0.001,       # 印花税率：千1（仅卖出）
    'slippage_rate': 0.001,        # 滑点率：千1
    'min_trade_amount': 1000       # 最小交易金额
}

# 日志配置
LOGGING_CONFIG = {
    'level': 'INFO',
    'format': '%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    'file_path': 'logs/rotation_strategy.log',
    'max_bytes': 10 * 1024 * 1024,  # 10MB
    'backup_count': 5
}

# 输出配置
OUTPUT_CONFIG = {
    'save_signals': True,          # 是否保存信号
    'save_backtest_results': True, # 是否保存回测结果
    'generate_plots': True,        # 是否生成图表
    'output_dir': 'output'         # 输出目录
}