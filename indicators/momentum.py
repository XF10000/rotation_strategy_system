"""
动量指标模块 - 使用TA-Lib实现
包含RSI、MACD等动量相关指标的计算
"""

import pandas as pd
import numpy as np
import logging
from typing import Dict

try:
    import talib
except ImportError:
    raise ImportError("请安装TA-Lib库: pip install TA-Lib")

from .exceptions import IndicatorCalculationError, InsufficientDataError, InvalidParameterError

logger = logging.getLogger(__name__)

def calculate_rsi(data: pd.Series, period: int = 14) -> pd.Series:
    """
    计算相对强弱指标 (RSI) - 使用TA-Lib
    
    Args:
        data: 价格序列
        period: 计算周期，默认14
        
    Returns:
        pd.Series: RSI值 (0-100)
    """
    try:
        if not isinstance(data, pd.Series):
            raise InvalidParameterError("数据必须是pandas Series类型")
        
        if not isinstance(period, int) or period <= 0:
            raise InvalidParameterError(f"周期必须是正整数，当前值: {period}")
        
        if len(data) < period + 1:
            raise InsufficientDataError(f"数据长度不足以计算RSI")
        
        # 处理NaN值
        clean_data = data.copy()
        if clean_data.isna().any():
            logger.warning(f"RSI计算前处理了 {clean_data.isna().sum()} 个NaN值")
            clean_data = clean_data.fillna(method='ffill').fillna(method='bfill')
        
        try:
            # 使用TA-Lib计算RSI
            rsi_values = talib.RSI(clean_data.values, timeperiod=period)
            
            # 检查结果是否有效
            if pd.isna(rsi_values).all():
                raise Exception("TA-Lib计算结果全为NaN")
                
        except Exception as e:
            logger.warning(f"TA-Lib RSI计算失败: {e}，使用pandas计算方法作为备用")
            
            # 使用pandas计算方法作为备用
            delta = clean_data.diff()
            gain = delta.clip(lower=0)
            loss = -delta.clip(upper=0)
            
            avg_gain = gain.rolling(window=period).mean()
            avg_loss = loss.rolling(window=period).mean()
            
            rs = avg_gain / avg_loss
            rsi_values = 100 - (100 / (1 + rs))
        
        rsi = pd.Series(rsi_values, index=data.index)
        
        logger.debug(f"成功计算RSI，周期={period}")
        return rsi
        
    except (InsufficientDataError, InvalidParameterError):
        raise
    except Exception as e:
        raise IndicatorCalculationError(f"RSI计算失败: {str(e)}") from e

def calculate_macd(data: pd.Series, fast: int = 12, slow: int = 26, 
                  signal: int = 9) -> Dict[str, pd.Series]:
    """
    计算MACD指标 - 使用TA-Lib
    
    Args:
        data: 价格序列
        fast: 快线周期，默认12
        slow: 慢线周期，默认26
        signal: 信号线周期，默认9
        
    Returns:
        Dict[str, pd.Series]: {'dif': DIF线, 'dea': DEA线, 'hist': 柱状图}
    """
    try:
        if not isinstance(data, pd.Series):
            raise InvalidParameterError("数据必须是pandas Series类型")
        
        if not all(isinstance(p, int) and p > 0 for p in [fast, slow, signal]):
            raise InvalidParameterError("所有周期参数必须是正整数")
        
        if fast >= slow:
            raise InvalidParameterError(f"快线周期({fast})必须小于慢线周期({slow})")
        
        if len(data) < slow + signal:
            raise InsufficientDataError(f"数据长度不足以计算MACD")
        
        # 处理NaN值
        clean_data = data.copy()
        if clean_data.isna().any():
            logger.warning(f"MACD计算前处理了 {clean_data.isna().sum()} 个NaN值")
            clean_data = clean_data.fillna(method='ffill').fillna(method='bfill')
        
        try:
            # 尝试使用TA-Lib计算MACD
            macd_line, signal_line, histogram = talib.MACD(
                clean_data.values, 
                fastperiod=fast, 
                slowperiod=slow, 
                signalperiod=signal
            )
            
            # 检查结果是否有效
            if pd.isna(macd_line).all() or pd.isna(signal_line).all():
                raise Exception("TA-Lib计算结果全为NaN")
                
        except Exception as e:
            logger.warning(f"TA-Lib MACD计算失败: {e}，使用pandas ewm方法作为备用")
            
            # 使用pandas ewm方法作为备用计算方法
            ema_fast = clean_data.ewm(span=fast, adjust=False).mean()
            ema_slow = clean_data.ewm(span=slow, adjust=False).mean()
            macd_line = ema_fast - ema_slow
            signal_line = macd_line.ewm(span=signal, adjust=False).mean()
            histogram = macd_line - signal_line
        
        result = {
            'dif': pd.Series(macd_line, index=data.index),
            'dea': pd.Series(signal_line, index=data.index),
            'hist': pd.Series(histogram, index=data.index)
        }
        
        logger.debug(f"成功计算MACD，参数=({fast},{slow},{signal})")
        return result
        
    except (InsufficientDataError, InvalidParameterError):
        raise
    except Exception as e:
        raise IndicatorCalculationError(f"MACD计算失败: {str(e)}") from e

def calculate_momentum(data: pd.Series, period: int = 10) -> pd.Series:
    """
    计算动量指标 (Momentum) - 使用TA-Lib
    
    Args:
        data: 价格序列
        period: 计算周期
        
    Returns:
        pd.Series: 动量值
    """
    try:
        if not isinstance(data, pd.Series):
            raise InvalidParameterError("数据必须是pandas Series类型")
        
        if len(data) < period + 1:
            raise InsufficientDataError(f"数据长度不足")
        
        # 使用TA-Lib计算动量
        mom_values = talib.MOM(data.values, timeperiod=period)
        momentum = pd.Series(mom_values, index=data.index)
        
        logger.debug(f"成功计算动量指标，周期={period}")
        return momentum
        
    except (InsufficientDataError, InvalidParameterError):
        raise
    except Exception as e:
        raise IndicatorCalculationError(f"动量指标计算失败: {str(e)}") from e

def calculate_roc(data: pd.Series, period: int = 10) -> pd.Series:
    """
    计算变化率指标 (Rate of Change) - 使用TA-Lib
    
    Args:
        data: 价格序列
        period: 计算周期
        
    Returns:
        pd.Series: 变化率 (百分比)
    """
    try:
        if not isinstance(data, pd.Series):
            raise InvalidParameterError("数据必须是pandas Series类型")
        
        if len(data) < period + 1:
            raise InsufficientDataError(f"数据长度不足")
        
        # 使用TA-Lib计算ROC
        roc_values = talib.ROC(data.values, timeperiod=period)
        roc = pd.Series(roc_values, index=data.index)
        
        logger.debug(f"成功计算ROC指标，周期={period}")
        return roc
        
    except (InsufficientDataError, InvalidParameterError):
        raise
    except Exception as e:
        raise IndicatorCalculationError(f"ROC指标计算失败: {str(e)}") from e

def is_macd_bullish_crossover(macd_data: Dict[str, pd.Series]) -> bool:
    """判断MACD是否出现金叉"""
    try:
        dif = macd_data['dif']
        dea = macd_data['dea']
        
        if len(dif) < 2 or len(dea) < 2:
            return False
        
        # 当前DIF > DEA 且 前一期DIF <= DEA
        current_bullish = dif.iloc[-1] > dea.iloc[-1]
        previous_bearish = dif.iloc[-2] <= dea.iloc[-2]
        
        return current_bullish and previous_bearish
        
    except Exception as e:
        logger.warning(f"MACD金叉判断失败: {str(e)}")
        return False

def is_macd_bearish_crossover(macd_data: Dict[str, pd.Series]) -> bool:
    """判断MACD是否出现死叉"""
    try:
        dif = macd_data['dif']
        dea = macd_data['dea']
        
        if len(dif) < 2 or len(dea) < 2:
            return False
        
        # 当前DIF < DEA 且 前一期DIF >= DEA
        current_bearish = dif.iloc[-1] < dea.iloc[-1]
        previous_bullish = dif.iloc[-2] >= dea.iloc[-2]
        
        return current_bearish and previous_bullish
        
    except Exception as e:
        logger.warning(f"MACD死叉判断失败: {str(e)}")
        return False

def detect_macd_histogram_shrinking(macd_data: Dict[str, pd.Series], periods: int = 2) -> Dict[str, bool]:
    """
    检测MACD柱体连续缩短趋势
    
    Args:
        macd_data: MACD数据字典，包含'hist'键
        periods: 检测的连续周期数，默认2
        
    Returns:
        Dict[str, bool]: {
            'red_shrinking': 红色柱体连续缩短,
            'green_shrinking': 绿色柱体连续缩短,
            'green_to_red_transition': 前期绿柱缩短+当前转红,
            'red_to_green_transition': 前期红柱缩短+当前转绿
        }
    """
    try:
        hist = macd_data['hist']
        
        if len(hist) < periods + 1:
            return {
                'red_shrinking': False,
                'green_shrinking': False,
                'green_to_red_transition': False,
                'red_to_green_transition': False
            }
        
        # 获取最近的柱体数据
        hist_current = hist.iloc[-1]
        hist_values = hist.iloc[-(periods+1):].values
        
        # 红色柱体连续缩短检测
        red_shrinking = False
        if all(h > 0 for h in hist_values):  # 所有柱体都是红色
            # 检查是否连续缩短
            red_shrinking = all(hist_values[i] < hist_values[i-1] for i in range(1, len(hist_values)))
        
        # 绿色柱体连续缩短检测
        green_shrinking = False
        if all(h < 0 for h in hist_values):  # 所有柱体都是绿色
            # 检查绝对值是否连续缩短
            green_shrinking = all(abs(hist_values[i]) < abs(hist_values[i-1]) for i in range(1, len(hist_values)))
        
        # 前期绿柱缩短 + 当前转红检测
        green_to_red_transition = False
        if len(hist) >= 3:
            hist_prev1 = hist.iloc[-2]
            hist_prev2 = hist.iloc[-3]
            if (hist_prev1 < 0 and hist_prev2 < 0 and  # 前2根是绿柱
                abs(hist_prev1) < abs(hist_prev2) and  # 前期绿柱在缩短
                hist_current > 0):  # 当前转为红柱
                green_to_red_transition = True
        
        # 前期红柱缩短 + 当前转绿检测
        red_to_green_transition = False
        if len(hist) >= 3:
            hist_prev1 = hist.iloc[-2]
            hist_prev2 = hist.iloc[-3]
            if (hist_prev1 > 0 and hist_prev2 > 0 and  # 前2根是红柱
                hist_prev1 < hist_prev2 and  # 前期红柱在缩短
                hist_current < 0):  # 当前转为绿柱
                red_to_green_transition = True
        
        result = {
            'red_shrinking': red_shrinking,
            'green_shrinking': green_shrinking,
            'green_to_red_transition': green_to_red_transition,
            'red_to_green_transition': red_to_green_transition
        }
        
        logger.debug(f"MACD柱体缩短检测结果: {result}")
        return result
        
    except Exception as e:
        logger.warning(f"MACD柱体缩短检测失败: {str(e)}")
        return {
            'red_shrinking': False,
            'green_shrinking': False,
            'green_to_red_transition': False,
            'red_to_green_transition': False
        }

if __name__ == "__main__":
    # 测试代码
    dates = pd.date_range('2023-01-01', periods=100, freq='D')
    prices = pd.Series([100 + i + np.random.normal(0, 2) for i in range(100)], index=dates)
    
    print("测试TA-Lib动量指标...")
    
    try:
        # 测试RSI
        rsi = calculate_rsi(prices, 14)
        print(f"✅ RSI计算成功，最新值: {rsi.iloc[-1]:.2f}")
        
        # 测试MACD
        macd = calculate_macd(prices, 12, 26, 9)
        print(f"✅ MACD计算成功")
        print(f"   DIF: {macd['dif'].iloc[-1]:.4f}")
        print(f"   DEA: {macd['dea'].iloc[-1]:.4f}")
        print(f"   HIST: {macd['hist'].iloc[-1]:.4f}")
        
        # 测试MACD信号
        bullish = is_macd_bullish_crossover(macd)
        bearish = is_macd_bearish_crossover(macd)
        print(f"   金叉: {bullish}, 死叉: {bearish}")
        
    except Exception as e:
        print(f"❌ 测试失败: {e}")