"""
数据存储管理器模块
提供数据缓存保存、加载和管理功能
"""

import os
import pandas as pd
import json
import logging
from datetime import datetime, timedelta
from typing import Optional, Dict, Any
from pathlib import Path

from .exceptions import DataStorageError

logger = logging.getLogger(__name__)

class DataStorage:
    """数据存储管理器"""
    
    def __init__(self, cache_dir: str = 'data_cache'):
        """
        初始化数据存储管理器
        
        Args:
            cache_dir: 缓存目录路径
        """
        self.cache_dir = Path(cache_dir)
        self.stock_data_dir = self.cache_dir / 'stock_data'
        self.indicators_dir = self.cache_dir / 'indicators'
        self.signals_dir = self.cache_dir / 'signals'
        self.backtest_dir = self.cache_dir / 'backtest'
        
        # 创建目录结构
        self._create_directories()
        
        logger.info(f"初始化数据存储管理器，缓存目录: {self.cache_dir}")
    
    def _create_directories(self):
        """创建必要的目录结构"""
        try:
            directories = [
                self.cache_dir,
                self.stock_data_dir,
                self.stock_data_dir / 'daily',
                self.stock_data_dir / 'weekly',
                self.stock_data_dir / 'monthly',
                self.indicators_dir,
                self.signals_dir,
                self.backtest_dir
            ]
            
            for directory in directories:
                directory.mkdir(parents=True, exist_ok=True)
                
        except Exception as e:
            raise DataStorageError(f"创建目录结构失败: {str(e)}") from e
    
    def save_data(self, data: pd.DataFrame, code: str, period: str) -> bool:
        """
        保存数据到缓存
        
        Args:
            data: 股票数据
            code: 股票代码
            period: 数据周期 ('daily', 'weekly', 'monthly')
            
        Returns:
            bool: 是否保存成功
        """
        try:
            if data is None or data.empty:
                logger.warning(f"尝试保存空数据: {code}")
                return False
            
            # 构建文件路径
            file_path = self._get_stock_data_path(code, period)
            
            # 保存数据
            data.to_csv(file_path, encoding='utf-8')
            
            # 保存元数据
            metadata = {
                'code': code,
                'period': period,
                'records': len(data),
                'start_date': data.index.min().strftime('%Y-%m-%d'),
                'end_date': data.index.max().strftime('%Y-%m-%d'),
                'columns': list(data.columns),
                'save_time': datetime.now().isoformat()
            }
            
            metadata_path = file_path.with_suffix('.json')
            with open(metadata_path, 'w', encoding='utf-8') as f:
                json.dump(metadata, f, ensure_ascii=False, indent=2)
            
            logger.info(f"成功保存数据: {code} ({period}), {len(data)} 条记录")
            return True
            
        except Exception as e:
            logger.error(f"保存数据失败: {code} ({period}), 错误: {str(e)}")
            return False
    
    def load_data(self, code: str, period: str) -> Optional[pd.DataFrame]:
        """
        从缓存加载数据
        
        Args:
            code: 股票代码
            period: 数据周期
            
        Returns:
            Optional[pd.DataFrame]: 缓存的数据或None
        """
        try:
            file_path = self._get_stock_data_path(code, period)
            
            if not file_path.exists():
                logger.debug(f"缓存文件不存在: {file_path}")
                return None
            
            # 加载数据
            data = pd.read_csv(file_path, index_col=0, parse_dates=True)
            
            logger.info(f"成功加载缓存数据: {code} ({period}), {len(data)} 条记录")
            return data
            
        except Exception as e:
            logger.error(f"加载缓存数据失败: {code} ({period}), 错误: {str(e)}")
            return None
    
    def is_data_fresh(self, code: str, period: str, max_age_days: int = 1) -> bool:
        """
        检查缓存数据是否新鲜
        
        Args:
            code: 股票代码
            period: 数据周期
            max_age_days: 最大缓存天数
            
        Returns:
            bool: 数据是否新鲜
        """
        try:
            metadata_path = self._get_stock_data_path(code, period).with_suffix('.json')
            
            if not metadata_path.exists():
                return False
            
            # 读取元数据
            with open(metadata_path, 'r', encoding='utf-8') as f:
                metadata = json.load(f)
            
            # 检查保存时间
            save_time = datetime.fromisoformat(metadata['save_time'])
            age = datetime.now() - save_time
            
            is_fresh = age.days < max_age_days
            
            logger.debug(f"数据新鲜度检查: {code} ({period}), 年龄: {age.days} 天, 新鲜: {is_fresh}")
            return is_fresh
            
        except Exception as e:
            logger.error(f"检查数据新鲜度失败: {code} ({period}), 错误: {str(e)}")
            return False
    
    def get_cached_data_info(self, code: str, period: str) -> Optional[Dict[str, Any]]:
        """
        获取缓存数据信息
        
        Args:
            code: 股票代码
            period: 数据周期
            
        Returns:
            Optional[Dict[str, Any]]: 数据信息或None
        """
        try:
            metadata_path = self._get_stock_data_path(code, period).with_suffix('.json')
            
            if not metadata_path.exists():
                return None
            
            with open(metadata_path, 'r', encoding='utf-8') as f:
                metadata = json.load(f)
            
            return metadata
            
        except Exception as e:
            logger.error(f"获取缓存数据信息失败: {code} ({period}), 错误: {str(e)}")
            return None
    
    def save_indicators(self, data: pd.DataFrame, code: str) -> bool:
        """
        保存技术指标数据
        
        Args:
            data: 技术指标数据
            code: 股票代码
            
        Returns:
            bool: 是否保存成功
        """
        try:
            if data is None or data.empty:
                logger.warning(f"尝试保存空指标数据: {code}")
                return False
            
            file_path = self.indicators_dir / f"{code}_indicators.csv"
            data.to_csv(file_path, encoding='utf-8')
            
            logger.info(f"成功保存指标数据: {code}, {len(data)} 条记录")
            return True
            
        except Exception as e:
            logger.error(f"保存指标数据失败: {code}, 错误: {str(e)}")
            return False
    
    def load_indicators(self, code: str) -> Optional[pd.DataFrame]:
        """
        加载技术指标数据
        
        Args:
            code: 股票代码
            
        Returns:
            Optional[pd.DataFrame]: 指标数据或None
        """
        try:
            file_path = self.indicators_dir / f"{code}_indicators.csv"
            
            if not file_path.exists():
                return None
            
            data = pd.read_csv(file_path, index_col=0, parse_dates=True)
            logger.info(f"成功加载指标数据: {code}, {len(data)} 条记录")
            return data
            
        except Exception as e:
            logger.error(f"加载指标数据失败: {code}, 错误: {str(e)}")
            return None
    
    def save_signals(self, signals: Dict[str, Any], date: str) -> bool:
        """
        保存交易信号
        
        Args:
            signals: 信号数据
            date: 信号日期
            
        Returns:
            bool: 是否保存成功
        """
        try:
            # 按年份组织目录
            year = date[:4]
            year_dir = self.signals_dir / year
            year_dir.mkdir(exist_ok=True)
            
            file_path = year_dir / f"signals_{date}.json"
            
            with open(file_path, 'w', encoding='utf-8') as f:
                json.dump(signals, f, ensure_ascii=False, indent=2, default=str)
            
            logger.info(f"成功保存信号数据: {date}")
            return True
            
        except Exception as e:
            logger.error(f"保存信号数据失败: {date}, 错误: {str(e)}")
            return False
    
    def load_signals(self, date: str) -> Optional[Dict[str, Any]]:
        """
        加载交易信号
        
        Args:
            date: 信号日期
            
        Returns:
            Optional[Dict[str, Any]]: 信号数据或None
        """
        try:
            year = date[:4]
            file_path = self.signals_dir / year / f"signals_{date}.json"
            
            if not file_path.exists():
                return None
            
            with open(file_path, 'r', encoding='utf-8') as f:
                signals = json.load(f)
            
            logger.info(f"成功加载信号数据: {date}")
            return signals
            
        except Exception as e:
            logger.error(f"加载信号数据失败: {date}, 错误: {str(e)}")
            return None
    
    def save_backtest_result(self, result: Dict[str, Any], start_date: str, end_date: str) -> bool:
        """
        保存回测结果
        
        Args:
            result: 回测结果
            start_date: 回测开始日期
            end_date: 回测结束日期
            
        Returns:
            bool: 是否保存成功
        """
        try:
            filename = f"backtest_{start_date}_{end_date}.json"
            file_path = self.backtest_dir / filename
            
            with open(file_path, 'w', encoding='utf-8') as f:
                json.dump(result, f, ensure_ascii=False, indent=2, default=str)
            
            logger.info(f"成功保存回测结果: {filename}")
            return True
            
        except Exception as e:
            logger.error(f"保存回测结果失败: {start_date}-{end_date}, 错误: {str(e)}")
            return False
    
    def clear_cache(self, older_than_days: int = 30) -> int:
        """
        清理过期缓存
        
        Args:
            older_than_days: 清理多少天前的缓存
            
        Returns:
            int: 清理的文件数量
        """
        try:
            cutoff_time = datetime.now() - timedelta(days=older_than_days)
            cleared_count = 0
            
            # 清理股票数据缓存
            for period_dir in ['daily', 'weekly', 'monthly']:
                period_path = self.stock_data_dir / period_dir
                if period_path.exists():
                    for file_path in period_path.glob('*.json'):  # 元数据文件
                        try:
                            with open(file_path, 'r', encoding='utf-8') as f:
                                metadata = json.load(f)
                            
                            save_time = datetime.fromisoformat(metadata['save_time'])
                            if save_time < cutoff_time:
                                # 删除数据文件和元数据文件
                                csv_file = file_path.with_suffix('.csv')
                                if csv_file.exists():
                                    csv_file.unlink()
                                file_path.unlink()
                                cleared_count += 2
                                
                        except Exception as e:
                            logger.warning(f"清理缓存文件失败: {file_path}, 错误: {str(e)}")
            
            logger.info(f"清理缓存完成，删除 {cleared_count} 个文件")
            return cleared_count
            
        except Exception as e:
            logger.error(f"清理缓存失败: {str(e)}")
            return 0
    
    def get_cache_statistics(self) -> Dict[str, Any]:
        """
        获取缓存统计信息
        
        Returns:
            Dict[str, Any]: 缓存统计信息
        """
        try:
            stats = {
                'stock_data': {},
                'indicators': 0,
                'signals': 0,
                'backtest': 0,
                'total_size_mb': 0
            }
            
            # 统计股票数据
            for period in ['daily', 'weekly', 'monthly']:
                period_path = self.stock_data_dir / period
                if period_path.exists():
                    csv_files = list(period_path.glob('*.csv'))
                    stats['stock_data'][period] = len(csv_files)
            
            # 统计指标数据
            if self.indicators_dir.exists():
                stats['indicators'] = len(list(self.indicators_dir.glob('*.csv')))
            
            # 统计信号数据
            if self.signals_dir.exists():
                signal_files = 0
                for year_dir in self.signals_dir.iterdir():
                    if year_dir.is_dir():
                        signal_files += len(list(year_dir.glob('*.json')))
                stats['signals'] = signal_files
            
            # 统计回测数据
            if self.backtest_dir.exists():
                stats['backtest'] = len(list(self.backtest_dir.glob('*.json')))
            
            # 计算总大小
            total_size = 0
            for root, dirs, files in os.walk(self.cache_dir):
                for file in files:
                    file_path = os.path.join(root, file)
                    if os.path.exists(file_path):
                        total_size += os.path.getsize(file_path)
            
            stats['total_size_mb'] = round(total_size / (1024 * 1024), 2)
            
            return stats
            
        except Exception as e:
            logger.error(f"获取缓存统计信息失败: {str(e)}")
            return {'error': str(e)}
    
    def _get_stock_data_path(self, code: str, period: str) -> Path:
        """
        获取股票数据文件路径
        
        Args:
            code: 股票代码
            period: 数据周期
            
        Returns:
            Path: 文件路径
        """
        return self.stock_data_dir / period / f"{code}.csv"

if __name__ == "__main__":
    # 测试代码
    logging.basicConfig(level=logging.INFO)
    
    storage = DataStorage()
    
    # 创建测试数据
    import pandas as pd
    import numpy as np
    
    dates = pd.date_range('2023-01-01', '2023-12-31', freq='W')
    test_data = pd.DataFrame({
        'open': np.random.uniform(10, 20, len(dates)),
        'high': np.random.uniform(15, 25, len(dates)),
        'low': np.random.uniform(5, 15, len(dates)),
        'close': np.random.uniform(10, 20, len(dates)),
        'volume': np.random.randint(1000, 10000, len(dates))
    }, index=dates)
    
    # 测试保存和加载数据
    code = '601088'
    period = 'weekly'
    
    print("测试数据存储功能...")
    
    # 保存数据
    success = storage.save_data(test_data, code, period)
    print(f"保存数据: {'成功' if success else '失败'}")
    
    # 检查数据新鲜度
    is_fresh = storage.is_data_fresh(code, period)
    print(f"数据新鲜度: {'新鲜' if is_fresh else '过期'}")
    
    # 加载数据
    loaded_data = storage.load_data(code, period)
    print(f"加载数据: {'成功' if loaded_data is not None else '失败'}")
    if loaded_data is not None:
        print(f"加载的数据记录数: {len(loaded_data)}")
    
    # 获取缓存信息
    info = storage.get_cached_data_info(code, period)
    print(f"缓存信息: {info}")
    
    # 获取缓存统计
    stats = storage.get_cache_statistics()
    print(f"缓存统计: {stats}")