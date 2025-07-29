"""
技术指标模块异常定义
"""

class IndicatorCalculationError(Exception):
    """指标计算异常"""
    pass

class InsufficientDataError(IndicatorCalculationError):
    """数据不足异常"""
    pass

class InvalidParameterError(IndicatorCalculationError):
    """参数无效异常"""
    pass