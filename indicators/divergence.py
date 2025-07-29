"""
背离检测模块 - 基于TA-Lib指标
检测价格与技术指标之间的背离现象
"""

import pandas as pd
import numpy as np
import logging
from typing import Dict, Tuple

from .exceptions import IndicatorCalculationError, InsufficientDataError, InvalidParameterError
from .momentum import calculate_rsi, calculate_macd

logger = logging.getLogger(__name__)

def detect_rsi_divergence(price: pd.Series, rsi: pd.Series, 
                         lookback: int = 13) -> Dict[str, bool]:
    """
    检测RSI背离
    
    Args:
        price: 价格序列
        rsi: RSI序列
        lookback: 回溯周期，默认13
        
    Returns:
        Dict[str, bool]: {'top_divergence': 顶背离, 'bottom_divergence': 底背离}
    """
    try:
        # 参数验证
        if not isinstance(price, pd.Series) or not isinstance(rsi, pd.Series):
            raise InvalidParameterError("价格和RSI数据必须是pandas Series类型")
        
        if not isinstance(lookback, int) or lookback <= 0:
            raise InvalidParameterError(f"回溯周期必须是正整数，当前值: {lookback}")
        
        if len(price) != len(rsi):
            raise InvalidParameterError("价格和RSI序列长度必须相同")
        
        if len(price) < lookback + 1:
            raise InsufficientDataError(f"数据长度不足以检测背离")
        
        # 获取最近的数据
        recent_price = price.tail(lookback + 1)
        recent_rsi = rsi.tail(lookback + 1)
        
        # 检测顶背离和底背离
        top_divergence = _detect_top_divergence(recent_price, recent_rsi)
        bottom_divergence = _detect_bottom_divergence(recent_price, recent_rsi)
        
        result = {
            'top_divergence': top_divergence,
            'bottom_divergence': bottom_divergence
        }
        
        logger.debug(f"RSI背离检测完成，顶背离={top_divergence}，底背离={bottom_divergence}")
        return result
        
    except (InsufficientDataError, InvalidParameterError):
        raise
    except Exception as e:
        raise IndicatorCalculationError(f"RSI背离检测失败: {str(e)}") from e

def _detect_top_divergence(price: pd.Series, indicator: pd.Series) -> bool:
    """检测顶背离：价格创新高，指标未创新高"""
    try:
        # 当前价格是否为回溯期内最高价
        current_price = price.iloc[-1]
        max_price = price.max()
        price_at_high = abs(current_price - max_price) < 0.01
        
        # 当前指标是否低于回溯期内最高指标值
        current_indicator = indicator.iloc[-1]
        max_indicator = indicator.max()
        indicator_below_high = current_indicator < max_indicator * 0.98
        
        return price_at_high and indicator_below_high
        
    except Exception as e:
        logger.warning(f"顶背离检测失败: {str(e)}")
        return False

def _detect_bottom_divergence(price: pd.Series, indicator: pd.Series) -> bool:
    """检测底背离：价格创新低，指标未创新低"""
    try:
        # 当前价格是否为回溯期内最低价
        current_price = price.iloc[-1]
        min_price = price.min()
        price_at_low = abs(current_price - min_price) < 0.01
        
        # 当前指标是否高于回溯期内最低指标值
        current_indicator = indicator.iloc[-1]
        min_indicator = indicator.min()
        indicator_above_low = current_indicator > min_indicator * 1.02
        
        return price_at_low and indicator_above_low
        
    except Exception as e:
        logger.warning(f"底背离检测失败: {str(e)}")
        return False

def detect_macd_divergence(price: pd.Series, macd_hist: pd.Series, 
                          lookback: int = 13) -> Dict[str, bool]:
    """
    检测MACD背离
    
    Args:
        price: 价格序列
        macd_hist: MACD柱状图序列
        lookback: 回溯周期
        
    Returns:
        Dict[str, bool]: {'top_divergence': 顶背离, 'bottom_divergence': 底背离}
    """
    try:
        if not isinstance(price, pd.Series) or not isinstance(macd_hist, pd.Series):
            raise InvalidParameterError("价格和MACD数据必须是pandas Series类型")
        
        if len(price) != len(macd_hist):
            raise InvalidParameterError("价格和MACD序列长度必须相同")
        
        if len(price) < lookback + 1:
            raise InsufficientDataError(f"数据长度不足以检测MACD背离")
        
        # 获取最近的数据
        recent_price = price.tail(lookback + 1)
        recent_macd = macd_hist.tail(lookback + 1)
        
        # 检测背离
        top_divergence = _detect_top_divergence(recent_price, recent_macd)
        bottom_divergence = _detect_bottom_divergence(recent_price, recent_macd)
        
        result = {
            'top_divergence': top_divergence,
            'bottom_divergence': bottom_divergence
        }
        
        logger.debug(f"MACD背离检测完成，顶背离={top_divergence}，底背离={bottom_divergence}")
        return result
        
    except Exception as e:
        raise IndicatorCalculationError(f"MACD背离检测失败: {str(e)}") from e

def detect_price_rsi_divergence_auto(price: pd.Series, lookback: int = 13) -> Dict[str, bool]:
    """
    自动计算RSI并检测背离
    
    Args:
        price: 价格序列
        lookback: 回溯周期
        
    Returns:
        Dict[str, bool]: 背离检测结果
    """
    try:
        # 自动计算RSI
        rsi = calculate_rsi(price, 14)
        
        # 检测背离
        return detect_rsi_divergence(price, rsi, lookback)
        
    except Exception as e:
        raise IndicatorCalculationError(f"自动RSI背离检测失败: {str(e)}") from e

def detect_price_macd_divergence_auto(price: pd.Series, lookback: int = 13) -> Dict[str, bool]:
    """
    自动计算MACD并检测背离
    
    Args:
        price: 价格序列
        lookback: 回溯周期
        
    Returns:
        Dict[str, bool]: 背离检测结果
    """
    try:
        # 自动计算MACD
        macd = calculate_macd(price, 12, 26, 9)
        
        # 检测背离
        return detect_macd_divergence(price, macd['hist'], lookback)
        
    except Exception as e:
        raise IndicatorCalculationError(f"自动MACD背离检测失败: {str(e)}") from e

if __name__ == "__main__":
    # 测试代码
    dates = pd.date_range('2023-01-01', periods=50, freq='D')
    
    # 创建模拟背离的价格数据
    price_data = []
    for i in range(50):
        if i < 15:
            price_data.append(100 + i * 2 + np.random.normal(0, 0.5))  # 上涨
        elif i < 30:
            price_data.append(130 - (i-15) * 1.5 + np.random.normal(0, 0.5))  # 下跌
        else:
            price_data.append(107.5 + (i-30) * 0.8 + np.random.normal(0, 0.3))  # 弱势上涨
    
    price_series = pd.Series(price_data, index=dates)
    
    print("测试TA-Lib背离检测...")
    
    try:
        # 测试自动RSI背离检测
        rsi_divergence = detect_price_rsi_divergence_auto(price_series, 13)
        print(f"✅ RSI背离检测完成:")
        print(f"   顶背离: {rsi_divergence['top_divergence']}")
        print(f"   底背离: {rsi_divergence['bottom_divergence']}")
        
        # 测试自动MACD背离检测
        macd_divergence = detect_price_macd_divergence_auto(price_series, 13)
        print(f"✅ MACD背离检测完成:")
        print(f"   顶背离: {macd_divergence['top_divergence']}")
        print(f"   底背离: {macd_divergence['bottom_divergence']}")
        
    except Exception as e:
        print(f"❌ 测试失败: {e}")