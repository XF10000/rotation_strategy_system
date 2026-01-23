"""
数据获取器模块
支持从不同数据源获取股票数据
"""

import logging
from abc import ABC, abstractmethod
from datetime import datetime, timedelta
from typing import Dict, List

import akshare as ak
import pandas as pd

try:
    import tushare as ts
    TUSHARE_AVAILABLE = True
except ImportError:
    TUSHARE_AVAILABLE = False
    ts = None

from .exceptions import DataFetchError

logger = logging.getLogger(__name__)

class DataFetcher(ABC):
    """数据获取器基类"""
    
    @abstractmethod
    def get_stock_data(self, code: str, start_date: str, end_date: str = None, 
                      period: str = 'weekly') -> pd.DataFrame:
        """
        获取股票历史数据
        
        Args:
            code: 股票代码 (如 '601088')
            start_date: 开始日期 ('YYYY-MM-DD')
            end_date: 结束日期 ('YYYY-MM-DD', None表示当前日期)
            period: 数据周期 ('daily', 'weekly', 'monthly')
            
        Returns:
            pd.DataFrame: 标准化的股票数据
            
        Raises:
            DataFetchError: 数据获取失败
        """
    
    def get_multiple_stocks_data(self, codes: List[str], start_date: str, 
                               end_date: str = None, period: str = 'weekly') -> Dict[str, pd.DataFrame]:
        """
        批量获取多只股票数据
        
        Args:
            codes: 股票代码列表
            start_date: 开始日期
            end_date: 结束日期
            period: 数据周期
            
        Returns:
            Dict[str, pd.DataFrame]: 股票代码到数据的映射
        """
        result = {}
        failed_codes = []
        
        for code in codes:
            try:
                logger.info(f"获取股票 {code} 的数据...")
                data = self.get_stock_data(code, start_date, end_date, period)
                result[code] = data
                logger.info(f"成功获取股票 {code} 的数据，共 {len(data)} 条记录")
            except Exception as e:
                logger.error(f"获取股票 {code} 数据失败: {str(e)}")
                failed_codes.append(code)
        
        if failed_codes:
            logger.warning(f"以下股票数据获取失败: {failed_codes}")
        
        return result

class AkshareDataFetcher(DataFetcher):
    """Akshare数据获取器实现"""
    
    def __init__(self):
        """初始化Akshare数据获取器"""
        self.source_name = "akshare"
        self.last_request_time = None  # 记录上次请求时间
        self.min_request_interval = 3.0  # 最小请求间隔（秒）- 增加到3秒以避免连接中断
        logger.info("初始化Akshare数据获取器")
    
    def get_stock_data(self, code: str, start_date: str, end_date: str = None, 
                      period: str = 'weekly') -> pd.DataFrame:
        """
        从Akshare获取股票历史数据
        
        Args:
            code: 股票代码 (如 '601088')
            start_date: 开始日期 ('YYYY-MM-DD')
            end_date: 结束日期 ('YYYY-MM-DD', None表示当前日期)
            period: 数据周期 ('daily', 'weekly', 'monthly')
            
        Returns:
            pd.DataFrame: 标准化的股票数据
            
        Raises:
            DataFetchError: 数据获取失败
        """
        try:
            # 参数验证
            if not self._validate_stock_code(code):
                raise DataFetchError(f"无效的股票代码: {code}")
            
            if not self._validate_date_format(start_date):
                raise DataFetchError(f"无效的开始日期格式: {start_date}")
            
            if end_date and not self._validate_date_format(end_date):
                raise DataFetchError(f"无效的结束日期格式: {end_date}")
            
            # 设置默认结束日期
            if end_date is None:
                end_date = datetime.now().strftime('%Y%m%d')
            else:
                # 正确处理日期格式，支持缺少前导零的情况
                try:
                    parsed_end_date = datetime.strptime(end_date, '%Y-%m-%d')
                    end_date = parsed_end_date.strftime('%Y%m%d')
                except ValueError:
                    # 如果解析失败，尝试处理缺少前导零的情况
                    parts = end_date.split('-')
                    if len(parts) == 3:
                        year, month, day = parts
                        month = month.zfill(2)
                        day = day.zfill(2)
                        fixed_date = f'{year}-{month}-{day}'
                        parsed_end_date = datetime.strptime(fixed_date, '%Y-%m-%d')
                        end_date = parsed_end_date.strftime('%Y%m%d')
                    else:
                        raise DataFetchError(f"无法解析结束日期格式: {end_date}")
            
            # 正确处理开始日期格式
            try:
                parsed_start_date = datetime.strptime(start_date, '%Y-%m-%d')
                start_date = parsed_start_date.strftime('%Y%m%d')
            except ValueError:
                # 如果解析失败，尝试处理缺少前导零的情况
                parts = start_date.split('-')
                if len(parts) == 3:
                    year, month, day = parts
                    month = month.zfill(2)
                    day = day.zfill(2)
                    fixed_date = f'{year}-{month}-{day}'
                    parsed_start_date = datetime.strptime(fixed_date, '%Y-%m-%d')
                    start_date = parsed_start_date.strftime('%Y%m%d')
                else:
                    raise DataFetchError(f"无法解析开始日期格式: {start_date}")
            
            # 映射周期参数
            period_map = {
                'daily': 'daily',
                'weekly': 'weekly', 
                'monthly': 'monthly'
            }
            
            if period not in period_map:
                raise DataFetchError(f"不支持的数据周期: {period}")
            
            ak_period = period_map[period]
            
            logger.debug(f"从Akshare获取数据: {code}, {start_date}-{end_date}, {ak_period}")
            
            # 调用akshare接口获取数据，增加重试机制
            max_retries = 5  # 增加重试次数
            df = None
            
            for attempt in range(max_retries):
                try:
                    import time

                    # 控制请求频率，避免触发反爬虫
                    if self.last_request_time is not None:
                        elapsed = time.time() - self.last_request_time
                        if elapsed < self.min_request_interval:
                            sleep_time = self.min_request_interval - elapsed
                            logger.debug(f"请求间隔控制：等待 {sleep_time:.2f} 秒")
                            time.sleep(sleep_time)
                    
                    # 重试时增加额外延迟
                    if attempt > 0:
                        wait_time = 5 + attempt * 5  # 增加重试等待时间: 5, 10, 15, 20...
                        logger.debug(f"重试等待: {wait_time}秒")
                        time.sleep(wait_time)
                    
                    # 更新请求时间
                    self.last_request_time = time.time()
                    
                    logger.debug(f"尝试获取股票 {code} 数据，第 {attempt + 1} 次")
                    
                    # 尝试不同的获取方式
                    if attempt < 3:
                        # 前3次使用标准方式
                        df = ak.stock_zh_a_hist(
                            symbol=code,
                            period=ak_period,
                            start_date=start_date,
                            end_date=end_date,
                            adjust=""  # 不复权数据
                        )
                    else:
                        # 后续尝试使用不同参数
                        df = ak.stock_zh_a_hist(
                            symbol=code,
                            period="daily",  # 改用日线数据
                            start_date=start_date,
                            end_date=end_date,
                            adjust=""  # 不复权数据
                        )
                    
                    if df is not None and not df.empty:
                        logger.debug(f"成功获取股票 {code} 数据，共 {len(df)} 条记录")
                        break
                    else:
                        logger.warning(f"第 {attempt + 1} 次尝试获取股票 {code} 数据为空")
                        
                except Exception as e:
                    logger.warning(f"第 {attempt + 1} 次尝试获取股票 {code} 数据失败: {str(e)}")
                    # 检测是否为连接中断错误
                    is_connection_error = "RemoteDisconnected" in str(e) or "Connection aborted" in str(e)
                    
                    if attempt < max_retries - 1:
                        # 如果是连接错误，等待更长时间
                        base_wait = 10 if is_connection_error else 3
                        sleep_time = base_wait + attempt * 5
                        logger.warning(f"等待 {sleep_time} 秒后重试...")
                        time.sleep(sleep_time)
                    else:
                        # 最后一次尝试，记录详细错误信息
                        logger.error(f"所有重试均失败，股票 {code} 可能暂时无法获取数据")
            
            if df is None or df.empty:
                raise DataFetchError(f"未获取到股票 {code} 的数据")
            
            # 标准化数据格式
            df = self._standardize_data_format(df)
            
            logger.debug(f"成功获取股票 {code} 数据，共 {len(df)} 条记录")
            return df
            
        except Exception as e:
            error_msg = f"获取股票 {code} 数据失败: {str(e)}"
            logger.error(error_msg)
            raise DataFetchError(error_msg) from e
    
    def _standardize_data_format(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        标准化数据格式
        
        Args:
            df: 原始akshare数据
            
        Returns:
            pd.DataFrame: 标准化后的数据
        """
        try:
            # 重命名列名为英文标准格式
            column_mapping = {
                '日期': 'date',
                '开盘': 'open',
                '收盘': 'close', 
                '最高': 'high',
                '最低': 'low',
                '成交量': 'volume',
                '成交额': 'amount',
                '振幅': 'amplitude',
                '涨跌幅': 'pct_change',
                '涨跌额': 'change',
                '换手率': 'turnover_rate'
            }
            
            # 重命名存在的列
            existing_columns = {k: v for k, v in column_mapping.items() if k in df.columns}
            df = df.rename(columns=existing_columns)
            
            # 确保必要的列存在
            required_columns = ['date', 'open', 'high', 'low', 'close', 'volume']
            missing_columns = [col for col in required_columns if col not in df.columns]
            
            if missing_columns:
                raise DataFetchError(f"缺少必要的数据列: {missing_columns}")
            
            # 转换日期格式
            df['date'] = pd.to_datetime(df['date'])
            
            # 设置日期为索引
            df = df.set_index('date')
            
            # 确保数值列为float类型
            numeric_columns = ['open', 'high', 'low', 'close', 'volume']
            if 'amount' in df.columns:
                numeric_columns.append('amount')
            if 'turnover_rate' in df.columns:
                numeric_columns.append('turnover_rate')
            
            for col in numeric_columns:
                if col in df.columns:
                    df[col] = pd.to_numeric(df[col], errors='coerce')
            
            # 按日期排序
            df = df.sort_index()
            
            # 选择需要的列
            output_columns = ['open', 'high', 'low', 'close', 'volume']
            if 'amount' in df.columns:
                output_columns.append('amount')
            if 'turnover_rate' in df.columns:
                output_columns.append('turnover_rate')
            
            df = df[output_columns]
            
            return df
            
        except Exception as e:
            raise DataFetchError(f"数据格式标准化失败: {str(e)}") from e
    
    def _validate_stock_code(self, code: str) -> bool:
        """
        验证股票代码格式
        
        Args:
            code: 股票代码
            
        Returns:
            bool: 是否有效
        """
        if not code or not isinstance(code, str):
            return False
        
        # 简单验证：6位数字
        return len(code) == 6 and code.isdigit()
    
    def _validate_date_format(self, date_str: str) -> bool:
        """
        验证日期格式
        
        Args:
            date_str: 日期字符串
            
        Returns:
            bool: 是否有效
        """
        try:
            datetime.strptime(date_str, '%Y-%m-%d')
            return True
        except ValueError:
            return False
    
    def get_latest_trading_date(self) -> str:
        """
        获取最新交易日期
        
        Returns:
            str: 最新交易日期 ('YYYY-MM-DD')
        """
        try:
            # 获取最近的交易日历
            today = datetime.now()
            
            # 简单实现：如果是周末，回退到周五
            weekday = today.weekday()
            if weekday == 5:  # 周六
                latest_date = today - timedelta(days=1)
            elif weekday == 6:  # 周日
                latest_date = today - timedelta(days=2)
            else:
                latest_date = today
            
            return latest_date.strftime('%Y-%m-%d')
            
        except Exception as e:
            logger.error(f"获取最新交易日期失败: {str(e)}")
            return datetime.now().strftime('%Y-%m-%d')
    
    def test_connection(self) -> bool:
        """
        测试数据源连接
        
        Returns:
            bool: 连接是否正常
        """
        try:
            # 尝试获取一只股票的少量数据来测试连接
            test_code = "000001"  # 平安银行
            end_date = datetime.now().strftime('%Y%m%d')
            start_date = (datetime.now() - timedelta(days=7)).strftime('%Y%m%d')
            
            df = ak.stock_zh_a_hist(
                symbol=test_code,
                period="daily",
                start_date=start_date,
                end_date=end_date,
                adjust="qfq"
            )
            
            return df is not None and not df.empty
            
        except Exception as e:
            logger.error(f"测试Akshare连接失败: {str(e)}")
            return False
    
    def get_dividend_data(self, code: str, start_date: str, end_date: str = None, 
                         use_cache: bool = True) -> pd.DataFrame:
        """
        获取股票分红配股数据（支持缓存）
        
        Args:
            code: 股票代码 (如 '601088')
            start_date: 开始日期 ('YYYY-MM-DD')
            end_date: 结束日期 ('YYYY-MM-DD', None表示当前日期)
            use_cache: 是否使用缓存
            
        Returns:
            pd.DataFrame: 分红配股数据
            
        Raises:
            DataFetchError: 数据获取失败
        """
        try:
            # 导入数据存储模块
            from .data_storage import DataStorage
            storage = DataStorage()
            
            # 如果启用缓存，先检查是否需要的日期范围已被缓存覆盖
            if use_cache:
                # 检查指定日期范围是否已被缓存完全覆盖
                if storage.is_dividend_date_range_cached(code, start_date or '1990-01-01', 
                                                       end_date or datetime.now().strftime('%Y-%m-%d')):
                    cached_data = storage.load_dividend_data(code)
                    if cached_data is not None:
                        logger.info(f"📦 使用分红配股缓存数据: {code}")
                        
                        # 按日期范围过滤缓存数据
                        filtered_data = cached_data.copy()
                        if start_date:
                            start_dt = pd.to_datetime(start_date)
                            filtered_data = filtered_data[filtered_data.index >= start_dt]
                        
                        if end_date:
                            end_dt = pd.to_datetime(end_date)
                            filtered_data = filtered_data[filtered_data.index <= end_dt]
                        
                        logger.info(f"✅ 缓存分红配股数据过滤后: {code}, {len(filtered_data)} 条记录")
                        return filtered_data
                else:
                    # 缓存范围不足，需要从网络获取
                    cache_coverage = storage.get_dividend_cache_coverage(code)
                    if cache_coverage:
                        logger.info(f"📊 {code} 缓存范围不足，需要网络获取")
                        logger.info(f"  缓存范围: {cache_coverage['start_date']} 到 {cache_coverage['end_date']}")
                        logger.info(f"  需要范围: {start_date or '1990-01-01'} 到 {end_date or datetime.now().strftime('%Y-%m-%d')}")
                    else:
                        logger.info(f"📊 {code} 无分红配股缓存，需要网络获取")
            
            # 缓存不存在或过期，从网络获取
            logger.info(f"🌐 从网络获取股票 {code} 的分红配股数据...")
            
            # 控制请求频率，避免触发反爬虫
            import time
            if self.last_request_time is not None:
                elapsed = time.time() - self.last_request_time
                if elapsed < self.min_request_interval:
                    sleep_time = self.min_request_interval - elapsed
                    logger.debug(f"请求间隔控制：等待 {sleep_time:.2f} 秒")
                    time.sleep(sleep_time)
            
            # 更新请求时间
            self.last_request_time = time.time()
            
            # 使用可用的akshare API
            dividend_data = ak.stock_history_dividend_detail(symbol=code)
            
            if dividend_data is None or dividend_data.empty:
                logger.warning(f"未获取到股票 {code} 的分红配股数据")
                # 即使是空数据也要缓存，避免重复请求
                if use_cache:
                    empty_df = pd.DataFrame()
                    storage.save_dividend_data(empty_df, code)
                return pd.DataFrame()
            
            logger.info(f"原始分红数据列名: {list(dividend_data.columns)}")
            logger.info(f"原始数据样例:\n{dividend_data.head(2)}")
            
            # 数据清洗和标准化
            processed_data = self._process_dividend_data(dividend_data)
            
            # 保存到缓存
            if use_cache and not processed_data.empty:
                storage.save_dividend_data(processed_data, code)
                logger.info(f"💾 分红配股数据已缓存: {code}")
            
            # 按日期范围过滤
            filtered_data = processed_data.copy()
            if start_date:
                start_dt = pd.to_datetime(start_date)
                filtered_data = filtered_data[filtered_data.index >= start_dt]
            
            if end_date:
                end_dt = pd.to_datetime(end_date)
                filtered_data = filtered_data[filtered_data.index <= end_dt]
            
            logger.info(f"成功获取股票 {code} 的分红配股数据，共 {len(filtered_data)} 条记录")
            return filtered_data
            
        except Exception as e:
            error_msg = f"获取股票 {code} 分红配股数据失败: {str(e)}"
            logger.warning(error_msg)
            # 返回空数据而不是抛出异常，以免影响整个回测
            return pd.DataFrame()
    
    def align_dividend_with_weekly_data(self, weekly_data: pd.DataFrame, 
                                      dividend_data: pd.DataFrame) -> pd.DataFrame:
        """
        将分红配股数据与周线数据对齐
        
        Args:
            weekly_data: 周线数据
            dividend_data: 分红配股数据
            
        Returns:
            pd.DataFrame: 对齐后的周线数据，包含分红配股信息
        """
        try:
            if dividend_data.empty:
                # 如果没有分红配股数据，添加空列
                weekly_data['dividend_amount'] = 0.0
                weekly_data['allotment_ratio'] = 0.0
                weekly_data['allotment_price'] = 0.0
                weekly_data['bonus_ratio'] = 0.0
                weekly_data['transfer_ratio'] = 0.0
                return weekly_data
            
            # 确保索引是日期类型
            weekly_data.index = pd.to_datetime(weekly_data.index)
            
            # 初始化分红配股列
            weekly_data['dividend_amount'] = 0.0
            weekly_data['allotment_ratio'] = 0.0
            weekly_data['allotment_price'] = 0.0
            weekly_data['bonus_ratio'] = 0.0
            weekly_data['transfer_ratio'] = 0.0
            
            # 将分红配股日期映射到对应的周线日期
            for ex_date, dividend_row in dividend_data.iterrows():
                try:
                    # ex_date 已经是索引，不需要从 dividend_row 中获取
                    
                    # 确保 ex_date 是 Timestamp 类型，并移除时区信息
                    if hasattr(ex_date, 'tz_localize'):
                        ex_date = ex_date.tz_localize(None) if ex_date.tz is not None else ex_date
                    else:
                        ex_date = pd.Timestamp(ex_date)
                    
                    # 找到最接近的周线日期（通常是当周或下周的周五）
                    # 找到除权除息日所在周的周五，如果除权日在周五之后，则映射到下周五
                    try:
                        weekday = ex_date.weekday()  # 0=Monday, 4=Friday
                        
                        if weekday <= 4:  # 周一到周五
                            # 映射到当周周五
                            days_to_friday = 4 - weekday
                            target_friday = ex_date + pd.Timedelta(days=days_to_friday)
                        else:  # 周六周日
                            # 映射到下周周五
                            days_to_next_friday = 4 + (7 - weekday)
                            target_friday = ex_date + pd.Timedelta(days=days_to_next_friday)
                    except Exception as date_calc_e:
                        # 如果计算target_friday失败，跳过这条分红记录
                        logger.debug(f"计算target_friday失败，跳过分红记录: ex_date={ex_date}")
                        continue
                    
                    # 找到最接近的周线数据日期
                    closest_date = None
                    min_diff = float('inf')
                    
                    for week_date in weekly_data.index:
                        try:
                            # 确保 week_date 也是 Timestamp 类型，并移除时区信息
                            if hasattr(week_date, 'tz_localize'):
                                week_date_normalized = week_date.tz_localize(None) if week_date.tz is not None else week_date
                            else:
                                week_date_normalized = pd.Timestamp(week_date)
                            
                            # 计算日期差异（使用total_seconds避免异常Timedelta的.days属性问题）
                            try:
                                time_diff = week_date_normalized - target_friday
                                # 使用total_seconds()转换为天数，更加稳定
                                diff_days = abs(time_diff.total_seconds() / 86400)  # 86400秒 = 1天
                            except (AttributeError, OverflowError, ValueError) as calc_e:
                                # 如果日期计算失败，跳过这个日期
                                continue
                            
                            if diff_days < min_diff:
                                min_diff = diff_days
                                closest_date = week_date
                        except Exception as inner_e:
                            logger.warning(f"计算日期差异失败，跳过此日期: week_date={week_date}, target_friday={target_friday}")
                            continue
                    
                    # 如果找到匹配的日期，更新分红配股信息
                    if closest_date is not None and min_diff <= 7:  # 允许7天内的误差
                        weekly_data.loc[closest_date, 'dividend_amount'] = dividend_row.get('dividend_amount', 0)
                        weekly_data.loc[closest_date, 'allotment_ratio'] = dividend_row.get('allotment_ratio', 0)
                        weekly_data.loc[closest_date, 'allotment_price'] = dividend_row.get('allotment_price', 0)
                        weekly_data.loc[closest_date, 'bonus_ratio'] = dividend_row.get('bonus_ratio', 0)
                        weekly_data.loc[closest_date, 'transfer_ratio'] = dividend_row.get('transfer_ratio', 0)
                        
                        logger.debug(f"分红配股信息已对齐: {ex_date.date()} -> {closest_date.date()}")
                except Exception as row_e:
                    # 将警告改为调试级别，避免大量警告信息
                    # 这些异常通常是由于日期计算问题导致的，不影响主要功能
                    logger.debug(f"处理分红记录失败 ex_date={ex_date}: {type(row_e).__name__}")
                    continue
            
            return weekly_data
            
        except Exception as e:
            logger.error(f"分红配股数据对齐失败: {str(e)}")
            # 返回原始数据，添加空的分红配股列
            weekly_data['dividend_amount'] = 0.0
            weekly_data['allotment_ratio'] = 0.0
            weekly_data['allotment_price'] = 0.0
            weekly_data['bonus_ratio'] = 0.0
            weekly_data['transfer_ratio'] = 0.0
            return weekly_data
    
    def _process_dividend_data(self, raw_data: pd.DataFrame) -> pd.DataFrame:
        """
        处理原始分红配股数据
        
        Args:
            raw_data: 原始分红数据
            
        Returns:
            pd.DataFrame: 处理后的分红数据，以除权日为索引
        """
        if raw_data is None or raw_data.empty:
            return pd.DataFrame()
        
        try:
            # 创建标准化的分红数据结构
            processed_data = pd.DataFrame()
            
            # 根据实际的列名进行映射和处理
            if '除权除息日' in raw_data.columns:
                processed_data['ex_date'] = pd.to_datetime(raw_data['除权除息日'])
            elif '除权日' in raw_data.columns:
                processed_data['ex_date'] = pd.to_datetime(raw_data['除权日'])
            elif 'ex_date' in raw_data.columns:
                processed_data['ex_date'] = pd.to_datetime(raw_data['ex_date'])
            else:
                logger.warning("未找到除权日列，使用第一列作为日期")
                processed_data['ex_date'] = pd.to_datetime(raw_data.iloc[:, 0])
            
            # 分红金额 (派息) - 注意：akshare返回的通常是每10股分红金额，需要除以10转换为每股金额
            if '派息' in raw_data.columns:
                processed_data['dividend_amount'] = pd.to_numeric(raw_data['派息'], errors='coerce').fillna(0) / 10.0
            elif '分红金额' in raw_data.columns:
                processed_data['dividend_amount'] = pd.to_numeric(raw_data['分红金额'], errors='coerce').fillna(0) / 10.0
            elif 'dividend' in raw_data.columns:
                processed_data['dividend_amount'] = pd.to_numeric(raw_data['dividend'], errors='coerce').fillna(0) / 10.0
            else:
                processed_data['dividend_amount'] = 0
            
            # 送股比例 - 注意：akshare返回的是每10股送X股，需要除以10转换为每股送股比例
            if '送股' in raw_data.columns:
                processed_data['bonus_ratio'] = pd.to_numeric(raw_data['送股'], errors='coerce').fillna(0) / 10.0
            elif '送股比例' in raw_data.columns:
                processed_data['bonus_ratio'] = pd.to_numeric(raw_data['送股比例'], errors='coerce').fillna(0) / 10.0
            elif 'bonus' in raw_data.columns:
                processed_data['bonus_ratio'] = pd.to_numeric(raw_data['bonus'], errors='coerce').fillna(0) / 10.0
            else:
                processed_data['bonus_ratio'] = 0
            
            # 转增比例 - 注意：akshare返回的是每10股转增X股，需要除以10转换为每股转增比例
            if '转增' in raw_data.columns:
                processed_data['transfer_ratio'] = pd.to_numeric(raw_data['转增'], errors='coerce').fillna(0) / 10.0
            elif '转增比例' in raw_data.columns:
                processed_data['transfer_ratio'] = pd.to_numeric(raw_data['转增比例'], errors='coerce').fillna(0) / 10.0
            elif 'transfer' in raw_data.columns:
                processed_data['transfer_ratio'] = pd.to_numeric(raw_data['transfer'], errors='coerce').fillna(0)
            else:
                processed_data['transfer_ratio'] = 0
            
            # 配股比例和价格 (暂时设为0，因为原始数据中没有这些字段)
            processed_data['allotment_ratio'] = 0
            processed_data['allotment_price'] = 0
            
            # 设置除权日为索引
            processed_data.set_index('ex_date', inplace=True)
            processed_data.sort_index(inplace=True)
            
            # 过滤掉所有值都为0的行
            mask = (processed_data['dividend_amount'] > 0) | \
                   (processed_data['bonus_ratio'] > 0) | \
                   (processed_data['transfer_ratio'] > 0) | \
                   (processed_data['allotment_ratio'] > 0)
            processed_data = processed_data[mask]
            
            logger.info(f"处理分红数据完成，有效记录数: {len(processed_data)}")
            return processed_data
            
        except Exception as e:
            logger.error(f"处理分红数据失败: {str(e)}")
            return pd.DataFrame()

class TushareDataFetcher(DataFetcher):
    """Tushare数据获取器实现"""
    
    def __init__(self, token: str):
        """
        初始化Tushare数据获取器
        
        Args:
            token: Tushare API Token
        """
        if not TUSHARE_AVAILABLE:
            raise DataFetchError("Tushare未安装，请运行: pip install tushare")
        
        if not token:
            raise DataFetchError("使用Tushare需要提供token")
        
        self.source_name = "tushare"
        self.token = token
        self.pro = ts.pro_api(token)
        self.last_request_time = None
        self.min_request_interval = 0.35  # 200次/分钟 = 每次间隔0.3秒，留0.05秒安全余量
        logger.info("初始化Tushare数据获取器")
    
    def _convert_stock_code(self, code: str) -> str:
        """
        转换股票代码格式: 601088 -> 601088.SH
        
        Args:
            code: 6位股票代码
            
        Returns:
            str: Tushare格式的股票代码
        """
        if code.startswith('6'):
            return f"{code}.SH"
        elif code.startswith('0') or code.startswith('3'):
            return f"{code}.SZ"
        else:
            raise ValueError(f"无法识别的股票代码: {code}")
    
    def _convert_date_format(self, date_str: str) -> str:
        """
        转换日期格式: 'YYYY-MM-DD' -> 'YYYYMMDD'
        
        Args:
            date_str: 日期字符串
            
        Returns:
            str: Tushare格式的日期
        """
        return date_str.replace('-', '')
    
    def get_stock_data(self, code: str, start_date: str, end_date: str = None, 
                      period: str = 'weekly') -> pd.DataFrame:
        """
        从Tushare获取股票历史数据
        
        Args:
            code: 股票代码 (如 '601088')
            start_date: 开始日期 ('YYYY-MM-DD')
            end_date: 结束日期 ('YYYY-MM-DD', None表示当前日期)
            period: 数据周期 ('daily', 'weekly', 'monthly')
            
        Returns:
            pd.DataFrame: 标准化的股票数据
            
        Raises:
            DataFetchError: 数据获取失败
        """
        try:
            # 参数验证
            if not code or len(code) != 6:
                raise DataFetchError(f"无效的股票代码: {code}")
            
            # 转换股票代码和日期格式
            ts_code = self._convert_stock_code(code)
            ts_start_date = self._convert_date_format(start_date)
            
            if end_date is None:
                end_date = datetime.now().strftime('%Y-%m-%d')
            ts_end_date = self._convert_date_format(end_date)
            
            logger.debug(f"从Tushare获取数据: {ts_code}, {ts_start_date}-{ts_end_date}")
            
            # 控制请求频率
            import time
            if self.last_request_time is not None:
                elapsed = time.time() - self.last_request_time
                if elapsed < self.min_request_interval:
                    sleep_time = self.min_request_interval - elapsed
                    logger.debug(f"请求间隔控制：等待 {sleep_time:.2f} 秒")
                    time.sleep(sleep_time)
            
            # 更新请求时间
            self.last_request_time = time.time()
            
            # Tushare只提供日线数据，周线需要从日线重采样
            # 调用daily接口获取日线数据（不复权）
            logger.debug(f"调用Tushare API: ts_code={ts_code}, start_date={ts_start_date}, end_date={ts_end_date}")
            df = self.pro.daily(
                ts_code=ts_code,
                start_date=ts_start_date,
                end_date=ts_end_date
            )
            
            logger.debug(f"Tushare API返回: df类型={type(df)}, 是否为None={df is None}, 是否为空={df.empty if df is not None else 'N/A'}")
            if df is not None and not df.empty:
                logger.debug(f"返回数据形状: {df.shape}, 列名: {list(df.columns)}")
            
            if df is None or df.empty:
                # 返回空DataFrame而不是抛出异常，让回测引擎的降级重试机制处理
                # 这种情况通常发生在请求非交易日或数据不存在时
                logger.warning(f"Tushare未返回股票 {code} 的数据（可能是非交易日或数据不存在）: {start_date} 到 {end_date}")
                return pd.DataFrame()
            
            logger.debug(f"成功获取股票 {code} 日线数据，共 {len(df)} 条记录")
            
            # 标准化数据格式
            df = self._standardize_data_format(df)
            
            # 如果需要周线数据，从日线重采样
            if period == 'weekly':
                from .data_processor import DataProcessor
                processor = DataProcessor()
                df = processor.resample_to_weekly(df)
                logger.debug(f"日线转周线完成，共 {len(df)} 条周线记录")
            elif period == 'monthly':
                from .data_processor import DataProcessor
                processor = DataProcessor()
                df = processor.resample_to_monthly(df)
                logger.debug(f"日线转月线完成，共 {len(df)} 条月线记录")
            
            logger.debug(f"成功获取股票 {code} 数据，共 {len(df)} 条记录")
            return df
            
        except Exception as e:
            error_msg = f"获取股票 {code} 数据失败: {str(e)}"
            logger.error(error_msg)
            raise DataFetchError(error_msg) from e
    
    def _standardize_data_format(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        标准化Tushare数据格式，确保与AkshareDataFetcher输出一致
        
        Args:
            df: 原始Tushare数据
            
        Returns:
            pd.DataFrame: 标准化后的数据
        """
        try:
            # Tushare列名映射
            column_mapping = {
                'trade_date': 'date',
                'open': 'open',
                'high': 'high',
                'low': 'low',
                'close': 'close',
                'vol': 'volume',      # 成交量（手）
                'amount': 'amount'    # 成交额（千元）
            }
            
            # 重命名列
            df = df.rename(columns=column_mapping)
            
            # 转换日期格式: YYYYMMDD -> datetime
            df['date'] = pd.to_datetime(df['date'], format='%Y%m%d')
            
            # 设置日期为索引
            df = df.set_index('date')
            
            # 单位转换
            # Tushare成交量单位是手（1手=100股），需要转换为股
            df['volume'] = df['volume'] * 100
            
            # Tushare成交额单位是千元，需要转换为元
            if 'amount' in df.columns:
                df['amount'] = df['amount'] * 1000
            
            # 确保数值列为float类型
            numeric_columns = ['open', 'high', 'low', 'close', 'volume']
            if 'amount' in df.columns:
                numeric_columns.append('amount')
            
            for col in numeric_columns:
                if col in df.columns:
                    df[col] = pd.to_numeric(df[col], errors='coerce')
            
            # 按日期排序（Tushare返回的数据是倒序的）
            df = df.sort_index()
            
            # 选择需要的列
            output_columns = ['open', 'high', 'low', 'close', 'volume']
            if 'amount' in df.columns:
                output_columns.append('amount')
            
            df = df[output_columns]
            
            return df
            
        except Exception as e:
            raise DataFetchError(f"数据格式标准化失败: {str(e)}") from e
    
    def get_dividend_data(self, code: str, start_date: str, end_date: str = None,
                         use_cache: bool = True) -> pd.DataFrame:
        """
        获取股票分红配股数据
        
        Args:
            code: 股票代码 (如 '601088')
            start_date: 开始日期 ('YYYY-MM-DD')
            end_date: 结束日期 ('YYYY-MM-DD', None表示当前日期)
            use_cache: 是否使用缓存
            
        Returns:
            pd.DataFrame: 分红配股数据
        """
        try:
            # 导入数据存储模块
            from .data_storage import DataStorage
            storage = DataStorage()
            
            # 如果启用缓存，先检查缓存
            if use_cache:
                if storage.is_dividend_date_range_cached(code, start_date or '1990-01-01',
                                                       end_date or datetime.now().strftime('%Y-%m-%d')):
                    cached_data = storage.load_dividend_data(code)
                    if cached_data is not None:
                        logger.info(f"📦 使用分红配股缓存数据: {code}")
                        
                        # 按日期范围过滤
                        filtered_data = cached_data.copy()
                        if start_date:
                            start_dt = pd.to_datetime(start_date)
                            filtered_data = filtered_data[filtered_data.index >= start_dt]
                        if end_date:
                            end_dt = pd.to_datetime(end_date)
                            filtered_data = filtered_data[filtered_data.index <= end_dt]
                        
                        logger.info(f"✅ 缓存分红配股数据过滤后: {code}, {len(filtered_data)} 条记录")
                        return filtered_data
            
            # 从网络获取
            logger.info(f"🌐 从Tushare获取股票 {code} 的分红配股数据...")
            
            # 控制请求频率
            import time
            if self.last_request_time is not None:
                elapsed = time.time() - self.last_request_time
                if elapsed < self.min_request_interval:
                    sleep_time = self.min_request_interval - elapsed
                    time.sleep(sleep_time)
            
            self.last_request_time = time.time()
            
            # 转换股票代码
            ts_code = self._convert_stock_code(code)
            
            # 调用Tushare分红接口（注意：dividend接口不支持start_date/end_date参数）
            # 需要获取全部数据，然后在处理后按日期过滤
            dividend_data = self.pro.dividend(ts_code=ts_code)
            
            if dividend_data is None or dividend_data.empty:
                logger.warning(f"未获取到股票 {code} 的分红配股数据")
                if use_cache:
                    empty_df = pd.DataFrame()
                    storage.save_dividend_data(empty_df, code)
                return pd.DataFrame()
            
            # 数据清洗和标准化
            processed_data = self._process_dividend_data(dividend_data)
            
            # 保存到缓存
            if use_cache and not processed_data.empty:
                storage.save_dividend_data(processed_data, code)
                logger.info(f"💾 分红配股数据已缓存: {code}")
            
            # 按日期范围过滤
            filtered_data = processed_data.copy()
            if start_date:
                start_dt = pd.to_datetime(start_date)
                filtered_data = filtered_data[filtered_data.index >= start_dt]
            if end_date:
                end_dt = pd.to_datetime(end_date)
                filtered_data = filtered_data[filtered_data.index <= end_dt]
            
            logger.info(f"成功获取股票 {code} 的分红配股数据，共 {len(filtered_data)} 条记录")
            return filtered_data
            
        except Exception as e:
            error_msg = f"获取股票 {code} 分红配股数据失败: {str(e)}"
            logger.warning(error_msg)
            return pd.DataFrame()
    
    def _process_dividend_data(self, raw_data: pd.DataFrame) -> pd.DataFrame:
        """
        处理Tushare原始分红配股数据
        
        Args:
            raw_data: 原始分红数据
            
        Returns:
            pd.DataFrame: 处理后的分红数据，以除权日为索引
        """
        if raw_data is None or raw_data.empty:
            return pd.DataFrame()
        
        try:
            processed_data = pd.DataFrame()
            
            # Tushare分红数据字段：
            # ex_date: 除权除息日
            # cash_div: 每股分红（税前）
            # stk_bo_rate: 送股比例（每10股送X股）
            # stk_co_rate: 转增比例（每10股转增X股）
            
            # 除权日
            if 'ex_date' in raw_data.columns:
                processed_data['ex_date'] = pd.to_datetime(raw_data['ex_date'], format='%Y%m%d')
            else:
                logger.warning("未找到除权日列")
                return pd.DataFrame()
            
            # 分红金额（每股）- Tushare已经是每股金额，不需要除以10
            if 'cash_div' in raw_data.columns:
                processed_data['dividend_amount'] = pd.to_numeric(raw_data['cash_div'], errors='coerce').fillna(0)
            else:
                processed_data['dividend_amount'] = 0
            
            # 送股比例 - Tushare是每10股送X股，需要除以10转换为每股比例
            if 'stk_bo_rate' in raw_data.columns:
                processed_data['bonus_ratio'] = pd.to_numeric(raw_data['stk_bo_rate'], errors='coerce').fillna(0) / 10.0
            else:
                processed_data['bonus_ratio'] = 0
            
            # 转增比例 - Tushare是每10股转增X股，需要除以10
            if 'stk_co_rate' in raw_data.columns:
                processed_data['transfer_ratio'] = pd.to_numeric(raw_data['stk_co_rate'], errors='coerce').fillna(0) / 10.0
            else:
                processed_data['transfer_ratio'] = 0
            
            # 配股比例和价格（暂时设为0）
            processed_data['allotment_ratio'] = 0
            processed_data['allotment_price'] = 0
            
            # 设置除权日为索引
            processed_data.set_index('ex_date', inplace=True)
            processed_data.sort_index(inplace=True)
            
            # 过滤掉所有值都为0的行
            mask = (processed_data['dividend_amount'] > 0) | \
                   (processed_data['bonus_ratio'] > 0) | \
                   (processed_data['transfer_ratio'] > 0) | \
                   (processed_data['allotment_ratio'] > 0)
            processed_data = processed_data[mask]
            
            logger.info(f"处理Tushare分红数据完成，有效记录数: {len(processed_data)}")
            return processed_data
            
        except Exception as e:
            logger.error(f"处理Tushare分红数据失败: {str(e)}")
            return pd.DataFrame()
    
    def align_dividend_with_weekly_data(self, weekly_data: pd.DataFrame,
                                      dividend_data: pd.DataFrame) -> pd.DataFrame:
        """
        将分红配股数据与周线数据对齐
        
        Args:
            weekly_data: 周线数据
            dividend_data: 分红配股数据
            
        Returns:
            pd.DataFrame: 对齐后的周线数据（包含分红配股信息）
        """
        try:
            # 如果没有分红数据，添加空列并返回
            if dividend_data is None or dividend_data.empty:
                weekly_data['dividend_amount'] = 0.0
                weekly_data['allotment_ratio'] = 0.0
                weekly_data['allotment_price'] = 0.0
                weekly_data['bonus_ratio'] = 0.0
                weekly_data['transfer_ratio'] = 0.0
                return weekly_data
            
            # 初始化分红配股列
            weekly_data['dividend_amount'] = 0.0
            weekly_data['allotment_ratio'] = 0.0
            weekly_data['allotment_price'] = 0.0
            weekly_data['bonus_ratio'] = 0.0
            weekly_data['transfer_ratio'] = 0.0
            
            # 遍历每个分红事件
            for ex_date, dividend_row in dividend_data.iterrows():
                try:
                    # 确保 ex_date 是 Timestamp 类型，并移除时区信息
                    try:
                        if hasattr(ex_date, 'tz_localize'):
                            ex_date_normalized = ex_date.tz_localize(None) if ex_date.tz is not None else ex_date
                        else:
                            ex_date_normalized = pd.Timestamp(ex_date)
                    except Exception as norm_e:
                        # 如果日期标准化失败，跳过这条分红记录
                        logger.debug(f"日期标准化失败，跳过分红记录: ex_date={ex_date}")
                        continue
                    
                    # 找到最接近的周线日期
                    closest_date = None
                    min_diff = pd.Timedelta(days=30)  # 使用合理的初始值避免溢出
                    
                    for week_date in weekly_data.index:
                        try:
                            # 确保 week_date 也是 Timestamp 类型，并移除时区信息
                            if hasattr(week_date, 'tz_localize'):
                                week_date_normalized = week_date.tz_localize(None) if week_date.tz is not None else week_date
                            else:
                                week_date_normalized = pd.Timestamp(week_date)
                            
                            # 计算日期差异（使用total_seconds避免异常Timedelta问题）
                            try:
                                time_diff = week_date_normalized - ex_date_normalized
                                # 转换为天数进行比较
                                diff_days = abs(time_diff.total_seconds() / 86400)
                                diff = pd.Timedelta(days=diff_days)
                            except (AttributeError, OverflowError, ValueError) as calc_e:
                                # 如果日期计算失败，跳过这个日期
                                continue
                            
                            if diff < min_diff:
                                min_diff = diff
                                closest_date = week_date
                        except Exception as inner_e:
                            logger.warning(f"计算日期差异失败，跳过此日期: week_date={week_date}, ex_date={ex_date}")
                            continue
                    
                    # 如果找到匹配的周线日期（允许7天内的差异）
                    if closest_date is not None and min_diff <= pd.Timedelta(days=7):
                        weekly_data.loc[closest_date, 'dividend_amount'] = dividend_row.get('dividend_amount', 0)
                        weekly_data.loc[closest_date, 'allotment_ratio'] = dividend_row.get('allotment_ratio', 0)
                        weekly_data.loc[closest_date, 'allotment_price'] = dividend_row.get('allotment_price', 0)
                        weekly_data.loc[closest_date, 'bonus_ratio'] = dividend_row.get('bonus_ratio', 0)
                        weekly_data.loc[closest_date, 'transfer_ratio'] = dividend_row.get('transfer_ratio', 0)
                        
                        logger.debug(f"分红配股信息已对齐: {ex_date_normalized.date()} -> {closest_date.date()}")
                except Exception as row_e:
                    # 将警告改为调试级别，避免大量警告信息
                    # 这些异常通常是由于日期计算问题导致的，不影响主要功能
                    logger.debug(f"处理分红记录失败 ex_date={ex_date}: {type(row_e).__name__}")
                    continue
            
            return weekly_data
            
        except Exception as e:
            logger.error(f"分红配股数据对齐失败: {str(e)}")
            # 返回原始数据，添加空的分红配股列
            weekly_data['dividend_amount'] = 0.0
            weekly_data['allotment_ratio'] = 0.0
            weekly_data['allotment_price'] = 0.0
            weekly_data['bonus_ratio'] = 0.0
            weekly_data['transfer_ratio'] = 0.0
            return weekly_data
    
    def test_connection(self) -> bool:
        """
        测试Tushare连接
        
        Returns:
            bool: 连接是否正常
        """
        try:
            # 尝试获取一只股票的少量数据来测试连接
            test_code = "000001.SZ"  # 平安银行
            end_date = datetime.now().strftime('%Y%m%d')
            start_date = (datetime.now() - timedelta(days=7)).strftime('%Y%m%d')
            
            df = self.pro.daily(
                ts_code=test_code,
                start_date=start_date,
                end_date=end_date
            )
            
            return df is not None and not df.empty
            
        except Exception as e:
            logger.error(f"测试Tushare连接失败: {str(e)}")
            return False


class DataFetcherFactory:
    """数据获取器工厂类"""
    
    @staticmethod
    def create_fetcher(source_type: str, config: dict = None) -> DataFetcher:
        """
        根据配置创建数据获取器
        
        Args:
            source_type: 数据源类型 ('akshare' 或 'tushare')
            config: 配置字典，包含:
                - tushare_token: Tushare API Token (使用tushare时必填)
        
        Returns:
            DataFetcher: 数据获取器实例
            
        Raises:
            ValueError: 不支持的数据源类型或缺少必要配置
        """
        if config is None:
            config = {}
        
        source_type = source_type.lower().strip()
        
        if source_type == 'akshare':
            logger.info("创建 Akshare 数据获取器")
            return AkshareDataFetcher()
            
        elif source_type == 'tushare':
            token = config.get('tushare_token')
            if not token:
                # 尝试从环境变量读取
                import os
                token = os.getenv('TUSHARE_TOKEN')
                if not token:
                    raise ValueError("使用 Tushare 数据源需要提供 tushare_token")
            logger.info("创建 Tushare 数据获取器")
            return TushareDataFetcher(token)
            
        else:
            raise ValueError(f"不支持的数据源类型: {source_type}，支持的类型: akshare, tushare")
    
    @staticmethod
    def create_with_fallback(primary: str, backup: str, config: dict) -> DataFetcher:
        """
        创建带降级的数据获取器
        
        尝试创建主数据源，如果失败则自动切换到备用数据源
        
        Args:
            primary: 主数据源类型
            backup: 备用数据源类型
            config: 配置字典
            
        Returns:
            DataFetcher: 成功创建的数据获取器实例
        """
        try:
            logger.info(f"尝试初始化主数据源: {primary}")
            return DataFetcherFactory.create_fetcher(primary, config)
        except Exception as e:
            logger.warning(f"主数据源 {primary} 初始化失败: {e}")
            logger.info(f"切换到备用数据源: {backup}")
            return DataFetcherFactory.create_fetcher(backup, config)


# 保留旧的工厂函数以保持向后兼容
def create_data_fetcher(source: str = 'akshare') -> DataFetcher:
    """
    创建数据获取器（向后兼容的工厂函数）
    
    Args:
        source: 数据源名称
        
    Returns:
        DataFetcher: 数据获取器实例
        
    Raises:
        DataFetchError: 不支持的数据源
    """
    try:
        return DataFetcherFactory.create_fetcher(source)
    except ValueError as e:
        raise DataFetchError(str(e)) from e

if __name__ == "__main__":
    # 测试代码
    logging.basicConfig(level=logging.INFO)
    
    fetcher = AkshareDataFetcher()
    
    # 测试连接
    if fetcher.test_connection():
        print("✅ Akshare连接正常")
    else:
        print("❌ Akshare连接失败")
    
    # 测试获取单只股票数据
    try:
        data = fetcher.get_stock_data('601088', '2023-01-01', '2023-12-31', 'weekly')
        print(f"✅ 成功获取中国神华周线数据，共 {len(data)} 条记录")
        print(data.head())
    except Exception as e:
        print(f"❌ 获取数据失败: {e}")