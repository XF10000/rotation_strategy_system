"""
数据处理管道

提供可扩展的数据处理流程，使用责任链模式。
每个处理步骤都是一个独立的处理器，可以灵活组合。
"""

import logging
from abc import ABC, abstractmethod
from typing import List

import pandas as pd


class DataProcessor(ABC):
    """
    数据处理器基类
    
    所有数据处理器都应该继承这个类并实现process和get_name方法。
    """
    
    @abstractmethod
    def process(self, data: pd.DataFrame) -> pd.DataFrame:
        """
        处理数据
        
        Args:
            data: 输入数据
            
        Returns:
            pd.DataFrame: 处理后的数据
        """
        pass
    
    @abstractmethod
    def get_name(self) -> str:
        """
        获取处理器名称
        
        Returns:
            str: 处理器名称，用于日志记录
        """
        pass


class DataPipeline:
    """
    数据处理管道
    
    使用责任链模式处理数据，按顺序执行多个处理步骤。
    支持链式调用添加处理步骤。
    
    Example:
        >>> pipeline = (DataPipeline()
        ...     .add_step(DataValidator())
        ...     .add_step(TechnicalIndicatorCalculator())
        ...     .add_step(DataNormalizer())
        ... )
        >>> processed_data = pipeline.process(raw_data)
    """
    
    def __init__(self):
        """初始化数据管道"""
        self.steps: List[DataProcessor] = []
        self.logger = logging.getLogger(__name__)
    
    def add_step(self, step: DataProcessor) -> 'DataPipeline':
        """
        添加处理步骤
        
        Args:
            step: 数据处理器实例
            
        Returns:
            DataPipeline: 返回self以支持链式调用
        """
        self.steps.append(step)
        self.logger.debug(f"添加处理步骤: {step.get_name()}")
        return self
    
    def process(self, data: pd.DataFrame) -> pd.DataFrame:
        """
        执行管道处理
        
        按顺序执行所有处理步骤，每个步骤的输出作为下一个步骤的输入。
        
        Args:
            data: 原始数据
            
        Returns:
            pd.DataFrame: 处理后的数据
        """
        if not self.steps:
            self.logger.warning("数据管道为空，未添加任何处理步骤")
            return data
        
        self.logger.info(f"开始数据管道处理，共{len(self.steps)}个步骤")
        
        for i, step in enumerate(self.steps, 1):
            step_name = step.get_name()
            self.logger.debug(f"步骤{i}/{len(self.steps)}: {step_name}")
            
            try:
                data = step.process(data)
                self.logger.debug(f"步骤{i}完成: {step_name}")
            except Exception as e:
                self.logger.error(f"步骤{i}失败: {step_name}, 错误: {e}")
                raise
        
        self.logger.info("数据管道处理完成")
        return data
    
    def get_steps(self) -> List[str]:
        """
        获取所有处理步骤的名称
        
        Returns:
            List[str]: 处理步骤名称列表
        """
        return [step.get_name() for step in self.steps]
    
    def clear(self) -> 'DataPipeline':
        """
        清空所有处理步骤
        
        Returns:
            DataPipeline: 返回self以支持链式调用
        """
        self.steps.clear()
        self.logger.debug("清空所有处理步骤")
        return self
