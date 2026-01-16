"""
波动率指标模块 - 使用TA-Lib实现
包含布林带等波动率相关指标的计算
"""

import logging
from typing import Dict

import numpy as np
import pandas as pd

try:
    import talib
except ImportError:
    raise ImportError("请安装TA-Lib库: pip install TA-Lib")

from .exceptions import IndicatorCalculationError, InsufficientDataError, InvalidParameterError

logger = logging.getLogger(__name__)

def calculate_bollinger_bands(data: pd.Series, period: int = 20, 
                            std_dev: float = 2.0) -> Dict[str, pd.Series]:
    """
    计算布林带 - 使用TA-Lib
    
    Args:
        data: 价格序列
        period: 计算周期，默认20
        std_dev: 标准差倍数，默认2.0
        
    Returns:
        Dict[str, pd.Series]: {'upper': 上轨, 'middle': 中轨, 'lower': 下轨}
    """
    try:
        if not isinstance(data, pd.Series):
            raise InvalidParameterError("数据必须是pandas Series类型")
        
        if not isinstance(period, int) or period <= 0:
            raise InvalidParameterError(f"周期必须是正整数，当前值: {period}")
        
        if not isinstance(std_dev, (int, float)) or std_dev <= 0:
            raise InvalidParameterError(f"标准差倍数必须是正数，当前值: {std_dev}")
        
        if len(data) < period:
            raise InsufficientDataError(f"数据长度不足以计算布林带")
        
        # 使用TA-Lib计算布林带
        upper, middle, lower = talib.BBANDS(
            data.values, 
            timeperiod=period, 
            nbdevup=std_dev, 
            nbdevdn=std_dev, 
            matype=0  # 简单移动平均
        )
        
        result = {
            'upper': pd.Series(upper, index=data.index),
            'middle': pd.Series(middle, index=data.index),
            'lower': pd.Series(lower, index=data.index)
        }
        
        logger.debug(f"成功计算布林带，周期={period}，标准差倍数={std_dev}")
        return result
        
    except (InsufficientDataError, InvalidParameterError):
        raise
    except Exception as e:
        raise IndicatorCalculationError(f"布林带计算失败: {str(e)}") from e

def calculate_atr(high: pd.Series, low: pd.Series, close: pd.Series, 
                 period: int = 14) -> pd.Series:
    """
    计算平均真实波幅 (ATR) - 使用TA-Lib
    
    Args:
        high: 最高价序列
        low: 最低价序列
        close: 收盘价序列
        period: 计算周期，默认14
        
    Returns:
        pd.Series: ATR值
    """
    try:
        if not all(isinstance(s, pd.Series) for s in [high, low, close]):
            raise InvalidParameterError("所有价格数据必须是pandas Series类型")
        
        if not isinstance(period, int) or period <= 0:
            raise InvalidParameterError(f"周期必须是正整数，当前值: {period}")
        
        if not (len(high) == len(low) == len(close)):
            raise InvalidParameterError("高低收价格序列长度必须相同")
        
        if len(high) < period + 1:
            raise InsufficientDataError(f"数据长度不足以计算ATR")
        
        # 使用TA-Lib计算ATR
        atr_values = talib.ATR(high.values, low.values, close.values, timeperiod=period)
        atr = pd.Series(atr_values, index=high.index)
        
        logger.debug(f"成功计算ATR，周期={period}")
        return atr
        
    except (InsufficientDataError, InvalidParameterError):
        raise
    except Exception as e:
        raise IndicatorCalculationError(f"ATR计算失败: {str(e)}") from e

def calculate_volatility(data: pd.Series, period: int = 20) -> pd.Series:
    """
    计算价格波动率（标准差）- 使用TA-Lib
    
    Args:
        data: 价格序列
        period: 计算周期
        
    Returns:
        pd.Series: 波动率
    """
    try:
        if not isinstance(data, pd.Series):
            raise InvalidParameterError("数据必须是pandas Series类型")
        
        if len(data) < period:
            raise InsufficientDataError(f"数据长度不足")
        
        # 使用TA-Lib计算标准差
        std_values = talib.STDDEV(data.values, timeperiod=period, nbdev=1)
        volatility = pd.Series(std_values, index=data.index)
        
        logger.debug(f"成功计算波动率，周期={period}")
        return volatility
        
    except (InsufficientDataError, InvalidParameterError):
        raise
    except Exception as e:
        raise IndicatorCalculationError(f"波动率计算失败: {str(e)}") from e

def is_price_at_bollinger_upper(price: float, bb_data: Dict[str, pd.Series], 
                               tolerance: float = 0.01) -> bool:
    """判断价格是否触及布林带上轨"""
    try:
        upper = bb_data['upper'].iloc[-1]
        return price >= upper * (1 - tolerance)
    except Exception as e:
        logger.warning(f"布林带上轨判断失败: {str(e)}")
        return False

def is_price_at_bollinger_lower(price: float, bb_data: Dict[str, pd.Series], 
                               tolerance: float = 0.01) -> bool:
    """判断价格是否触及布林带下轨"""
    try:
        lower = bb_data['lower'].iloc[-1]
        return price <= lower * (1 + tolerance)
    except Exception as e:
        logger.warning(f"布林带下轨判断失败: {str(e)}")
        return False

if __name__ == "__main__":
    # 测试代码
    dates = pd.date_range('2023-01-01', periods=100, freq='D')
    close_prices = pd.Series([100 + i + np.random.normal(0, 2) for i in range(100)], index=dates)
    high_prices = close_prices + np.random.uniform(0.5, 2, 100)
    low_prices = close_prices - np.random.uniform(0.5, 2, 100)
    
    print("测试TA-Lib波动率指标...")
    
    try:
        # 测试布林带
        bb = calculate_bollinger_bands(close_prices, 20, 2.0)
        print(f"✅ 布林带计算成功")
        print(f"   上轨: {bb['upper'].iloc[-1]:.2f}")
        print(f"   中轨: {bb['middle'].iloc[-1]:.2f}")
        print(f"   下轨: {bb['lower'].iloc[-1]:.2f}")
        
        # 测试ATR
        atr = calculate_atr(high_prices, low_prices, close_prices, 14)
        print(f"✅ ATR计算成功，最新值: {atr.iloc[-1]:.4f}")
        
        # 测试波动率
        volatility = calculate_volatility(close_prices, 20)
        print(f"✅ 波动率计算成功，最新值: {volatility.iloc[-1]:.4f}")
        
    except Exception as e:
        print(f"❌ 测试失败: {e}")