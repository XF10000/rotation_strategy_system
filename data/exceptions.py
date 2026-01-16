"""
数据模块异常定义
"""

class RotationStrategyError(Exception):
    """策略系统基础异常"""

class DataFetchError(RotationStrategyError):
    """数据获取异常"""

class DataProcessError(RotationStrategyError):
    """数据处理异常"""

class DataStorageError(RotationStrategyError):
    """数据存储异常"""
