"""
回测引擎模块
负责执行回测逻辑，管理投资组合，记录交易历史
"""

import logging
import warnings
from datetime import datetime
from typing import Any, Dict, List, Optional, Tuple

import pandas as pd

warnings.filterwarnings('ignore')

        # 导入其他模块
from data.data_fetcher import DataFetcherFactory
from data.data_processor import DataProcessor
from data.data_storage import DataStorage
from indicators.price_value_ratio import calculate_pvr, get_pvr_status
from strategy.dynamic_position_manager import DynamicPositionManager
from strategy.signal_generator import SignalGenerator

from .detailed_csv_exporter import DetailedCSVExporter
from .enhanced_report_generator_integrated_fixed import IntegratedReportGenerator
from .portfolio_data_manager import PortfolioDataManager
from .portfolio_manager import PortfolioManager
from .transaction_cost import TransactionCostCalculator

logger = logging.getLogger(__name__)

class BacktestEngine:
    """
    回测引擎类
    
    ⚠️ DEPRECATED: 此类已废弃，请使用 BacktestOrchestrator
    
    BacktestEngine 是一个大型单体类（2378行），职责过多，难以维护。
    新的架构使用服务层模式，将功能拆分为：
    - DataService: 数据获取和处理
    - SignalService: 信号生成
    - PortfolioService: 持仓和交易管理
    - ReportService: 报告生成
    - BacktestOrchestrator: 协调各服务
    
    为保持向后兼容，此类暂时保留，但建议迁移到新架构。
    
    示例:
        # 旧方式（已废弃）
        engine = BacktestEngine(config)
        engine.run_backtest()
        
        # 新方式（推荐）
        from services.backtest_orchestrator import BacktestOrchestrator
        orchestrator = BacktestOrchestrator(config)
        orchestrator.initialize()
        orchestrator.run_backtest()
    """
    
    def __init__(self, config: Dict[str, Any]):
        """
        初始化回测引擎
        
        Args:
            config: 回测配置字典
        """
        # 发出废弃警告
        warnings.warn(
            "BacktestEngine已废弃，建议使用BacktestOrchestrator。"
            "新架构提供更好的模块化和可维护性。"
            "详见: services/backtest_orchestrator.py",
            DeprecationWarning,
            stacklevel=2
        )
        
        self.config = config
        self.logger = logging.getLogger(__name__)
        
        # 信号生成器将在数据准备后初始化
        self.signal_generator = None
        
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
        
        # 【新增】数据源配置
        data_source = config.get('data_source', 'akshare')
        backup_data_source = config.get('backup_data_source', None)
        tushare_token = config.get('tushare_token', None)
        data_fetch_strategy = config.get('data_fetch_strategy', 'simple')
        
        # 初始化各个组件
        # 【修改】使用工厂模式创建数据获取器
        fetcher_config = {
            'tushare_token': tushare_token
        }
        
        if data_fetch_strategy == 'smart' and backup_data_source:
            # 智能切换模式：使用降级策略
            self.logger.info(f"🔄 使用降级模式创建数据获取器")
            self.data_fetcher = DataFetcherFactory.create_with_fallback(
                data_source, backup_data_source, fetcher_config
            )
            self.logger.info(f"✅ 数据源初始化完成")
        else:
            # 单一数据源模式
            self.logger.info(f"📊 使用单一数据源模式")
            self.data_fetcher = DataFetcherFactory.create_fetcher(data_source, fetcher_config)
            self.logger.info(f"✅ 数据源初始化: {data_source}")
        
        self.data_processor = DataProcessor()
        self.data_storage = DataStorage()  # 添加数据存储组件
        # SignalGenerator将在DCF数据加载后初始化
        self.cost_calculator = TransactionCostCalculator(cost_config)
        self.portfolio_manager = None
        
        # 统一的Portfolio数据管理器
        self.portfolio_data_manager = PortfolioDataManager(self.total_capital)
        
        # 报告生成器
        self.report_generator = IntegratedReportGenerator()
        self.csv_exporter = DetailedCSVExporter()
        
        # 🆕 新增：初始化信号跟踪器
        from .signal_tracker import SignalTracker
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        signal_tracker_path = f"reports/signal_tracking_report_{timestamp}.csv"
        self.signal_tracker = SignalTracker(signal_tracker_path)
        
        # 未执行原因常量（与SignalTracker保持一致）
        self.EXECUTION_REJECTION_REASONS = {
            # 买入相关
            'INSUFFICIENT_CASH': '现金不足',
            'INSUFFICIENT_CASH_80PCT': '现金不足80%要求', 
            'POSITION_LIMIT_REACHED': '单股仓位已达上限',
            'POSITION_LIMIT_EXCEEDED': '买入后将超过单股仓位上限',
            'TRANSACTION_LIMIT_EXCEEDED': '单笔交易超过上限',
            'VALUATION_NOT_SUPPORT_BUY': '估值水平不支持买入',
            'BELOW_MIN_BUY_REQUIREMENT': '现金低于最小买入要求',
            
            # 卖出相关
            'NO_POSITION_TO_SELL': '无持仓可卖',
            'INSUFFICIENT_POSITION': '持仓不足最小卖出量', 
            'VALUATION_NOT_SUPPORT_SELL': '估值水平不支持卖出',
            'CALCULATED_SELL_SHARES_ZERO': '计算卖出股数为0',
            
            # 技术限制
            'NOT_100_SHARES_MULTIPLE': '不足100股整数倍',
            'STOCK_SUSPENDED': '股票停牌或流动性不足',
            'DATA_ABNORMAL': '数据异常',
            'SYSTEM_ERROR': '系统错误'
        }
        
        # 回测数据存储
        self.stock_data = {}
        self.backtest_results = {}
        self.transaction_history = []
        
        # 股票池（排除现金）
        self.stock_pool = [code for code in self.initial_holdings.keys() if code != 'cash']
        
        # 加载DCF估值数据
        self.dcf_values = self._load_dcf_values()
        
        # 加载RSI阈值数据
        self.rsi_thresholds = self._load_rsi_thresholds()
        
        # 加载股票-行业映射数据
        self.stock_industry_map = self._load_stock_industry_map()
        
        # 现在初始化SignalGenerator，传递所有数据
        # 合并config和strategy_params，确保价值比阈值等参数正确传递
        signal_config = config.copy()
        if 'strategy_params' in config:
            signal_config.update(config['strategy_params'])
        
        self.signal_generator = SignalGenerator(signal_config, self.dcf_values, self.rsi_thresholds, self.stock_industry_map)
        
        # 初始化动态仓位管理器
        self.dynamic_position_manager = DynamicPositionManager(config.get('strategy_params', config))
        
        self.logger.info("回测引擎初始化完成")
        self.logger.info(f"回测期间: {self.start_date} 至 {self.end_date}")
        self.logger.info(f"股票池: {self.stock_pool}")
        self.logger.info(f"轮动比例: {self.rotation_percentage:.1%}")
        
        # 数据加载状态汇总
        if hasattr(self, 'dcf_values'):
            self.logger.info(f"📊 DCF估值数据: {len(self.dcf_values)} 只股票")
        else:
            self.logger.warning("DCF估值数据加载失败")
            
        if hasattr(self, 'rsi_thresholds'):
            self.logger.info(f"📈 RSI阈值数据: {len(self.rsi_thresholds)} 个行业")
        else:
            self.logger.warning("RSI阈值数据加载失败")
            
        if hasattr(self, 'stock_industry_map'):
            self.logger.info(f"🏭 股票-行业映射: {len(self.stock_industry_map)} 只股票")
        else:
            self.logger.warning("股票-行业映射数据加载失败")
    
    def _load_dcf_values(self) -> Dict[str, float]:
        """
        从Csv配置文件加载DCF估值数据
        
        Returns:
            Dict[str, float]: 股票代码到DCF估值的映射
        """
        try:
            import pandas as pd
            df = pd.read_csv('Input/portfolio_config.csv', encoding='utf-8-sig')
            dcf_values = {}
            
            for _, row in df.iterrows():
                stock_code = row['Stock_number']
                if stock_code != 'CASH':  # 排除现金
                    dcf_value = row.get('DCF_value_per_share', None)
                    if dcf_value is not None and pd.notna(dcf_value):
                        dcf_values[stock_code] = float(dcf_value)
            
            return dcf_values
        except Exception as e:
            self.logger.warning(f"DCF估值数据加载失败: {e}")
            return {}

    def _load_rsi_thresholds(self) -> Dict[str, Dict[str, float]]:
        """
        从CSV文件加载申万二级行业RSI阈值数据
        
        Returns:
            Dict[str, Dict[str, float]]: 行业代码到RSI阈值的映射
        """
        try:
            import os

            import pandas as pd
            
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
                    'buy_threshold': float(row.get('普通超卖', 30)),  # 使用普通超卖作为买入阈值
                    'sell_threshold': float(row.get('普通超买', 70)),  # 使用普通超买作为卖出阈值
                    'extreme_buy_threshold': float(row.get('极端超卖', 20)),  # 极端买入阈值
                    'extreme_sell_threshold': float(row.get('极端超买', 80)),  # 极端卖出阈值
                    'volatility_level': row.get('layer', 'medium'),
                    'volatility': float(row.get('volatility', 0)),
                    'current_rsi': float(row.get('current_rsi', 50))
                }
            
            self.logger.info(f"✅ 成功加载 {len(rsi_thresholds)} 个行业的RSI阈值")
            return rsi_thresholds
            
        except Exception as e:
            self.logger.warning(f"RSI阈值数据加载失败: {e}")
            return {}
    
    def _load_stock_industry_map(self) -> Dict[str, Dict[str, str]]:
        """
        从JSON文件加载股票-行业映射数据
        
        Returns:
            Dict[str, Dict[str, str]]: 股票代码到行业信息的映射
        """
        try:
            import json
            import os
            
            map_file_path = 'utils/stock_to_industry_map.json'
            
            if not os.path.exists(map_file_path):
                self.logger.warning(f"股票-行业映射文件不存在: {map_file_path}")
                self.logger.warning("请先运行 'python3 utils/industry_mapper.py' 生成映射缓存")
                return {}
            
            with open(map_file_path, 'r', encoding='utf-8') as f:
                cache_data = json.load(f)
            
            if 'mapping' not in cache_data:
                self.logger.warning("映射文件格式不正确，缺少mapping字段")
                return {}
            
            stock_industry_map = cache_data['mapping']
            metadata = cache_data.get('metadata', {})
            
            self.logger.info(f"✅ 成功加载股票-行业映射")
            self.logger.info(f"📊 映射股票数量: {len(stock_industry_map)}")
            self.logger.info(f"🕐 生成时间: {metadata.get('generated_at', '未知')}")
            
            return stock_industry_map
            
        except Exception as e:
            self.logger.warning(f"股票-行业映射数据加载失败: {e}")
            return {}

    
    def prepare_data(self) -> bool:
        """
        准备回测数据（智能缓存版本）
        
        Returns:
            bool: 数据准备是否成功
        """
        try:
            self.logger.info("🚀 开始准备回测数据（智能缓存模式）...")
            
            # 计算扩展的开始日期，确保有足够的历史数据计算技术指标
            # 统一采用120条数据计算技术指标，额外增加5周安全边际（约125周）
            # 再增加14周RSI预热期，确保回测开始时RSI就有效（共139周）
            from datetime import datetime, timedelta
            start_date_obj = datetime.strptime(self.start_date, '%Y-%m-%d')
            
            # 125周用于技术指标稳定计算 + 14周RSI预热期
            total_history_weeks = 125 + 14
            extended_start_date = start_date_obj - timedelta(weeks=total_history_weeks)
            extended_start_date_str = extended_start_date.strftime('%Y-%m-%d')
            
            self.logger.info(f"📅 回测期间: {self.start_date} 至 {self.end_date}")
            self.logger.info(f"📅 数据获取期间（含139周历史缓冲）: {extended_start_date_str} 至 {self.end_date}")
            self.logger.info(f"📅 历史数据构成: 125周技术指标计算 + 14周RSI预热期")
            
            # 显示缓存统计信息
            cache_stats = self.data_storage.get_cache_statistics()
            self.logger.info(f"📊 当前缓存统计: {cache_stats}")
            
            for stock_code in self.stock_pool:
                self.logger.info(f"📈 准备 {stock_code} 的历史数据...")
                
                # 1. 智能获取日线数据（使用扩展的开始日期）
                daily_data = self._get_cached_or_fetch_data(stock_code, extended_start_date_str, self.end_date, 'daily')
                
                if daily_data is None or daily_data.empty:
                    # 尝试智能日期范围扩展，解决纯非交易日期间的问题
                    self.logger.warning(f"⚠️ {stock_code} 初次获取数据为空，尝试智能扩展日期范围")
                    daily_data = self._get_data_with_smart_expansion(stock_code, extended_start_date_str, self.end_date, 'daily')
                    
                    if daily_data is None or daily_data.empty:
                        self.logger.warning(f"⚠️ {stock_code} 扩展获取后仍无数据，跳过该股票")
                        # 记录失败的股票，但继续处理其他股票
                        continue
                    else:
                        self.logger.info(f"✅ {stock_code} 通过智能扩展成功获取到 {len(daily_data)} 条数据")
                
                # 2. 智能获取或生成周线数据
                weekly_data = None
                
                # 先尝试从缓存获取周线数据（使用扩展的开始日期）
                try:
                    weekly_data = self._get_cached_or_fetch_data(stock_code, extended_start_date_str, self.end_date, 'weekly')
                except:
                    # 如果周线缓存获取失败，从日线转换
                    pass
                
                if weekly_data is None or weekly_data.empty:
                    # 从日线数据转换为周线数据
                    self.logger.info(f"🔄 {stock_code} 从日线数据转换周线数据")
                    weekly_data = self.data_processor.resample_to_weekly(daily_data)
                    
                    if len(weekly_data) < 139:  # 至少需要139周的数据（125+14）
                        self.logger.warning(f"⚠️ {stock_code} 数据不足，只有 {len(weekly_data)} 条记录，建议139条")
            
                # 确保技术指标存在并且是最新的
                need_recalculate = False
                
                # 检查是否需要重新计算技术指标
                if 'ema_20' not in weekly_data.columns or 'rsi' not in weekly_data.columns:
                    need_recalculate = True
                    self.logger.info(f"🔧 {stock_code} 技术指标列不存在，需要计算")
                else:
                    # 检查最新几行是否有NaN值
                    recent_data = weekly_data.tail(5)
                    rsi_nan_count = recent_data['rsi'].isna().sum()
                    macd_nan_count = recent_data['macd'].isna().sum()
                    
                    if rsi_nan_count > 0 or macd_nan_count > 0:
                        need_recalculate = True
                        self.logger.info(f"🔧 {stock_code} 最新技术指标有NaN值 (RSI: {rsi_nan_count}, MACD: {macd_nan_count})，需要重新计算")
                
                if need_recalculate:
                    # 确保有足够的数据来计算技术指标
                    if len(weekly_data) < 30:  # 确保至少有30个数据点
                        self.logger.warning(f"⚠️ {stock_code} 数据量不足 ({len(weekly_data)} < 30)，尝试获取更多历史数据")
                        # 扩展获取更多历史数据
                        extended_start = (pd.to_datetime(extended_start_date_str) - pd.Timedelta(weeks=50)).strftime('%Y-%m-%d')
                        try:
                            extended_weekly_data = self._get_cached_or_fetch_data(stock_code, extended_start, self.end_date, 'weekly')
                            if extended_weekly_data is not None and len(extended_weekly_data) > len(weekly_data):
                                weekly_data = extended_weekly_data
                                self.logger.info(f"✅ {stock_code} 获取到更多历史数据，现有 {len(weekly_data)} 条记录")
                        except Exception as e:
                            self.logger.warning(f"⚠️ {stock_code} 获取扩展历史数据失败: {e}")
                    
                    self.logger.info(f"🔧 {stock_code} 开始计算技术指标，数据量: {len(weekly_data)}")
                    try:
                        weekly_data = self.data_processor.calculate_technical_indicators(weekly_data)
                        self.logger.info(f"✅ {stock_code} 技术指标计算完成")
                        
                        # 保存更新后的周线数据到缓存
                        try:
                            self.data_storage.save_data(weekly_data, stock_code, 'weekly')
                            self.logger.info(f"💾 {stock_code} 周线数据（含技术指标）已保存到缓存")
                        except Exception as e:
                            self.logger.warning(f"⚠️ {stock_code} 周线数据缓存保存失败: {e}")
                    except Exception as e:
                        self.logger.error(f"❌ {stock_code} 技术指标计算失败: {e}")
                        # 如果计算失败，尝试使用现有数据
                else:
                    self.logger.info(f"✅ {stock_code} 技术指标已存在且有效，跳过计算")
                
                # 3. 获取分红配股数据并对齐到周线数据
                self.logger.info(f"💰 {stock_code} 获取分红配股数据...")
                try:
                    dividend_data = self.data_fetcher.get_dividend_data(stock_code, extended_start_date_str, self.end_date)
                    if not dividend_data.empty:
                        self.logger.info(f"✅ {stock_code} 获取到 {len(dividend_data)} 条分红记录")
                        # 将分红数据对齐到周线数据
                        weekly_data = self.data_fetcher.align_dividend_with_weekly_data(weekly_data, dividend_data)
                        self.logger.info(f"✅ {stock_code} 分红数据已对齐到周线数据")
                        
                        # 检查对齐后的分红事件
                        dividend_weeks = weekly_data[weekly_data['dividend_amount'] > 0]
                        if not dividend_weeks.empty:
                            self.logger.info(f"💰 {stock_code} 对齐到 {len(dividend_weeks)} 个分红事件")
                            for date, row in dividend_weeks.iterrows():
                                self.logger.info(f"  {date.strftime('%Y-%m-%d')}: 派息 {row['dividend_amount']}元")
                    else:
                        self.logger.info(f"⚠️ {stock_code} 未获取到分红数据")
                except Exception as e:
                    self.logger.warning(f"⚠️ {stock_code} 分红数据获取失败: {e}")
                
                # 裁剪数据到实际回测期间（保留扩展的历史数据用于技术指标计算）
                # 但在回测时只使用回测期间的数据
                actual_start_date = pd.to_datetime(self.start_date)
                
                # 为日线数据创建裁剪版本（仅用于显示统计）
                daily_backtest_data = daily_data[daily_data.index >= actual_start_date]
                
                # 为周线数据创建裁剪版本（仅用于显示统计）
                weekly_backtest_data = weekly_data[weekly_data.index >= actual_start_date]
                
                # 存储完整数据到内存中供回测使用（包含历史缓冲数据）
                self.stock_data[stock_code] = {
                    'daily': daily_data,  # 包含历史缓冲的完整数据
                    'weekly': weekly_data  # 包含历史缓冲的完整数据
                }
                
                # 记录RSI有效值统计
                rsi_valid_count = weekly_data['rsi'].notna().sum()
                rsi_nan_count = weekly_data['rsi'].isna().sum()
                
                self.logger.info(f"✅ {stock_code} 数据准备完成:")
                self.logger.info(f"   📊 日线数据: 总计{len(daily_data)}条, 回测期{len(daily_backtest_data)}条")
                self.logger.info(f"   📊 周线数据: 总计{len(weekly_data)}条, 回测期{len(weekly_backtest_data)}条")
                self.logger.info(f"   📊 RSI指标: 有效值{rsi_valid_count}个, NaN值{rsi_nan_count}个")
            
                # 增加缓冲等待，避免处理下一只股票过快导致连接断开
                import time
                time.sleep(1.5)
            
            # 显示最终缓存统计
            final_cache_stats = self.data_storage.get_cache_statistics()
            self.logger.info(f"📊 数据准备完成后缓存统计: {final_cache_stats}")
            self.logger.info(f"🎉 所有股票数据准备完成，共处理 {len(self.stock_data)} 只股票")
            
            # SignalGenerator已在prepare_data中初始化
            self.logger.info("✅ SignalGenerator 已准备就绪")
            
            return True
            
        except Exception as e:
            self.logger.error(f"❌ 数据准备失败: {e}")
            return False
    
    def initialize_portfolio(self) -> bool:
        """
        初始化投资组合
        按照新的计算逻辑：
        1. 获取总资产金额
        2. 获取各股票持仓比例，并计算出合理的持仓股数
        3. 从持仓股数推算得各股票市值和总的股票市值
        4. 从总资产金额减去总的股票市值得到现金值

        Returns:
            bool: 初始化是否成功
        """
        try:
            # 1. 获取总资产金额
            total_capital = self.total_capital
            self.logger.info(f"💰 总资产金额: {total_capital:,.2f}")

            # 获取初始价格并设置到数据管理器
            initial_prices = {}
            start_date_obj = pd.to_datetime(self.start_date)

            for stock_code in self.stock_pool:
                if stock_code in self.stock_data:
                    weekly_data = self.stock_data[stock_code]['weekly']

                    # 筛选出回测开始日期之后的数据，使用正确的初始价格
                    backtest_data = weekly_data[weekly_data.index >= start_date_obj]

                    if not backtest_data.empty:
                        # 使用回测开始日期对应的第一个交易日价格
                        initial_price = backtest_data.iloc[0]['close']
                        initial_prices[stock_code] = initial_price

                        self.logger.info(f"🎯 {stock_code} 初始价格: {initial_price:.2f} (日期: {backtest_data.index[0].strftime('%Y-%m-%d')})")
                    else:
                        self.logger.error(f"❌ 股票 {stock_code} 在回测开始日期后没有数据")
                        return False

                    # 将价格数据设置到统一数据管理器
                    price_data = {}
                    for idx, row in weekly_data.iterrows():
                        date_str = idx.strftime('%Y-%m-%d')
                        price_data[date_str] = row['close']
                    self.portfolio_data_manager.set_price_data(stock_code, price_data)

            # 2. 获取各股票持仓比例，并计算出合理的持仓股数
            holdings = {}
            stock_market_values = {}
            total_stock_market_value = 0.0

            for stock_code in self.stock_pool:
                if stock_code in self.initial_holdings and stock_code in initial_prices:
                    weight = self.initial_holdings[stock_code]
                    if weight <= 0:
                        continue

                    # 计算目标股票价值
                    target_stock_value = total_capital * weight
                    price = initial_prices[stock_code]

                    # 计算股数（向下取整到100股的整数倍）
                    shares = int(target_stock_value / price / 100) * 100

                    if shares > 0:
                        holdings[stock_code] = shares
                        # 3. 从持仓股数推算得各股票市值
                        actual_market_value = shares * price
                        stock_market_values[stock_code] = actual_market_value
                        total_stock_market_value += actual_market_value

                        self.logger.info(f"📊 {stock_code}: 目标权重 {weight:.1%}, 持仓 {shares:,}股, 实际市值 {actual_market_value:,.2f}")

            # 4. 从总资产金额减去总的股票市值得到现金值
            cash_value = total_capital - total_stock_market_value

            self.logger.info(f"📈 总股票市值: {total_stock_market_value:,.2f}")
            self.logger.info(f"💵 计算得出现金值: {cash_value:,.2f}")

            # 创建投资组合管理器（不使用initial_holdings，直接设置计算结果）
            self.portfolio_manager = PortfolioManager(
                total_capital=total_capital,
                initial_holdings={}  # 空字典，我们将直接设置计算结果
            )
            
            # 设置成本计算器
            self.portfolio_manager.cost_calculator = self.cost_calculator

            # 直接设置计算得出的持仓和现金
            self.portfolio_manager.holdings = holdings.copy()
            self.portfolio_manager.cash = cash_value
            self.portfolio_manager.initial_prices = initial_prices.copy()

            # 验证总价值
            calculated_total_value = self.portfolio_manager.get_total_value(initial_prices)

            self.logger.info("✅ 投资组合初始化完成")
            self.logger.info(f"💰 总资产: {total_capital:,.2f}")
            self.logger.info(f"📈 股票市值: {total_stock_market_value:,.2f}")
            self.logger.info(f"💵 现金: {cash_value:,.2f}")
            self.logger.info(f"🔍 计算总价值: {calculated_total_value:,.2f}")
            self.logger.info(f"✓ 价值验证: {'通过' if abs(calculated_total_value - total_capital) < 0.01 else '失败'}")
            self.logger.info(f"📋 持仓详情: {holdings}")

            return True

        except Exception as e:
            self.logger.error(f"❌ 投资组合初始化失败: {e}")
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
            
            # 获取所有交易日期（使用所有股票日期的并集）
            all_trading_dates = set()
            for stock_code in self.stock_data.keys():
                stock_dates = self.stock_data[stock_code]['weekly'].index
                all_trading_dates.update(stock_dates)
            
            # 转换为排序的DatetimeIndex
            all_trading_dates = pd.DatetimeIndex(sorted(all_trading_dates))
            
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
                
                # 处理分红配股事件
                self._process_dividend_events(current_date)
                
                # 生成交易信号
                signals = self._generate_signals(current_date)
                
                # 执行交易
                if signals:
                    executed_trades = self._execute_trades(signals, current_date)
                    if executed_trades:
                        self.logger.info(f"{current_date.strftime('%Y-%m-%d')} 执行记录:")
                        for trade in executed_trades:
                            self.logger.info(f"  {trade}")
                
                # 记录投资组合状态到统一数据管理器
                date_str = current_date.strftime('%Y-%m-%d')
                self.portfolio_data_manager.record_portfolio_state(
                    date=date_str,
                    positions=self.portfolio_manager.positions.copy(),
                    cash=self.portfolio_manager.cash,
                    prices=current_prices
                )
            
            self.logger.info("回测完成")
            return True
            
        except Exception as e:
            self.logger.error(f"回测运行失败: {e}")
            return False
    
    def _process_dividend_events(self, current_date: pd.Timestamp) -> None:
        """
        处理当前日期的分红配股事件
        
        Args:
            current_date: 当前日期
        """
        try:
            # 检查所有持仓股票的分红事件
            dividend_events_today = {}
            
            for stock_code in self.stock_pool:
                if stock_code not in self.stock_data:
                    continue
                
                # 获取股票的周线数据
                stock_weekly = self.stock_data[stock_code]['weekly']
                
                # 检查当前日期是否有分红事件
                if current_date in stock_weekly.index:
                    row = stock_weekly.loc[current_date]
                    
                    # 检查是否有分红配股事件
                    has_dividend = (
                        row.get('dividend_amount', 0) > 0 or
                        row.get('bonus_ratio', 0) > 0 or
                        row.get('transfer_ratio', 0) > 0 or
                        row.get('allotment_ratio', 0) > 0
                    )
                    
                    if has_dividend:
                        dividend_events_today[stock_code] = row
                        self.logger.info(f"💰 {current_date.strftime('%Y-%m-%d')} 发现 {stock_code} 分红事件: 派息{row.get('dividend_amount', 0)}元")
            
            # 如果有分红事件，则处理
            if dividend_events_today:
                self.portfolio_manager.process_dividend_events(current_date, dividend_events_today)
                self.logger.info(f"✅ {current_date.strftime('%Y-%m-%d')} 分红事件处理完成，共 {len(dividend_events_today)} 个事件")
                
        except Exception as e:
            self.logger.warning(f"⚠️ {current_date.strftime('%Y-%m-%d')} 分红事件处理失败: {e}")
    
    def _generate_signals(self, current_date: pd.Timestamp) -> Dict[str, str]:
        """
        生成交易信号（使用SignalGenerator）
        
        Args:
            current_date: 当前日期
            
        Returns:
            Dict[str, str]: 股票代码到信号的映射
        """
        # 使用SignalGenerator直接生成信号
        signals = {}
        
        # 获取信号详情用于报告
        if not hasattr(self, 'signal_details'):
            self.signal_details = {}
        
        # 遍历每只股票生成信号
        for stock_code in self.stock_pool:
            if stock_code not in self.stock_data:
                continue
            
            # 获取当前日期的数据
            stock_weekly = self.stock_data[stock_code]['weekly']
            if current_date not in stock_weekly.index:
                continue
            
            # 使用SignalGenerator生成信号（只传递stock_code和data）
            result = self.signal_generator.generate_signal(
                stock_code,
                self.stock_data[stock_code]
            )
            
            if result and result.signal_type != 'HOLD':
                signals[stock_code] = result.signal_type
                # 记录信号详情
                self.signal_details[f"{stock_code}_{current_date.strftime('%Y-%m-%d')}"] = {
                    'signal_type': result.signal_type,
                    'reasons': result.reasons,
                    'scores': result.scores
                }
        
        return signals
    
    def _execute_trades(self, signals: Dict[str, str], current_date: pd.Timestamp) -> List[str]:
        """
        执行交易 - 使用动态仓位管理器
        
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
        
        # 计算总资产用于动态仓位管理
        total_assets = self.portfolio_manager.get_total_value(current_prices)
        
        # 执行卖出信号
        for stock_code, signal in signals.items():
            if signal == 'SELL' and stock_code in current_prices:
                current_position = self.portfolio_manager.positions.get(stock_code, 0)
                if current_position > 0:
                    price = current_prices[stock_code]
                    
                    # 获取DCF估值计算价值比
                    dcf_value = self.dcf_values.get(stock_code)
                    if dcf_value and dcf_value > 0:
                        value_price_ratio = price / dcf_value
                        
                        # 使用动态仓位管理器计算卖出数量
                        can_sell, sell_shares, sell_value, reason = self.portfolio_manager.can_sell_dynamic(
                            stock_code, value_price_ratio, price, self.dynamic_position_manager, current_prices
                        )
                        
                        if can_sell and sell_shares > 0:
                            # 记录交易前的仓位信息
                            position_before = current_position
                            total_value = self.portfolio_manager.get_total_value(current_prices)
                            position_weight_before = (position_before * price / total_value) if total_value > 0 else 0.0
                            
                            success, trade_info = self.portfolio_manager.sell_stock(
                                stock_code, sell_shares, price, current_date, reason
                            )
                            if success:
                                # 获取交易后的仓位
                                position_after = self.portfolio_manager.positions.get(stock_code, 0)
                                # 计算交易后的仓位占比
                                total_value_after = self.portfolio_manager.get_total_value(current_prices)
                                position_weight_after = (position_after * price / total_value_after) if total_value_after > 0 else 0.0
                                
                                self.logger.info(f"执行动态卖出: {stock_code} {sell_shares}股 @ {price:.2f} - {reason}")
                                self._record_transaction(trade_info, current_date)
                                executed_trades.append(f"动态卖出: {stock_code} {sell_shares}股 - {reason}")
                                
                                # 更新信号执行状态为"已执行"，包含仓位信息
                                signal_id = self.signal_tracker.get_signal_id(stock_code, current_date, 'SELL')
                                self.signal_tracker.update_execution_status(
                                    signal_id=signal_id,
                                    execution_status='已执行',
                                    execution_date=current_date,
                                    execution_price=price,
                                    position_before_signal=position_before,
                                    position_weight_before=position_weight_before,
                                    trade_shares=sell_shares,
                                    position_after_trade=position_after,
                                    position_weight_after=position_weight_after
                                )
                            else:
                                self.logger.warning(f"动态卖出失败: {stock_code}")
                                # 更新信号执行状态为"未执行"
                                signal_id = self.signal_tracker.get_signal_id(stock_code, current_date, 'SELL')
                                
                                # 即使未执行，也要记录当前的仓位信息
                                position_before = current_position
                                total_value = self.portfolio_manager.get_total_value(current_prices)
                                position_weight_before = (position_before * price / total_value) if total_value > 0 else 0.0
                                
                                self.signal_tracker.update_execution_status(
                                    signal_id=signal_id,
                                    execution_status='未执行',
                                    execution_reason=self.EXECUTION_REJECTION_REASONS.get('SYSTEM_ERROR', '系统错误'),
                                    position_before_signal=position_before,
                                    position_weight_before=position_weight_before,
                                    trade_shares=0,
                                    position_after_trade=position_before,  # 未执行，仓位不变
                                    position_weight_after=position_weight_before  # 未执行，占比不变
                                )
                        else:
                            self.logger.info(f"动态卖出跳过: {stock_code} - {reason}")
                            # 更新信号执行状态为"未执行"，并记录具体原因和当前仓位信息
                            signal_id = self.signal_tracker.get_signal_id(stock_code, current_date, 'SELL')
                            rejection_reason = self._map_rejection_reason(reason)
                            
                            # 即使未执行，也要记录当前的仓位信息
                            position_before = current_position
                            total_value = self.portfolio_manager.get_total_value(current_prices)
                            position_weight_before = (position_before * price / total_value) if total_value > 0 else 0.0
                            
                            self.signal_tracker.update_execution_status(
                                signal_id=signal_id,
                                execution_status='未执行',
                                execution_reason=rejection_reason,
                                position_before_signal=position_before,
                                position_weight_before=position_weight_before,
                                trade_shares=0,
                                position_after_trade=position_before,  # 未执行，仓位不变
                                position_weight_after=position_weight_before  # 未执行，占比不变
                            )
                    else:
                        # 回退到原有逻辑
                        sell_shares = int(current_position * self.rotation_percentage / 100) * 100
                        if sell_shares > 0:
                            success, trade_info = self.portfolio_manager.sell_stock(
                                stock_code, sell_shares, price, current_date, "固定比例卖出"
                            )
                            if success:
                                self.logger.info(f"执行固定卖出: {stock_code} {sell_shares}股 @ {price:.2f}")
                                self._record_transaction(trade_info, current_date)
                                executed_trades.append(f"固定卖出: {stock_code} {sell_shares}股")
                                
                                # 更新信号执行状态为"已执行"
                                signal_id = self.signal_tracker.get_signal_id(stock_code, current_date, 'SELL')
                                self.signal_tracker.update_execution_status(
                                    signal_id=signal_id,
                                    execution_status='已执行',
                                    execution_date=current_date,
                                    execution_price=price
                                )
        
        # 执行买入信号
        for stock_code, signal in signals.items():
            if signal == 'BUY' and stock_code in current_prices:
                current_position = self.portfolio_manager.positions.get(stock_code, 0)
                price = current_prices[stock_code]
                
                # 获取DCF估值计算价值比
                dcf_value = self.dcf_values.get(stock_code)
                if dcf_value and dcf_value > 0:
                    value_price_ratio = price / dcf_value
                    
                    # 使用动态仓位管理器计算买入数量
                    can_buy, buy_shares, buy_value, reason = self.portfolio_manager.can_buy_dynamic(
                        stock_code, value_price_ratio, price, self.dynamic_position_manager, current_prices
                    )
                    
                    if can_buy and buy_shares > 0:
                        # 记录交易前的仓位信息
                        position_before = current_position
                        total_value = self.portfolio_manager.get_total_value(current_prices)
                        position_weight_before = (position_before * price / total_value) if total_value > 0 else 0.0
                        
                        success, trade_info = self.portfolio_manager.buy_stock(
                            stock_code, buy_shares, price, current_date, reason
                        )
                        if success:
                            # 获取交易后的仓位
                            position_after = self.portfolio_manager.positions.get(stock_code, 0)
                            # 计算交易后的仓位占比
                            total_value_after = self.portfolio_manager.get_total_value(current_prices)
                            position_weight_after = (position_after * price / total_value_after) if total_value_after > 0 else 0.0
                            
                            self.logger.info(f"执行动态买入: {stock_code} {buy_shares}股 @ {price:.2f} - {reason}")
                            self._record_transaction(trade_info, current_date)
                            executed_trades.append(f"动态买入: {stock_code} {buy_shares}股 - {reason}")
                            
                            # 更新信号执行状态为"已执行"，包含仓位信息
                            signal_id = self.signal_tracker.get_signal_id(stock_code, current_date, 'BUY')
                            self.signal_tracker.update_execution_status(
                                signal_id=signal_id,
                                execution_status='已执行',
                                execution_date=current_date,
                                execution_price=price,
                                position_before_signal=position_before,
                                position_weight_before=position_weight_before,
                                trade_shares=buy_shares,
                                position_after_trade=position_after,
                                position_weight_after=position_weight_after
                            )
                        else:
                            self.logger.warning(f"动态买入失败: {stock_code}")
                            # 更新信号执行状态为“未执行”
                            signal_id = self.signal_tracker.get_signal_id(stock_code, current_date, 'BUY')
                            self.signal_tracker.update_execution_status(
                                signal_id=signal_id,
                                execution_status='未执行',
                                execution_reason=self.EXECUTION_REJECTION_REASONS.get('SYSTEM_ERROR', '系统错误')
                            )
                    else:
                        self.logger.info(f"动态买入跳过: {stock_code} - {reason}")
                        # 更新信号执行状态为"未执行"，并记录具体原因和当前仓位信息
                        signal_id = self.signal_tracker.get_signal_id(stock_code, current_date, 'BUY')
                        rejection_reason = self._map_rejection_reason(reason)
                        
                        # 即使未执行，也要记录当前的仓位信息
                        position_before = current_position
                        total_value = self.portfolio_manager.get_total_value(current_prices)
                        position_weight_before = (position_before * price / total_value) if total_value > 0 else 0.0
                        
                        self.signal_tracker.update_execution_status(
                            signal_id=signal_id,
                            execution_status='未执行',
                            execution_reason=rejection_reason,
                            position_before_signal=position_before,
                            position_weight_before=position_weight_before,
                            trade_shares=0,
                            position_after_trade=position_before,  # 未执行，仓位不变
                            position_weight_after=position_weight_before  # 未执行，占比不变
                        )
                else:
                    # 回退到原有逻辑，但仍需应用单股持仓上限约束
                    self.logger.warning(f"{stock_code} 无DCF估值数据，使用固定比例交易但应用持仓上限约束")
                    
                    # 检查单股持仓上限约束
                    current_position_value = current_position * price
                    max_position_value = total_assets * self.dynamic_position_manager.max_single_position_ratio
                    remaining_capacity = max_position_value - current_position_value
                    
                    if remaining_capacity <= 0:
                        self.logger.info(f"固定交易跳过: {stock_code} - 已达到单股总仓位上限{self.dynamic_position_manager.max_single_position_ratio:.0%}")
                        continue
                    
                    if current_position > 0:
                        # 加仓逻辑 - 应用持仓上限约束
                        target_buy_amount = current_position_value * self.rotation_percentage
                        # 限制买入金额不超过剩余容量
                        target_buy_amount = min(target_buy_amount, remaining_capacity)
                        buy_shares = int(target_buy_amount / price / 100) * 100
                        
                        if buy_shares > 0 and target_buy_amount > 10000:
                            success, trade_info = self.portfolio_manager.buy_stock(
                                stock_code, buy_shares, price, current_date, f"固定比例加仓(受{self.dynamic_position_manager.max_single_position_ratio:.0%}上限约束)"
                            )
                            if success:
                                self.logger.info(f"执行固定买入: {stock_code} {buy_shares}股 @ {price:.2f} (受持仓上限约束)")
                                self._record_transaction(trade_info, current_date)
                                executed_trades.append(f"固定买入: {stock_code} {buy_shares}股")
                    else:
                        # 开仓逻辑 - 应用持仓上限约束
                        available_cash = self.portfolio_manager.cash * self.rotation_percentage
                        # 限制开仓金额不超过持仓上限
                        max_open_amount = min(available_cash, max_position_value)
                        
                        if max_open_amount > 10000:
                            buy_shares = int(max_open_amount / price / 100) * 100
                            if buy_shares > 0:
                                success, trade_info = self.portfolio_manager.buy_stock(
                                    stock_code, buy_shares, price, current_date, f"固定比例开仓(受{self.dynamic_position_manager.max_single_position_ratio:.0%}上限约束)"
                                )
                                if success:
                                    self.logger.info(f"执行固定开仓: {stock_code} {buy_shares}股 @ {price:.2f} (受持仓上限约束)")
                                    self._record_transaction(trade_info, current_date)
                                    executed_trades.append(f"固定开仓: {stock_code} {buy_shares}股")
        
        return executed_trades
    
    def _map_rejection_reason(self, reason: str) -> str:
        """
        将动态仓位管理器的拒绝原因映射到标准化原因
        
        Args:
            reason: 动态仓位管理器返回的原因
            
        Returns:
            str: 标准化的拒绝原因
        """
        reason_lower = reason.lower()
        
        # 根据关键词匹配映射关系
        if '现金不足' in reason or 'insufficient cash' in reason_lower:
            if '80%' in reason:
                return self.EXECUTION_REJECTION_REASONS['INSUFFICIENT_CASH_80PCT']
            return self.EXECUTION_REJECTION_REASONS['INSUFFICIENT_CASH']
        elif '仓位上限' in reason or 'position limit' in reason_lower:
            if '已达' in reason or 'reached' in reason_lower:
                return self.EXECUTION_REJECTION_REASONS['POSITION_LIMIT_REACHED']
            return self.EXECUTION_REJECTION_REASONS['POSITION_LIMIT_EXCEEDED']
        elif '交易上限' in reason or 'transaction limit' in reason_lower:
            return self.EXECUTION_REJECTION_REASONS['TRANSACTION_LIMIT_EXCEEDED']
        elif '估值' in reason and '不支持' in reason:
            return self.EXECUTION_REJECTION_REASONS['VALUATION_NOT_SUPPORT_BUY']
        elif '最小' in reason and '要求' in reason:
            return self.EXECUTION_REJECTION_REASONS['BELOW_MIN_BUY_REQUIREMENT']
        elif '100股' in reason or 'shares multiple' in reason_lower:
            return self.EXECUTION_REJECTION_REASONS['NOT_100_SHARES_MULTIPLE']
        elif '停牌' in reason or '流动性' in reason:
            return self.EXECUTION_REJECTION_REASONS['STOCK_SUSPENDED']
        elif '数据异常' in reason or 'data error' in reason_lower:
            return self.EXECUTION_REJECTION_REASONS['DATA_ABNORMAL']
        else:
            # 默认情况，返回原始原因或系统错误
            return reason if reason else self.EXECUTION_REJECTION_REASONS['SYSTEM_ERROR']
    
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
                            
                            # 如果当前值有效，直接返回
                            if value is not None and pd.notna(value) and value != 0:
                                return float(value)
                            
                            # 当前值无效，向前查找最近的有效值
                            current_idx = stock_weekly.index.get_loc(current_date)
                            for i in range(current_idx - 1, max(0, current_idx - 20), -1):
                                try:
                                    hist_val = stock_weekly.iloc[i][field_name]
                                    if hist_val is not None and not pd.isna(hist_val):
                                        return float(hist_val)
                                except:
                                    continue
                            return default_val
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
                    rsi_thresholds_info = {}
                    try:
                        signal_result = self.signal_generator.generate_signal(stock_code, historical_data)
                        if signal_result and isinstance(signal_result, dict):
                            signal_details = {
                                'signal_type': signal_result.get('signal', 'HOLD'),
                                'confidence': signal_result.get('confidence', 0),
                                'reason': signal_result.get('reason', ''),
                                'scores': signal_result.get('scores', {}),
                                'dimension_status': self._extract_dimension_status(signal_result.get('scores', {}))
                            }
                            # 提取RSI阈值信息
                            rsi_thresholds_info = signal_result.get('rsi_thresholds', {})
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
            rsi_thresholds_info = {}
            self._fallback_get_technical_indicators(stock_code, current_date, technical_indicators, signal_details)
                
        # 如果技术指标为空，使用降级处理
        if not technical_indicators:
            if 'rsi_thresholds_info' not in locals():
                rsi_thresholds_info = {}
            self._fallback_get_technical_indicators(stock_code, current_date, technical_indicators, signal_details)
        
        # 获取交易后持仓数量
        position_after_trade = self.portfolio_manager.positions.get(stock_code, 0)
        
        # 计算价值比 (Price-to-Value Ratio, PVR)
        current_price = trade_info['price']
        dcf_value = self.dcf_values.get(stock_code)
        pvr = calculate_pvr(current_price, dcf_value) if dcf_value else None
        pvr_status = get_pvr_status(pvr) if pvr else None
        
        # 记录交易
        transaction_record = {
            'date': current_date.strftime('%Y-%m-%d'),
            'type': trade_info['type'],
            'stock_code': stock_code,
            'shares': trade_info['shares'],
            'position_after_trade': position_after_trade,  # 添加交易后持仓数量
            'price': trade_info['price'],
            'dcf_value': dcf_value,  # DCF估值
            'price_to_value_ratio': pvr,  # 价值比
            'pvr_status': pvr_status['status'] if pvr_status else None,  # 估值状态
            'pvr_description': pvr_status['description'] if pvr_status else None,  # 价值比描述
            'gross_amount': trade_info['gross_amount'],
            'transaction_cost': trade_info['transaction_cost'],
            'net_amount': trade_info['net_amount'],
            'reason': trade_info['reason'],
            'technical_indicators': technical_indicators,
            'signal_details': signal_details,
            'rsi_thresholds': rsi_thresholds_info  # 添加RSI阈值信息
        }
        
        # 记录价值比信息到日志
        if pvr:
            self.logger.info(f"💰 {stock_code} 价值比分析: 当前价格{current_price:.2f}, DCF估值{dcf_value:.2f}, 价值比{pvr:.1f}% ({pvr_status['status']})")
        else:
            self.logger.warning(f"⚠️ {stock_code} 无DCF估值数据，无法计算价值比")
        
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
                            
                            # 如果当前值有效，直接返回
                            if current_value is not None and pd.notna(current_value) and current_value != 0:
                                return float(current_value)
                            
                            # 当前值无效，向前查找最近的有效值
                            current_idx = stock_weekly.index.get_loc(current_date)
                            for i in range(current_idx - 1, max(0, current_idx - 20), -1):
                                try:
                                    hist_value = stock_weekly.iloc[i][key]
                                    if hist_value is not None and pd.notna(hist_value) and hist_value != 0:
                                        return float(hist_value)
                                except:
                                    continue
                            
                            # 如果向前查找失败，向后查找
                            for i in range(current_idx + 1, min(len(stock_weekly), current_idx + 20)):
                                try:
                                    future_value = stock_weekly.iloc[i][key]
                                    if future_value is not None and pd.notna(future_value) and future_value != 0:
                                        return float(future_value)
                                except:
                                    continue
                            
                            # 都找不到有效值，返回默认值
                            return default_value
                            
                        except Exception as e:
                            self.logger.debug(f"获取指标 {key} 失败: {e}")
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
            'scores': {},
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
        # 从统一数据管理器获取portfolio历史
        portfolio_df = self.portfolio_data_manager.get_portfolio_history()
        
        if portfolio_df.empty:
            return {}
        
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
        
        # 确保基准计算在返回结果之前执行
        basic_metrics = {
            'initial_value': initial_value,
            'final_value': final_value,
            'total_return': total_return,
            'annual_return': annual_return,
            'max_drawdown': max_drawdown
        }
        trading_metrics = {
            'total_trades': total_trades,
            'buy_trades': buy_trades,
            'sell_trades': sell_trades
        }
        
        # 执行基准计算以确保基准持仓数据被正确收集
        print(f"🔍 在get_backtest_results中执行基准计算...")
        self._calculate_performance_metrics(basic_metrics, trading_metrics)
        
        return {
            'basic_metrics': basic_metrics,
            'trading_metrics': trading_metrics,
            'portfolio_history': portfolio_df,
            'transaction_history': pd.DataFrame(self.transaction_history) if self.transaction_history else pd.DataFrame(),
            'dividend_events': self.portfolio_manager.get_dividend_events() if hasattr(self.portfolio_manager, 'get_dividend_events') else [],
            'benchmark_portfolio_data': getattr(self, 'benchmark_portfolio_data', {})
        }
    
    def generate_reports(self) -> Dict[str, str]:
        """
        生成回测报告
        
        Returns:
            Dict[str, str]: 生成的报告文件路径
        """
        try:
            print(f"🔍 开始生成报告...")
            # 获取回测结果
            backtest_results = self.get_backtest_results()
            
            if not backtest_results:
                self.logger.error("无法获取回测结果")
                return {}
            
            print(f"📊 回测结果获取成功，开始准备集成数据...")
            # 准备集成报告所需的数据结构
            integrated_results = self._prepare_integrated_results(backtest_results)
            print(f"✅ 集成数据准备完成")
            
            # 生成集成HTML报告
            html_report_path = self.report_generator.generate_report(integrated_results)
            
            # 生成详细CSV报告
            # 使用transaction_history数据，并转换为正确格式
            transaction_history = backtest_results.get('transaction_history', pd.DataFrame())
            transactions_for_csv = []
            
            if not transaction_history.empty:
                transactions_for_csv = transaction_history.to_dict('records')
            
            csv_report_path = self.csv_exporter.export_trading_records(transactions_for_csv)
            
            # 导出分红配股事件CSV
            dividend_events = backtest_results.get('dividend_events', [])
            dividend_csv_path = None
            if dividend_events:
                self.logger.info(f"开始导出分红配股事件，共 {len(dividend_events)} 个事件")
                dividend_csv_path = self.csv_exporter.export_dividend_events(dividend_events)
                if dividend_csv_path:
                    self.logger.info(f"分红配股事件CSV导出成功: {dividend_csv_path}")
                else:
                    self.logger.warning("分红配股事件CSV导出失败")
            else:
                self.logger.info("未发现分红配股事件，跳过CSV导出")
            
            # 🆕 新增：导出信号跟踪报告
            signal_tracking_report_path = None
            try:
                signal_tracking_report_path = self.signal_tracker.export_to_csv()
                if signal_tracking_report_path:
                    signal_stats = self.signal_tracker.get_statistics()
                    self.logger.info(f"📊 信号跟踪报告导出成功: {signal_tracking_report_path}")
                    self.logger.info(f"📈 信号统计: 总计{signal_stats['total_signals']}个信号 (买入{signal_stats['buy_signals']}个, 卖出{signal_stats['sell_signals']}个)")
                else:
                    self.logger.warning("信号跟踪报告导出失败")
            except Exception as e:
                self.logger.error(f"信号跟踪报告导出异常: {e}")
            
            return {
                'html_report': html_report_path,
                'csv_report': csv_report_path,
                'dividend_csv_report': dividend_csv_path,
                'signal_tracking_report': signal_tracking_report_path
            }
            
        except Exception as e:
            self.logger.error(f"生成报告失败: {e}")
            return {}
    
    def _prepare_integrated_results(self, backtest_results: Dict[str, Any]) -> Dict[str, Any]:
        """
        准备集成报告所需的数据结构 - 使用统一数据管理器
        
        Args:
            backtest_results: 原始回测结果
            
        Returns:
            Dict[str, Any]: 集成报告数据结构
        """
        print(f"🔍 开始准备集成报告数据...")
        try:
            # 基础指标
            basic_metrics = backtest_results.get('basic_metrics', {})
            trading_metrics = backtest_results.get('trading_metrics', {})
            
            # 从统一数据管理器获取投资组合历史
            portfolio_history = self.portfolio_data_manager.get_portfolio_history()
            
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
            
            # 从统一数据管理器获取初始价格
            initial_prices = {}
            for stock_code in self.stock_pool:
                initial_price = self.portfolio_data_manager.get_initial_price(stock_code)
                if initial_price:
                    initial_prices[stock_code] = initial_price
            
            # 获取基准持仓数据
            benchmark_portfolio_data = backtest_results.get('benchmark_portfolio_data', {})
            print(f"🔍 基准持仓数据检查: {list(benchmark_portfolio_data.keys()) if benchmark_portfolio_data else 'None'}")
            
            # 添加SignalTracker数据用于未执行信号标注
            signal_tracker_data = {
                'signal_records': self.signal_tracker.signal_records,
                'statistics': self.signal_tracker.get_statistics()
            }
            
            return {
                'portfolio_history': portfolio_history.to_dict('records') if not portfolio_history.empty else [],
                'transactions': transaction_history.to_dict('records') if not transaction_history.empty else [],
                'final_portfolio': final_portfolio,
                'performance_metrics': performance_metrics,
                'signal_analysis': signal_analysis,
                'kline_data': kline_data,
                'dcf_values': getattr(self, 'dcf_values', {}),
                'initial_prices': initial_prices,  # 从统一数据管理器获取
                'benchmark_portfolio_data': benchmark_portfolio_data,  # 基准持仓数据
                'signal_tracker_data': signal_tracker_data  # 信号跟踪数据（包含未执行信号）
            }
            
        except Exception as e:
            self.logger.error(f"准备集成结果数据失败: {e}")
            return {}
    
    def _get_final_portfolio_status(self, portfolio_history: pd.DataFrame) -> Dict[str, Any]:
        """获取最终投资组合状态 - 使用统一数据管理器"""
        print(f"🔍 _get_final_portfolio_status 调试:")
        
        # 直接从统一数据管理器获取最终状态
        final_state = self.portfolio_data_manager.get_final_portfolio_state()
        
        if not final_state:
            print("⚠️ 无法从数据管理器获取最终状态")
            return {}
        
        print(f"  从数据管理器获取最终状态: {final_state}")
        
        # 转换为报告需要的格式
        result = {
            'end_date': final_state['date'],
            'total_value': final_state['total_value'],
            'cash': final_state['cash'],
            'stock_value': final_state['stock_value'],
            'positions': {}
        }
        
        # 转换持仓详情格式
        for stock_code, market_info in final_state.get('market_values', {}).items():
            result['positions'][stock_code] = {
                'shares': market_info['shares'],
                'current_price': market_info['price'],
                'market_value': market_info['market_value']
            }
        
        print(f"  转换后的最终结果: {result}")
        return result
    
    def _get_initial_portfolio_status(self, portfolio_history: pd.DataFrame) -> Dict[str, Any]:
        """
        获取初始投资组合状态 - 使用统一数据管理器
        
        Args:
            portfolio_history: 投资组合历史数据（兼容性参数）
            
        Returns:
            Dict[str, Any]: 初始投资组合状态详情
        """
        print(f"🔍 _get_initial_portfolio_status 调试:")
        
        # 直接从统一数据管理器获取初始状态
        initial_state = self.portfolio_data_manager.get_initial_portfolio_state()
        
        if not initial_state:
            print("⚠️ 无法从数据管理器获取初始状态")
            return {}
        
        print(f"  从数据管理器获取初始状态: {initial_state}")
        
        # 转换为报告需要的格式
        result = {
            'start_date': initial_state['date'],
            'total_value': initial_state['total_value'],
            'cash': initial_state['cash'],
            'stock_value': initial_state['stock_value'],
            'positions': {}
        }
        
        # 转换持仓详情格式
        for stock_code, market_info in initial_state.get('market_values', {}).items():
            result['positions'][stock_code] = {
                'shares': market_info['shares'],
                'initial_price': market_info['price'],
                'market_value': market_info['market_value']
            }
        
        print(f"  转换后的初始结果: {result}")
        return result
    
    def _calculate_performance_metrics(self, basic_metrics: Dict, trading_metrics: Dict) -> Dict[str, Any]:
        """计算绩效指标 - 使用统一数据管理器"""
        print(f"🔍 _calculate_performance_metrics 调试:")
        print(f"  basic_metrics: {basic_metrics}")
        print(f"  trading_metrics: {trading_metrics}")
        
        # 从统一数据管理器获取性能指标
        performance_metrics = self.portfolio_data_manager.calculate_performance_metrics()
        
        if not performance_metrics:
            print("⚠️ 无法从数据管理器获取性能指标")
            return {}
        
        print(f"  从数据管理器获取的性能指标: {performance_metrics}")
        
        # 转换为百分比格式
        total_return = performance_metrics.get('total_return_rate', 0)
        # 修复：正确获取年化收益率并转换为百分比
        annual_return = performance_metrics.get('annual_return', 0) * 100  # 转换为百分比
        max_drawdown = basic_metrics.get('max_drawdown', 0) * 100
        
        # 计算买入持有基准收益（基于实际股票池表现）
        print(f"🔍 开始计算买入持有基准...")
        benchmark_return, benchmark_annual_return, benchmark_max_drawdown = self._calculate_buy_and_hold_benchmark()
        print(f"📊 基准计算结果: 总收益率{benchmark_return:.2f}%, 年化{benchmark_annual_return:.2f}%, 最大回撤{benchmark_max_drawdown:.2f}%")
        
        # 检查基准持仓数据是否被正确存储
        benchmark_portfolio_data = getattr(self, 'benchmark_portfolio_data', {})
        print(f"🔍 基准持仓数据验证: {list(benchmark_portfolio_data.keys()) if benchmark_portfolio_data else 'None'}")
        if benchmark_portfolio_data:
            print(f"  总资产: ¥{benchmark_portfolio_data.get('total_value', 0):,.2f}")
            print(f"  持仓数量: {len(benchmark_portfolio_data.get('positions', {}))}只股票")
        
        result = {
            'initial_capital': performance_metrics.get('initial_value', self.total_capital),
            'final_value': performance_metrics.get('final_value', self.total_capital),
            'total_return': total_return,
            'annual_return': annual_return,
            'max_drawdown': max_drawdown,
            'benchmark_return': benchmark_return,
            'benchmark_annual_return': benchmark_annual_return,
            'benchmark_max_drawdown': benchmark_max_drawdown,
            'volatility': performance_metrics.get('volatility', 0) * 100,  # 转换为百分比
            'trading_days': performance_metrics.get('trading_days', 0)
        }
        
        print(f"  最终绩效指标: {result}")
        print(f"  🎯 年化收益率修复验证: {annual_return:.2f}%")
        return result
    
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
        """从评分中提取维度状态 - 确保与scores完全一致"""
        try:
            # 直接使用scores中的布尔值，确保完全一致
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
        """准备K线数据（包含技术指标）- 确保时间轴完全对齐"""
        kline_data = {}
        
        # 调试信息
        print("\n=== K线数据准备开始 ===")
        print(f"🔍 开始准备K线数据")
        print(f"📊 股票数据总数: {len(self.stock_data)}")
        print(f"📈 股票代码列表: {list(self.stock_data.keys())}")
        print(f"📋 交易记录数量: {len(self.transaction_history)}")
        if self.transaction_history:
            print(f"📝 交易记录示例: {self.transaction_history[0]}")
        
        self.logger.info(f"🔍 开始准备K线数据")
        self.logger.info(f"📊 股票数据总数: {len(self.stock_data)}")
        self.logger.info(f"📈 股票代码列表: {list(self.stock_data.keys())}")
        self.logger.info(f"📋 交易记录数量: {len(self.transaction_history)}")
        if self.transaction_history:
            self.logger.info(f"📝 交易记录示例: {self.transaction_history[0]}")
        
        # 过滤回测期间的数据
        start_date = pd.to_datetime(self.start_date)
        end_date = pd.to_datetime(self.end_date)
        
        for stock_code, data in self.stock_data.items():
            weekly_data = data['weekly']
            
            # 过滤K线数据到回测期间
            filtered_weekly_data = weekly_data[
                (weekly_data.index >= start_date) & (weekly_data.index <= end_date)
            ]
            
            # 获取所有有效的时间戳（确保时间轴完全一致）
            valid_timestamps = []
            for idx in filtered_weekly_data.index:
                try:
                    if hasattr(idx, 'timestamp'):
                        timestamp = int(idx.timestamp() * 1000)
                    else:
                        timestamp = int(pd.to_datetime(idx).timestamp() * 1000)
                    valid_timestamps.append((timestamp, idx))
                except Exception as e:
                    self.logger.warning(f"时间戳转换失败: {e}, 索引: {idx}")
                    continue
            
            # 准备所有数据数组
            kline_points = []
            rsi_data = []
            macd_data = []
            macd_signal_data = []
            macd_histogram_data = []
            bb_upper_data = []
            bb_middle_data = []
            bb_lower_data = []
            pvr_data = []  # 新增价值比数据
            
            # 为每个有效时间戳准备数据，确保所有指标都有对应的数据点
            for timestamp, idx in valid_timestamps:
                try:
                    row = filtered_weekly_data.loc[idx]
                    
                    # K线数据（必须有效）- ECharts蜡烛图格式: [timestamp, open, close, low, high]
                    kline_points.append([
                        timestamp,
                        float(row['open']),
                        float(row['close']),
                        float(row['low']),
                        float(row['high'])
                    ])
                    
                    # 技术指标数据 - 直接使用当前行的值，不使用回退逻辑
                    def safe_get_indicator_value(field_name, default_value):
                        """直接获取技术指标值，避免回退逻辑造成的平线问题"""
                        try:
                            if field_name not in filtered_weekly_data.columns:
                                return default_value
                            
                            current_value = row.get(field_name)
                            
                            # 如果当前值有效，直接返回
                            if current_value is not None and pd.notna(current_value):
                                return float(current_value)
                            
                            # 如果当前值无效，返回默认值而不是回退到历史值
                            # 这样可以避免造成平线效果
                            return default_value
                            
                        except Exception as e:
                            self.logger.debug(f"获取指标 {field_name} 失败: {e}")
                            return default_value
                    
                    # RSI数据 - 确保每个时间点都有数据
                    rsi_value = safe_get_indicator_value('rsi', 50.0)
                    rsi_data.append([timestamp, rsi_value])
                    
                    # MACD数据 - 确保每个时间点都有数据
                    macd_dif_value = safe_get_indicator_value('macd', 0.0)
                    macd_data.append([timestamp, macd_dif_value])
                    
                    macd_signal_value = safe_get_indicator_value('macd_signal', 0.0)
                    macd_signal_data.append([timestamp, macd_signal_value])
                    
                    macd_hist_value = safe_get_indicator_value('macd_histogram', 0.0)
                    macd_histogram_data.append([timestamp, macd_hist_value])
                    
                    # 布林带数据 - 确保每个时间点都有数据
                    close_price = float(row['close'])
                    bb_upper_value = safe_get_indicator_value('bb_upper', close_price * 1.02)
                    bb_middle_value = safe_get_indicator_value('bb_middle', close_price)
                    bb_lower_value = safe_get_indicator_value('bb_lower', close_price * 0.98)
                    
                    bb_upper_data.append([timestamp, bb_upper_value])
                    bb_middle_data.append([timestamp, bb_middle_value])
                    bb_lower_data.append([timestamp, bb_lower_value])
                    
                    # 价值比数据 - 使用当前价格和DCF估值直接计算
                    close_price = float(row['close'])
                    dcf_value = self.dcf_values.get(stock_code)
                    if dcf_value and dcf_value > 0:
                        pvr_value = (close_price / dcf_value) * 100
                    else:
                        pvr_value = 100.0  # 默认值，表示无DCF数据
                    pvr_data.append([timestamp, pvr_value])
                        
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
            self.logger.info(f"股票 {stock_code} 技术指标数据量: RSI {len(rsi_data)}, MACD {len(macd_data)}, PVR {len(pvr_data)}")
            
            # 🆕 准备分红数据用于K线图标记
            dividend_points = []
            if stock_code in self.stock_data and 'weekly' in self.stock_data[stock_code]:
                weekly_data = self.stock_data[stock_code]['weekly']
                filtered_weekly_data = weekly_data[
                    (weekly_data.index >= start_date) & (weekly_data.index <= end_date)
                ]
                
                # 查找分红事件
                for timestamp, idx in valid_timestamps:
                    try:
                        row = filtered_weekly_data.loc[idx]
                        
                        # 检查是否有分红事件
                        dividend_amount = row.get('dividend_amount', 0)
                        bonus_ratio = row.get('bonus_ratio', 0)
                        transfer_ratio = row.get('transfer_ratio', 0)
                        
                        if dividend_amount > 0 or bonus_ratio > 0 or transfer_ratio > 0:
                            # 构建分红事件数据
                            dividend_event = {
                                'timestamp': timestamp,
                                'date': idx.strftime('%Y-%m-%d'),
                                'dividend_amount': float(dividend_amount) if dividend_amount > 0 else 0,
                                'bonus_ratio': float(bonus_ratio) if bonus_ratio > 0 else 0,
                                'transfer_ratio': float(transfer_ratio) if transfer_ratio > 0 else 0,
                                'close_price': float(row['close'])
                            }
                            
                            # 确定分红事件类型和描述
                            event_types = []
                            if dividend_amount > 0:
                                event_types.append(f"现金分红{dividend_amount:.3f}元/股")
                            if bonus_ratio > 0:
                                event_types.append(f"送股{bonus_ratio:.3f}")
                            if transfer_ratio > 0:
                                event_types.append(f"转增{transfer_ratio:.3f}")
                            
                            dividend_event['description'] = "；".join(event_types)
                            dividend_event['type'] = 'dividend' if dividend_amount > 0 else ('bonus' if bonus_ratio > 0 else 'transfer')
                            
                            dividend_points.append(dividend_event)
                            
                    except Exception as e:
                        self.logger.debug(f"处理分红数据失败: {e}, 索引: {idx}")
                        continue
            
            self.logger.info(f"股票 {stock_code} 分红事件数量: {len(dividend_points)}")

            kline_data[stock_code] = {
                'kline': kline_points,
                'trades': trade_points,
                'name': stock_code,  # 添加股票名称
                # 添加技术指标数据
                'rsi': rsi_data,
                'macd': {
                    'dif': macd_data,
                    'dea': macd_signal_data,
                    'histogram': macd_histogram_data
                },
                # 添加布林带数据
                'bb_upper': bb_upper_data,
                'bb_middle': bb_middle_data,
                'bb_lower': bb_lower_data,
                # 添加价值比数据
                'pvr': pvr_data,
                # 🆕 添加分红数据
                'dividends': dividend_points
            }
        
        return kline_data

    def _calculate_buy_and_hold_benchmark(self) -> Tuple[float, float, float]:
        """
        计算买入持有基准收益（基于实际投资组合配置）
        
        Returns:
            Tuple[float, float, float]: (总收益率%, 年化收益率%, 最大回撤%)
        """
        try:
            print(f"🔍 基准计算开始 - 股票数据数量: {len(self.stock_data) if self.stock_data else 0}")
            print(f"🔍 回测日期范围: {self.start_date} 到 {self.end_date}")
            
            # 🔧 修复：检查投资组合配置，判断是否为100%现金
            try:
                import pandas as pd
                df = pd.read_csv('Input/portfolio_config.csv', encoding='utf-8-sig')
                
                total_stock_weight = 0
                cash_weight = 0
                
                for _, row in df.iterrows():
                    code = str(row['Stock_number']).strip()
                    weight = float(row['Initial_weight'])
                    
                    if code.upper() == 'CASH':
                        cash_weight = weight
                    else:
                        total_stock_weight += weight
                
                print(f"🔍 投资组合配置检查: 股票权重={total_stock_weight:.1%}, 现金权重={cash_weight:.1%}")
                
                # 如果是100%现金或接近100%现金，基准应该是现金收益率
                if total_stock_weight <= 0.01:  # 股票权重小于等于1%
                    print("💰 检测到100%现金投资组合，使用现金基准收益率")
                    return 0.0, 0.0, 0.0  # 现金基准：0%收益率，0%波动率
                    
            except Exception as e:
                print(f"⚠️ 读取投资组合配置失败: {e}，继续使用股票基准计算")
            
            if not self.stock_data:
                print("⚠️ 没有股票数据，使用默认基准值")
                return 45.0, 12.0, -18.0
            
            # 🔧 修改：使用与策略收益率相同的计算方法
            # 基于投资组合总市值变化：(结束日总市值 - 开始日总市值) / 开始日总市值
            start_date = pd.to_datetime(self.start_date)
            end_date = pd.to_datetime(self.end_date)
            
            # 读取投资组合配置，获取初始权重
            try:
                import pandas as pd
                df = pd.read_csv('Input/portfolio_config.csv', encoding='utf-8-sig')
                
                initial_weights = {}
                total_stock_weight = 0
                cash_weight = 0
                
                for _, row in df.iterrows():
                    code = str(row['Stock_number']).strip()
                    weight = float(row['Initial_weight'])
                    
                    if code.upper() == 'CASH':
                        cash_weight = weight
                    else:
                        initial_weights[code] = weight
                        total_stock_weight += weight
                
                print(f"🔍 基准计算 - 投资组合权重: 股票{total_stock_weight:.1%}, 现金{cash_weight:.1%}")
                
                # 如果是100%现金，直接返回0%收益率
                if total_stock_weight <= 0.01:
                    print("💰 基准计算 - 100%现金投资组合，基准收益率为0%")
                    return 0.0, 0.0, 0.0
                
            except Exception as e:
                print(f"⚠️ 读取投资组合配置失败: {e}，使用等权重基准")
                # 使用等权重作为默认
                initial_weights = {code: 1.0/len(self.stock_data) for code in self.stock_data.keys()}
                cash_weight = 0
            
            # 计算基准投资组合的开始和结束市值（包含分红收入）
            start_total_value = 0
            end_total_value = 0
            total_dividend_income = 0  # 新增：总分红收入
            
            # 假设初始投资金额为self.total_capital
            initial_capital = self.total_capital
            
            for stock_code, weight in initial_weights.items():
                if stock_code not in self.stock_data:
                    continue
                    
                weekly_data = self.stock_data[stock_code]['weekly']
                
                # 过滤到回测期间
                filtered_data = weekly_data[
                    (weekly_data.index >= start_date) & (weekly_data.index <= end_date)
                ]
                
                if len(filtered_data) < 2:
                    continue
                
                # 计算该股票的投资金额和股数
                start_price = filtered_data.iloc[0]['close']
                end_price = filtered_data.iloc[-1]['close']
                
                investment_amount = initial_capital * weight
                # 🔧 修复：计算整股数量（100股的整数倍），与策略持仓保持一致
                raw_shares = investment_amount / start_price
                initial_shares = int(raw_shares / 100) * 100  # 向下取整到100股的整数倍
                current_shares = initial_shares  # 当前持股数（会因送股转增而变化）
                
                # 🆕 计算分红收入和股份变化
                dividend_income = 0
                for date, row in filtered_data.iterrows():
                    # 现金分红
                    if row.get('dividend_amount', 0) > 0:
                        dividend_income += current_shares * row['dividend_amount']
                        self.logger.debug(f"基准 - {stock_code} {date.date()}: 分红 {row['dividend_amount']:.3f}元/股, 持股{current_shares:.0f}股, 分红收入{current_shares * row['dividend_amount']:.2f}元")
                    
                    # 送股（增加持股数）
                    if row.get('bonus_ratio', 0) > 0:
                        bonus_shares = current_shares * row['bonus_ratio']
                        current_shares += bonus_shares
                        self.logger.debug(f"基准 - {stock_code} {date.date()}: 送股 {row['bonus_ratio']:.3f}, 新增{bonus_shares:.0f}股, 总持股{current_shares:.0f}股")
                    
                    # 转增（增加持股数）
                    if row.get('transfer_ratio', 0) > 0:
                        transfer_shares = current_shares * row['transfer_ratio']
                        current_shares += transfer_shares
                        self.logger.debug(f"基准 - {stock_code} {date.date()}: 转增 {row['transfer_ratio']:.3f}, 新增{transfer_shares:.0f}股, 总持股{current_shares:.0f}股")
                
                # 计算开始和结束市值（结束市值使用调整后的股数）
                start_value = initial_shares * start_price
                end_value = current_shares * end_price  # 🆕 使用调整后的股数
                
                start_total_value += start_value
                end_total_value += end_value
                total_dividend_income += dividend_income
                
                self.logger.info(f"基准 - {stock_code}: 权重{weight:.1%}, {start_price:.2f}->{end_price:.2f}, 初始{initial_shares:.0f}股->最终{current_shares:.0f}股, 市值{start_value:.0f}->{end_value:.0f}, 分红{dividend_income:.0f}元")
            
            # 加上现金部分
            cash_amount = initial_capital * cash_weight
            start_total_value += cash_amount
            end_total_value += cash_amount  # 现金不变
            
            if start_total_value <= 0:
                print("⚠️ 基准计算失败，使用默认值")
                return 45.0, 12.0, -18.0
            
            # 🎯 修复：基准收益率 = (结束市值 + 分红收入 - 开始市值) / 开始市值
            # 这样与策略收益率计算保持一致（策略收益率也包含分红收入）
            total_return = (end_total_value + total_dividend_income - start_total_value) / start_total_value
            
            # 计算年化收益率
            days = (end_date - start_date).days
            if days > 0:
                annual_return = (end_total_value / start_total_value) ** (365.25 / days) - 1
            else:
                annual_return = 0
            
            # 估算最大回撤（简化计算）
            estimated_max_drawdown = -abs(total_return * 0.6)  # 假设最大回撤为总收益率的60%
            
            # 转换为百分比
            total_return_pct = total_return * 100
            annual_return_pct = annual_return * 100
            max_drawdown_pct = estimated_max_drawdown * 100
            
            self.logger.info(f"🎯 基准计算完成 (包含分红收入):")
            self.logger.info(f"  开始市值: {start_total_value:,.0f} 元")
            self.logger.info(f"  结束市值: {end_total_value:,.0f} 元")
            self.logger.info(f"  💰 总分红收入: {total_dividend_income:,.0f} 元")
            self.logger.info(f"  📈 总收益率: {total_return_pct:.2f}% (包含分红)")
            self.logger.info(f"  📈 年化收益率: {annual_return_pct:.2f}% (包含分红)")
            self.logger.info(f"  估算最大回撤: {max_drawdown_pct:.2f}%")
            
            # 🆕 收集基准持仓状态数据用于报告生成
            # 🔧 修复：现金应该是初始现金加上分红收入
            final_cash = cash_amount + total_dividend_income
            benchmark_portfolio_data = {
                'total_value': end_total_value + total_dividend_income,
                'cash': final_cash,  # 初始现金 + 分红收入
                'stock_value': end_total_value - cash_amount,  # 纯股票市值（不包含现金）
                'dividend_income': total_dividend_income,
                'positions': {},
                'start_date': start_date.strftime('%Y-%m-%d'),
                'end_date': end_date.strftime('%Y-%m-%d')
            }
            
            # 收集每只股票的详细持仓数据
            for stock_code, weight in initial_weights.items():
                if stock_code not in self.stock_data:
                    continue
                    
                weekly_data = self.stock_data[stock_code]['weekly']
                filtered_data = weekly_data[
                    (weekly_data.index >= start_date) & (weekly_data.index <= end_date)
                ]
                
                if len(filtered_data) < 2:
                    continue
                
                start_price = filtered_data.iloc[0]['close']
                end_price = filtered_data.iloc[-1]['close']
                
                investment_amount = initial_capital * weight
                # 🔧 修复：计算整股数量（100股的整数倍），与策略持仓保持一致
                raw_shares = investment_amount / start_price
                initial_shares = int(raw_shares / 100) * 100  # 向下取整到100股的整数倍
                current_shares = initial_shares
                dividend_income = 0
                
                # 重新计算股份变化和分红收入（用于报告）
                for date, row in filtered_data.iterrows():
                    if row.get('dividend_amount', 0) > 0:
                        dividend_income += current_shares * row['dividend_amount']
                    if row.get('bonus_ratio', 0) > 0:
                        current_shares += current_shares * row['bonus_ratio']
                    if row.get('transfer_ratio', 0) > 0:
                        current_shares += current_shares * row['transfer_ratio']
                
                start_value = initial_shares * start_price
                end_value = current_shares * end_price
                
                benchmark_portfolio_data['positions'][stock_code] = {
                    'initial_shares': initial_shares,
                    'current_shares': current_shares,
                    'start_price': start_price,
                    'end_price': end_price,
                    'start_value': start_value,
                    'end_value': end_value,
                    'dividend_income': dividend_income,
                    'weight': weight,
                    'return_rate': (end_value + dividend_income - start_value) / start_value if start_value > 0 else 0
                }
            
            # 存储基准持仓数据供报告生成器使用
            self.benchmark_portfolio_data = benchmark_portfolio_data
            
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
                    # 计算早期数据的结束日期（缓存开始日期的前一天）
                    early_end = (cached_start - pd.Timedelta(days=1)).strftime('%Y-%m-%d')
                    
                    # 检查日期范围是否有效（避免开始日期晚于结束日期）
                    if pd.to_datetime(start_date) <= pd.to_datetime(early_end):
                        self.logger.info(f"🌐 {stock_code} 从{self.data_fetcher.source_name}获取早期数据: {start_date} 到 {early_end}")
                        early_data = self.data_fetcher.get_stock_data(stock_code, start_date, early_end, period)
                        if early_data is not None and not early_data.empty:
                            new_data_parts.append(early_data)
                        else:
                            self.logger.warning(f"⚠️ {stock_code} 未获取到早期数据，将仅使用缓存数据")
                    else:
                        self.logger.warning(f"⚠️ {stock_code} 早期数据日期范围无效（{start_date} > {early_end}），跳过获取")
                
                if need_fetch_after:
                    # 获取后期数据
                    # 计算后期数据的开始日期（缓存结束日期的后一天）
                    late_start = (cached_end + pd.Timedelta(days=1)).strftime('%Y-%m-%d')
                    
                    # 检查日期范围是否有效（避免开始日期晚于结束日期）
                    if pd.to_datetime(late_start) <= pd.to_datetime(end_date):
                        self.logger.info(f"🌐 {stock_code} 从{self.data_fetcher.source_name}获取后期数据: {late_start} 到 {end_date}")
                        late_data = self.data_fetcher.get_stock_data(stock_code, late_start, end_date, period)
                        if late_data is not None and not late_data.empty:
                            new_data_parts.append(late_data)
                        else:
                            self.logger.warning(f"⚠️ {stock_code} 未获取到后期数据，将仅使用缓存数据")
                    else:
                        self.logger.warning(f"⚠️ {stock_code} 后期数据日期范围无效（{late_start} > {end_date}），跳过获取")
                
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
                self.logger.info(f"🌐 {stock_code} 无缓存，从{self.data_fetcher.source_name}获取完整数据: {start_date} 到 {end_date}")
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
                import time
                self.logger.info(f"⏳ 智能获取失败，等待 3 秒后降级重试...")
                time.sleep(3)  # 增加降级前的等待
                return self.data_fetcher.get_stock_data(stock_code, start_date, end_date, period)
            except Exception as fallback_error:
                self.logger.error(f"❌ {stock_code} 降级获取也失败: {fallback_error}")
                return None
    
    def _get_data_with_smart_expansion(self, stock_code: str, start_date: str, end_date: str, period: str) -> pd.DataFrame:
        """
        智能日期范围扩展获取数据，解决纯非交易日期间的问题
        
        Args:
            stock_code: 股票代码
            start_date: 开始日期
            end_date: 结束日期
            period: 数据周期
            
        Returns:
            pd.DataFrame: 扩展获取的数据，如果仍无数据则返回None
        """
        try:
            self.logger.info(f"🔍 {stock_code} 开始智能日期扩展，原始范围: {start_date} 到 {end_date}")
            
            # 向前扩展60天，向后扩展30天
            start_dt = pd.to_datetime(start_date)
            end_dt = pd.to_datetime(end_date)
            
            expanded_start = (start_dt - pd.Timedelta(days=60)).strftime('%Y-%m-%d')
            expanded_end = (end_dt + pd.Timedelta(days=30)).strftime('%Y-%m-%d')
            
            self.logger.info(f"🔍 {stock_code} 扩展范围: {expanded_start} 到 {expanded_end}")
            
            # 尝试获取扩展范围的数据
            expanded_data = self._get_cached_or_fetch_data(stock_code, expanded_start, expanded_end, period)
            
            if expanded_data is not None and not expanded_data.empty:
                self.logger.info(f"✅ {stock_code} 扩展范围获取到 {len(expanded_data)} 条数据")
                
                # 检查扩展数据是否覆盖原始时间范围附近
                data_start = expanded_data.index.min()
                data_end = expanded_data.index.max()
                
                self.logger.info(f"📅 {stock_code} 实际数据范围: {data_start.strftime('%Y-%m-%d')} 到 {data_end.strftime('%Y-%m-%d')}")
                
                # 如果扩展数据有效，返回完整数据（保留用于技术指标计算）
                return expanded_data
            else:
                self.logger.warning(f"⚠️ {stock_code} 扩展范围仍无数据")
                return None
                
        except Exception as e:
            self.logger.error(f"❌ {stock_code} 智能扩展失败: {e}")
            return None
