"""
技术指标模块 - 基于TA-Lib实现
提供各类技术指标计算功能，使用业界标准的TA-Lib库
"""

from .divergence import (
    detect_macd_divergence,
    detect_price_macd_divergence_auto,
    detect_price_rsi_divergence_auto,
    detect_rsi_divergence,
)
from .momentum import (
    calculate_macd,
    calculate_momentum,
    calculate_roc,
    calculate_rsi,
    is_macd_bearish_crossover,
    is_macd_bullish_crossover,
)
from .trend import calculate_ema, calculate_sma, is_ema_trending_up
from .volatility import (
    calculate_atr,
    calculate_bollinger_bands,
    calculate_volatility,
    is_price_at_bollinger_lower,
    is_price_at_bollinger_upper,
)

__all__ = [
    # 趋势指标
    'calculate_ema',
    'is_ema_trending_up',
    'calculate_sma',
    
    # 动量指标
    'calculate_rsi', 
    'calculate_macd',
    'calculate_momentum',
    'calculate_roc',
    'is_macd_bullish_crossover',
    'is_macd_bearish_crossover',
    
    # 波动率指标
    'calculate_bollinger_bands',
    'calculate_atr',
    'calculate_volatility',
    'is_price_at_bollinger_upper',
    'is_price_at_bollinger_lower',
    
    # 背离检测
    'detect_rsi_divergence',
    'detect_macd_divergence',
    'detect_price_rsi_divergence_auto',
    'detect_price_macd_divergence_auto'
]

# 版本信息
__version__ = "1.0.0"
__description__ = "基于TA-Lib的技术指标计算模块"