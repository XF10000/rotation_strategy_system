"""
数据获取器适配器

将新的插件系统适配到现有的DataFetcher接口，保持向后兼容。
"""

import logging

import pandas as pd

from .data_fetcher import DataFetcher
from .data_source_manager import DataSourceManager
from .data_source_plugin import (
    AksharePlugin,
    DataSourceConfig,
    DataSourceType
)


class PluginDataFetcherAdapter(DataFetcher):
    """
    插件数据获取器适配器
    
    将新的插件系统适配到现有的DataFetcher接口。
    支持多数据源自动降级，但对外保持原有接口不变。
    """
    
    def __init__(self, config: dict = None):
        """
        初始化适配器
        
        Args:
            config: 配置字典，可包含数据源配置
        """
        self.logger = logging.getLogger(__name__)
        self.manager = DataSourceManager()
        
        # 默认注册Akshare（保持向后兼容）
        akshare_config = DataSourceConfig(
            source_type=DataSourceType.AKSHARE,
            rate_limit=3.0,
            max_retries=5,
            priority=1,
            enabled=True
        )
        akshare_plugin = AksharePlugin(akshare_config)
        self.manager.register_plugin(akshare_plugin)
        
        self.logger.info("插件数据获取器适配器初始化完成")
        self.logger.info(f"可用数据源: {self.manager.get_available_sources()}")
    
    def get_stock_data(self, code: str, start_date: str, end_date: str = None, 
                      period: str = 'weekly') -> pd.DataFrame:
        """
        获取股票历史数据（适配器方法）
        
        Args:
            code: 股票代码
            start_date: 开始日期
            end_date: 结束日期
            period: 数据周期
            
        Returns:
            pd.DataFrame: 股票数据
        """
        # 如果没有指定结束日期，使用当前日期
        if end_date is None:
            from datetime import datetime
            end_date = datetime.now().strftime('%Y-%m-%d')
        
        # 使用管理器获取数据（自动降级）
        data = self.manager.get_stock_data(code, start_date, end_date, period)
        
        if data is None or data.empty:
            self.logger.warning(f"无法获取 {code} 数据")
            return pd.DataFrame()
        
        return data
    
    def get_active_source(self) -> str:
        """
        获取当前活动数据源
        
        Returns:
            str: 数据源名称
        """
        return self.manager.get_active_source()
    
    def check_health(self) -> dict:
        """
        检查所有数据源健康状态
        
        Returns:
            dict: 健康状态报告
        """
        return self.manager.check_health()
