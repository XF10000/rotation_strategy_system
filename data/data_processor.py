"""
数据预处理器模块
提供数据验证、清洗和格式转换功能
"""

import pandas as pd
import numpy as np
import logging
from typing import Tuple, List, Optional

from .exceptions import DataProcessError

logger = logging.getLogger(__name__)

class DataProcessor:
    """数据预处理器"""
    
    def __init__(self):
        """初始化数据处理器"""
        self.required_columns = ['open', 'high', 'low', 'close', 'volume']
        self.dividend_columns = ['dividend_amount', 'allotment_ratio', 'allotment_price', 
                               'bonus_ratio', 'transfer_ratio']
        logger.info("初始化数据处理器")
    
    def validate_data(self, df: pd.DataFrame) -> Tuple[bool, List[str]]:
        """
        验证数据完整性
        
        Args:
            df: 原始数据
            
        Returns:
            Tuple[bool, List[str]]: (是否有效, 问题列表)
        """
        issues = []
        
        try:
            # 检查是否为空
            if df is None or df.empty:
                issues.append("数据为空")
                return False, issues
            
            # 检查必要列是否存在
            missing_columns = [col for col in self.required_columns if col not in df.columns]
            if missing_columns:
                issues.append(f"缺少必要列: {missing_columns}")
            
            # 检查分红配股列（可选）
            dividend_columns_present = [col for col in self.dividend_columns if col in df.columns]
            if dividend_columns_present:
                logger.debug(f"发现分红配股列: {dividend_columns_present}")
                # 验证分红配股数据的数值类型
                for col in dividend_columns_present:
                    if not pd.api.types.is_numeric_dtype(df[col]):
                        issues.append(f"分红配股列 {col} 不是数值类型")
            
            # 检查数据类型
            for col in ['open', 'high', 'low', 'close']:
                if col in df.columns and not pd.api.types.is_numeric_dtype(df[col]):
                    issues.append(f"列 {col} 不是数值类型")
            
            # 检查OHLC逻辑
            if all(col in df.columns for col in ['open', 'high', 'low', 'close']):
                invalid_ohlc = self._check_ohlc_logic(df)
                if invalid_ohlc > 0:
                    issues.append(f"发现 {invalid_ohlc} 条OHLC逻辑错误的记录")
            
            # 检查缺失值比例
            if not df.empty:
                missing_ratio = df.isnull().sum().sum() / (len(df) * len(df.columns))
                if missing_ratio > 0.05:  # 超过5%的缺失值
                    issues.append(f"缺失值比例过高: {missing_ratio:.2%}")
            
            # 检查异常值
            price_columns = ['open', 'high', 'low', 'close']
            for col in price_columns:
                if col in df.columns:
                    if (df[col] <= 0).any():
                        issues.append(f"列 {col} 存在非正数值")
                    
                    # 检查极端值（价格变化超过50%）
                    if len(df) > 1:
                        pct_change = df[col].pct_change().abs()
                        extreme_changes = (pct_change > 0.5).sum()
                        if extreme_changes > 0:
                            issues.append(f"列 {col} 存在 {extreme_changes} 个极端变化值")
            
            # 检查成交量
            if 'volume' in df.columns:
                if (df['volume'] < 0).any():
                    issues.append("成交量存在负数")
            
            # 检查日期索引
            if not isinstance(df.index, pd.DatetimeIndex):
                issues.append("索引不是日期类型")
            elif not df.index.is_monotonic_increasing:
                issues.append("日期索引不是递增顺序")
            
            is_valid = len(issues) == 0
            return is_valid, issues
            
        except Exception as e:
            issues.append(f"数据验证过程出错: {str(e)}")
            return False, issues
    
    def clean_data(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        清洗数据（处理缺失值、异常值等）
        
        Args:
            df: 原始数据
            
        Returns:
            pd.DataFrame: 清洗后的数据
        """
        try:
            if df is None or df.empty:
                raise DataProcessError("输入数据为空")
            
            logger.info(f"开始清洗数据，原始数据 {len(df)} 条记录")
            
            # 复制数据避免修改原始数据
            cleaned_df = df.copy()
            
            # 1. 处理重复日期
            if cleaned_df.index.duplicated().any():
                logger.warning("发现重复日期，保留最后一条记录")
                cleaned_df = cleaned_df[~cleaned_df.index.duplicated(keep='last')]
            
            # 2. 排序
            cleaned_df = cleaned_df.sort_index()
            
            # 3. 处理缺失值
            # 对于价格数据，使用前向填充
            price_columns = ['open', 'high', 'low', 'close']
            for col in price_columns:
                if col in cleaned_df.columns:
                    if cleaned_df[col].isnull().any():
                        logger.warning(f"发现 {col} 列缺失值，使用前向填充")
                        cleaned_df[col] = cleaned_df[col].fillna(method='ffill')
            
            # 对于成交量，使用0填充
            if 'volume' in cleaned_df.columns:
                cleaned_df['volume'] = cleaned_df['volume'].fillna(0)
            
            # 对于分红配股数据，使用0填充（表示无分红配股）
            for col in self.dividend_columns:
                if col in cleaned_df.columns:
                    cleaned_df[col] = cleaned_df[col].fillna(0)
                    # 确保分红配股数据为非负数
                    if col != 'allotment_price':  # 配股价格可能为0但不应为负
                        cleaned_df[col] = cleaned_df[col].clip(lower=0)
            
            # 4. 处理异常值
            cleaned_df = self._handle_outliers(cleaned_df)
            
            # 5. 验证OHLC逻辑并修正
            cleaned_df = self._fix_ohlc_logic(cleaned_df)
            
            # 6. 最终验证
            is_valid, issues = self.validate_data(cleaned_df)
            if not is_valid:
                logger.warning(f"清洗后数据仍存在问题: {issues}")
            
            logger.info(f"数据清洗完成，清洗后数据 {len(cleaned_df)} 条记录")
            return cleaned_df
            
        except Exception as e:
            raise DataProcessError(f"数据清洗失败: {str(e)}") from e
    
    def resample_to_weekly(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        将日线数据重采样为周线数据
        
        Args:
            df: 日线数据
            
        Returns:
            pd.DataFrame: 周线数据
        """
        try:
            if df is None or df.empty:
                raise DataProcessError("输入数据为空")
            
            logger.info(f"将日线数据重采样为周线，原始数据 {len(df)} 条记录")
            
            # 确保索引是日期类型
            if not isinstance(df.index, pd.DatetimeIndex):
                raise DataProcessError("数据索引必须是日期类型")
            
            # 定义重采样规则
            agg_rules = {
                'open': 'first',    # 开盘价取第一个
                'high': 'max',      # 最高价取最大值
                'low': 'min',       # 最低价取最小值
                'close': 'last',    # 收盘价取最后一个
                'volume': 'sum'     # 成交量求和
            }
            
            # 添加其他可能存在的列
            if 'amount' in df.columns:
                agg_rules['amount'] = 'sum'
            if 'turnover_rate' in df.columns:
                agg_rules['turnover_rate'] = 'mean'
            
            # 重采样到周线（周五为一周结束）
            weekly_df = df.resample('W-FRI').agg(agg_rules)
            
            # 删除全为NaN的行（可能是没有交易的周）
            weekly_df = weekly_df.dropna(how='all')
            
            # 处理部分NaN值
            # 对于价格数据，使用前向填充后再后向填充
            price_columns = ['open', 'high', 'low', 'close']
            for col in price_columns:
                if col in weekly_df.columns:
                    weekly_df[col] = weekly_df[col].ffill().bfill()
            
            # 对于成交量，使用0填充
            if 'volume' in weekly_df.columns:
                weekly_df['volume'] = weekly_df['volume'].fillna(0)
            
            # 对于成交额，使用0填充
            if 'amount' in weekly_df.columns:
                weekly_df['amount'] = weekly_df['amount'].fillna(0)
            
            # 确保OHLC逻辑正确
            weekly_df = self._fix_ohlc_logic(weekly_df)
            
            # 最终检查，删除任何仍然有NaN的行
            weekly_df = weekly_df.dropna()
            
            logger.info(f"重采样完成，周线数据 {len(weekly_df)} 条记录")
            return weekly_df
            
        except Exception as e:
            raise DataProcessError(f"重采样失败: {str(e)}") from e
    
    def _handle_missing_values(self, df: pd.DataFrame) -> pd.DataFrame:
        """处理缺失值"""
        try:
            # 对于价格数据，使用前向填充
            price_columns = ['open', 'high', 'low', 'close']
            for col in price_columns:
                if col in df.columns:
                    # 先前向填充，再后向填充
                    df[col] = df[col].ffill().bfill()
            
            # 对于成交量，使用0填充（表示无交易）
            if 'volume' in df.columns:
                df['volume'] = df['volume'].fillna(0)
            
            # 对于成交额，使用0填充
            if 'amount' in df.columns:
                df['amount'] = df['amount'].fillna(0)
            
            # 删除仍然有缺失值的行
            df = df.dropna()
            
            return df
            
        except Exception as e:
            raise DataProcessError(f"处理缺失值失败: {str(e)}") from e
    
    def _handle_outliers(self, df: pd.DataFrame) -> pd.DataFrame:
        """处理异常值"""
        try:
            # 处理价格异常值（使用3倍标准差规则）
            price_columns = ['open', 'high', 'low', 'close']
            
            for col in price_columns:
                if col in df.columns and len(df) > 10:
                    # 计算价格变化率
                    pct_change = df[col].pct_change().abs()
                    
                    # 识别异常变化（超过3倍标准差）
                    mean_change = pct_change.mean()
                    std_change = pct_change.std()
                    threshold = mean_change + 3 * std_change
                    
                    outliers = pct_change > threshold
                    if outliers.any():
                        logger.warning(f"发现 {outliers.sum()} 个 {col} 异常值")
                        
                        # 用前一个有效值替换异常值
                        for idx in df.index[outliers]:
                            if idx != df.index[0]:  # 不是第一行
                                prev_idx = df.index[df.index < idx][-1]
                                df.loc[idx, col] = df.loc[prev_idx, col]
            
            # 处理成交量异常值
            if 'volume' in df.columns and len(df) > 10:
                # 成交量不能为负数
                df.loc[df['volume'] < 0, 'volume'] = 0
                
                # 处理极端大的成交量（超过中位数的100倍）
                median_volume = df['volume'].median()
                if median_volume > 0:
                    extreme_volume = df['volume'] > median_volume * 100
                    if extreme_volume.any():
                        logger.warning(f"发现 {extreme_volume.sum()} 个成交量异常值")
                        df.loc[extreme_volume, 'volume'] = median_volume
            
            return df
            
        except Exception as e:
            raise DataProcessError(f"处理异常值失败: {str(e)}") from e
    
    def _check_ohlc_logic(self, df: pd.DataFrame) -> int:
        """检查OHLC逻辑错误的记录数"""
        try:
            if not all(col in df.columns for col in ['open', 'high', 'low', 'close']):
                return 0
            
            # 检查 high >= max(open, close) 和 low <= min(open, close)
            invalid_high = df['high'] < df[['open', 'close']].max(axis=1)
            invalid_low = df['low'] > df[['open', 'close']].min(axis=1)
            
            return (invalid_high | invalid_low).sum()
            
        except Exception:
            return 0
    
    def _fix_ohlc_logic(self, df: pd.DataFrame) -> pd.DataFrame:
        """修正OHLC逻辑错误"""
        try:
            if not all(col in df.columns for col in ['open', 'high', 'low', 'close']):
                return df
            
            # 修正最高价：确保 high >= max(open, close)
            max_oc = df[['open', 'close']].max(axis=1)
            df.loc[df['high'] < max_oc, 'high'] = max_oc
            
            # 修正最低价：确保 low <= min(open, close)
            min_oc = df[['open', 'close']].min(axis=1)
            df.loc[df['low'] > min_oc, 'low'] = min_oc
            
            return df
            
        except Exception as e:
            logger.warning(f"修正OHLC逻辑失败: {str(e)}")
            return df
    
    def calculate_technical_indicators(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        计算技术指标 - 带详细调试日志
        
        Args:
            df: 包含OHLCV数据的DataFrame
            
        Returns:
            pd.DataFrame: 包含技术指标的数据
        """
        try:
            if df is None or df.empty:
                raise DataProcessError("输入数据为空")
            
            logger.info("=" * 60)
            logger.info("🔍 开始计算技术指标 - 详细调试模式")
            logger.info("=" * 60)
            
            # 复制数据避免修改原始数据
            result_df = df.copy()
            
            # 输入数据检查
            logger.info(f"📊 输入数据概况:")
            logger.info(f"   - 数据行数: {len(result_df)}")
            logger.info(f"   - 数据列数: {len(result_df.columns)}")
            logger.info(f"   - 数据范围: {result_df.index.min()} 到 {result_df.index.max()}")
            logger.info(f"   - 收盘价范围: {result_df['close'].min():.4f} - {result_df['close'].max():.4f}")
            logger.info(f"   - 收盘价NaN数量: {result_df['close'].isna().sum()}")
            
            # 计算RSI
            logger.info("\n🔄 计算RSI指标...")
            result_df['rsi'] = self._calculate_rsi_debug(result_df['close'])
            
            # 计算EMA（使用分层标准化策略）
            logger.info("\n🔄 计算EMA指标...")
            logger.info("   - 计算EMA20...")
            ema_20_data = self._calculate_ema_debug(result_df['close'], 20)
            result_df['ema_20'] = ema_20_data
            logger.info(f"   - EMA20 NaN数量: {result_df['ema_20'].isna().sum()}")
            logger.info(f"   - EMA20 最后5个值: {result_df['ema_20'].tail().values}")
            
            logger.info("   - 计算EMA50...")
            ema_50_data = self._calculate_ema_debug(result_df['close'], 50)
            result_df['ema_50'] = ema_50_data
            logger.info(f"   - EMA50 NaN数量: {result_df['ema_50'].isna().sum()}")
            logger.info(f"   - EMA50 最后5个值: {result_df['ema_50'].tail().values}")
            
            logger.info("   - 计算EMA60...")
            ema_60_data = self._calculate_ema_debug(result_df['close'], 60)
            result_df['ema_60'] = ema_60_data
            logger.info(f"   - EMA60 NaN数量: {result_df['ema_60'].isna().sum()}")
            logger.info(f"   - EMA60 最后5个值: {result_df['ema_60'].tail().values}")
            
            # 计算MACD
            logger.info("\n🔄 计算MACD指标...")
            macd_data = self._calculate_macd_debug(result_df['close'])
            result_df['macd'] = macd_data['macd']
            result_df['macd_signal'] = macd_data['signal']
            result_df['macd_histogram'] = macd_data['histogram']
            
            # 计算布林带
            logger.info("\n🔄 计算布林带指标...")
            bb_data = self._calculate_bollinger_bands_debug(result_df['close'])
            result_df['bb_upper'] = bb_data['upper']
            result_df['bb_middle'] = bb_data['middle']
            result_df['bb_lower'] = bb_data['lower']
            
            # 计算移动平均线 - 使用TA-Lib SMA
            logger.info("\n🔄 计算移动平均线...")
            
            # 使用TA-Lib计算SMA
            from indicators.trend import calculate_sma
            
            logger.info("   - 计算MA5...")
            result_df['ma_5'] = calculate_sma(result_df['close'], 5)
            logger.info(f"   - MA5 NaN数量: {result_df['ma_5'].isna().sum()}")
            
            # 检查MA5回测期间有效性
            if len(result_df['ma_5']) >= 126:
                backtest_ma5 = result_df['ma_5'].iloc[125:]
                backtest_nan = backtest_ma5.isna().sum()
                if backtest_nan == 0:
                    logger.info(f"   - ✅ 回测期间MA5 100%有效")
                else:
                    logger.warning(f"   - ⚠️ 回测期间MA5存在{backtest_nan}个NaN")
            
            logger.info("   - 计算MA10...")
            result_df['ma_10'] = calculate_sma(result_df['close'], 10)
            logger.info(f"   - MA10 NaN数量: {result_df['ma_10'].isna().sum()}")
            
            # 检查MA10回测期间有效性
            if len(result_df['ma_10']) >= 126:
                backtest_ma10 = result_df['ma_10'].iloc[125:]
                backtest_nan = backtest_ma10.isna().sum()
                if backtest_nan == 0:
                    logger.info(f"   - ✅ 回测期间MA10 100%有效")
                else:
                    logger.warning(f"   - ⚠️ 回测期间MA10存在{backtest_nan}个NaN")
            
            logger.info("   - 计算MA20...")
            result_df['ma_20'] = calculate_sma(result_df['close'], 20)
            logger.info(f"   - MA20 NaN数量: {result_df['ma_20'].isna().sum()}")
            
            # 检查MA20回测期间有效性
            if len(result_df['ma_20']) >= 126:
                backtest_ma20 = result_df['ma_20'].iloc[125:]
                backtest_nan = backtest_ma20.isna().sum()
                if backtest_nan == 0:
                    logger.info(f"   - ✅ 回测期间MA20 100%有效")
                else:
                    logger.warning(f"   - ⚠️ 回测期间MA20存在{backtest_nan}个NaN")
            
            # 计算成交量指标
            if 'volume' in result_df.columns:
                logger.info("\n🔄 计算成交量指标...")
                logger.info(f"   - 成交量NaN数量: {result_df['volume'].isna().sum()}")
                logger.info(f"   - 成交量范围: {result_df['volume'].min()} - {result_df['volume'].max()}")
                
                # 使用4周均量（策略文档要求：极端价格量能判断使用4周均量）
                result_df['volume_ma'] = result_df['volume'].rolling(window=4).mean()
                logger.info(f"   - 成交量MA4 NaN数量: {result_df['volume_ma'].isna().sum()}")
                
                # 检查除零情况
                zero_volume_ma = (result_df['volume_ma'] == 0).sum()
                logger.info(f"   - 成交量MA4为0的数量: {zero_volume_ma}")
                
                result_df['volume_ratio'] = result_df['volume'] / result_df['volume_ma']
                logger.info(f"   - 成交量比率 NaN数量: {result_df['volume_ratio'].isna().sum()}")
                logger.info(f"   - 成交量比率 无穷大数量: {np.isinf(result_df['volume_ratio']).sum()}")
            
            # 最终统计
            logger.info("\n📈 技术指标计算完成统计:")
            logger.info("-" * 40)
            for col in result_df.columns:
                if col not in ['open', 'high', 'low', 'close', 'volume']:
                    nan_count = result_df[col].isna().sum()
                    inf_count = np.isinf(result_df[col]).sum() if result_df[col].dtype in ['float64', 'float32'] else 0
                    logger.info(f"   {col:15}: NaN={nan_count:3d}, Inf={inf_count:3d}")
            
            logger.info("=" * 60)
            
            return result_df
            
        except Exception as e:
            logger.error(f"❌ 计算技术指标失败: {str(e)}")
            import traceback
            logger.error(traceback.format_exc())
            raise DataProcessError(f"计算技术指标失败: {str(e)}") from e
    
    def _calculate_rsi(self, prices: pd.Series, period: int = 14) -> pd.Series:
        """计算RSI指标 - 修复版本：使用全部历史数据"""
        try:
            # v4.2修复：直接使用全部历史数据计算RSI，不使用复杂的滚动窗口
            # 这样可以充分利用已获取的125周历史数据
            from indicators.momentum import calculate_rsi
            rsi = calculate_rsi(prices, period)
            
            return rsi
            
        except Exception as e:
            raise DataProcessError(f"RSI计算失败: {str(e)}") from e
    
    def _calculate_ema_debug(self, prices: pd.Series, period: int) -> pd.Series:
        """计算EMA指标 - 使用TA-Lib确保回测期间100%有效"""
        try:
            logger.info(f"   - EMA{period}计算输入: 价格序列长度={len(prices)}, 周期={period}")
            logger.info(f"   - 价格序列NaN数量: {prices.isna().sum()}")
            
            # v4.2修复：使用TA-Lib计算EMA，但确保回测期间100%有效
            # 策略：TA-Lib需要预热期，但我们有125周历史数据足够覆盖预热期
            from indicators.trend import calculate_ema
            
            # 使用TA-Lib计算EMA（会有前period-1个NaN）
            ema_full = calculate_ema(prices, period)
            
            # 检查实际的NaN分布
            nan_count = ema_full.isna().sum()
            valid_count = len(ema_full) - nan_count
            valid_rate = (valid_count / len(ema_full)) * 100
            
            logger.info(f"   - 使用TA-Lib计算EMA{period}")
            logger.info(f"   - 总数据点: {len(ema_full)}")
            logger.info(f"   - NaN数量: {nan_count} (前{nan_count}个点)")
            logger.info(f"   - 有效数据点: {valid_count}")
            logger.info(f"   - 有效率: {valid_rate:.2f}%")
            
            # 对于125周历史数据，前19个点为NaN（EMA20），但回测期间（第126个点开始）100%有效
            if len(ema_full) >= 126:  # 如果有足够的数据
                backtest_period = ema_full.iloc[125:]  # 回测期间数据
                backtest_nan = backtest_period.isna().sum()
                logger.info(f"   - 回测期间({len(backtest_period)}个点): NaN数量={backtest_nan}")
                if backtest_nan == 0:
                    logger.info(f"   - ✅ 回测期间EMA{period} 100%有效")
                else:
                    logger.warning(f"   - ⚠️ 回测期间EMA{period}存在{backtest_nan}个NaN")
            
            logger.info(f"   - EMA{period} 最后5个值: {ema_full.tail().values}")
            return ema_full
            
        except Exception as e:
            logger.error(f"   - EMA{period}计算失败: {str(e)}")
            raise DataProcessError(f"EMA{period}计算失败: {str(e)}") from e
    
    def _calculate_rsi_debug(self, prices: pd.Series, period: int = 14) -> pd.Series:
        """计算RSI指标 - 使用TA-Lib实现，确保回测期间100%有效"""
        try:
            logger.info(f"   - RSI计算输入: 价格序列长度={len(prices)}, 周期={period}")
            logger.info(f"   - 价格序列NaN数量: {prices.isna().sum()}")
            
            # 使用TA-Lib计算RSI，充分利用125周历史数据
            from indicators.momentum import calculate_rsi
            rsi = calculate_rsi(prices, period)
            
            logger.info(f"   - 使用TA-Lib计算RSI{period}，利用{len(prices)}周历史数据")
            logger.info(f"   - RSI NaN数量: {rsi.isna().sum()}")
            logger.info(f"   - RSI 预期前{period}个点为NaN，这是TA-Lib的正常行为")
            
            # 检查回测期间有效性
            if len(rsi) >= 126:
                backtest_period = rsi.iloc[125:]
                backtest_nan = backtest_period.isna().sum()
                logger.info(f"   - 回测期间({len(backtest_period)}个点): NaN数量={backtest_nan}")
                if backtest_nan == 0:
                    logger.info(f"   - ✅ 回测期间RSI{period} 100%有效")
                else:
                    logger.warning(f"   - ⚠️ 回测期间RSI{period}存在{backtest_nan}个NaN")
            
            logger.info(f"   - RSI 最后5个值: {rsi.tail().values}")
            return rsi
            
        except Exception as e:
            logger.error(f"   - RSI计算失败: {str(e)}")
            raise DataProcessError(f"RSI计算失败: {str(e)}") from e
    
    def _calculate_macd(self, prices: pd.Series, fast: int = 12, slow: int = 26, signal: int = 9) -> dict:
        """计算MACD指标 - 使用TA-Lib确保准确性"""
        try:
            # v4.2修复：使用TA-Lib计算MACD，确保计算准确性
            # 虽然会有预热期NaN，但回测期间（基于125周历史数据）会100%有效
            from indicators.momentum import calculate_macd
            
            macd_result = calculate_macd(prices, fast, slow, signal)
            
            return {
                'macd': macd_result['dif'],
                'signal': macd_result['dea'],
                'histogram': macd_result['hist']
            }
                
        except Exception:
            return {
                'macd': pd.Series(index=prices.index, dtype=float),
                'signal': pd.Series(index=prices.index, dtype=float),
                'histogram': pd.Series(index=prices.index, dtype=float)
            }
    
    def _calculate_macd_debug(self, prices: pd.Series, fast: int = 12, slow: int = 26, signal: int = 9) -> dict:
        """计算MACD指标 - 使用TA-Lib实现，确保回测期间100%有效"""
        try:
            logger.info(f"   - MACD计算输入: 价格序列长度={len(prices)}, 快线={fast}, 慢线={slow}, 信号线={signal}")
            
            from indicators.momentum import calculate_macd
            macd_result = calculate_macd(prices, fast, slow, signal)
            
            logger.info(f"   - 使用TA-Lib计算MACD成功")
            logger.info(f"   - MACD线 NaN数量: {macd_result['dif'].isna().sum()}")
            logger.info(f"   - MACD信号线 NaN数量: {macd_result['dea'].isna().sum()}")
            logger.info(f"   - MACD柱状图 NaN数量: {macd_result['hist'].isna().sum()}")
            
            # 检查回测期间有效性
            if len(macd_result['dif']) >= 126:
                backtest_dif = macd_result['dif'].iloc[125:]
                backtest_nan = backtest_dif.isna().sum()
                logger.info(f"   - 回测期间({len(backtest_dif)}个点): MACD线 NaN数量={backtest_nan}")
                if backtest_nan == 0:
                    logger.info(f"   - ✅ 回测期间MACD 100%有效")
                else:
                    logger.warning(f"   - ⚠️ 回测期间MACD存在{backtest_nan}个NaN")
            
            logger.info(f"   - MACD线范围: {macd_result['dif'].min():.6f} - {macd_result['dif'].max():.6f}")
            logger.info(f"   - MACD柱状图范围: {macd_result['hist'].min():.6f} - {macd_result['hist'].max():.6f}")
            
            return {
                'macd': macd_result['dif'],
                'signal': macd_result['dea'],
                'histogram': macd_result['hist']
            }
            
        except Exception as e:
            logger.error(f"   - MACD计算失败: {str(e)}")
            raise DataProcessError(f"MACD计算失败: {str(e)}") from e
    
    def _calculate_bollinger_bands(self, prices: pd.Series, period: int = 20, std_dev: float = 2) -> dict:
        """计算布林带指标 - 使用TA-Lib实现"""
        try:
            # 使用TA-Lib volatility.py模块计算布林带
            from indicators.volatility import calculate_bollinger_bands
            return calculate_bollinger_bands(prices, period, std_dev)
                
        except Exception as e:
            raise DataProcessError(f"布林带计算失败: {str(e)}") from e
    
    def _calculate_bollinger_bands_debug(self, prices: pd.Series, period: int = 20, std_dev: float = 2) -> dict:
        """计算布林带指标 - 使用TA-Lib实现，确保回测期间100%有效"""
        try:
            logger.info(f"   - 布林带计算输入: 价格序列长度={len(prices)}, 周期={period}, 标准差倍数={std_dev}")
            
            # 使用TA-Lib volatility.py模块计算布林带
            from indicators.volatility import calculate_bollinger_bands
            bb_result = calculate_bollinger_bands(prices, period, std_dev)
            
            logger.info(f"   - 使用TA-Lib计算布林带成功")
            logger.info(f"   - 上轨 NaN数量: {bb_result['upper'].isna().sum()}")
            logger.info(f"   - 中轨 NaN数量: {bb_result['middle'].isna().sum()}")
            logger.info(f"   - 下轨 NaN数量: {bb_result['lower'].isna().sum()}")
            
            # 检查回测期间有效性
            if len(bb_result['upper']) >= 126:
                backtest_upper = bb_result['upper'].iloc[125:]
                backtest_nan = backtest_upper.isna().sum()
                logger.info(f"   - 回测期间({len(backtest_upper)}个点): NaN数量={backtest_nan}")
                if backtest_nan == 0:
                    logger.info(f"   - ✅ 回测期间布林带 100%有效")
                else:
                    logger.warning(f"   - ⚠️ 回测期间布林带存在{backtest_nan}个NaN")
            
            return bb_result
            
        except Exception as e:
            logger.error(f"   - 布林带计算失败: {str(e)}")
            raise DataProcessError(f"布林带计算失败: {str(e)}") from e

    def get_data_summary(self, df: pd.DataFrame) -> dict:
        """
        获取数据摘要信息
        
        Args:
            df: 数据DataFrame
            
        Returns:
            dict: 数据摘要
        """
        try:
            if df is None or df.empty:
                return {"error": "数据为空"}
            
            summary = {
                "记录数": len(df),
                "开始日期": df.index.min().strftime('%Y-%m-%d') if not df.empty else None,
                "结束日期": df.index.max().strftime('%Y-%m-%d') if not df.empty else None,
                "列数": len(df.columns),
                "列名": list(df.columns),
                "缺失值": df.isnull().sum().to_dict(),
                "数据类型": df.dtypes.to_dict()
            }
            
            # 添加价格统计信息
            if 'close' in df.columns:
                summary["收盘价统计"] = {
                    "最小值": float(df['close'].min()),
                    "最大值": float(df['close'].max()),
                    "平均值": float(df['close'].mean()),
                    "标准差": float(df['close'].std())
                }
            
            return summary
            
        except Exception as e:
            return {"error": f"生成数据摘要失败: {str(e)}"}
    
    def process_dividend_events(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        处理分红配股事件，计算对股价和持仓的影响
        
        Args:
            df: 包含分红配股信息的数据
            
        Returns:
            pd.DataFrame: 处理后的数据，包含除权除息调整信息
        """
        try:
            if df is None or df.empty:
                return df
            
            processed_df = df.copy()
            
            # 添加除权除息标记列
            processed_df['has_dividend'] = (processed_df.get('dividend_amount', 0) > 0)
            processed_df['has_allotment'] = (processed_df.get('allotment_ratio', 0) > 0)
            processed_df['has_bonus'] = (processed_df.get('bonus_ratio', 0) > 0)
            processed_df['has_transfer'] = (processed_df.get('transfer_ratio', 0) > 0)
            
            # 计算除权除息调整因子
            processed_df['rights_factor'] = 1.0  # 除权因子
            processed_df['dividend_factor'] = 0.0  # 分红因子
            
            for idx in processed_df.index:
                row = processed_df.loc[idx]
                
                # 计算除权因子（送股、转增、配股的影响）
                bonus_ratio = row.get('bonus_ratio', 0) / 10  # 10送X转换为比例
                transfer_ratio = row.get('transfer_ratio', 0) / 10  # 10转X转换为比例
                allotment_ratio = row.get('allotment_ratio', 0) / 10  # 10配X转换为比例
                
                # 除权因子 = 1 / (1 + 送股比例 + 转增比例 + 配股比例)
                rights_factor = 1.0 / (1.0 + bonus_ratio + transfer_ratio + allotment_ratio)
                processed_df.loc[idx, 'rights_factor'] = rights_factor
                
                # 分红因子（每股分红金额）
                dividend_amount = row.get('dividend_amount', 0)
                processed_df.loc[idx, 'dividend_factor'] = dividend_amount
                
                if (bonus_ratio > 0 or transfer_ratio > 0 or allotment_ratio > 0 or dividend_amount > 0):
                    logger.debug(f"除权除息事件 {idx.date()}: "
                               f"送股{bonus_ratio:.3f}, 转增{transfer_ratio:.3f}, "
                               f"配股{allotment_ratio:.3f}, 分红{dividend_amount:.3f}")
            
            logger.info(f"处理分红配股事件完成，共发现 "
                       f"{processed_df['has_dividend'].sum()} 个分红事件，"
                       f"{processed_df['has_allotment'].sum()} 个配股事件，"
                       f"{processed_df['has_bonus'].sum()} 个送股事件，"
                       f"{processed_df['has_transfer'].sum()} 个转增事件")
            
            return processed_df
            
        except Exception as e:
            logger.error(f"处理分红配股事件失败: {str(e)}")
            return df

if __name__ == "__main__":
    # 测试代码
    logging.basicConfig(level=logging.INFO)
    
    # 创建测试数据
    dates = pd.date_range('2023-01-01', '2023-12-31', freq='D')
    test_data = pd.DataFrame({
        'open': np.random.uniform(10, 20, len(dates)),
        'high': np.random.uniform(15, 25, len(dates)),
        'low': np.random.uniform(5, 15, len(dates)),
        'close': np.random.uniform(10, 20, len(dates)),
        'volume': np.random.randint(1000, 10000, len(dates))
    }, index=dates)
    
    # 添加一些异常值进行测试
    test_data.loc[test_data.index[10], 'high'] = test_data.loc[test_data.index[10], 'low'] - 1  # OHLC逻辑错误
    test_data.loc[test_data.index[20:25], 'close'] = np.nan  # 缺失值
    
    processor = DataProcessor()
    
    # 测试数据验证
    is_valid, issues = processor.validate_data(test_data)
    print(f"数据验证结果: {is_valid}")
    if issues:
        print(f"发现问题: {issues}")
    
    # 测试数据清洗
    cleaned_data = processor.clean_data(test_data)
    print(f"清洗前: {len(test_data)} 条记录")
    print(f"清洗后: {len(cleaned_data)} 条记录")
    
    # 测试重采样
    weekly_data = processor.resample_to_weekly(cleaned_data)
    print(f"周线数据: {len(weekly_data)} 条记录")
    
    # 测试数据摘要
    summary = processor.get_data_summary(weekly_data)
    print(f"数据摘要: {summary}")