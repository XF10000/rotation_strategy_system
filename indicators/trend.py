"""
趋势指标模块 - 使用TA-Lib实现
包含EMA等趋势相关指标的计算
"""

import pandas as pd
import numpy as np
import logging
from typing import Union

try:
    import talib
except ImportError:
    raise ImportError("请安装TA-Lib库: pip install TA-Lib")

from .exceptions import IndicatorCalculationError, InsufficientDataError, InvalidParameterError

logger = logging.getLogger(__name__)

def calculate_ema(data: pd.Series, period: int) -> pd.Series:
    """
    计算指数移动平均线 (EMA) - 使用TA-Lib
    
    Args:
        data: 价格序列
        period: 周期
        
    Returns:
        pd.Series: EMA值
        
    Raises:
        IndicatorCalculationError: 计算失败
        InsufficientDataError: 数据不足
        InvalidParameterError: 参数无效
    """
    try:
        # 参数验证
        if not isinstance(data, pd.Series):
            raise InvalidParameterError("数据必须是pandas Series类型")
        
        if not isinstance(period, int) or period <= 0:
            raise InvalidParameterError(f"周期必须是正整数，当前值: {period}")
        
        if len(data) < period:
            raise InsufficientDataError(f"数据长度({len(data)})小于所需周期({period})")
        
        if data.isnull().all():
            raise InsufficientDataError("数据全部为空值")
        
        # 使用TA-Lib计算EMA
        ema_values = talib.EMA(data.values, timeperiod=period)
        ema = pd.Series(ema_values, index=data.index)
        
        logger.debug(f"成功计算EMA，周期={period}，数据点={len(ema)}")
        return ema
        
    except (InsufficientDataError, InvalidParameterError):
        raise
    except Exception as e:
        raise IndicatorCalculationError(f"EMA计算失败: {str(e)}") from e

def detect_ema_trend(ema: pd.Series, regression_periods: int = 8, flat_threshold: float = 0.003) -> str:
    """
    使用线性回归法检测EMA趋势方向
    
    Args:
        ema: EMA序列
        regression_periods: 用于线性回归的周期数，默认8周
        flat_threshold: 判断走平的相对斜率阈值，默认0.003(0.3%)
        
    Returns:
        str: 趋势方向，"向上"、"向下"或"走平"
        
    Raises:
        IndicatorCalculationError: 计算失败
        InsufficientDataError: 数据不足
        InvalidParameterError: 参数无效
    """
    try:
        if not isinstance(ema, pd.Series):
            raise InvalidParameterError("EMA数据必须是pandas Series类型")
        
        if len(ema) < regression_periods:
            raise InsufficientDataError(f"EMA数据长度({len(ema)})小于所需周期({regression_periods})")
        
        # 去除空值
        ema_clean = ema.dropna()
        if len(ema_clean) < regression_periods:
            raise InsufficientDataError(f"去除空值后数据不足以判断趋势")
        
        # 获取最近N周的EMA数据
        recent_ema = ema_clean.iloc[-regression_periods:].values
        
        # 创建X轴数据
        x = np.arange(len(recent_ema))
        
        # 计算线性回归
        slope, _, _, _, _ = np.polyfit(x, recent_ema, 1, full=True)
        
        # 计算相对斜率：斜率除以均值，得到归一化的斜率
        relative_slope = slope[0] / np.mean(recent_ema)
        
        # 判断走平：相对斜率的绝对值小于阈值
        if abs(relative_slope) < flat_threshold:
            trend = "走平"
        elif relative_slope > 0:
            trend = "向上"
        else:
            trend = "向下"
        
        logger.debug(f"EMA趋势判断(线性回归法): 相对斜率={relative_slope:.6f}, 趋势={trend}")
        
        return trend
        
    except (InsufficientDataError, InvalidParameterError):
        raise
    except Exception as e:
        raise IndicatorCalculationError(f"EMA趋势判断失败: {str(e)}") from e

def is_ema_trending_up(ema: pd.Series, lookback: int = 2) -> bool:
    """
    判断EMA是否向上趋势
    
    Args:
        ema: EMA序列
        lookback: 回看周期数
        
    Returns:
        bool: 是否向上趋势
    """
    try:
        if not isinstance(ema, pd.Series):
            raise InvalidParameterError("EMA数据必须是pandas Series类型")
        
        if len(ema) < lookback + 1:
            raise InsufficientDataError(f"EMA数据长度不足以判断趋势")
        
        # 去除空值
        ema_clean = ema.dropna()
        if len(ema_clean) < lookback + 1:
            raise InsufficientDataError("去除空值后数据不足以判断趋势")
        
        # 判断趋势：最新值是否大于前lookback个周期的值
        current_value = ema_clean.iloc[-1]
        previous_value = ema_clean.iloc[-(lookback + 1)]
        
        is_up = current_value > previous_value
        
        logger.debug(f"EMA趋势判断: 当前值={current_value:.4f}, "
                    f"{lookback}周期前值={previous_value:.4f}, 向上趋势={is_up}")
        
        return is_up
        
    except (InsufficientDataError, InvalidParameterError):
        raise
    except Exception as e:
        raise IndicatorCalculationError(f"EMA趋势判断失败: {str(e)}") from e

def calculate_sma(data: pd.Series, period: int) -> pd.Series:
    """
    计算简单移动平均线 (SMA) - 使用TA-Lib
    
    Args:
        data: 价格序列
        period: 周期
        
    Returns:
        pd.Series: SMA值
    """
    try:
        if not isinstance(data, pd.Series):
            raise InvalidParameterError("数据必须是pandas Series类型")
        
        if not isinstance(period, int) or period <= 0:
            raise InvalidParameterError(f"周期必须是正整数，当前值: {period}")
        
        if len(data) < period:
            raise InsufficientDataError(f"数据长度不足")
        
        # 使用TA-Lib计算SMA
        sma_values = talib.SMA(data.values, timeperiod=period)
        sma = pd.Series(sma_values, index=data.index)
        
        logger.debug(f"成功计算SMA，周期={period}")
        return sma
        
    except (InsufficientDataError, InvalidParameterError):
        raise
    except Exception as e:
        raise IndicatorCalculationError(f"SMA计算失败: {str(e)}") from e

if __name__ == "__main__":
    # 测试代码
    import matplotlib.pyplot as plt
    
    # 创建测试数据
    dates = pd.date_range('2023-01-01', periods=100, freq='D')
    prices = pd.Series([100 + i + np.random.normal(0, 1) for i in range(100)], index=dates)
    
    print("测试TA-Lib趋势指标...")
    
    try:
        # 测试EMA
        ema_20 = calculate_ema(prices, 20)
        print(f"✅ EMA-20计算成功，最新值: {ema_20.iloc[-1]:.2f}")
        
        # 测试趋势判断(简单方法)
        is_up = is_ema_trending_up(ema_20, 2)
        print(f"✅ EMA趋势判断(简单方法): {'向上' if is_up else '向下'}")
        
        # 测试趋势判断(线性回归法)
        trend = detect_ema_trend(ema_20, 8, 0.003)
        print(f"✅ EMA趋势判断(线性回归法): {trend}")
        
        # 测试SMA
        sma_20 = calculate_sma(prices, 20)
        print(f"✅ SMA-20计算成功，最新值: {sma_20.iloc[-1]:.2f}")
        
        # 可视化
        plt.figure(figsize=(12, 6))
        plt.plot(prices.index, prices.values, label='价格')
        plt.plot(ema_20.index, ema_20.values, label='EMA-20')
        plt.plot(sma_20.index, sma_20.values, label='SMA-20')
        plt.title('价格与移动平均线')
        plt.legend()
        plt.grid(True)
        plt.savefig('trend_indicators_test.png')
        print("✅ 图表已保存为 trend_indicators_test.png")
        
    except Exception as e:
        print(f"❌ 测试失败: {e}")
