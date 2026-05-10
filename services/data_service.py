"""
数据服务
负责所有数据获取、缓存、处理和技术指标计算
"""

from datetime import datetime, timedelta
from typing import Any, Dict, Optional

import pandas as pd

from config.path_manager import get_path_manager
from data.data_fetcher import DataFetcherFactory
from data.data_processor import DataProcessor
from data.data_storage import DataStorage
from pipelines import DataPipeline, DataValidator, DataNormalizer

from .base_service import BaseService


class DataService(BaseService):
    """
    数据服务 - 统一的数据访问层
    
    职责：
    1. 股票数据获取（网络/缓存）
    2. 数据缓存管理
    3. 数据预处理
    4. 技术指标计算
    5. DCF估值数据加载
    6. RSI阈值数据加载
    7. 股票-行业映射加载
    """
    
    def __init__(self, config: Dict[str, Any]):
        """
        初始化数据服务
        
        Args:
            config: 配置字典
        """
        super().__init__(config)
        
        # 初始化组件
        self.data_fetcher = None
        self.data_processor = DataProcessor()
        self.data_storage = DataStorage()
        
        # 创建数据处理管道
        self.data_pipeline = (DataPipeline()
            .add_step(DataValidator())
            .add_step(DataNormalizer(fill_method='ffill', remove_duplicates=True))
        )
        self.logger.info(f"📊 数据管道已创建: {self.data_pipeline.get_steps()}")
        
        # 数据缓存
        self.stock_data: Dict[str, Dict[str, pd.DataFrame]] = {}
        self.dcf_values: Dict[str, float] = {}
        self.rsi_thresholds: Dict[str, Dict[str, float]] = {}
        self.stock_industry_map: Dict[str, Dict[str, str]] = {}
        
        # 配置参数
        self.start_date = config.get('start_date', '2022-01-01')
        self.end_date = config.get('end_date', '2024-12-31')
        
        # 从initial_holdings提取股票池（排除现金）
        initial_holdings = config.get('initial_holdings', {})
        self.stock_pool = [code for code in initial_holdings.keys() if code.lower() != 'cash']
        
        # 如果stock_pool为空，尝试从其他配置中获取
        if not self.stock_pool:
            self.logger.warning("从initial_holdings中未找到股票，尝试其他配置源...")
            # 可以从其他地方获取股票池
    
    def initialize(self) -> bool:
        """
        初始化数据服务
        
        Returns:
            bool: 初始化是否成功
        """
        try:
            # 创建数据获取器
            data_source = self.config.get('data_source', 'akshare')
            self.data_fetcher = DataFetcherFactory.create_fetcher(data_source, self.config)
            
            # 加载配置数据
            self.dcf_values = self.load_dcf_values()
            self.rsi_thresholds = self.load_rsi_thresholds()
            self.stock_industry_map = self.load_stock_industry_map()
            
            self._initialized = True
            self.logger.info("DataService 初始化成功")
            return True
        except Exception as e:
            self.logger.error(f"DataService 初始化失败: {e}")
            return False
    
    def prepare_backtest_data(self) -> bool:
        """
        准备回测数据（智能缓存版本）
        
        Returns:
            bool: 数据准备是否成功
        """
        try:
            self.logger.info("🚀 开始准备回测数据（智能缓存模式）...")
            
            # 计算扩展的开始日期
            start_date_obj = datetime.strptime(self.start_date, '%Y-%m-%d')
            total_history_weeks = 125 + 14  # 125周技术指标 + 14周RSI预热
            extended_start_date = start_date_obj - timedelta(weeks=total_history_weeks)
            extended_start_date_str = extended_start_date.strftime('%Y-%m-%d')
            
            self.logger.info(f"📅 回测期间: {self.start_date} 至 {self.end_date}")
            self.logger.info(f"📅 数据获取期间（含139周历史缓冲）: {extended_start_date_str} 至 {self.end_date}")
            
            # 显示缓存统计
            cache_stats = self.data_storage.get_cache_statistics()
            self.logger.info(f"📊 当前缓存统计: {cache_stats}")
            
            for stock_code in self.stock_pool:
                self.logger.info(f"📈 准备 {stock_code} 的历史数据...")
                
                # 1. 获取日线数据
                daily_data = self._get_cached_or_fetch_data(
                    stock_code, extended_start_date_str, self.end_date, 'daily'
                )
                
                if daily_data is None or daily_data.empty:
                    self.logger.warning(f"⚠️ {stock_code} 初次获取数据为空，尝试智能扩展日期范围")
                    daily_data = self._get_data_with_smart_expansion(
                        stock_code, extended_start_date_str, self.end_date, 'daily'
                    )
                    
                    if daily_data is None or daily_data.empty:
                        self.logger.warning(f"⚠️ {stock_code} 扩展获取后仍无数据，跳过该股票")
                        continue
                    else:
                        self.logger.info(f"✅ {stock_code} 通过智能扩展成功获取到 {len(daily_data)} 条数据")
                
                # 2. 获取或生成周线数据
                weekly_data = self._get_or_generate_weekly_data(
                    stock_code, daily_data, extended_start_date_str
                )
                
                if weekly_data is None or weekly_data.empty:
                    self.logger.warning(f"⚠️ {stock_code} 周线数据生成失败，跳过该股票")
                    continue
                
                # 3. 计算技术指标
                weekly_data = self._ensure_technical_indicators(stock_code, weekly_data)

                # 验证技术指标计算是否成功
                actual_start_date = pd.to_datetime(self.start_date)
                weekly_backtest_data = weekly_data[weekly_data.index >= actual_start_date]
                if 'rsi' not in weekly_backtest_data.columns:
                    self.logger.warning(f"⚠️ {stock_code} 技术指标计算失败（缺少RSI列），跳过该股票")
                    continue

                # 4. 获取分红配股数据
                weekly_data = self._process_dividend_data(
                    stock_code, weekly_data, extended_start_date_str
                )

                # 5. 存储数据
                self.stock_data[stock_code] = {
                    'daily': daily_data,
                    'weekly': weekly_data
                }

                # 显示统计信息
                self.logger.info(f"✅ {stock_code} 数据准备完成:")
                self.logger.info(f"   - 日线数据: {len(daily_data)} 条")
                self.logger.info(f"   - 周线数据: {len(weekly_data)} 条 (回测期 {len(weekly_backtest_data)} 条)")

                # RSI统计
                rsi_valid = weekly_backtest_data['rsi'].notna().sum()
                rsi_nan = weekly_backtest_data['rsi'].isna().sum()
                self.logger.info(f"   - RSI: {rsi_valid} 有效值, {rsi_nan} NaN值")
            
            self.logger.info(f"✅ 数据准备完成，共 {len(self.stock_data)} 只股票")
            return True
            
        except Exception as e:
            self.logger.error(f"❌ 数据准备失败: {e}")
            import traceback
            self.logger.error(traceback.format_exc())
            return False
    
    def get_stock_data(self, stock_code: str, freq: str = 'weekly') -> Optional[pd.DataFrame]:
        """
        获取股票数据
        
        Args:
            stock_code: 股票代码
            freq: 频率 ('daily' 或 'weekly')
            
        Returns:
            股票数据DataFrame，如果不存在返回None
        """
        if stock_code not in self.stock_data:
            return None
        return self.stock_data[stock_code].get(freq)
    
    def get_all_stock_data(self, freq: str = 'weekly') -> Dict[str, pd.DataFrame]:
        """
        获取所有股票的数据
        
        Args:
            freq: 频率 ('daily' 或 'weekly')
            
        Returns:
            股票代码到数据的映射
        """
        return {code: data[freq] for code, data in self.stock_data.items() if freq in data}
    
    def load_dcf_values(self) -> Dict[str, float]:
        """
        从CSV配置文件加载DCF估值数据
        
        Returns:
            股票代码到DCF估值的映射
        """
        try:
            path_manager = get_path_manager()
            portfolio_config_path = path_manager.get_portfolio_config_path()
            
            df = pd.read_csv(portfolio_config_path, encoding='utf-8-sig')
            dcf_values = {}
            
            for _, row in df.iterrows():
                stock_code = row['Stock_number']
                if stock_code != 'CASH':
                    dcf_value = row.get('DCF_value_per_share', None)
                    if dcf_value is not None and pd.notna(dcf_value):
                        dcf_values[stock_code] = float(dcf_value)
            
            self.logger.info(f"✅ 成功加载 {len(dcf_values)} 只股票的DCF估值")
            return dcf_values
        except Exception as e:
            self.logger.warning(f"DCF估值数据加载失败: {e}")
            return {}
    
    def load_rsi_thresholds(self) -> Dict[str, Dict[str, float]]:
        """
        从CSV文件加载申万二级行业RSI阈值数据
        
        Returns:
            行业代码到RSI阈值的映射
        """
        try:
            import os
            
            rsi_file_path = 'sw_rsi_thresholds/output/sw2_rsi_threshold.csv'
            
            if not os.path.exists(rsi_file_path):
                self.logger.warning(f"RSI阈值文件不存在: {rsi_file_path}")
                return {}
            
            df = pd.read_csv(rsi_file_path, encoding='utf-8-sig')
            rsi_thresholds = {}
            
            for _, row in df.iterrows():
                industry_code = str(row['行业代码']).strip()
                rsi_thresholds[industry_code] = {
                    'industry_name': row.get('行业名称', ''),
                    'buy_threshold': float(row.get('普通超卖', 30)),
                    'sell_threshold': float(row.get('普通超买', 70)),
                    'extreme_buy_threshold': float(row.get('极端超卖', 20)),
                    'extreme_sell_threshold': float(row.get('极端超买', 80)),
                    'volatility_level': row.get('layer', 'medium'),
                    'volatility': float(row.get('volatility', 0)),
                    'current_rsi': float(row.get('current_rsi', 50))
                }
            
            self.logger.info(f"✅ 成功加载 {len(rsi_thresholds)} 个行业的RSI阈值")
            return rsi_thresholds
            
        except Exception as e:
            self.logger.warning(f"RSI阈值数据加载失败: {e}")
            return {}
    
    def load_stock_industry_map(self) -> Dict[str, Dict[str, str]]:
        """
        从JSON文件加载股票-行业映射数据
        
        Returns:
            股票代码到行业信息的映射
        """
        try:
            import json
            import os
            
            map_file_path = 'utils/stock_to_industry_map.json'
            
            if not os.path.exists(map_file_path):
                self.logger.warning(f"股票-行业映射文件不存在: {map_file_path}")
                return {}
            
            with open(map_file_path, 'r', encoding='utf-8') as f:
                cache_data = json.load(f)
            
            # 提取mapping字段
            if 'mapping' not in cache_data:
                self.logger.warning("映射文件格式不正确，缺少mapping字段")
                return {}
            
            stock_industry_map = cache_data['mapping']
            metadata = cache_data.get('metadata', {})
            
            self.logger.info(f"✅ 成功加载 {len(stock_industry_map)} 只股票的行业映射")
            self.logger.info(f"📊 映射数据版本: {metadata.get('version', '未知')}")
            self.logger.info(f"🕐 生成时间: {metadata.get('generated_at', '未知')}")
            
            return stock_industry_map
            
        except Exception as e:
            self.logger.warning(f"股票-行业映射加载失败: {e}")
            return {}
    
    def _get_cached_or_fetch_data(self, stock_code: str, start_date: str, 
                                   end_date: str, freq: str) -> Optional[pd.DataFrame]:
        """
        智能获取数据（优先缓存，缓存失败则网络获取）
        
        Args:
            stock_code: 股票代码
            start_date: 开始日期
            end_date: 结束日期
            freq: 频率
            
        Returns:
            股票数据DataFrame
        """
        try:
            # 1. 尝试从缓存加载
            cached_data = self.data_storage.load_data(stock_code, freq)
            
            if cached_data is not None and not cached_data.empty:
                # 检查缓存数据是否覆盖所需日期范围
                cache_start = cached_data.index.min()
                cache_end = cached_data.index.max()
                required_start = pd.to_datetime(start_date)
                required_end = pd.to_datetime(end_date)
                
                if cache_start <= required_start and cache_end >= required_end:
                    self.logger.info(f"✅ {stock_code} 从缓存加载{freq}数据")
                    return cached_data[(cached_data.index >= required_start) & 
                                      (cached_data.index <= required_end)]
            
            # 2. 缓存不可用，从网络获取
            self.logger.info(f"🌐 {stock_code} 从网络获取{freq}数据")
            data = self.data_fetcher.get_stock_data(stock_code, start_date, end_date, freq)
            
            if data is not None and not data.empty:
                # 保存到缓存
                self.data_storage.save_data(data, stock_code, freq)
                self.logger.info(f"💾 {stock_code} {freq}数据已保存到缓存")
                return data
            
            return None
            
        except Exception as e:
            self.logger.error(f"❌ {stock_code} 数据获取失败: {e}")
            return None
    
    def _get_data_with_smart_expansion(self, stock_code: str, start_date: str,
                                       end_date: str, freq: str) -> Optional[pd.DataFrame]:
        """
        智能扩展日期范围获取数据
        
        Args:
            stock_code: 股票代码
            start_date: 开始日期
            end_date: 结束日期
            freq: 频率
            
        Returns:
            股票数据DataFrame
        """
        try:
            # 向前扩展30天
            extended_start = (pd.to_datetime(start_date) - pd.Timedelta(days=30)).strftime('%Y-%m-%d')
            # 向后扩展30天
            extended_end = (pd.to_datetime(end_date) + pd.Timedelta(days=30)).strftime('%Y-%m-%d')
            
            self.logger.info(f"🔄 {stock_code} 扩展日期范围: {extended_start} 至 {extended_end}")
            
            data = self.data_fetcher.get_stock_data(stock_code, extended_start, extended_end, freq)
            
            if data is not None and not data.empty:
                # 裁剪回原始日期范围
                original_start = pd.to_datetime(start_date)
                original_end = pd.to_datetime(end_date)
                data = data[(data.index >= original_start) & (data.index <= original_end)]
                
                # 保存到缓存
                if not data.empty:
                    self.data_storage.save_data(data, stock_code, freq)
                
                return data
            
            return None
            
        except Exception as e:
            self.logger.error(f"❌ {stock_code} 智能扩展获取失败: {e}")
            return None
    
    def _get_or_generate_weekly_data(self, stock_code: str, daily_data: pd.DataFrame,
                                     extended_start_date: str) -> Optional[pd.DataFrame]:
        """
        获取或生成周线数据
        
        Args:
            stock_code: 股票代码
            daily_data: 日线数据
            extended_start_date: 扩展开始日期
            
        Returns:
            周线数据DataFrame
        """
        try:
            # 始终从日线数据转换周线，确保end_date参数被正确传递
            # 不使用缓存的周线数据，因为缓存可能不包含正确的end_date处理
            self.logger.info(f"🔄 {stock_code} 从日线数据转换周线数据")
            weekly_data = self.data_processor.resample_to_weekly(daily_data, end_date=self.end_date)
            
            if len(weekly_data) < 139:
                self.logger.warning(f"⚠️ {stock_code} 数据不足，只有 {len(weekly_data)} 条记录，建议139条")
            
            return weekly_data
            
        except Exception as e:
            self.logger.error(f"❌ {stock_code} 周线数据获取失败: {e}")
            return None
    
    def _ensure_technical_indicators(self, stock_code: str, 
                                     weekly_data: pd.DataFrame) -> pd.DataFrame:
        """
        确保技术指标存在且有效
        
        Args:
            stock_code: 股票代码
            weekly_data: 周线数据
            
        Returns:
            包含技术指标的周线数据
        """
        try:
            need_recalculate = False
            
            # 检查是否需要重新计算
            if 'ema_20' not in weekly_data.columns or 'rsi' not in weekly_data.columns:
                need_recalculate = True
                self.logger.info(f"🔧 {stock_code} 技术指标列不存在，需要计算")
            else:
                # 检查最新几行是否有NaN
                recent_data = weekly_data.tail(5)
                rsi_nan_count = recent_data['rsi'].isna().sum()
                macd_nan_count = recent_data['macd'].isna().sum()
                
                if rsi_nan_count > 0 or macd_nan_count > 0:
                    need_recalculate = True
                    self.logger.info(f"🔧 {stock_code} 最新技术指标有NaN值，需要重新计算")
            
            if need_recalculate:
                # 确保有足够数据
                if len(weekly_data) < 30:
                    self.logger.warning(f"⚠️ {stock_code} 数据量不足 ({len(weekly_data)} < 30)")
                
                self.logger.info(f"🔧 {stock_code} 开始计算技术指标，数据量: {len(weekly_data)}")
                
                # 使用数据管道处理数据（验证和标准化）
                try:
                    weekly_data = self.data_pipeline.process(weekly_data)
                    self.logger.debug(f"✅ {stock_code} 数据管道处理完成")
                except Exception as e:
                    self.logger.warning(f"⚠️ {stock_code} 数据管道处理失败: {e}，使用原始数据")
                
                # 计算技术指标
                weekly_data = self.data_processor.calculate_technical_indicators(weekly_data)
                self.logger.info(f"✅ {stock_code} 技术指标计算完成")
                
                # 保存到缓存
                try:
                    self.data_storage.save_data(weekly_data, stock_code, 'weekly')
                    self.logger.info(f"💾 {stock_code} 周线数据（含技术指标）已保存到缓存")
                except Exception as e:
                    self.logger.warning(f"⚠️ {stock_code} 周线数据缓存保存失败: {e}")
            else:
                self.logger.info(f"✅ {stock_code} 技术指标已存在且有效，跳过计算")
            
            return weekly_data
            
        except Exception as e:
            self.logger.error(f"❌ {stock_code} 技术指标处理失败: {e}")
            return weekly_data
    
    def _process_dividend_data(self, stock_code: str, weekly_data: pd.DataFrame,
                               extended_start_date: str) -> pd.DataFrame:
        """
        处理分红配股数据
        
        Args:
            stock_code: 股票代码
            weekly_data: 周线数据
            extended_start_date: 扩展开始日期
            
        Returns:
            包含分红信息的周线数据
        """
        try:
            self.logger.info(f"💰 {stock_code} 获取分红配股数据...")
            dividend_data = self.data_fetcher.get_dividend_data(
                stock_code, extended_start_date, self.end_date
            )
            
            if not dividend_data.empty:
                self.logger.info(f"✅ {stock_code} 获取到 {len(dividend_data)} 条分红记录")
                weekly_data = self.data_fetcher.align_dividend_with_weekly_data(
                    weekly_data, dividend_data
                )
                self.logger.info(f"✅ {stock_code} 分红数据已对齐到周线数据")
                
                # 检查对齐后的分红事件
                dividend_weeks = weekly_data[weekly_data['dividend_amount'] > 0]
                if not dividend_weeks.empty:
                    self.logger.info(f"💰 {stock_code} 对齐到 {len(dividend_weeks)} 个分红事件")
                    for date, row in dividend_weeks.iterrows():
                        self.logger.info(f"  {date.strftime('%Y-%m-%d')}: 派息 {row['dividend_amount']}元")
            else:
                self.logger.info(f"⚠️ {stock_code} 未获取到分红数据")
            
            return weekly_data
            
        except Exception as e:
            self.logger.warning(f"⚠️ {stock_code} 分红数据获取失败: {e}")
            return weekly_data
    
    def get_dcf_value(self, stock_code: str) -> Optional[float]:
        """获取股票的DCF估值"""
        return self.dcf_values.get(stock_code)
    
    def get_rsi_thresholds(self, industry_code: str) -> Optional[Dict[str, float]]:
        """获取行业的RSI阈值"""
        return self.rsi_thresholds.get(industry_code)
    
    def get_stock_industry(self, stock_code: str) -> Optional[Dict[str, str]]:
        """获取股票的行业信息"""
        return self.stock_industry_map.get(stock_code)
