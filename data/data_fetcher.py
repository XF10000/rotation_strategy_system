"""
数据获取器模块
支持从不同数据源获取股票数据
"""

import akshare as ak
import pandas as pd
import logging
from datetime import datetime, timedelta
from typing import Dict, List, Optional
from abc import ABC, abstractmethod

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
        pass
    
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
                end_date = end_date.replace('-', '')
            
            start_date = start_date.replace('-', '')
            
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
                    # 增加请求间隔，避免频率限制
                    if attempt > 0:
                        time.sleep(2 + attempt)  # 递增延迟
                    
                    logger.debug(f"尝试获取股票 {code} 数据，第 {attempt + 1} 次")
                    
                    # 尝试不同的获取方式
                    if attempt < 3:
                        # 前3次使用标准方式
                        df = ak.stock_zh_a_hist(
                            symbol=code,
                            period=ak_period,
                            start_date=start_date,
                            end_date=end_date,
                            adjust="qfq"  # 前复权
                        )
                    else:
                        # 后续尝试使用不同参数
                        df = ak.stock_zh_a_hist(
                            symbol=code,
                            period="daily",  # 改用日线数据
                            start_date=start_date,
                            end_date=end_date,
                            adjust="hfq"  # 后复权
                        )
                    
                    if df is not None and not df.empty:
                        logger.debug(f"成功获取股票 {code} 数据，共 {len(df)} 条记录")
                        break
                    else:
                        logger.warning(f"第 {attempt + 1} 次尝试获取股票 {code} 数据为空")
                        
                except Exception as e:
                    logger.warning(f"第 {attempt + 1} 次尝试获取股票 {code} 数据失败: {str(e)}")
                    if attempt < max_retries - 1:
                        time.sleep(3 + attempt)  # 递增等待时间
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

# 工厂函数
def create_data_fetcher(source: str = 'akshare') -> DataFetcher:
    """
    创建数据获取器
    
    Args:
        source: 数据源名称
        
    Returns:
        DataFetcher: 数据获取器实例
        
    Raises:
        DataFetchError: 不支持的数据源
    """
    if source.lower() == 'akshare':
        return AkshareDataFetcher()
    else:
        raise DataFetchError(f"不支持的数据源: {source}")

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