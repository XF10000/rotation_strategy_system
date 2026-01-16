"""
策略模块异常定义
"""

class StrategyError(Exception):
    """策略基础异常"""

class SignalGenerationError(StrategyError):
    """信号生成异常"""

class PositionManagementError(StrategyError):
    """仓位管理异常"""

class RiskManagementError(StrategyError):
    """风险管理异常"""

class StrategyConfigError(StrategyError):
    """策略配置异常"""

class InsufficientDataError(StrategyError):
    """数据不足异常"""
