"""
数据源插件系统

支持灵活的数据源扩展和切换，使用插件化架构。
每个数据源实现为一个独立的插件，可以方便地添加、切换和管理。
"""

import logging
import time
from abc import ABC, abstractmethod
from dataclasses import dataclass
from enum import Enum
from typing import Dict, Optional

import pandas as pd


class DataSourceType(Enum):
    """数据源类型枚举"""
    AKSHARE = "akshare"
    TUSHARE = "tushare"
    WIND = "wind"
    EASTMONEY = "eastmoney"
    CUSTOM = "custom"


@dataclass
class DataSourceConfig:
    """
    数据源配置
    
    Attributes:
        source_type: 数据源类型
        api_key: API密钥（如果需要）
        rate_limit: 请求间隔（秒）
        max_retries: 最大重试次数
        timeout: 超时时间（秒）
        priority: 优先级（数字越小优先级越高）
        enabled: 是否启用
        custom_params: 自定义参数
    """
    source_type: DataSourceType
    api_key: Optional[str] = None
    rate_limit: float = 3.0
    max_retries: int = 5
    timeout: int = 30
    priority: int = 1
    enabled: bool = True
    custom_params: Dict = None


class DataFetchError(Exception):
    """数据获取异常"""
    pass


class DataSourcePlugin(ABC):
    """
    数据源插件基类
    
    所有数据源实现都继承此类，提供统一的接口和标准化的数据格式。
    使用模板方法模式，将通用逻辑（重试、频率控制、标准化）放在基类中，
    具体的数据获取逻辑由子类实现。
    """
    
    def __init__(self, config: DataSourceConfig):
        """
        初始化数据源插件
        
        Args:
            config: 数据源配置
        """
        self.config = config
        self.source_type = config.source_type
        self.logger = logging.getLogger(f"DataSource.{self.source_type.value}")
        self._last_request_time = 0
    
    @abstractmethod
    def fetch_raw_data(self, code: str, start_date: str, 
                      end_date: str, period: str) -> pd.DataFrame:
        """
        获取原始数据（由子类实现）
        
        注意：此方法只负责获取原始数据，不做标准化处理。
        
        Args:
            code: 股票代码
            start_date: 开始日期 (YYYY-MM-DD)
            end_date: 结束日期 (YYYY-MM-DD)
            period: 周期 ('daily' 或 'weekly')
            
        Returns:
            pd.DataFrame: 原始数据
        """
        pass
    
    @abstractmethod
    def test_connection(self) -> bool:
        """
        测试数据源连接
        
        Returns:
            bool: 连接是否正常
        """
        pass
    
    @abstractmethod
    def get_source_name(self) -> str:
        """
        获取数据源名称
        
        Returns:
            str: 数据源名称
        """
        pass
    
    def get_stock_data(self, code: str, start_date: str, 
                      end_date: str, period: str) -> pd.DataFrame:
        """
        获取标准化的股票数据（模板方法）
        
        此方法不需要子类重写，统一处理：
        1. 参数验证
        2. 重试逻辑
        3. 频率控制
        4. 数据标准化
        
        Args:
            code: 股票代码
            start_date: 开始日期
            end_date: 结束日期
            period: 周期
            
        Returns:
            pd.DataFrame: 标准化后的数据
        """
        # 1. 参数验证
        self._validate_params(code, start_date, end_date, period)
        
        # 2. 带重试的数据获取
        raw_data = self._fetch_with_retry(code, start_date, end_date, period)
        
        # 3. 数据标准化（统一格式）
        standardized_data = self._standardize_data(raw_data)
        
        return standardized_data
    
    def _fetch_with_retry(self, code: str, start_date: str, 
                         end_date: str, period: str) -> pd.DataFrame:
        """
        带重试机制的数据获取（统一实现）
        
        Args:
            code: 股票代码
            start_date: 开始日期
            end_date: 结束日期
            period: 周期
            
        Returns:
            pd.DataFrame: 原始数据
            
        Raises:
            DataFetchError: 获取失败
        """
        for attempt in range(self.config.max_retries):
            try:
                # 频率控制
                self._rate_limit_control()
                
                # 调用子类实现的原始数据获取
                data = self.fetch_raw_data(code, start_date, end_date, period)
                
                if data is not None and not data.empty:
                    self.logger.debug(f"成功获取 {code} 数据，共 {len(data)} 条")
                    return data
                else:
                    self.logger.warning(f"第 {attempt + 1} 次获取 {code} 数据为空")
                
            except Exception as e:
                self.logger.warning(f"第 {attempt + 1} 次获取失败: {str(e)}")
                if attempt < self.config.max_retries - 1:
                    wait_time = (attempt + 1) * 3
                    self.logger.info(f"等待 {wait_time} 秒后重试...")
                    time.sleep(wait_time)
        
        raise DataFetchError(f"获取 {code} 数据失败，已重试 {self.config.max_retries} 次")
    
    def _standardize_data(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        统一的数据标准化（所有数据源共用）
        
        输出标准格式：
        - 索引：date (datetime)
        - 列：open, high, low, close, volume
        
        Args:
            df: 原始数据
            
        Returns:
            pd.DataFrame: 标准化后的数据
        """
        if df is None or df.empty:
            return df
        
        # 创建副本避免修改原数据
        result = df.copy()
        
        # 确保日期索引
        if 'date' in result.columns and not isinstance(result.index, pd.DatetimeIndex):
            result['date'] = pd.to_datetime(result['date'])
            result.set_index('date', inplace=True)
        
        # 确保索引是DatetimeIndex
        if not isinstance(result.index, pd.DatetimeIndex):
            result.index = pd.to_datetime(result.index)
        
        # 标准化列名（小写）
        result.columns = result.columns.str.lower()
        
        # 确保必要列存在
        required_columns = ['open', 'high', 'low', 'close', 'volume']
        for col in required_columns:
            if col not in result.columns:
                self.logger.warning(f"缺少必要列: {col}")
        
        # 按日期排序
        result.sort_index(inplace=True)
        
        return result
    
    def _validate_params(self, code: str, start_date: str, 
                        end_date: str, period: str):
        """
        参数验证（统一实现）
        
        Args:
            code: 股票代码
            start_date: 开始日期
            end_date: 结束日期
            period: 周期
            
        Raises:
            ValueError: 参数无效
        """
        if not code:
            raise ValueError("股票代码不能为空")
        
        if not start_date or not end_date:
            raise ValueError("日期不能为空")
        
        if period not in ['daily', 'weekly']:
            raise ValueError(f"不支持的周期: {period}")
        
        # 验证日期格式
        try:
            pd.to_datetime(start_date)
            pd.to_datetime(end_date)
        except Exception as e:
            raise ValueError(f"日期格式错误: {e}")
    
    def _rate_limit_control(self):
        """
        频率控制（统一实现）
        
        确保两次请求之间有足够的时间间隔，避免被限流。
        """
        current_time = time.time()
        time_since_last_request = current_time - self._last_request_time
        
        if time_since_last_request < self.config.rate_limit:
            sleep_time = self.config.rate_limit - time_since_last_request
            self.logger.debug(f"频率控制：等待 {sleep_time:.2f} 秒")
            time.sleep(sleep_time)
        
        self._last_request_time = time.time()


class AksharePlugin(DataSourcePlugin):
    """
    Akshare数据源插件
    
    使用Akshare库获取A股数据，免费且无需API密钥。
    """
    
    def fetch_raw_data(self, code: str, start_date: str, 
                      end_date: str, period: str) -> pd.DataFrame:
        """
        获取Akshare原始数据
        
        Args:
            code: 股票代码
            start_date: 开始日期
            end_date: 结束日期
            period: 周期
            
        Returns:
            pd.DataFrame: 原始数据
        """
        import akshare as ak
        
        # 只负责调用API，不做其他处理
        df = ak.stock_zh_a_hist(
            symbol=code,
            period=period,
            start_date=start_date.replace('-', ''),
            end_date=end_date.replace('-', ''),
            adjust=""  # 不复权
        )
        return df
    
    def test_connection(self) -> bool:
        """
        测试Akshare连接
        
        Returns:
            bool: 连接是否正常
        """
        try:
            test_data = self.fetch_raw_data("000001", "2024-01-01", "2024-01-07", "daily")
            return test_data is not None and not test_data.empty
        except Exception as e:
            self.logger.error(f"Akshare连接测试失败: {e}")
            return False
    
    def get_source_name(self) -> str:
        """获取数据源名称"""
        return "Akshare"


class TusharePlugin(DataSourcePlugin):
    """
    Tushare数据源插件
    
    使用Tushare Pro接口获取数据，需要API Token。
    """
    
    def __init__(self, config: DataSourceConfig):
        """
        初始化Tushare插件
        
        Args:
            config: 数据源配置（需包含api_key）
        """
        super().__init__(config)
        
        if not config.api_key:
            raise ValueError("Tushare需要API Token")
        
        try:
            import tushare as ts
            self.pro = ts.pro_api(config.api_key)
            self.logger.info("Tushare Pro API初始化成功")
        except Exception as e:
            self.logger.error(f"Tushare初始化失败: {e}")
            raise
    
    def fetch_raw_data(self, code: str, start_date: str, 
                      end_date: str, period: str) -> pd.DataFrame:
        """
        获取Tushare原始数据
        
        Args:
            code: 股票代码
            start_date: 开始日期
            end_date: 结束日期
            period: 周期
            
        Returns:
            pd.DataFrame: 原始数据
        """
        # 转换股票代码格式（Tushare需要带后缀）
        if code.startswith('6'):
            ts_code = f"{code}.SH"
        elif code.startswith(('0', '3')):
            ts_code = f"{code}.SZ"
        else:
            ts_code = f"{code}.SH"  # 默认上海
        
        # 调用Tushare API
        if period == 'daily':
            df = self.pro.daily(
                ts_code=ts_code,
                start_date=start_date.replace('-', ''),
                end_date=end_date.replace('-', '')
            )
        elif period == 'weekly':
            df = self.pro.weekly(
                ts_code=ts_code,
                start_date=start_date.replace('-', ''),
                end_date=end_date.replace('-', '')
            )
        else:
            raise ValueError(f"不支持的周期: {period}")
        
        # Tushare返回的列名需要映射
        if df is not None and not df.empty:
            df.rename(columns={
                'trade_date': 'date',
                'vol': 'volume'
            }, inplace=True)
        
        return df
    
    def test_connection(self) -> bool:
        """
        测试Tushare连接
        
        Returns:
            bool: 连接是否正常
        """
        try:
            test_data = self.fetch_raw_data("000001", "2024-01-01", "2024-01-07", "daily")
            return test_data is not None and not test_data.empty
        except Exception as e:
            self.logger.error(f"Tushare连接测试失败: {e}")
            return False
    
    def get_source_name(self) -> str:
        """获取数据源名称"""
        return "Tushare"
