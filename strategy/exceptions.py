"""
策略模块异常定义
"""

class StrategyError(Exception):
    """策略基础异常"""
    pass

class SignalGenerationError(StrategyError):
    """信号生成异常"""
    pass

class PositionManagementError(StrategyError):
    """仓位管理异常"""
    pass

class RiskManagementError(StrategyError):
    """风险管理异常"""
    pass

class StrategyConfigError(StrategyError):
    """策略配置异常"""
    pass

class InsufficientDataError(StrategyError):
    """数据不足异常"""
    pass