"""
服务基类
所有服务的抽象基类
"""

import logging
from abc import ABC
from typing import Any, Dict


class BaseService(ABC):
    """
    服务基类
    
    提供所有服务的通用功能：
    1. 日志记录
    2. 配置访问
    3. 错误处理
    """
    
    def __init__(self, config: Dict[str, Any]):
        """
        初始化服务
        
        Args:
            config: 配置字典
        """
        self.config = config
        self.logger = logging.getLogger(self.__class__.__name__)
        self._initialized = False
    
    def initialize(self) -> bool:
        """
        初始化服务
        子类可以重写此方法实现特定的初始化逻辑
        
        Returns:
            bool: 初始化是否成功
        """
        try:
            self._initialized = True
            self.logger.info(f"{self.__class__.__name__} 初始化成功")
            return True
        except Exception as e:
            self.logger.error(f"{self.__class__.__name__} 初始化失败: {e}")
            return False
    
    def is_initialized(self) -> bool:
        """检查服务是否已初始化"""
        return self._initialized
    
    def get_config(self, key: str, default: Any = None) -> Any:
        """
        获取配置值
        
        Args:
            key: 配置键
            default: 默认值
            
        Returns:
            配置值
        """
        return self.config.get(key, default)
