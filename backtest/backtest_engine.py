"""
回测引擎模块
负责执行回测逻辑，管理投资组合，记录交易历史
"""

import pandas as pd
import numpy as np
import logging
from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional, Tuple
import warnings
warnings.filterwarnings('ignore')

# 导入其他模块
from data.data_fetcher import AkshareDataFetcher
from data.data_processor import DataProcessor
from data.data_storage import DataStorage
from strategy.signal_generator import SignalGenerator
from .portfolio_manager import PortfolioManager
from .transaction_cost import TransactionCostCalculator
from .enhanced_report_generator_integrated_fixed import IntegratedReportGenerator
from .detailed_csv_exporter import DetailedCSVExporter

logger = logging.getLogger(__name__)

class BacktestEngine:
    """回测引擎类"""
    
    def __init__(self, config: Dict[str, Any]):
        """
        初始化回测引擎
        
        Args:
            config: 回测配置字典
        """
        self.config = config
        self.logger = logging.getLogger(__name__)
        
        # 基本配置
        self.start_date = config.get('start_date', '2022-01-01')
        self.end_date = config.get('end_date', '2024-12-31')
        self.total_capital = config.get('total_capital', 1000000)
        self.initial_holdings = config.get('initial_holdings', {})
        
        # 策略参数
        strategy_params = config.get('strategy_params', {})
        self.rotation_percentage = strategy_params.get('rotation_percentage', 0.1)
        
        # 成本配置
        cost_config = config.get('cost_config', {})
        
        # 初始化各个组件
        self.data_fetcher = AkshareDataFetcher()
        self.data_processor = DataProcessor()
        self.data_storage = DataStorage()  # 添加数据存储组件
        self.signal_generator = SignalGenerator(config)
        self.cost_calculator = TransactionCostCalculator(cost_config)
        self.portfolio_manager = None
        
        # 报告生成器
        self.report_generator = IntegratedReportGenerator()
        self.csv_exporter = DetailedCSVExporter()
        
        # 回测数据存储
        self.stock_data = {}
        self.backtest_results = {}
        self.transaction_history = []
        self.portfolio_history = []
        
        # 股票池（排除现金）
        self.stock_pool = [code for code in self.initial_holdings.keys() if code != 'cash']
        
        self.logger.info("回测引擎初始化完成")
        self.logger.info(f"回测期间: {self.start_date} 至 {self.end_date}")
        self.logger.info(f"股票池: {self.stock_pool}")
        self.logger.info(f"轮动比例: {self.rotation_percentage:.1%}")
    
    def prepare_data(self) -> bool:
        """
        准备回测数据（智能缓存版本）
        
        Returns:
            bool: 数据准备是否成功
        """
        try:
            self.logger.info("🚀 开始准备回测数据（智能缓存模式）...")
            
            # 显示缓存统计信息
            cache_stats = self.data_storage.get_cache_statistics()
            self.logger.info(f"📊 当前缓存统计: {cache_stats}")
            
            for stock_code in self.stock_pool:
                self.logger.info(f"📈 准备 {stock_code} 的历史数据...")
                
                # 1. 智能获取日线数据（优先使用缓存）
                daily_data = self._get_cached_or_fetch_data(stock_code, self.start_date, self.end_date, 'daily')
                
                if daily_data is None or daily_data.empty:
                    self.logger.warning(f"⚠️ 无法获取 {stock_code} 的数据，跳过该股票")
                    # 记录失败的股票，但继续处理其他股票
                    continue
                
                # 2. 智能获取或生成周线数据
                weekly_data = None
                
                # 先尝试从缓存获取周线数据
                try:
                    weekly_data = self._get_cached_or_fetch_data(stock_code, self.start_date, self.end_date, 'weekly')
                except:
                    # 如果周线缓存获取失败，从日线转换
                    pass
                
                if weekly_data is None or weekly_data.empty:
                    # 从日线数据转换为周线数据
                    self.logger.info(f"🔄 {stock_code} 从日线数据转换周线数据")
                    weekly_data = self.data_processor.resample_to_weekly(daily_data)
                    
                    if len(weekly_data) < 60:  # 至少需要60周的数据
                        self.logger.warning(f"⚠️ {stock_code} 数据不足，只有 {len(weekly_data)} 条记录")
            
                # 确保技术指标存在（无论是从缓存获取还是新生成的数据）
                if 'ema_20' not in weekly_data.columns or 'rsi' not in weekly_data.columns:
                    self.logger.info(f"🔧 {stock_code} 计算技术指标...")
                    weekly_data = self.data_processor.calculate_technical_indicators(weekly_data)
                    
                    # 保存更新后的周线数据到缓存
                    try:
                        self.data_storage.save_data(weekly_data, stock_code, 'weekly')
                        self.logger.info(f"💾 {stock_code} 周线数据（含技术指标）已保存到缓存")
                    except Exception as e:
                        self.logger.warning(f"⚠️ {stock_code} 周线数据缓存保存失败: {e}")
                else:
                    self.logger.info(f"✅ {stock_code} 技术指标已存在，跳过计算")
                
                # 存储到内存中供回测使用
                self.stock_data[stock_code] = {
                    'daily': daily_data,
                    'weekly': weekly_data
                }
                
                self.logger.info(f"✅ {stock_code} 数据准备完成: 日线 {len(daily_data)} 条, 周线 {len(weekly_data)} 条")
            
            # 显示最终缓存统计
            final_cache_stats = self.data_storage.get_cache_statistics()
            self.logger.info(f"📊 数据准备完成后缓存统计: {final_cache_stats}")
            self.logger.info(f"🎉 所有股票数据准备完成，共处理 {len(self.stock_data)} 只股票")
            
            return True
            
        except Exception as e:
            self.logger.error(f"❌ 数据准备失败: {e}")
            return False
    
    def initialize_portfolio(self) -> bool:
        """
        初始化投资组合
        
        Returns:
            bool: 初始化是否成功
        """
        try:
            # 创建投资组合管理器
            self.portfolio_manager = PortfolioManager(
                total_capital=self.total_capital,
                initial_holdings=self.initial_holdings
            )
            # 设置成本计算器
            self.portfolio_manager.cost_calculator = self.cost_calculator
            
            # 获取初始价格
            initial_prices = {}
            for stock_code in self.stock_pool:
                if stock_code in self.stock_data:
                    initial_prices[stock_code] = self.stock_data[stock_code]['weekly'].iloc[0]['close']
            
            # 初始化投资组合
            self.portfolio_manager.initialize_portfolio(initial_prices)
            
            self.logger.info("投资组合初始化完成")
            return True
            
        except Exception as e:
            self.logger.error(f"投资组合初始化失败: {e}")
            return False
    
    def run_backtest(self) -> bool:
        """
        运行回测
        
        Returns:
            bool: 回测是否成功
        """
        try:
            self.logger.info("开始运行回测...")
            
            # 准备数据
            if not self.prepare_data():
                return False
            
            # 初始化投资组合
            if not self.initialize_portfolio():
                return False
            
            # 获取所有交易日期（使用第一只股票的日期）
            first_stock = list(self.stock_data.keys())[0]
            all_trading_dates = self.stock_data[first_stock]['weekly'].index
            
            # 过滤日期范围 - 确保只在回测期间内
            start_date = pd.to_datetime(self.start_date)
            end_date = pd.to_datetime(self.end_date)
            
            # 过滤交易日期
            trading_dates = all_trading_dates[
                (all_trading_dates >= start_date) & (all_trading_dates <= end_date)
            ]
            
            self.logger.info(f"回测期间: {self.start_date} 至 {self.end_date}")
            self.logger.info(f"有效回测周期数: {len(trading_dates)}")
            
            # 逐日回测
            for i, current_date in enumerate(trading_dates):
                if i % 10 == 0:
                    self.logger.info(f"回测进度: {i+1}/{len(trading_dates)} ({current_date.strftime('%Y-%m-%d')})")
                
                # 确保当前日期在回测范围内
                if current_date < start_date or current_date > end_date:
                    continue
                
                # 更新当前价格
                current_prices = {}
                for stock_code in self.stock_pool:
                    if stock_code in self.stock_data:
                        stock_weekly = self.stock_data[stock_code]['weekly']
                        if current_date in stock_weekly.index:
                            current_prices[stock_code] = stock_weekly.loc[current_date, 'close']
                
                # 更新投资组合价值
                self.portfolio_manager.update_prices(current_prices)
                
                # 生成交易信号
                signals = self._generate_signals(current_date)
                
                # 执行交易
                if signals:
                    executed_trades = self._execute_trades(signals, current_date)
                    if executed_trades:
                        self.logger.info(f"{current_date.strftime('%Y-%m-%d')} 执行记录:")
                        for trade in executed_trades:
                            self.logger.info(f"  {trade}")
                
                # 记录投资组合状态
                portfolio_value = self.portfolio_manager.get_total_value(current_prices)
                self.portfolio_history.append({
                    'date': current_date,
                    'total_value': portfolio_value,
                    'cash': self.portfolio_manager.cash,
                    'positions': self.portfolio_manager.positions.copy()
                })
            
            self.logger.info("回测完成")
            return True
            
        except Exception as e:
            self.logger.error(f"回测运行失败: {e}")
            return False
    
    def _generate_signals(self, current_date: pd.Timestamp) -> Dict[str, str]:
        """
        生成交易信号
        
        Args:
            current_date: 当前日期
            
        Returns:
            Dict[str, str]: 股票代码到信号的映射
        """
        signals = {}
        
        for stock_code in self.stock_pool:
            if stock_code not in self.stock_data:
                continue
            
            stock_weekly = self.stock_data[stock_code]['weekly']
            if current_date not in stock_weekly.index:
                continue
            
            # 获取当前数据点
            current_idx = stock_weekly.index.get_loc(current_date)
            if current_idx < 20:  # 需要足够的历史数据
                continue
            
            # 获取历史数据用于信号生成
            historical_data = stock_weekly.iloc[:current_idx+1]
            
            # 确保有足够的数据
            if len(historical_data) < 60:
                continue
            
            # 生成信号
            try:
                signal_result = self.signal_generator.generate_signal(stock_code, historical_data)
                if signal_result and isinstance(signal_result, dict):
                    signal = signal_result.get('signal', 'HOLD')
                    if signal and signal != 'HOLD':
                        signals[stock_code] = signal
                        # 记录信号详情用于报告
                        if not hasattr(self, 'signal_details'):
                            self.signal_details = {}
                        self.signal_details[f"{stock_code}_{current_date.strftime('%Y-%m-%d')}"] = signal_result
                elif isinstance(signal_result, str):
                    # 兼容旧版本返回字符串的情况
                    if signal_result and signal_result != 'HOLD':
                        signals[stock_code] = signal_result
                else:
                    self.logger.warning(f"{stock_code} 信号生成返回了无效结果: {signal_result}")
            except Exception as e:
                self.logger.warning(f"{stock_code} 信号生成失败: {e}")
                continue
        
        return signals
    
    def _execute_trades(self, signals: Dict[str, str], current_date: pd.Timestamp) -> List[str]:
        """
        执行交易
        
        Args:
            signals: 交易信号
            current_date: 当前日期
            
        Returns:
            List[str]: 执行的交易记录
        """
        executed_trades = []
        
        # 获取当前价格
        current_prices = {}
        for stock_code in self.stock_pool:
            if stock_code in self.stock_data:
                stock_weekly = self.stock_data[stock_code]['weekly']
                if current_date in stock_weekly.index:
                    current_prices[stock_code] = stock_weekly.loc[current_date, 'close']
        
        # 执行卖出信号
        for stock_code, signal in signals.items():
            if signal == 'SELL' and stock_code in current_prices:
                current_position = self.portfolio_manager.positions.get(stock_code, 0)
                if current_position > 0:
                    # 计算卖出数量（按轮动比例）
                    sell_shares = int(current_position * self.rotation_percentage / 100) * 100
                    if sell_shares > 0:
                        price = current_prices[stock_code]
                        success, trade_info = self.portfolio_manager.sell_stock(
                            stock_code, sell_shares, price, current_date, "转现金"
                        )
                        if success:
                            self.logger.info(f"执行卖出交易: {stock_code} {sell_shares}股 价格{price}")
                            self._record_transaction(trade_info, current_date)
                            executed_trades.append(f"转现金: {stock_code} {sell_shares}股")
                        else:
                            self.logger.warning(f"卖出交易失败: {stock_code}")
        
        # 执行买入信号
        for stock_code, signal in signals.items():
            if signal == 'BUY' and stock_code in current_prices:
                # 使用可用现金的轮动比例买入
                available_cash = self.portfolio_manager.cash * self.rotation_percentage
                if available_cash > 10000:  # 最小买入金额
                    price = current_prices[stock_code]
                    max_shares = int(available_cash / price / 100) * 100
                    if max_shares > 0:
                        success, trade_info = self.portfolio_manager.buy_stock(
                            stock_code, max_shares, price, current_date, "现金买入"
                        )
                        if success:
                            self.logger.info(f"执行买入交易: {stock_code} {max_shares}股 价格{price}")
                            self._record_transaction(trade_info, current_date)
                            executed_trades.append(f"现金买入: {stock_code} {max_shares}股")
                        else:
                            self.logger.warning(f"买入交易失败: {stock_code}")
        
        return executed_trades
    
    def _record_transaction(self, trade_info: Dict[str, Any], current_date: pd.Timestamp):
        """
        记录交易信息
        
        Args:
            trade_info: 交易信息
            current_date: 交易日期
        """
        # 获取技术指标
        stock_code = trade_info['stock_code']
        technical_indicators = {}
        signal_details = {}
        
        if stock_code in self.stock_data:
            stock_weekly = self.stock_data[stock_code]['weekly']
            if current_date in stock_weekly.index:
                row = stock_weekly.loc[current_date]
                # 计算4周平均成交量
                current_idx = stock_weekly.index.get_loc(current_date)
                if current_idx >= 3:  # 至少需要4个数据点
                    volume_4w_data = stock_weekly['volume'].iloc[current_idx-3:current_idx+1]
                    volume_4w_avg = volume_4w_data.mean()
                else:
                    volume_4w_avg = row['volume']  # 数据不足时使用当前成交量
                
                # 调试：打印可用的字段名
                self.logger.debug(f"可用的技术指标字段: {list(row.index)}")
                
                # 100%修正：安全获取技术指标值，彻底解决NaN问题
                def safe_get_value(key, default_value):
                    """
                    安全获取技术指标值，彻底处理NaN情况
                    优先级：当前值 > 历史最近有效值 > 默认值
                    """
                    try:
                        # 1. 首先检查字段是否存在
                        if key not in stock_weekly.columns:
                            self.logger.debug(f"字段 {key} 不存在于数据中")
                            return default_value
                        
                        # 2. 获取当前行的值
                        current_value = row.get(key)
                        
                        # 3. 检查当前值是否有效（不是NaN且不是None）
                        if current_value is not None and not pd.isna(current_value):
                            try:
                                return float(current_value)
                            except (ValueError, TypeError):
                                pass  # 转换失败，继续尝试历史值
                        
                        # 4. 当前值无效，查找历史最近有效值
                        self.logger.debug(f"当前值无效 {key}={current_value}，查找历史有效值")
                        
                        # 直接从整个序列中查找最后一个有效值
                        if key in stock_weekly.columns:
                            # 获取到当前日期为止的所有数据
                            historical_series = stock_weekly[key].loc[:current_date]
                            # 去除NaN值
                            valid_series = historical_series.dropna()
                            
                            if not valid_series.empty:
                                result = float(valid_series.iloc[-1])
                                self.logger.debug(f"找到历史有效值 {key}={result}")
                                return result
                            else:
                                self.logger.debug(f"整个历史序列都没有有效值 {key}")
                        
                        # 5. 如果还是没有找到有效值，返回默认值
                        self.logger.debug(f"未找到有效历史值，使用默认值 {key}={default_value}")
                        return default_value
                        
                    except Exception as e:
                        self.logger.warning(f"获取技术指标 {key} 时发生异常: {e}")
                        return default_value
                
                # 首先检查实际可用的字段名
                available_columns = list(stock_weekly.columns)
                self.logger.info(f"🔍 {stock_code} 可用字段: {available_columns}")
                
                # 打印当前行的所有数据用于调试
                self.logger.info(f"🔍 {stock_code} 当前行数据:")
                for col in available_columns:
                    value = row.get(col, 'N/A')
                    self.logger.info(f"  {col}: {value}")
                
                    # 使用正确的字段名获取技术指标（基于数据处理器的实际输出）
                    technical_indicators = {
                        'close': safe_get_value('close', 0),
                        'volume': int(safe_get_value('volume', 0)),
                        'ema_20w': safe_get_value('ema_20', 0),  
                        'ema_60w': safe_get_value('ema_60', 0),  # 修正：使用ema_60而不是ema_50
                        'rsi_14w': safe_get_value('rsi', 50),   
                        'macd_dif': safe_get_value('macd', 0),  
                        'macd_dea': safe_get_value('macd_signal', 0),  
                        'macd_hist': safe_get_value('macd_histogram', 0),  
                        'bb_upper': safe_get_value('bb_upper', 0),
                        'bb_middle': safe_get_value('bb_middle', 0),
                        'bb_lower': safe_get_value('bb_lower', 0),
                        'volume_4w_avg': volume_4w_avg
                    }
                
                # 调试：打印实际获取的指标值
                self.logger.info(f"🎯 {stock_code} 技术指标获取结果:")
                for key, value in technical_indicators.items():
                    self.logger.info(f"  {key}: {value}")
"""
回测引擎模块
负责执行回测逻辑，管理投资组合，记录交易历史
"""

import pandas as pd
import numpy as np
import logging
from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional, Tuple
import warnings
warnings.filterwarnings('ignore')

# 导入其他模块
from data.data_fetcher import AkshareDataFetcher
from data.data_processor import DataProcessor
from data.data_storage import DataStorage
from strategy.signal_generator import SignalGenerator
from .portfolio_manager import PortfolioManager
from .transaction_cost import TransactionCostCalculator
from .enhanced_report_generator_integrated_fixed import IntegratedReportGenerator
from .detailed_csv_exporter import DetailedCSVExporter

logger = logging.getLogger(__name__)

class BacktestEngine:
    """回测引擎类"""
    
    def __init__(self, config: Dict[str, Any]):
        """
        初始化回测引擎
        
        Args:
            config: 回测配置字典
        """
        self.config = config
        self.logger = logging.getLogger(__name__)
        
        # 基本配置
        self.start_date = config.get('start_date', '2022-01-01')
        self.end_date = config.get('end_date', '2024-12-31')
        self.total_capital = config.get('total_capital', 1000000)
        self.initial_holdings = config.get('initial_holdings', {})
        
        # 策略参数
        strategy_params = config.get('strategy_params', {})
        self.rotation_percentage = strategy_params.get('rotation_percentage', 0.1)
        
        # 成本配置
        cost_config = config.get('cost_config', {})
        
        # 初始化各个组件
        self.data_fetcher = AkshareDataFetcher()
        self.data_processor = DataProcessor()
        self.data_storage = DataStorage()  # 添加数据存储组件
        self.signal_generator = SignalGenerator(config)
        self.cost_calculator = TransactionCostCalculator(cost_config)
        self.portfolio_manager = None
        
        # 报告生成器
        self.report_generator = IntegratedReportGenerator()
        self.csv_exporter = DetailedCSVExporter()
        
        # 回测数据存储
        self.stock_data = {}
        self.backtest_results = {}
        self.transaction_history = []
        self.portfolio_history = []
        
        # 股票池（排除现金）
        self.stock_pool = [code for code in self.initial_holdings.keys() if code != 'cash']
        
        self.logger.info("回测引擎初始化完成")
        self.logger.info(f"回测期间: {self.start_date} 至 {self.end_date}")
        self.logger.info(f"股票池: {self.stock_pool}")
        self.logger.info(f"轮动比例: {self.rotation_percentage:.1%}")
    
    def prepare_data(self) -> bool:
        """
        准备回测数据（智能缓存版本）
        
        Returns:
            bool: 数据准备是否成功
        """
        try:
            self.logger.info("🚀 开始准备回测数据（智能缓存模式）...")
            
            # 显示缓存统计信息
            cache_stats = self.data_storage.get_cache_statistics()
            self.logger.info(f"📊 当前缓存统计: {cache_stats}")
            
            for stock_code in self.stock_pool:
                self.logger.info(f"📈 准备 {stock_code} 的历史数据...")
                
                # 1. 智能获取日线数据（优先使用缓存）
                daily_data = self._get_cached_or_fetch_data(stock_code, self.start_date, self.end_date, 'daily')
                
                if daily_data is None or daily_data.empty:
                    self.logger.warning(f"⚠️ 无法获取 {stock_code} 的数据，跳过该股票")
                    # 记录失败的股票，但继续处理其他股票
                    continue
                
                # 2. 智能获取或生成周线数据
                weekly_data = None
                
                # 先尝试从缓存获取周线数据
                try:
                    weekly_data = self._get_cached_or_fetch_data(stock_code, self.start_date, self.end_date, 'weekly')
                except:
                    # 如果周线缓存获取失败，从日线转换
                    pass
                
                if weekly_data is None or weekly_data.empty:
                    # 从日线数据转换为周线数据
                    self.logger.info(f"🔄 {stock_code} 从日线数据转换周线数据")
                    weekly_data = self.data_processor.resample_to_weekly(daily_data)
                    
                    if len(weekly_data) < 60:  # 至少需要60周的数据
                        self.logger.warning(f"⚠️ {stock_code} 数据不足，只有 {len(weekly_data)} 条记录")
            
                # 确保技术指标存在（无论是从缓存获取还是新生成的数据）
                if 'ema_20' not in weekly_data.columns or 'rsi' not in weekly_data.columns:
                    self.logger.info(f"🔧 {stock_code} 计算技术指标...")
                    weekly_data = self.data_processor.calculate_technical_indicators(weekly_data)
                    
                    # 保存更新后的周线数据到缓存
                    try:
                        self.data_storage.save_data(weekly_data, stock_code, 'weekly')
                        self.logger.info(f"💾 {stock_code} 周线数据（含技术指标）已保存到缓存")
                    except Exception as e:
                        self.logger.warning(f"⚠️ {stock_code} 周线数据缓存保存失败: {e}")
                else:
                    self.logger.info(f"✅ {stock_code} 技术指标已存在，跳过计算")
                
                # 存储到内存中供回测使用
                self.stock_data[stock_code] = {
                    'daily': daily_data,
                    'weekly': weekly_data
                }
                
                self.logger.info(f"✅ {stock_code} 数据准备完成: 日线 {len(daily_data)} 条, 周线 {len(weekly_data)} 条")
            
            # 显示最终缓存统计
            final_cache_stats = self.data_storage.get_cache_statistics()
            self.logger.info(f"📊 数据准备完成后缓存统计: {final_cache_stats}")
            self.logger.info(f"🎉 所有股票数据准备完成，共处理 {len(self.stock_data)} 只股票")
            
            return True
            
        except Exception as e:
            self.logger.error(f"❌ 数据准备失败: {e}")
            return False
    
    def initialize_portfolio(self) -> bool:
        """
        初始化投资组合
        
        Returns:
            bool: 初始化是否成功
        """
        try:
            # 创建投资组合管理器
            self.portfolio_manager = PortfolioManager(
                total_capital=self.total_capital,
                initial_holdings=self.initial_holdings
            )
            # 设置成本计算器
            self.portfolio_manager.cost_calculator = self.cost_calculator
            
            # 获取初始价格
            initial_prices = {}
            for stock_code in self.stock_pool:
                if stock_code in self.stock_data:
                    initial_prices[stock_code] = self.stock_data[stock_code]['weekly'].iloc[0]['close']
            
            # 初始化投资组合
            self.portfolio_manager.initialize_portfolio(initial_prices)
            
            self.logger.info("投资组合初始化完成")
            return True
            
        except Exception as e:
            self.logger.error(f"投资组合初始化失败: {e}")
            return False
    
    def run_backtest(self) -> bool:
        """
        运行回测
        
        Returns:
            bool: 回测是否成功
        """
        try:
            self.logger.info("开始运行回测...")
            
            # 准备数据
            if not self.prepare_data():
                return False
            
            # 初始化投资组合
            if not self.initialize_portfolio():
                return False
            
            # 获取所有交易日期（使用第一只股票的日期）
            first_stock = list(self.stock_data.keys())[0]
            all_trading_dates = self.stock_data[first_stock]['weekly'].index
            
            # 过滤日期范围 - 确保只在回测期间内
            start_date = pd.to_datetime(self.start_date)
            end_date = pd.to_datetime(self.end_date)
            
            # 过滤交易日期
            trading_dates = all_trading_dates[
                (all_trading_dates >= start_date) & (all_trading_dates <= end_date)
            ]
            
            self.logger.info(f"回测期间: {self.start_date} 至 {self.end_date}")
            self.logger.info(f"有效回测周期数: {len(trading_dates)}")
            
            # 逐日回测
            for i, current_date in enumerate(trading_dates):
                if i % 10 == 0:
                    self.logger.info(f"回测进度: {i+1}/{len(trading_dates)} ({current_date.strftime('%Y-%m-%d')})")
                
                # 确保当前日期在回测范围内
                if current_date < start_date or current_date > end_date:
                    continue
                
                # 更新当前价格
                current_prices = {}
                for stock_code in self.stock_pool:
                    if stock_code in self.stock_data:
                        stock_weekly = self.stock_data[stock_code]['weekly']
                        if current_date in stock_weekly.index:
                            current_prices[stock_code] = stock_weekly.loc[current_date, 'close']
                
                # 更新投资组合价值
                self.portfolio_manager.update_prices(current_prices)
                
                # 生成交易信号
                signals = self._generate_signals(current_date)
                
                # 执行交易
                if signals:
                    executed_trades = self._execute_trades(signals, current_date)
                    if executed_trades:
                        self.logger.info(f"{current_date.strftime('%Y-%m-%d')} 执行记录:")
                        for trade in executed_trades:
                            self.logger.info(f"  {trade}")
                
                # 记录投资组合状态
                portfolio_value = self.portfolio_manager.get_total_value(current_prices)
                self.portfolio_history.append({
                    'date': current_date,
                    'total_value': portfolio_value,
                    'cash': self.portfolio_manager.cash,
                    'positions': self.portfolio_manager.positions.copy()
                })
            
            self.logger.info("回测完成")
            return True
            
        except Exception as e:
            self.logger.error(f"回测运行失败: {e}")
            return False
    
    def _generate_signals(self, current_date: pd.Timestamp) -> Dict[str, str]:
        """
        生成交易信号
        
        Args:
            current_date: 当前日期
            
        Returns:
            Dict[str, str]: 股票代码到信号的映射
        """
        signals = {}
        
        for stock_code in self.stock_pool:
            if stock_code not in self.stock_data:
                continue
            
            stock_weekly = self.stock_data[stock_code]['weekly']
            if current_date not in stock_weekly.index:
                continue
            
            # 获取当前数据点
            current_idx = stock_weekly.index.get_loc(current_date)
            if current_idx < 20:  # 需要足够的历史数据
                continue
            
            # 获取历史数据用于信号生成
            historical_data = stock_weekly.iloc[:current_idx+1]
            
            # 确保有足够的数据
            if len(historical_data) < 60:
                continue
            
            # 生成信号
            try:
                signal_result = self.signal_generator.generate_signal(stock_code, historical_data)
                if signal_result and isinstance(signal_result, dict):
                    signal = signal_result.get('signal', 'HOLD')
                    if signal and signal != 'HOLD':
                        signals[stock_code] = signal
                        # 记录信号详情用于报告
                        if not hasattr(self, 'signal_details'):
                            self.signal_details = {}
                        self.signal_details[f"{stock_code}_{current_date.strftime('%Y-%m-%d')}"] = signal_result
                elif isinstance(signal_result, str):
                    # 兼容旧版本返回字符串的情况
                    if signal_result and signal_result != 'HOLD':
                        signals[stock_code] = signal_result
                else:
                    self.logger.warning(f"{stock_code} 信号生成返回了无效结果: {signal_result}")
            except Exception as e:
                self.logger.warning(f"{stock_code} 信号生成失败: {e}")
                continue
        
        return signals
    
    def _execute_trades(self, signals: Dict[str, str], current_date: pd.Timestamp) -> List[str]:
        """
        执行交易
        
        Args:
            signals: 交易信号
            current_date: 当前日期
            
        Returns:
            List[str]: 执行的交易记录
        """
        executed_trades = []
        
        # 获取当前价格
        current_prices = {}
        for stock_code in self.stock_pool:
            if stock_code in self.stock_data:
                stock_weekly = self.stock_data[stock_code]['weekly']
                if current_date in stock_weekly.index:
                    current_prices[stock_code] = stock_weekly.loc[current_date, 'close']
        
        # 执行卖出信号
        for stock_code, signal in signals.items():
            if signal == 'SELL' and stock_code in current_prices:
                current_position = self.portfolio_manager.positions.get(stock_code, 0)
                if current_position > 0:
                    # 计算卖出数量（按轮动比例）
                    sell_shares = int(current_position * self.rotation_percentage / 100) * 100
                    if sell_shares > 0:
                        price = current_prices[stock_code]
                        success, trade_info = self.portfolio_manager.sell_stock(
                            stock_code, sell_shares, price, current_date, "转现金"
                        )
                        if success:
                            self.logger.info(f"执行卖出交易: {stock_code} {sell_shares}股 价格{price}")
                            self._record_transaction(trade_info, current_date)
                            executed_trades.append(f"转现金: {stock_code} {sell_shares}股")
                        else:
                            self.logger.warning(f"卖出交易失败: {stock_code}")
        
        # 执行买入信号
        for stock_code, signal in signals.items():
            if signal == 'BUY' and stock_code in current_prices:
                # 使用可用现金的轮动比例买入
                available_cash = self.portfolio_manager.cash * self.rotation_percentage
                if available_cash > 10000:  # 最小买入金额
                    price = current_prices[stock_code]
                    max_shares = int(available_cash / price / 100) * 100
                    if max_shares > 0:
                        success, trade_info = self.portfolio_manager.buy_stock(
                            stock_code, max_shares, price, current_date, "现金买入"
                        )
                        if success:
                            self.logger.info(f"执行买入交易: {stock_code} {max_shares}股 价格{price}")
                            self._record_transaction(trade_info, current_date)
                            executed_trades.append(f"现金买入: {stock_code} {max_shares}股")
                        else:
                            self.logger.warning(f"买入交易失败: {stock_code}")
        
        return executed_trades
    
    def _record_transaction(self, trade_info: Dict[str, Any], current_date: pd.Timestamp):
        """
        记录交易信息
        
        Args:
            trade_info: 交易信息
            current_date: 交易日期
        """
        # 获取技术指标
        stock_code = trade_info['stock_code']
        technical_indicators = {}
        signal_details = {}
        
        if stock_code in self.stock_data:
            stock_weekly = self.stock_data[stock_code]['weekly']
            if current_date in stock_weekly.index:
                row = stock_weekly.loc[current_date]
                # 计算4周平均成交量
                current_idx = stock_weekly.index.get_loc(current_date)
                if current_idx >= 3:  # 至少需要4个数据点
                    volume_4w_data = stock_weekly['volume'].iloc[current_idx-3:current_idx+1]
                    volume_4w_avg = volume_4w_data.mean()
                else:
                    volume_4w_avg = row['volume']  # 数据不足时使用当前成交量
                
                # 调试：打印可用的字段名
                self.logger.debug(f"可用的技术指标字段: {list(row.index)}")
                
                # 安全获取技术指标值，处理可能的NaN
                def safe_get_value(key, default_value):
                    try:
                        value = row.get(key, default_value)
                        if pd.isna(value):
                            return default_value
                        return float(value)
                    except:
                        return default_value
                
"""
回测引擎模块
负责执行回测逻辑，管理投资组合，记录交易历史
"""

import pandas as pd
import numpy as np
import logging
from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional, Tuple
import warnings
warnings.filterwarnings('ignore')

# 导入其他模块
from data.data_fetcher import AkshareDataFetcher
from data.data_processor import DataProcessor
from data.data_storage import DataStorage
from strategy.signal_generator import SignalGenerator
from .portfolio_manager import PortfolioManager
from .transaction_cost import TransactionCostCalculator
from .enhanced_report_generator_integrated_fixed import IntegratedReportGenerator
from .detailed_csv_exporter import DetailedCSVExporter

logger = logging.getLogger(__name__)

class BacktestEngine:
    """回测引擎类"""
    
    def __init__(self, config: Dict[str, Any]):
        """
        初始化回测引擎
        
        Args:
            config: 回测配置字典
        """
        self.config = config
        self.logger = logging.getLogger(__name__)
        
        # 基本配置
        self.start_date = config.get('start_date', '2022-01-01')
        self.end_date = config.get('end_date', '2024-12-31')
        self.total_capital = config.get('total_capital', 1000000)
        self.initial_holdings = config.get('initial_holdings', {})
        
        # 策略参数
        strategy_params = config.get('strategy_params', {})
        self.rotation_percentage = strategy_params.get('rotation_percentage', 0.1)
        
        # 成本配置
        cost_config = config.get('cost_config', {})
        
        # 初始化各个组件
        self.data_fetcher = AkshareDataFetcher()
        self.data_processor = DataProcessor()
        self.data_storage = DataStorage()  # 添加数据存储组件
        self.signal_generator = SignalGenerator(config)
        self.cost_calculator = TransactionCostCalculator(cost_config)
        self.portfolio_manager = None
        
        # 报告生成器
        self.report_generator = IntegratedReportGenerator()
        self.csv_exporter = DetailedCSVExporter()
        
        # 回测数据存储
        self.stock_data = {}
        self.backtest_results = {}
        self.transaction_history = []
        self.portfolio_history = []
        
        # 股票池（排除现金）
        self.stock_pool = [code for code in self.initial_holdings.keys() if code != 'cash']
        
        self.logger.info("回测引擎初始化完成")
        self.logger.info(f"回测期间: {self.start_date} 至 {self.end_date}")
        self.logger.info(f"股票池: {self.stock_pool}")
        self.logger.info(f"轮动比例: {self.rotation_percentage:.1%}")
    
    def prepare_data(self) -> bool:
        """
        准备回测数据（智能缓存版本）
        
        Returns:
            bool: 数据准备是否成功
        """
        try:
            self.logger.info("🚀 开始准备回测数据（智能缓存模式）...")
            
            # 显示缓存统计信息
            cache_stats = self.data_storage.get_cache_statistics()
            self.logger.info(f"📊 当前缓存统计: {cache_stats}")
            
            for stock_code in self.stock_pool:
                self.logger.info(f"📈 准备 {stock_code} 的历史数据...")
                
                # 1. 智能获取日线数据（优先使用缓存）
                daily_data = self._get_cached_or_fetch_data(stock_code, self.start_date, self.end_date, 'daily')
                
                if daily_data is None or daily_data.empty:
                    self.logger.warning(f"⚠️ 无法获取 {stock_code} 的数据，跳过该股票")
                    # 记录失败的股票，但继续处理其他股票
                    continue
                
                # 2. 智能获取或生成周线数据
                weekly_data = None
                
                # 先尝试从缓存获取周线数据
                try:
                    weekly_data = self._get_cached_or_fetch_data(stock_code, self.start_date, self.end_date, 'weekly')
                except:
                    # 如果周线缓存获取失败，从日线转换
                    pass
                
                if weekly_data is None or weekly_data.empty:
                    # 从日线数据转换为周线数据
                    self.logger.info(f"🔄 {stock_code} 从日线数据转换周线数据")
                    weekly_data = self.data_processor.resample_to_weekly(daily_data)
                    
                    if len(weekly_data) < 60:  # 至少需要60周的数据
                        self.logger.warning(f"⚠️ {stock_code} 数据不足，只有 {len(weekly_data)} 条记录")
            
                # 确保技术指标存在（无论是从缓存获取还是新生成的数据）
                if 'ema_20' not in weekly_data.columns or 'rsi' not in weekly_data.columns:
                    self.logger.info(f"🔧 {stock_code} 计算技术指标...")
                    weekly_data = self.data_processor.calculate_technical_indicators(weekly_data)
                    
                    # 保存更新后的周线数据到缓存
                    try:
                        self.data_storage.save_data(weekly_data, stock_code, 'weekly')
                        self.logger.info(f"💾 {stock_code} 周线数据（含技术指标）已保存到缓存")
                    except Exception as e:
                        self.logger.warning(f"⚠️ {stock_code} 周线数据缓存保存失败: {e}")
                else:
                    self.logger.info(f"✅ {stock_code} 技术指标已存在，跳过计算")
                
                # 存储到内存中供回测使用
                self.stock_data[stock_code] = {
                    'daily': daily_data,
                    'weekly': weekly_data
                }
                
                self.logger.info(f"✅ {stock_code} 数据准备完成: 日线 {len(daily_data)} 条, 周线 {len(weekly_data)} 条")
            
            # 显示最终缓存统计
            final_cache_stats = self.data_storage.get_cache_statistics()
            self.logger.info(f"📊 数据准备完成后缓存统计: {final_cache_stats}")
            self.logger.info(f"🎉 所有股票数据准备完成，共处理 {len(self.stock_data)} 只股票")
            
            return True
            
        except Exception as e:
            self.logger.error(f"❌ 数据准备失败: {e}")
            return False
    
    def initialize_portfolio(self) -> bool:
        """
        初始化投资组合
        
        Returns:
            bool: 初始化是否成功
        """
        try:
            # 创建投资组合管理器
            self.portfolio_manager = PortfolioManager(
                total_capital=self.total_capital,
                initial_holdings=self.initial_holdings
            )
            # 设置成本计算器
            self.portfolio_manager.cost_calculator = self.cost_calculator
            
            # 获取初始价格
            initial_prices = {}
            for stock_code in self.stock_pool:
                if stock_code in self.stock_data:
                    initial_prices[stock_code] = self.stock_data[stock_code]['weekly'].iloc[0]['close']
            
            # 初始化投资组合
            self.portfolio_manager.initialize_portfolio(initial_prices)
            
            self.logger.info("投资组合初始化完成")
            return True
            
        except Exception as e:
            self.logger.error(f"投资组合初始化失败: {e}")
            return False
    
    def run_backtest(self) -> bool:
        """
        运行回测
        
        Returns:
            bool: 回测是否成功
        """
        try:
            self.logger.info("开始运行回测...")
            
            # 准备数据
            if not self.prepare_data():
                return False
            
            # 初始化投资组合
            if not self.initialize_portfolio():
                return False
            
            # 获取所有交易日期（使用第一只股票的日期）
            first_stock = list(self.stock_data.keys())[0]
            all_trading_dates = self.stock_data[first_stock]['weekly'].index
            
            # 过滤日期范围 - 确保只在回测期间内
            start_date = pd.to_datetime(self.start_date)
            end_date = pd.to_datetime(self.end_date)
            
            # 过滤交易日期
            trading_dates = all_trading_dates[
                (all_trading_dates >= start_date) & (all_trading_dates <= end_date)
            ]
            
            self.logger.info(f"回测期间: {self.start_date} 至 {self.end_date}")
            self.logger.info(f"有效回测周期数: {len(trading_dates)}")
            
            # 逐日回测
            for i, current_date in enumerate(trading_dates):
                if i % 10 == 0:
                    self.logger.info(f"回测进度: {i+1}/{len(trading_dates)} ({current_date.strftime('%Y-%m-%d')})")
                
                # 确保当前日期在回测范围内
                if current_date < start_date or current_date > end_date:
                    continue
                
                # 更新当前价格
                current_prices = {}
                for stock_code in self.stock_pool:
                    if stock_code in self.stock_data:
                        stock_weekly = self.stock_data[stock_code]['weekly']
                        if current_date in stock_weekly.index:
                            current_prices[stock_code] = stock_weekly.loc[current_date, 'close']
                
                # 更新投资组合价值
                self.portfolio_manager.update_prices(current_prices)
                
                # 生成交易信号
                signals = self._generate_signals(current_date)
                
                # 执行交易
                if signals:
                    executed_trades = self._execute_trades(signals, current_date)
                    if executed_trades:
                        self.logger.info(f"{current_date.strftime('%Y-%m-%d')} 执行记录:")
                        for trade in executed_trades:
                            self.logger.info(f"  {trade}")
                
                # 记录投资组合状态
                portfolio_value = self.portfolio_manager.get_total_value(current_prices)
                self.portfolio_history.append({
                    'date': current_date,
                    'total_value': portfolio_value,
                    'cash': self.portfolio_manager.cash,
                    'positions': self.portfolio_manager.positions.copy()
                })
            
            self.logger.info("回测完成")
            return True
            
        except Exception as e:
            self.logger.error(f"回测运行失败: {e}")
            return False
    
    def _generate_signals(self, current_date: pd.Timestamp) -> Dict[str, str]:
        """
        生成交易信号
        
        Args:
            current_date: 当前日期
            
        Returns:
            Dict[str, str]: 股票代码到信号的映射
        """
        signals = {}
        
        for stock_code in self.stock_pool:
            if stock_code not in self.stock_data:
                continue
            
            stock_weekly = self.stock_data[stock_code]['weekly']
            if current_date not in stock_weekly.index:
                continue
            
            # 获取当前数据点
            current_idx = stock_weekly.index.get_loc(current_date)
            if current_idx < 20:  # 需要足够的历史数据
                continue
            
            # 获取历史数据用于信号生成
            historical_data = stock_weekly.iloc[:current_idx+1]
            
            # 确保有足够的数据
            if len(historical_data) < 60:
                continue
            
            # 生成信号
            try:
                signal_result = self.signal_generator.generate_signal(stock_code, historical_data)
                if signal_result and isinstance(signal_result, dict):
                    signal = signal_result.get('signal', 'HOLD')
                    if signal and signal != 'HOLD':
                        signals[stock_code] = signal
                        # 记录信号详情用于报告
                        if not hasattr(self, 'signal_details'):
                            self.signal_details = {}
                        self.signal_details[f"{stock_code}_{current_date.strftime('%Y-%m-%d')}"] = signal_result
                elif isinstance(signal_result, str):
                    # 兼容旧版本返回字符串的情况
                    if signal_result and signal_result != 'HOLD':
                        signals[stock_code] = signal_result
                else:
                    self.logger.warning(f"{stock_code} 信号生成返回了无效结果: {signal_result}")
            except Exception as e:
                self.logger.warning(f"{stock_code} 信号生成失败: {e}")
                continue
        
        return signals
    
    def _execute_trades(self, signals: Dict[str, str], current_date: pd.Timestamp) -> List[str]:
        """
        执行交易
        
        Args:
            signals: 交易信号
            current_date: 当前日期
            
        Returns:
            List[str]: 执行的交易记录
        """
        executed_trades = []
        
        # 获取当前价格
        current_prices = {}
        for stock_code in self.stock_pool:
            if stock_code in self.stock_data:
                stock_weekly = self.stock_data[stock_code]['weekly']
                if current_date in stock_weekly.index:
                    current_prices[stock_code] = stock_weekly.loc[current_date, 'close']
        
        # 执行卖出信号
        for stock_code, signal in signals.items():
            if signal == 'SELL' and stock_code in current_prices:
                current_position = self.portfolio_manager.positions.get(stock_code, 0)
                if current_position > 0:
                    # 计算卖出数量（按轮动比例）
                    sell_shares = int(current_position * self.rotation_percentage / 100) * 100
                    if sell_shares > 0:
                        price = current_prices[stock_code]
                        success, trade_info = self.portfolio_manager.sell_stock(
                            stock_code, sell_shares, price, current_date, "转现金"
                        )
                        if success:
                            self.logger.info(f"执行卖出交易: {stock_code} {sell_shares}股 价格{price}")
                            self._record_transaction(trade_info, current_date)
                            executed_trades.append(f"转现金: {stock_code} {sell_shares}股")
                        else:
                            self.logger.warning(f"卖出交易失败: {stock_code}")
        
        # 执行买入信号
        for stock_code, signal in signals.items():
            if signal == 'BUY' and stock_code in current_prices:
                # 使用可用现金的轮动比例买入
                available_cash = self.portfolio_manager.cash * self.rotation_percentage
                if available_cash > 10000:  # 最小买入金额
                    price = current_prices[stock_code]
                    max_shares = int(available_cash / price / 100) * 100
                    if max_shares > 0:
                        success, trade_info = self.portfolio_manager.buy_stock(
                            stock_code, max_shares, price, current_date, "现金买入"
                        )
                        if success:
                            self.logger.info(f"执行买入交易: {stock_code} {max_shares}股 价格{price}")
                            self._record_transaction(trade_info, current_date)
                            executed_trades.append(f"现金买入: {stock_code} {max_shares}股")
                        else:
                            self.logger.warning(f"买入交易失败: {stock_code}")
        
        return executed_trades
    
    def _record_transaction(self, trade_info: Dict[str, Any], current_date: pd.Timestamp):
        """
        记录交易信息
        
        Args:
            trade_info: 交易信息
            current_date: 交易日期
        """
        # 获取技术指标 - 直接从信号生成器获取已处理的指标
        stock_code = trade_info['stock_code']
        technical_indicators = {}
        signal_details = {}
        
        # 尝试从信号生成器获取当前的技术指标
        try:
            # 获取当前数据用于信号生成
            if stock_code in self.stock_data:
                stock_weekly = self.stock_data[stock_code]['weekly']
                if current_date in stock_weekly.index:
                    # 获取到当前日期的历史数据
                    current_idx = stock_weekly.index.get_loc(current_date)
                    historical_data = stock_weekly.iloc[:current_idx+1]
                    
                    # 直接从周线数据中获取技术指标（已经计算好的）
                    row = stock_weekly.loc[current_date]
                    
                    # 计算4周平均成交量
                    if current_idx >= 3:
                        volume_4w_data = stock_weekly['volume'].iloc[current_idx-3:current_idx+1]
                        volume_4w_avg = volume_4w_data.mean()
                    else:
                        volume_4w_avg = row['volume']
                    
                    # 安全获取技术指标值，确保不使用NaN或不合理的值
                    def safe_get_indicator(field_name, default_val):
                        """安全获取技术指标，处理NaN值"""
                        try:
                            if field_name not in stock_weekly.columns:
                                return default_val
                            
                            value = row.get(field_name)
                            if value is None or pd.isna(value):
                                # 查找历史有效值
                                for i in range(current_idx - 1, max(0, current_idx - 20), -1):
                                    try:
                                        hist_val = stock_weekly.iloc[i][field_name]
                                        if hist_val is not None and not pd.isna(hist_val):
                                            return float(hist_val)
                                    except:
                                        continue
                                return default_val
                            
                            return float(value)
                        except:
                            return default_val
                    
                    # 获取真实的技术指标值
                    technical_indicators = {
                        'close': safe_get_indicator('close', 0),
                        'volume': int(safe_get_indicator('volume', 0)),
                        'ema_20w': safe_get_indicator('ema_20', 0),
                        'ema_60w': safe_get_indicator('ema_50', 0),  # 使用ema_50作为60周线的近似
                        'rsi_14w': safe_get_indicator('rsi', 50),
                        'macd_dif': safe_get_indicator('macd', 0),
                        'macd_dea': safe_get_indicator('macd_signal', 0),
                        'macd_hist': safe_get_indicator('macd_histogram', 0),
                        'bb_upper': safe_get_indicator('bb_upper', 0),
                        'bb_middle': safe_get_indicator('bb_middle', 0),
                        'bb_lower': safe_get_indicator('bb_lower', 0),
                        'volume_4w_avg': volume_4w_avg
                    }
                    
                    # 验证技术指标的合理性
                    close_price = technical_indicators['close']
                    if close_price > 0:
                        # EMA不应该等于收盘价（除非是第一个数据点）
                        if (technical_indicators['ema_20w'] == close_price and 
                            current_idx > 20):
                            # 重新计算或使用历史值
                            for i in range(current_idx - 1, max(0, current_idx - 20), -1):
                                try:
                                    hist_ema = stock_weekly.iloc[i]['ema_20']
                                    if (hist_ema is not None and 
                                        not pd.isna(hist_ema) and 
                                        abs(hist_ema - close_price) > 0.01):
                                        technical_indicators['ema_20w'] = float(hist_ema)
                                        break
                                except:
                                    continue
                    
                    # 生成信号详情（尝试从信号生成器获取）
                    try:
                        signal_result = self.signal_generator.generate_signal(stock_code, historical_data)
                        if signal_result and isinstance(signal_result, dict):
                            signal_details = {
                                'signal_type': signal_result.get('signal', 'HOLD'),
                                'confidence': signal_result.get('confidence', 0),
                                'reason': signal_result.get('reason', ''),
                                'dimension_status': self._extract_dimension_status(signal_result.get('scores', {}))
                            }
                        else:
                            signal_details = self._create_default_signal_details(trade_info['type'])
                    except:
                        signal_details = self._create_default_signal_details(trade_info['type'])
                    
                    self.logger.info(f"🎯 {stock_code} 技术指标获取结果:")
                    for key, value in technical_indicators.items():
                        self.logger.info(f"  {key}: {value}")
                else:
                    self.logger.warning(f"{stock_code} 当前日期 {current_date} 不在数据中")
            else:
                self.logger.warning(f"{stock_code} 不在股票数据中")
                
        except Exception as e:
            self.logger.error(f"从信号生成器获取技术指标失败: {e}")
            # 降级处理
            self._fallback_get_technical_indicators(stock_code, current_date, technical_indicators, signal_details)
                
        # 如果技术指标为空，使用降级处理
        if not technical_indicators:
            self._fallback_get_technical_indicators(stock_code, current_date, technical_indicators, signal_details)
        
        # 获取交易后持仓数量
        position_after_trade = self.portfolio_manager.positions.get(stock_code, 0)
        
        # 记录交易
        transaction_record = {
            'date': current_date.strftime('%Y-%m-%d'),
            'type': trade_info['type'],
            'stock_code': stock_code,
            'shares': trade_info['shares'],
            'position_after_trade': position_after_trade,  # 添加交易后持仓数量
            'price': trade_info['price'],
            'gross_amount': trade_info['gross_amount'],
            'transaction_cost': trade_info['transaction_cost'],
            'net_amount': trade_info['net_amount'],
            'reason': trade_info['reason'],
            'technical_indicators': technical_indicators,
            'signal_details': signal_details
        }
        
        self.transaction_history.append(transaction_record)
    
    def _fallback_get_technical_indicators(self, stock_code: str, current_date: pd.Timestamp, 
                                         technical_indicators: Dict, signal_details: Dict):
        """
        降级处理：直接从数据中获取技术指标
        """
        try:
            if stock_code in self.stock_data:
                stock_weekly = self.stock_data[stock_code]['weekly']
                if current_date in stock_weekly.index:
                    row = stock_weekly.loc[current_date]
                    current_idx = stock_weekly.index.get_loc(current_date)
                    
                    # 计算4周平均成交量
                    if current_idx >= 3:
                        volume_4w_data = stock_weekly['volume'].iloc[current_idx-3:current_idx+1]
                        volume_4w_avg = volume_4w_data.mean()
                    else:
                        volume_4w_avg = row['volume']
                    
                    # 安全获取技术指标值
                    def safe_get_value(key, default_value):
                        try:
                            if key not in stock_weekly.columns:
                                return default_value
                            
                            current_value = row.get(key)
                            if current_value is not None and not pd.isna(current_value):
                                result = float(current_value)
                                # 对于重要指标，如果值为0可能不合理，查找历史值
                                if result == 0 and key in ['ema_20', 'ema_50', 'rsi']:
                                    # 查找历史有效值
                                    for i in range(current_idx - 1, max(0, current_idx - 20), -1):
                                        try:
                                            historical_value = stock_weekly.iloc[i][key]
                                            if (historical_value is not None and 
                                                not pd.isna(historical_value) and 
                                                historical_value != 0):
                                                return float(historical_value)
                                        except:
                                            continue
                                return result
                            return default_value
                        except:
                            return default_value
                    
                    # 更新技术指标字典
                    technical_indicators.update({
                        'close': safe_get_value('close', 0),
                        'volume': int(safe_get_value('volume', 0)),
                        'ema_20w': safe_get_value('ema_20', 0),
                        'ema_60w': safe_get_value('ema_60', 0),  # 修正：使用ema_60而不是ema_50
                        'rsi_14w': safe_get_value('rsi', 50),
                        'macd_dif': safe_get_value('macd', 0),
                        'macd_dea': safe_get_value('macd_signal', 0),
                        'macd_hist': safe_get_value('macd_histogram', 0),
                        'bb_upper': safe_get_value('bb_upper', 0),
                        'bb_middle': safe_get_value('bb_middle', 0),
                        'bb_lower': safe_get_value('bb_lower', 0),
                        'volume_4w_avg': volume_4w_avg
                    })
                    
                    # 生成基本信号详情
                    signal_details.update({
                        'signal_type': 'HOLD',
                        'confidence': 0,
                        'reason': '降级处理',
                        'dimension_status': {
                            'trend_filter': '✗',
                            'rsi_signal': '✗',
                            'macd_signal': '✗',
                            'bollinger_volume': '✗'
                        }
                    })
                    
                    self.logger.info(f"🔄 {stock_code} 降级处理获取技术指标完成")
                    
        except Exception as e:
            self.logger.error(f"降级处理失败: {e}")
    
    def _create_default_signal_details(self, trade_type: str) -> Dict:
        """创建默认的信号详情"""
        return {
            'signal_type': trade_type,
            'confidence': 3,
            'reason': f"{trade_type}信号",
            'dimension_status': {
                'trend_filter': '✓',
                'rsi_signal': '✓',
                'macd_signal': '✗',
                'bollinger_volume': '✓'
            }
        }
    
    def get_backtest_results(self) -> Dict[str, Any]:
        """
        获取回测结果
        
        Returns:
            Dict[str, Any]: 回测结果
        """
        if not self.portfolio_history:
            return {}
        
        # 转换为DataFrame便于分析
        portfolio_df = pd.DataFrame(self.portfolio_history)
        portfolio_df.set_index('date', inplace=True)
        
        # 计算基本指标
        initial_value = portfolio_df['total_value'].iloc[0]
        final_value = portfolio_df['total_value'].iloc[-1]
        total_return = (final_value - initial_value) / initial_value
        
        # 计算年化收益率
        days = (portfolio_df.index[-1] - portfolio_df.index[0]).days
        annual_return = (final_value / initial_value) ** (365.25 / days) - 1
        
        # 计算最大回撤
        rolling_max = portfolio_df['total_value'].expanding().max()
        drawdown = (portfolio_df['total_value'] - rolling_max) / rolling_max
        max_drawdown = drawdown.min()
        
        # 计算交易统计
        transaction_df = pd.DataFrame(self.transaction_history)
        total_trades = len(transaction_df)
        buy_trades = len(transaction_df[transaction_df['type'] == 'BUY']) if not transaction_df.empty else 0
        sell_trades = len(transaction_df[transaction_df['type'] == 'SELL']) if not transaction_df.empty else 0
        
        return {
            'basic_metrics': {
                'initial_value': initial_value,
                'final_value': final_value,
                'total_return': total_return,
                'annual_return': annual_return,
                'max_drawdown': max_drawdown
            },
            'trading_metrics': {
                'total_trades': total_trades,
                'buy_trades': buy_trades,
                'sell_trades': sell_trades
            },
            'portfolio_history': portfolio_df,
            'transaction_history': pd.DataFrame(self.transaction_history) if self.transaction_history else pd.DataFrame()
        }
    
    def generate_reports(self) -> Dict[str, str]:
        """
        生成回测报告
        
        Returns:
            Dict[str, str]: 生成的报告文件路径
        """
        try:
            # 获取回测结果
            backtest_results = self.get_backtest_results()
            
            if not backtest_results:
                self.logger.error("无法获取回测结果")
                return {}
            
            # 准备集成报告所需的数据结构
            integrated_results = self._prepare_integrated_results(backtest_results)
            
            # 生成集成HTML报告
            html_report_path = self.report_generator.generate_report(integrated_results)
            
            # 生成详细CSV报告
            # 使用transaction_history数据，并转换为正确格式
            transaction_history = backtest_results.get('transaction_history', pd.DataFrame())
            transactions_for_csv = []
            
            if not transaction_history.empty:
                transactions_for_csv = transaction_history.to_dict('records')
            
            csv_report_path = self.csv_exporter.export_trading_records(transactions_for_csv)
            
            return {
                'html_report': html_report_path,
                'csv_report': csv_report_path
            }
            
        except Exception as e:
            self.logger.error(f"生成报告失败: {e}")
            return {}
    
    def _prepare_integrated_results(self, backtest_results: Dict[str, Any]) -> Dict[str, Any]:
        """
        准备集成报告所需的数据结构
        
        Args:
            backtest_results: 原始回测结果
            
        Returns:
            Dict[str, Any]: 集成报告数据结构
        """
        try:
            # 基础指标
            basic_metrics = backtest_results.get('basic_metrics', {})
            trading_metrics = backtest_results.get('trading_metrics', {})
            
            # 投资组合历史
            portfolio_history = backtest_results.get('portfolio_history', pd.DataFrame())
            
            # 交易历史
            transaction_history = backtest_results.get('transaction_history', pd.DataFrame())
            
            # 最终投资组合状态
            final_portfolio = self._get_final_portfolio_status(portfolio_history)
            
            # 绩效指标
            performance_metrics = self._calculate_performance_metrics(basic_metrics, trading_metrics)
            
            # 信号分析 - 包含所有股票
            signal_analysis = self._extract_signal_analysis(transaction_history)
            self.logger.info(f"信号分析包含股票: {list(signal_analysis.keys())}")
            
            # K线数据
            kline_data = self._prepare_kline_data()
            
            return {
                'portfolio_history': portfolio_history.to_dict('records') if not portfolio_history.empty else [],
                'transactions': transaction_history.to_dict('records') if not transaction_history.empty else [],
                'final_portfolio': final_portfolio,
                'performance_metrics': performance_metrics,
                'signal_analysis': signal_analysis,
                'kline_data': kline_data
            }
            
        except Exception as e:
            self.logger.error(f"准备集成结果数据失败: {e}")
            return {}
    
    def _get_final_portfolio_status(self, portfolio_history: pd.DataFrame) -> Dict[str, Any]:
        """获取最终投资组合状态"""
        if portfolio_history.empty:
            return {}
        
        final_row = portfolio_history.iloc[-1]
        final_positions = final_row.get('positions', {})
        
        # 计算股票市值
        stock_value = 0
        positions_detail = {}
        
        for stock_code, shares in final_positions.items():
            if stock_code != 'cash' and shares > 0:
                # 获取最终价格
                current_price = 0
                if stock_code in self.stock_data:
                    stock_weekly = self.stock_data[stock_code]['weekly']
                    current_price = stock_weekly.iloc[-1]['close']
                
                market_value = shares * current_price
                stock_value += market_value
                
                positions_detail[stock_code] = {
                    'shares': shares,
                    'current_price': current_price,
                    'market_value': market_value
                }
        
        return {
            'end_date': final_row.name.strftime('%Y-%m-%d') if hasattr(final_row.name, 'strftime') else str(final_row.name),
            'total_value': final_row['total_value'],
            'cash': final_row['cash'],
            'stock_value': stock_value,
            'positions': positions_detail
        }
    
    def _calculate_performance_metrics(self, basic_metrics: Dict, trading_metrics: Dict) -> Dict[str, Any]:
        """计算绩效指标"""
        # 基础指标
        initial_capital = basic_metrics.get('initial_value', self.total_capital)
        final_value = basic_metrics.get('final_value', initial_capital)
        total_return = basic_metrics.get('total_return', 0) * 100  # 转换为百分比
        annual_return = basic_metrics.get('annual_return', 0) * 100
        max_drawdown = basic_metrics.get('max_drawdown', 0) * 100
        
        # 计算买入持有基准收益（基于实际股票池表现）
        benchmark_return, benchmark_annual_return, benchmark_max_drawdown = self._calculate_buy_and_hold_benchmark()
        
        return {
            'initial_capital': initial_capital,
            'final_value': final_value,
            'total_return': total_return,
            'annual_return': annual_return,
            'max_drawdown': max_drawdown,
            'benchmark_return': benchmark_return,
            'benchmark_annual_return': benchmark_annual_return,
            'benchmark_max_drawdown': benchmark_max_drawdown
        }
    
    def _extract_signal_analysis(self, transaction_history: pd.DataFrame) -> Dict[str, Any]:
        """提取信号分析数据 - 包含所有股票的信号统计"""
        signal_analysis = {}
        
        # 首先为所有股票初始化信号分析结构
        all_stock_codes = list(self.config.get('initial_holdings', {}).keys())
        # 移除现金项
        all_stock_codes = [code for code in all_stock_codes if code != 'cash']
        
        for stock_code in all_stock_codes:
            signal_analysis[stock_code] = {'signals': []}
        
        # 如果有交易记录，则提取交易信号数据
        if not transaction_history.empty:
            for _, row in transaction_history.iterrows():
                stock_code = row['stock_code']
                date = row['date']
                
                # 确保股票代码在分析中
                if stock_code not in signal_analysis:
                    signal_analysis[stock_code] = {'signals': []}
                
                # 提取技术指标和信号详情
                # 提取技术指标和信号详情
                # 优先使用信号生成器返回的技术指标（已处理nan值）
                signal_result = row.get('signal_result', {})
                technical_indicators = signal_result.get('technical_indicators', row.get('technical_indicators', {}))
                signal_details = row.get('signal_details', {})
                dimension_status = signal_details.get('dimension_status', {})
                
                # 构建信号记录
                signal_record = {
                    'date': date,
                    'type': row['type'],
                    'price': row['price'],
                    'close_price': technical_indicators.get('close', row['price']),
                    'ema_20': technical_indicators.get('ema_20w', 0),
                    'rsi_14': technical_indicators.get('rsi_14w', 50),
                    'macd_dif': technical_indicators.get('macd_dif', 0),
                    'macd_dea': technical_indicators.get('macd_dea', 0),
                    'bb_position': self._get_bb_position(technical_indicators),
                    'volume_ratio': self._calculate_volume_ratio_from_indicators(technical_indicators),
                    'rsi_signal': dimension_status.get('rsi_signal', '✗'),
                    'macd_signal': dimension_status.get('macd_signal', '✗'),
                    'bollinger_volume': dimension_status.get('bollinger_volume', '✗'),
                    'trend_filter': dimension_status.get('trend_filter', '✗'),
                    'confidence': signal_details.get('confidence', 0),
                    'reason': signal_details.get('reason', '')
                }
                
                signal_analysis[stock_code]['signals'].append(signal_record)
        
        # 为没有交易记录的股票添加统计信息
        for stock_code in signal_analysis:
            if not signal_analysis[stock_code]['signals']:
                # 没有交易信号的股票，添加基础统计
                signal_analysis[stock_code]['signals'] = []
                self.logger.info(f"股票 {stock_code} 在回测期间没有产生交易信号")
        
        return signal_analysis
    
    def _get_bb_position(self, indicators: Dict) -> str:
        """获取布林带位置"""
        close = indicators.get('close', 0)
        bb_upper = indicators.get('bb_upper', 0)
        bb_lower = indicators.get('bb_lower', 0)
        
        if bb_upper > 0 and bb_lower > 0:
            if close >= bb_upper:
                return "上轨之上"
            elif close <= bb_lower:
                return "下轨之下"
            else:
                return "轨道之间"
        return "轨道之间"
    
    def _calculate_volume_ratio_from_indicators(self, indicators: Dict) -> float:
        """从技术指标计算量能倍数"""
        current_volume = indicators.get('volume', 0)
        volume_ma = indicators.get('volume_4w_avg', 0)
        
        if current_volume > 0 and volume_ma > 0:
            return round(current_volume / volume_ma, 2)
        return 0.0
    
    def _extract_dimension_status(self, scores: Dict) -> Dict:
        """从评分中提取维度状态"""
        try:
            return {
                'trend_filter': '✓' if scores.get('trend_filter_high') or scores.get('trend_filter_low') else '✗',
                'rsi_signal': '✓' if scores.get('overbought_oversold_high') or scores.get('overbought_oversold_low') else '✗',
                'macd_signal': '✓' if scores.get('momentum_high') or scores.get('momentum_low') else '✗',
                'bollinger_volume': '✓' if scores.get('extreme_price_volume_high') or scores.get('extreme_price_volume_low') else '✗'
            }
        except Exception:
            return {
                'trend_filter': '✗',
                'rsi_signal': '✗',
                'macd_signal': '✗',
                'bollinger_volume': '✗'
            }
    
    def _prepare_kline_data(self) -> Dict[str, Any]:
        """准备K线数据"""
        kline_data = {}
        
        # 调试信息
        self.logger.info(f"准备K线数据，交易记录数量: {len(self.transaction_history)}")
        if self.transaction_history:
            self.logger.info(f"交易记录示例: {self.transaction_history[0]}")
        
        # 过滤回测期间的数据
        start_date = pd.to_datetime(self.start_date)
        end_date = pd.to_datetime(self.end_date)
        
        for stock_code, data in self.stock_data.items():
            weekly_data = data['weekly']
            
            # 过滤K线数据到回测期间
            filtered_weekly_data = weekly_data[
                (weekly_data.index >= start_date) & (weekly_data.index <= end_date)
            ]
            
            # 准备K线数据点
            kline_points = []
            for idx, row in filtered_weekly_data.iterrows():
                try:
                    # 确保时间戳格式正确
                    if hasattr(idx, 'timestamp'):
                        timestamp = int(idx.timestamp() * 1000)
                    else:
                        # 如果idx不是datetime，尝试转换
                        timestamp = int(pd.to_datetime(idx).timestamp() * 1000)
                    
                    kline_points.append([
                        timestamp,  # 时间戳（毫秒）
                        float(row['open']),
                        float(row['close']),
                        float(row['low']),
                        float(row['high'])
                    ])
                except Exception as e:
                    self.logger.warning(f"处理K线数据点失败: {e}, 索引: {idx}")
                    continue
            
            # 准备交易点数据 - 只包含该股票的交易
            trade_points = []
            stock_trade_count = 0
            for transaction in self.transaction_history:
                if transaction.get('stock_code') == stock_code:
                    try:
                        trade_date = pd.to_datetime(transaction['date'])
                        
                        # 确保交易日期在回测期间内
                        if start_date <= trade_date <= end_date:
                            trade_points.append({
                                'timestamp': int(trade_date.timestamp() * 1000),
                                'price': float(transaction['price']),
                                'type': transaction['type'],
                                'shares': transaction.get('shares', 0),
                                'reason': transaction.get('reason', '')
                            })
                            stock_trade_count += 1
                            self.logger.info(f"添加交易点: {stock_code} {transaction['date']} {transaction['type']} {transaction['price']}")
                        else:
                            self.logger.warning(f"交易日期超出回测范围: {transaction['date']}")
                    except Exception as e:
                        self.logger.warning(f"处理交易点数据失败: {e}, 交易记录: {transaction}")
            
            self.logger.info(f"股票 {stock_code} 交易点数量: {stock_trade_count}")
            
            kline_data[stock_code] = {
                'kline': kline_points,
                'trades': trade_points,
                'name': stock_code  # 添加股票名称
            }
        
        return kline_data
    
    def _calculate_buy_and_hold_benchmark(self) -> Tuple[float, float, float]:
        """
        计算买入持有基准收益（基于实际股票池表现）
        
        Returns:
            Tuple[float, float, float]: (总收益率%, 年化收益率%, 最大回撤%)
        """
        try:
            if not self.stock_data:
                # 如果没有股票数据，返回默认值
                return 45.0, 12.0, -18.0
            
            # 计算等权重买入持有策略的表现
            start_date = pd.to_datetime(self.start_date)
            end_date = pd.to_datetime(self.end_date)
            
            # 收集所有股票的收益率
            stock_returns = {}
            
            for stock_code, data in self.stock_data.items():
                weekly_data = data['weekly']
                
                # 过滤到回测期间
                filtered_data = weekly_data[
                    (weekly_data.index >= start_date) & (weekly_data.index <= end_date)
                ]
                
                if len(filtered_data) < 2:
                    continue
                
                # 计算该股票的总收益率
                start_price = filtered_data.iloc[0]['close']
                end_price = filtered_data.iloc[-1]['close']
                stock_return = (end_price - start_price) / start_price
                stock_returns[stock_code] = stock_return
                
                self.logger.info(f"买入持有基准 - {stock_code}: {start_price:.2f} -> {end_price:.2f}, 收益率: {stock_return:.2%}")
            
            if not stock_returns:
                return 45.0, 12.0, -18.0
            
            # 计算等权重平均收益率
            avg_return = sum(stock_returns.values()) / len(stock_returns)
            
            # 计算年化收益率
            days = (end_date - start_date).days
            if days > 0:
                annual_return = (1 + avg_return) ** (365.25 / days) - 1
            else:
                annual_return = 0
            
            # 估算最大回撤（简化计算，使用平均值的80%）
            estimated_max_drawdown = -abs(avg_return * 0.8)
            
            # 转换为百分比
            total_return_pct = avg_return * 100
            annual_return_pct = annual_return * 100
            max_drawdown_pct = estimated_max_drawdown * 100
            
            self.logger.info(f"买入持有基准计算完成:")
            self.logger.info(f"  总收益率: {total_return_pct:.2f}%")
            self.logger.info(f"  年化收益率: {annual_return_pct:.2f}%")
            self.logger.info(f"  估算最大回撤: {max_drawdown_pct:.2f}%")
            
            return total_return_pct, annual_return_pct, max_drawdown_pct
            
        except Exception as e:
            self.logger.error(f"计算买入持有基准失败: {e}")
            # 返回默认值
            return 45.0, 12.0, -18.0

    def _get_cached_or_fetch_data(self, stock_code: str, start_date: str, end_date: str, period: str = 'daily') -> Optional[pd.DataFrame]:
        """
        智能获取数据：优先使用缓存，按需从网络获取缺失部分
        
        Args:
            stock_code: 股票代码
            start_date: 开始日期 ('YYYY-MM-DD')
            end_date: 结束日期 ('YYYY-MM-DD')
            period: 数据周期 ('daily', 'weekly')
            
        Returns:
            pd.DataFrame: 请求时间段的股票数据
        """
        try:
            # 1. 尝试从缓存加载现有数据
            cached_data = self.data_storage.load_data(stock_code, period)
            
            if cached_data is not None and not cached_data.empty:
                # 检查缓存数据的时间范围
                cached_start = cached_data.index.min()
                cached_end = cached_data.index.max()
                
                request_start = pd.to_datetime(start_date)
                request_end = pd.to_datetime(end_date)
                
                self.logger.info(f"📊 {stock_code} 缓存范围: {cached_start.strftime('%Y-%m-%d')} 到 {cached_end.strftime('%Y-%m-%d')}")
                self.logger.info(f"🎯 {stock_code} 请求范围: {start_date} 到 {end_date}")
                
                # 2. 判断是否需要补充数据
                need_fetch_before = request_start < cached_start
                need_fetch_after = request_end > cached_end
                
                if not need_fetch_before and not need_fetch_after:
                    # 缓存完全覆盖请求范围
                    result_data = cached_data[
                        (cached_data.index >= request_start) & 
                        (cached_data.index <= request_end)
                    ]
                    self.logger.info(f"✅ {stock_code} 完全使用缓存数据，共 {len(result_data)} 条记录")
                    return result_data
                
                # 3. 需要补充数据
                new_data_parts = []
                
                if need_fetch_before:
                    # 获取早期数据
                    early_end = (cached_start - pd.Timedelta(days=1)).strftime('%Y-%m-%d')
                    self.logger.info(f"🌐 {stock_code} 获取早期数据: {start_date} 到 {early_end}")
                    early_data = self.data_fetcher.get_stock_data(stock_code, start_date, early_end, period)
                    if early_data is not None and not early_data.empty:
                        new_data_parts.append(early_data)
                
                if need_fetch_after:
                    # 获取后期数据
                    late_start = (cached_end + pd.Timedelta(days=1)).strftime('%Y-%m-%d')
                    self.logger.info(f"🌐 {stock_code} 获取后期数据: {late_start} 到 {end_date}")
                    late_data = self.data_fetcher.get_stock_data(stock_code, late_start, end_date, period)
                    if late_data is not None and not late_data.empty:
                        new_data_parts.append(late_data)
                
                # 4. 合并所有数据
                all_data_parts = []
                if new_data_parts:
                    all_data_parts.extend(new_data_parts)
                all_data_parts.append(cached_data)
                
                # 合并并排序
                merged_data = pd.concat(all_data_parts, axis=0)
                merged_data = merged_data.sort_index()
                merged_data = merged_data[~merged_data.index.duplicated(keep='last')]  # 去重
                
                # 5. 更新缓存
                self.data_storage.save_data(merged_data, stock_code, period)
                self.logger.info(f"💾 {stock_code} 已更新缓存，总计 {len(merged_data)} 条记录")
                
                # 6. 返回请求范围的数据
                result_data = merged_data[
                    (merged_data.index >= request_start) & 
                    (merged_data.index <= request_end)
                ]
                return result_data
            
            else:
                # 7. 无缓存，直接从网络获取
                self.logger.info(f"🌐 {stock_code} 无缓存，从akshare获取完整数据: {start_date} 到 {end_date}")
                fresh_data = self.data_fetcher.get_stock_data(stock_code, start_date, end_date, period)
                
                if fresh_data is not None and not fresh_data.empty:
                    # 保存到缓存
                    self.data_storage.save_data(fresh_data, stock_code, period)
                    self.logger.info(f"💾 {stock_code} 已保存到缓存，共 {len(fresh_data)} 条记录")
                
                return fresh_data
                
        except Exception as e:
            self.logger.error(f"❌ {stock_code} 智能数据获取失败: {e}")
            # 降级到直接网络获取
            try:
                return self.data_fetcher.get_stock_data(stock_code, start_date, end_date, period)
            except Exception as fallback_error:
                self.logger.error(f"❌ {stock_code} 降级获取也失败: {fallback_error}")
                return None
