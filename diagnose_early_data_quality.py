#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
历史数据质量诊断脚本
用于分析2015年开始回测时技术指标异常的根本原因

问题背景：
- 回测起始时间提前到2015年1月8日时，2019年以前的技术指标变成直线
- 中国神华等大型股票也出现此问题，排除数据不足的可能
- 需要定位是数据质量问题还是代码逻辑问题
"""

import pandas as pd
import numpy as np
import logging
from datetime import datetime, timedelta
import sys
import os

# 添加项目路径
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from data.data_fetcher import AkshareDataFetcher
from data.data_processor import DataProcessor
from strategy.signal_generator import SignalGenerator
from config.csv_config_loader import load_backtest_settings

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('data_quality_diagnosis.log', encoding='utf-8'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

class EarlyDataQualityDiagnoser:
    """早期数据质量诊断器"""
    
    def __init__(self):
        self.data_fetcher = AkshareDataFetcher()
        self.data_processor = DataProcessor()
        
    def diagnose_stock_data_quality(self, stock_code: str, start_date: str = "2015-01-08"):
        """
        诊断单只股票的数据质量
        
        Args:
            stock_code: 股票代码
            start_date: 回测开始日期
        """
        logger.info(f"\n{'='*60}")
        logger.info(f"🔍 开始诊断股票 {stock_code} 的数据质量")
        logger.info(f"🕐 回测开始日期: {start_date}")
        logger.info(f"{'='*60}")
        
        try:
            # 1. 获取原始数据
            logger.info("📊 步骤1: 获取原始股票数据...")
            
            # 计算需要的历史数据起始日期（125周历史数据）
            start_dt = datetime.strptime(start_date, "%Y-%m-%d")
            history_start = start_dt - timedelta(weeks=125)
            history_start_str = history_start.strftime("%Y-%m-%d")
            
            logger.info(f"   - 历史数据起始日期: {history_start_str}")
            logger.info(f"   - 回测开始日期: {start_date}")
            
            # 获取股票数据
            stock_data = self.data_fetcher.get_stock_data(
                stock_code, 
                start_date=history_start_str,
                end_date="2025-01-01"  # 获取到当前
            )
            
            if stock_data is None or stock_data.empty:
                logger.error(f"❌ 无法获取股票 {stock_code} 的数据")
                return None
                
            logger.info(f"   - 原始数据行数: {len(stock_data)}")
            logger.info(f"   - 数据时间范围: {stock_data.index.min()} 到 {stock_data.index.max()}")
            
            # 2. 数据完整性检查
            logger.info("\n📋 步骤2: 数据完整性检查...")
            self._check_data_completeness(stock_data, history_start_str, start_date)
            
            # 3. 数据质量检查
            logger.info("\n🔬 步骤3: 数据质量检查...")
            self._check_data_quality(stock_data)
            
            # 4. 重采样为周线数据
            logger.info("\n📈 步骤4: 重采样为周线数据...")
            weekly_data = self.data_processor.resample_to_weekly(stock_data)
            logger.info(f"   - 周线数据行数: {len(weekly_data)}")
            logger.info(f"   - 周线时间范围: {weekly_data.index.min()} 到 {weekly_data.index.max()}")
            
            # 5. 技术指标计算诊断
            logger.info("\n🔧 步骤5: 技术指标计算诊断...")
            self._diagnose_technical_indicators(weekly_data, start_date)
            
            # 6. 信号生成器诊断
            logger.info("\n🎯 步骤6: 信号生成器诊断...")
            self._diagnose_signal_generator(stock_code, weekly_data, start_date)
            
            return weekly_data
            
        except Exception as e:
            logger.error(f"❌ 诊断股票 {stock_code} 时发生错误: {str(e)}")
            import traceback
            logger.error(traceback.format_exc())
            return None
    
    def _check_data_completeness(self, data: pd.DataFrame, history_start: str, backtest_start: str):
        """检查数据完整性"""
        
        # 检查缺失值
        missing_data = data.isnull().sum()
        logger.info(f"   - 缺失值统计:")
        for col, missing_count in missing_data.items():
            if missing_count > 0:
                logger.warning(f"     {col}: {missing_count} 个缺失值")
            else:
                logger.info(f"     {col}: 无缺失值")
        
        # 检查时间连续性
        date_range = pd.date_range(start=history_start, end=data.index.max(), freq='D')
        trading_days = len([d for d in date_range if d.weekday() < 5])  # 工作日
        actual_days = len(data)
        
        logger.info(f"   - 时间连续性检查:")
        logger.info(f"     期间总工作日: {trading_days}")
        logger.info(f"     实际数据天数: {actual_days}")
        logger.info(f"     数据完整率: {actual_days/trading_days*100:.1f}%")
        
        # 检查关键时间点的数据
        backtest_start_dt = datetime.strptime(backtest_start, "%Y-%m-%d")
        key_dates = [
            backtest_start_dt - timedelta(days=365*2),  # 回测前2年
            backtest_start_dt - timedelta(days=365),    # 回测前1年
            backtest_start_dt,                          # 回测开始
            backtest_start_dt + timedelta(days=365*2),  # 回测后2年
            backtest_start_dt + timedelta(days=365*4)   # 回测后4年
        ]
        
        logger.info(f"   - 关键时间点数据检查:")
        for date in key_dates:
            closest_data = data[data.index <= date]
            if not closest_data.empty:
                closest_date = closest_data.index.max()
                days_diff = (date - closest_date).days
                logger.info(f"     {date.strftime('%Y-%m-%d')}: 最近数据 {closest_date.strftime('%Y-%m-%d')} (相差{days_diff}天)")
            else:
                logger.warning(f"     {date.strftime('%Y-%m-%d')}: ❌ 无数据")
    
    def _check_data_quality(self, data: pd.DataFrame):
        """检查数据质量"""
        
        # 检查价格合理性
        logger.info(f"   - 价格合理性检查:")
        
        for col in ['open', 'high', 'low', 'close']:
            if col in data.columns:
                prices = data[col]
                logger.info(f"     {col}: 范围 {prices.min():.2f} - {prices.max():.2f}")
                
                # 检查零值或负值
                zero_or_negative = (prices <= 0).sum()
                if zero_or_negative > 0:
                    logger.warning(f"     {col}: ❌ 发现 {zero_or_negative} 个零值或负值")
                
                # 检查极端变化
                pct_change = prices.pct_change().abs()
                extreme_changes = (pct_change > 0.5).sum()
                if extreme_changes > 0:
                    logger.warning(f"     {col}: ⚠️ 发现 {extreme_changes} 个极端变化(>50%)")
                    # 显示极端变化的日期
                    extreme_dates = data[pct_change > 0.5].index
                    for date in extreme_dates[:5]:  # 显示前5个
                        logger.warning(f"       极端变化: {date.strftime('%Y-%m-%d')}")
        
        # 检查OHLC逻辑
        if all(col in data.columns for col in ['open', 'high', 'low', 'close']):
            invalid_high = data['high'] < data[['open', 'close']].max(axis=1)
            invalid_low = data['low'] > data[['open', 'close']].min(axis=1)
            
            invalid_ohlc = (invalid_high | invalid_low).sum()
            if invalid_ohlc > 0:
                logger.warning(f"   - OHLC逻辑: ❌ 发现 {invalid_ohlc} 条逻辑错误")
            else:
                logger.info(f"   - OHLC逻辑: ✅ 正常")
        
        # 检查成交量
        if 'volume' in data.columns:
            volume = data['volume']
            zero_volume = (volume == 0).sum()
            negative_volume = (volume < 0).sum()
            
            logger.info(f"   - 成交量检查:")
            logger.info(f"     范围: {volume.min()} - {volume.max()}")
            if zero_volume > 0:
                logger.warning(f"     ⚠️ 零成交量: {zero_volume} 个")
            if negative_volume > 0:
                logger.warning(f"     ❌ 负成交量: {negative_volume} 个")
    
    def _diagnose_technical_indicators(self, weekly_data: pd.DataFrame, backtest_start: str):
        """诊断技术指标计算"""
        
        try:
            # 计算技术指标
            logger.info(f"   - 计算技术指标...")
            indicators_data = self.data_processor.calculate_technical_indicators(weekly_data)
            
            # 分析各个时间段的技术指标
            backtest_start_dt = datetime.strptime(backtest_start, "%Y-%m-%d")
            
            time_periods = [
                ("历史数据期", indicators_data.index.min(), backtest_start_dt),
                ("回测初期(2015-2017)", backtest_start_dt, backtest_start_dt + timedelta(days=365*2)),
                ("回测中期(2017-2019)", backtest_start_dt + timedelta(days=365*2), backtest_start_dt + timedelta(days=365*4)),
                ("回测后期(2019-2021)", backtest_start_dt + timedelta(days=365*4), backtest_start_dt + timedelta(days=365*6)),
                ("近期(2021至今)", backtest_start_dt + timedelta(days=365*6), indicators_data.index.max())
            ]
            
            for period_name, start_date, end_date in time_periods:
                logger.info(f"\n   📊 {period_name} ({start_date.strftime('%Y-%m-%d')} 到 {end_date.strftime('%Y-%m-%d')}):")
                
                period_data = indicators_data[(indicators_data.index >= start_date) & (indicators_data.index <= end_date)]
                
                if period_data.empty:
                    logger.warning(f"     ❌ 该时期无数据")
                    continue
                
                # 检查RSI
                if 'rsi' in period_data.columns:
                    rsi = period_data['rsi'].dropna()
                    if len(rsi) > 0:
                        logger.info(f"     RSI: 均值={rsi.mean():.2f}, 标准差={rsi.std():.2f}, 范围={rsi.min():.2f}-{rsi.max():.2f}")
                        
                        # 检查是否是直线
                        if rsi.std() < 0.1:
                            logger.warning(f"     ⚠️ RSI疑似直线 (标准差={rsi.std():.4f})")
                            logger.warning(f"     RSI前5个值: {rsi.head().values}")
                            logger.warning(f"     RSI后5个值: {rsi.tail().values}")
                    else:
                        logger.warning(f"     ❌ RSI全为NaN")
                
                # 检查EMA
                for ema_col in ['ema_20', 'ema_50', 'ema_60']:
                    if ema_col in period_data.columns:
                        ema = period_data[ema_col].dropna()
                        if len(ema) > 0:
                            logger.info(f"     {ema_col.upper()}: 有效值={len(ema)}, 范围={ema.min():.2f}-{ema.max():.2f}")
                        else:
                            logger.warning(f"     ❌ {ema_col.upper()}全为NaN")
                
                # 检查MACD
                if 'macd' in period_data.columns:
                    macd = period_data['macd'].dropna()
                    if len(macd) > 0:
                        logger.info(f"     MACD: 有效值={len(macd)}, 范围={macd.min():.4f}-{macd.max():.4f}")
                    else:
                        logger.warning(f"     ❌ MACD全为NaN")
                        
        except Exception as e:
            logger.error(f"   ❌ 技术指标计算失败: {str(e)}")
            import traceback
            logger.error(traceback.format_exc())
    
    def _diagnose_signal_generator(self, stock_code: str, weekly_data: pd.DataFrame, backtest_start: str):
        """诊断信号生成器"""
        
        try:
            # 加载配置
            backtest_settings = load_backtest_settings()
            
            logger.info(f"   - 找到配置: 回测设置")
            
            # 创建信号生成器
            signal_generator = SignalGenerator(backtest_settings)
            
            # 分析不同时期的信号生成
            backtest_start_dt = datetime.strptime(backtest_start, "%Y-%m-%d")
            
            # 检查2015-2019年期间的信号
            early_period = weekly_data[
                (weekly_data.index >= backtest_start_dt) & 
                (weekly_data.index <= backtest_start_dt + timedelta(days=365*4))
            ].copy()
            
            if not early_period.empty:
                logger.info(f"   - 分析2015-2019年期间信号生成...")
                
                # 添加技术指标
                early_with_indicators = self.data_processor.calculate_technical_indicators(early_period)
                
                # 生成信号
                for i, (date, row) in enumerate(early_with_indicators.iterrows()):
                    if i >= 10:  # 只检查前10个信号
                        break
                        
                    try:
                        signals = signal_generator.generate_signal(stock_code, early_with_indicators)
                        # 从信号结果中获取RSI值
                        current_rsi = signals.get('technical_indicators', {}).get('rsi_14w', row.get('rsi', 'NaN'))
                        logger.info(f"     {date.strftime('%Y-%m-%d')}: RSI={current_rsi:.2f}, 信号={signals.get('signal', 'UNKNOWN')}")
                        
                        # 检查是否使用了默认值
                        if abs(current_rsi - 70.0) < 0.01:
                            logger.warning(f"     ⚠️ RSI疑似使用默认值70")
                        
                    except Exception as e:
                        logger.error(f"     ❌ 信号生成失败 {date.strftime('%Y-%m-%d')}: {str(e)}")
                        
        except Exception as e:
            logger.error(f"   ❌ 信号生成器诊断失败: {str(e)}")
            import traceback
            logger.error(traceback.format_exc())

def compare_backtest_start_dates():
    """对比不同回测起始日期的差异"""
    logger.info("🔍 对比不同回测起始日期的差异")
    logger.info("=" * 80)
    
    diagnoser = EarlyDataQualityDiagnoser()
    
    # 对比三个不同的起始日期
    start_dates = [
        "2015-01-08",  # 用户发现问题的日期
        "2018-01-01",  # 中间日期
        "2021-01-01"   # 用户说没问题的日期
    ]
    
    test_stock = "601088"  # 中国神华
    
    for start_date in start_dates:
        logger.info(f"\n🗓️ 测试回测起始日期: {start_date}")
        logger.info("=" * 60)
        
        try:
            # 计算历史数据起始日期
            start_dt = datetime.strptime(start_date, "%Y-%m-%d")
            history_start = start_dt - timedelta(weeks=125)
            history_start_str = history_start.strftime("%Y-%m-%d")
            
            logger.info(f"📅 历史数据起始: {history_start_str}")
            logger.info(f"📅 回测开始: {start_date}")
            logger.info(f"📊 历史数据缓冲期: {(start_dt - history_start).days / 365.25:.1f} 年")
            
            # 获取数据
            stock_data = diagnoser.data_fetcher.get_stock_data(
                test_stock, 
                start_date=history_start_str,
                end_date="2023-01-01"
            )
            
            if stock_data is None or stock_data.empty:
                logger.error(f"❌ 无法获取 {start_date} 的数据")
                continue
            
            # 重采样为周线
            weekly_data = diagnoser.data_processor.resample_to_weekly(stock_data)
            
            # 计算技术指标
            indicators_data = diagnoser.data_processor.calculate_technical_indicators(weekly_data)
            
            # 分析回测期间的RSI
            backtest_data = indicators_data[indicators_data.index >= start_dt]
            
            if not backtest_data.empty and 'rsi' in backtest_data.columns:
                rsi_data = backtest_data['rsi'].dropna()
                
                if len(rsi_data) > 0:
                    logger.info(f"📈 回测期间RSI分析:")
                    logger.info(f"   - 数据点数: {len(rsi_data)}")
                    logger.info(f"   - 均值: {rsi_data.mean():.2f}")
                    logger.info(f"   - 标准差: {rsi_data.std():.4f}")
                    logger.info(f"   - 范围: {rsi_data.min():.2f} - {rsi_data.max():.2f}")
                    
                    # 检查前10个RSI值
                    logger.info(f"   - 前10个RSI值: {rsi_data.head(10).round(2).tolist()}")
                    
                    # 判断是否为直线
                    if rsi_data.std() < 0.1:
                        logger.warning(f"   ⚠️ RSI疑似直线 (标准差={rsi_data.std():.4f})")
                        # 检查是否所有值都相同
                        unique_values = rsi_data.nunique()
                        logger.warning(f"   ⚠️ RSI唯一值数量: {unique_values}")
                        if unique_values == 1:
                            logger.error(f"   ❌ 所有RSI值完全相同: {rsi_data.iloc[0]:.2f}")
                    else:
                        logger.info(f"   ✅ RSI正常波动")
                
                else:
                    logger.error(f"   ❌ 回测期间RSI全为NaN")
            else:
                logger.error(f"   ❌ 无回测数据或RSI列")
                
            # 测试信号生成器
            logger.info(f"\n🎯 测试信号生成器:")
            try:
                backtest_settings = load_backtest_settings()
                signal_generator = SignalGenerator(backtest_settings)
                
                # 测试前5个回测日期的信号生成
                test_dates = backtest_data.head(5)
                for i, (date, row) in enumerate(test_dates.iterrows()):
                    try:
                        # 获取到当前日期为止的所有历史数据
                        historical_data = weekly_data[weekly_data.index <= date]
                        
                        # 确保有足够的历史数据（至少60个数据点）
                        if len(historical_data) < 60:
                            logger.warning(f"   {date.strftime('%Y-%m-%d')}: 历史数据不足({len(historical_data)}个点)，跳过")
                            continue
                        
                        # 调用信号生成器
                        signals = signal_generator.generate_signal(test_stock, historical_data)
                        current_rsi = signals.get('technical_indicators', {}).get('rsi_14w', 'NaN')
                        signal_type = signals.get('signal', 'UNKNOWN')
                        
                        logger.info(f"   {date.strftime('%Y-%m-%d')}: RSI={current_rsi:.2f}, 信号={signal_type}")
                        
                        # 对比数据处理器计算的RSI
                        data_rsi = historical_data['rsi'].iloc[-1] if 'rsi' in historical_data.columns else 'NaN'
                        if isinstance(data_rsi, (int, float)) and isinstance(current_rsi, (int, float)):
                            rsi_diff = abs(current_rsi - data_rsi)
                            if rsi_diff > 0.01:
                                logger.warning(f"   ⚠️ RSI差异: 信号生成器={current_rsi:.2f}, 数据处理器={data_rsi:.2f}, 差异={rsi_diff:.4f}")
                            else:
                                logger.info(f"   ✅ RSI一致: {current_rsi:.2f}")
                        
                        # 检查是否是固定值
                        if isinstance(current_rsi, (int, float)):
                            if abs(current_rsi - 41.15) < 0.01 or abs(current_rsi - 50.0) < 0.01:  # 常见的固定值
                                logger.warning(f"   ⚠️ 发现疑似固定RSI值: {current_rsi}")
                            
                    except Exception as e:
                        logger.error(f"   ❌ 信号生成失败 {date.strftime('%Y-%m-%d')}: {str(e)}")
                        import traceback
                        logger.error(traceback.format_exc())
                        
            except Exception as e:
                logger.error(f"   ❌ 信号生成器测试失败: {str(e)}")
                
        except Exception as e:
            logger.error(f"❌ 测试 {start_date} 失败: {str(e)}")
            import traceback
            logger.error(traceback.format_exc())
    
    # 总结分析
    logger.info(f"\n📋 对比分析总结:")
    logger.info("=" * 80)
    logger.info("🔍 请检查上述日志，对比不同起始日期的差异:")
    logger.info("   1. 历史数据缓冲期长度的影响")
    logger.info("   2. RSI计算结果的差异")
    logger.info("   3. 信号生成器行为的差异")
    logger.info("   4. 数据边界效应的影响")

def main():
    """主函数"""
    logger.info("🚀 开始回测起始日期对比分析")
    logger.info("=" * 80)
    
    # 执行对比分析
    compare_backtest_start_dates()
    
    logger.info("\n📝 详细分析日志已保存到: data_quality_diagnosis.log")
    logger.info("🎯 对比分析完成，请查看不同起始日期的差异")

if __name__ == "__main__":
    main()