"""
技术指标模块异常定义
"""

class IndicatorCalculationError(Exception):
    """指标计算异常"""

class InsufficientDataError(IndicatorCalculationError):
    """数据不足异常"""

class InvalidParameterError(IndicatorCalculationError):
    """参数无效异常"""
