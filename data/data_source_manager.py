"""
数据源管理器

支持多数据源降级、负载均衡、健康检查。
当主数据源失败时，自动切换到备用数据源。
"""

import logging
from typing import List, Optional

import pandas as pd

from .data_source_plugin import DataSourcePlugin, DataFetchError


class DataSourceManager:
    """
    数据源管理器
    
    功能：
    1. 管理多个数据源
    2. 自动降级（主数据源失败时切换到备用）
    3. 健康检查
    4. 负载均衡（可选）
    
    使用示例：
        >>> manager = DataSourceManager()
        >>> manager.register_plugin(akshare_plugin)
        >>> manager.register_plugin(tushare_plugin)
        >>> data = manager.get_stock_data("000001", "2024-01-01", "2024-12-31")
    """
    
    def __init__(self):
        """初始化数据源管理器"""
        self.plugins: List[DataSourcePlugin] = []
        self.active_plugin: Optional[DataSourcePlugin] = None
        self.logger = logging.getLogger(__name__)
        self._health_status = {}
    
    def register_plugin(self, plugin: DataSourcePlugin):
        """
        注册数据源插件
        
        Args:
            plugin: 数据源插件实例
        """
        if not plugin.config.enabled:
            self.logger.info(f"跳过已禁用的数据源: {plugin.get_source_name()}")
            return
        
        self.plugins.append(plugin)
        # 按优先级排序（数字越小优先级越高）
        self.plugins.sort(key=lambda p: p.config.priority)
        
        self.logger.info(
            f"注册数据源: {plugin.get_source_name()} "
            f"(优先级: {plugin.config.priority})"
        )
        
        # 如果是第一个插件，设为活动插件
        if self.active_plugin is None:
            self.active_plugin = plugin
            self.logger.info(f"设置活动数据源: {plugin.get_source_name()}")
    
    def get_stock_data(self, code: str, start_date: str, 
                      end_date: str, period: str = 'weekly') -> Optional[pd.DataFrame]:
        """
        获取股票数据（带自动降级）
        
        尝试从活动数据源获取数据，如果失败则自动切换到备用数据源。
        
        Args:
            code: 股票代码
            start_date: 开始日期
            end_date: 结束日期
            period: 周期 ('daily' 或 'weekly')
            
        Returns:
            pd.DataFrame: 股票数据，如果所有数据源都失败则返回None
        """
        if not self.plugins:
            self.logger.error("没有可用的数据源")
            return None
        
        # 尝试所有数据源（按优先级）
        for plugin in self.plugins:
            try:
                self.logger.debug(
                    f"尝试从 {plugin.get_source_name()} 获取 {code} 数据"
                )
                
                data = plugin.get_stock_data(code, start_date, end_date, period)
                
                if data is not None and not data.empty:
                    # 成功获取数据
                    if plugin != self.active_plugin:
                        self.logger.info(
                            f"数据源切换: {self.active_plugin.get_source_name() if self.active_plugin else 'None'} "
                            f"-> {plugin.get_source_name()}"
                        )
                        self.active_plugin = plugin
                    
                    self._update_health_status(plugin, True)
                    return data
                else:
                    self.logger.warning(
                        f"{plugin.get_source_name()} 返回空数据"
                    )
                    self._update_health_status(plugin, False)
                    
            except DataFetchError as e:
                self.logger.warning(
                    f"{plugin.get_source_name()} 获取失败: {e}"
                )
                self._update_health_status(plugin, False)
                continue
                
            except Exception as e:
                self.logger.error(
                    f"{plugin.get_source_name()} 发生异常: {e}"
                )
                self._update_health_status(plugin, False)
                continue
        
        # 所有数据源都失败
        self.logger.error(f"所有数据源都无法获取 {code} 数据")
        return None
    
    def check_health(self) -> dict:
        """
        检查所有数据源的健康状态
        
        Returns:
            dict: 数据源名称到健康状态的映射
        """
        health_report = {}
        
        for plugin in self.plugins:
            source_name = plugin.get_source_name()
            self.logger.info(f"检查 {source_name} 健康状态...")
            
            try:
                is_healthy = plugin.test_connection()
                health_report[source_name] = {
                    'healthy': is_healthy,
                    'priority': plugin.config.priority,
                    'enabled': plugin.config.enabled
                }
                
                if is_healthy:
                    self.logger.info(f"✅ {source_name} 健康")
                else:
                    self.logger.warning(f"⚠️ {source_name} 不健康")
                    
            except Exception as e:
                self.logger.error(f"❌ {source_name} 健康检查失败: {e}")
                health_report[source_name] = {
                    'healthy': False,
                    'priority': plugin.config.priority,
                    'enabled': plugin.config.enabled,
                    'error': str(e)
                }
        
        return health_report
    
    def get_active_source(self) -> Optional[str]:
        """
        获取当前活动数据源名称
        
        Returns:
            str: 数据源名称，如果没有活动数据源则返回None
        """
        if self.active_plugin:
            return self.active_plugin.get_source_name()
        return None
    
    def get_available_sources(self) -> List[str]:
        """
        获取所有可用数据源名称列表
        
        Returns:
            List[str]: 数据源名称列表
        """
        return [plugin.get_source_name() for plugin in self.plugins]
    
    def switch_to_source(self, source_name: str) -> bool:
        """
        手动切换到指定数据源
        
        Args:
            source_name: 数据源名称
            
        Returns:
            bool: 切换是否成功
        """
        for plugin in self.plugins:
            if plugin.get_source_name() == source_name:
                old_source = self.active_plugin.get_source_name() if self.active_plugin else "None"
                self.active_plugin = plugin
                self.logger.info(f"手动切换数据源: {old_source} -> {source_name}")
                return True
        
        self.logger.error(f"未找到数据源: {source_name}")
        return False
    
    def _update_health_status(self, plugin: DataSourcePlugin, is_healthy: bool):
        """
        更新数据源健康状态
        
        Args:
            plugin: 数据源插件
            is_healthy: 是否健康
        """
        source_name = plugin.get_source_name()
        
        if source_name not in self._health_status:
            self._health_status[source_name] = {
                'success_count': 0,
                'failure_count': 0
            }
        
        if is_healthy:
            self._health_status[source_name]['success_count'] += 1
        else:
            self._health_status[source_name]['failure_count'] += 1
    
    def get_health_statistics(self) -> dict:
        """
        获取健康统计信息
        
        Returns:
            dict: 健康统计信息
        """
        return self._health_status.copy()
    
    def reset_health_statistics(self):
        """重置健康统计信息"""
        self._health_status.clear()
        self.logger.info("健康统计信息已重置")
