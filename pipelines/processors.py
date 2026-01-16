"""
数据处理器实现

包含各种具体的数据处理器，用于数据管道。
"""

import logging

import numpy as np
import pandas as pd

from .data_pipeline import DataProcessor


class DataValidator(DataProcessor):
    """
    数据验证器
    
    验证数据的完整性和正确性：
    - 必要列是否存在
    - 数据类型是否正确
    - 数据范围是否合理
    - 是否有缺失值
    """
    
    def __init__(self, required_columns: list = None):
        """
        初始化数据验证器
        
        Args:
            required_columns: 必需的列名列表，如果为None则使用默认列
        """
        self.logger = logging.getLogger(__name__)
        self.required_columns = required_columns or [
            'date', 'open', 'high', 'low', 'close', 'volume'
        ]
    
    def process(self, data: pd.DataFrame) -> pd.DataFrame:
        """
        验证数据
        
        Args:
            data: 输入数据
            
        Returns:
            pd.DataFrame: 验证通过的数据
            
        Raises:
            ValueError: 如果数据验证失败
        """
        if data.empty:
            raise ValueError("数据为空")
        
        # 验证必要列存在
        missing_columns = set(self.required_columns) - set(data.columns)
        if missing_columns:
            raise ValueError(f"缺少必要列: {missing_columns}")
        
        # 验证数据类型
        numeric_columns = ['open', 'high', 'low', 'close', 'volume']
        for col in numeric_columns:
            if col in data.columns and not pd.api.types.is_numeric_dtype(data[col]):
                self.logger.warning(f"列 {col} 不是数值类型，尝试转换")
                try:
                    data[col] = pd.to_numeric(data[col], errors='coerce')
                except Exception as e:
                    raise ValueError(f"列 {col} 无法转换为数值类型: {e}")
        
        # 验证价格数据的合理性
        if 'high' in data.columns and 'low' in data.columns:
            invalid_rows = data[data['high'] < data['low']]
            if not invalid_rows.empty:
                raise ValueError(f"发现 {len(invalid_rows)} 行数据的最高价低于最低价")
        
        if 'open' in data.columns and 'high' in data.columns and 'low' in data.columns:
            invalid_open = data[(data['open'] > data['high']) | (data['open'] < data['low'])]
            if not invalid_open.empty:
                self.logger.warning(f"发现 {len(invalid_open)} 行数据的开盘价超出最高最低价范围")
        
        # 验证成交量非负
        if 'volume' in data.columns:
            negative_volume = data[data['volume'] < 0]
            if not negative_volume.empty:
                raise ValueError(f"发现 {len(negative_volume)} 行数据的成交量为负")
        
        # 检查缺失值
        null_counts = data[self.required_columns].isnull().sum()
        if null_counts.any():
            self.logger.warning(f"发现缺失值:\n{null_counts[null_counts > 0]}")
        
        self.logger.debug(f"数据验证通过，共 {len(data)} 行")
        return data
    
    def get_name(self) -> str:
        """获取处理器名称"""
        return "数据验证"


class TechnicalIndicatorCalculator(DataProcessor):
    """
    技术指标计算器
    
    计算常用技术指标：
    - RSI (相对强弱指标)
    - MACD (指数平滑异同移动平均线)
    - EMA (指数移动平均)
    - 布林带
    
    注意：这个处理器假设数据已经包含必要的价格列。
    """
    
    def __init__(self, calculate_rsi: bool = True, 
                 calculate_macd: bool = True,
                 calculate_ema: bool = True,
                 calculate_bollinger: bool = True):
        """
        初始化技术指标计算器
        
        Args:
            calculate_rsi: 是否计算RSI
            calculate_macd: 是否计算MACD
            calculate_ema: 是否计算EMA
            calculate_bollinger: 是否计算布林带
        """
        self.logger = logging.getLogger(__name__)
        self.calculate_rsi = calculate_rsi
        self.calculate_macd = calculate_macd
        self.calculate_ema = calculate_ema
        self.calculate_bollinger = calculate_bollinger
    
    def process(self, data: pd.DataFrame) -> pd.DataFrame:
        """
        计算技术指标
        
        Args:
            data: 输入数据（必须包含close列）
            
        Returns:
            pd.DataFrame: 添加了技术指标的数据
        """
        if 'close' not in data.columns:
            raise ValueError("数据必须包含close列才能计算技术指标")
        
        # 创建副本避免修改原数据
        result = data.copy()
        
        # 计算RSI
        if self.calculate_rsi and 'rsi' not in result.columns:
            try:
                from indicators.momentum import calculate_rsi
                result['rsi'] = calculate_rsi(result, period=14)
                self.logger.debug("RSI计算完成")
            except Exception as e:
                self.logger.warning(f"RSI计算失败: {e}")
        
        # 计算MACD
        if self.calculate_macd and 'macd' not in result.columns:
            try:
                from indicators.momentum import calculate_macd
                macd, signal, hist = calculate_macd(result)
                result['macd'] = macd
                result['macd_signal'] = signal
                result['macd_histogram'] = hist
                self.logger.debug("MACD计算完成")
            except Exception as e:
                self.logger.warning(f"MACD计算失败: {e}")
        
        # 计算EMA
        if self.calculate_ema and 'ema_20' not in result.columns:
            try:
                from indicators.trend import calculate_ema
                result['ema_20'] = calculate_ema(result, period=20)
                self.logger.debug("EMA计算完成")
            except Exception as e:
                self.logger.warning(f"EMA计算失败: {e}")
        
        # 计算布林带
        if self.calculate_bollinger and 'bb_upper' not in result.columns:
            try:
                from indicators.volatility import calculate_bollinger_bands
                upper, middle, lower = calculate_bollinger_bands(result, period=20, std=2.0)
                result['bb_upper'] = upper
                result['bb_middle'] = middle
                result['bb_lower'] = lower
                self.logger.debug("布林带计算完成")
            except Exception as e:
                self.logger.warning(f"布林带计算失败: {e}")
        
        self.logger.debug(f"技术指标计算完成，数据形状: {result.shape}")
        return result
    
    def get_name(self) -> str:
        """获取处理器名称"""
        return "技术指标计算"


class DataNormalizer(DataProcessor):
    """
    数据标准化器
    
    处理数据的标准化和清洗：
    - 处理缺失值
    - 去除异常值
    - 数据排序
    - 索引重置
    """
    
    def __init__(self, fill_method: str = 'ffill', 
                 remove_duplicates: bool = True,
                 sort_by_date: bool = True):
        """
        初始化数据标准化器
        
        Args:
            fill_method: 缺失值填充方法 ('ffill', 'bfill', 'drop')
            remove_duplicates: 是否移除重复行
            sort_by_date: 是否按日期排序
        """
        self.logger = logging.getLogger(__name__)
        self.fill_method = fill_method
        self.remove_duplicates = remove_duplicates
        self.sort_by_date = sort_by_date
    
    def process(self, data: pd.DataFrame) -> pd.DataFrame:
        """
        标准化数据
        
        Args:
            data: 输入数据
            
        Returns:
            pd.DataFrame: 标准化后的数据
        """
        result = data.copy()
        original_len = len(result)
        
        # 按日期排序
        if self.sort_by_date and 'date' in result.columns:
            if not isinstance(result.index, pd.DatetimeIndex):
                result = result.sort_values('date')
                self.logger.debug("按日期排序完成")
        
        # 移除重复行
        if self.remove_duplicates:
            result = result.drop_duplicates()
            duplicates_removed = original_len - len(result)
            if duplicates_removed > 0:
                self.logger.info(f"移除 {duplicates_removed} 行重复数据")
        
        # 处理缺失值
        null_count_before = result.isnull().sum().sum()
        if null_count_before > 0:
            if self.fill_method == 'ffill':
                result = result.fillna(method='ffill')
                self.logger.debug(f"使用前向填充处理 {null_count_before} 个缺失值")
            elif self.fill_method == 'bfill':
                result = result.fillna(method='bfill')
                self.logger.debug(f"使用后向填充处理 {null_count_before} 个缺失值")
            elif self.fill_method == 'drop':
                result = result.dropna()
                rows_dropped = original_len - len(result)
                self.logger.info(f"删除 {rows_dropped} 行包含缺失值的数据")
            
            null_count_after = result.isnull().sum().sum()
            if null_count_after > 0:
                self.logger.warning(f"仍有 {null_count_after} 个缺失值未处理")
        
        # 重置索引
        result = result.reset_index(drop=True)
        
        self.logger.debug(f"数据标准化完成，最终数据量: {len(result)} 行")
        return result
    
    def get_name(self) -> str:
        """获取处理器名称"""
        return "数据标准化"
