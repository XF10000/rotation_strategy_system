"""
回测协调器
轻量级协调各服务完成回测流程
"""

import pandas as pd
import logging
from typing import Dict, List, Optional, Any
from datetime import datetime

from services.data_service import DataService
from services.portfolio_service import PortfolioService
from services.report_service import ReportService
from .portfolio_manager import PortfolioManager
from .portfolio_data_manager import PortfolioDataManager
from strategy.dynamic_position_manager import DynamicPositionManager
from strategy.signal_generator import SignalGenerator
from .signal_tracker import SignalTracker


class BacktestOrchestrator:
    """
    回测协调器 - 协调各服务完成回测流程
    
    职责：
    1. 协调各服务的初始化
    2. 控制回测主流程
    3. 异常处理和日志记录
    
    不负责：
    - 数据获取（DataService）
    - 信号生成（SignalGenerator，暂未服务化）
    - 交易执行（PortfolioService）
    - 报告生成（ReportService）
    """
    
    def __init__(self, config: Dict[str, Any]):
        """
        初始化回测协调器
        
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
        
        # 股票池（排除现金）
        self.stock_pool = [code for code in self.initial_holdings.keys() if code != 'cash']
        
        # 初始化服务
        self.data_service = DataService(config)
        self.data_service.initialize()
        
        self.portfolio_service = None  # 将在数据准备后初始化
        self.report_service = ReportService(config)
        self.report_service.initialize()
        
        # 核心组件（暂未服务化）
        self.signal_generator = None  # 将在数据准备后初始化
        self.signal_tracker = None
        self.portfolio_manager = None
        self.portfolio_data_manager = None
        self.dynamic_position_manager = None
        
        # 回测数据
        self.stock_data = {}
        self.transaction_history = []
        self.signal_details = {}
        
        self.logger.info("BacktestOrchestrator 初始化完成")
    
    def run_backtest(self) -> bool:
        """
        运行回测 - 主流程
        
        Returns:
            bool: 回测是否成功
        """
        try:
            self.logger.info("=" * 60)
            self.logger.info("🚀 开始回测")
            self.logger.info("=" * 60)
            
            # 1. 准备数据
            if not self._prepare_data():
                self.logger.error("数据准备失败")
                return False
            
            # 2. 初始化投资组合
            if not self._initialize_portfolio():
                self.logger.error("投资组合初始化失败")
                return False
            
            # 3. 初始化PortfolioService
            self._initialize_portfolio_service()
            
            # 4. 执行回测循环
            self._run_backtest_loop()
            
            # 5. 计算最终结果
            self._calculate_final_results()
            
            self.logger.info("=" * 60)
            self.logger.info("✅ 回测完成")
            self.logger.info("=" * 60)
            
            return True
            
        except Exception as e:
            self.logger.error(f"回测运行失败: {e}")
            import traceback
            self.logger.error(traceback.format_exc())
            return False
    
    def _prepare_data(self) -> bool:
        """
        准备回测数据
        
        Returns:
            bool: 数据准备是否成功
        """
        try:
            self.logger.info("🚀 开始准备回测数据...")
            
            # 使用DataService准备数据
            success = self.data_service.prepare_backtest_data()
            
            if not success:
                return False
            
            # 从DataService获取数据
            self.stock_data = self.data_service.stock_data
            dcf_values = self.data_service.dcf_values
            rsi_thresholds = self.data_service.rsi_thresholds
            stock_industry_map = self.data_service.stock_industry_map
            
            # 初始化SignalGenerator
            signal_config = self.config.copy()
            if 'strategy_params' in self.config:
                signal_config.update(self.config['strategy_params'])
            
            self.signal_generator = SignalGenerator(
                signal_config,
                dcf_values,
                rsi_thresholds,
                stock_industry_map
            )
            
            # 初始化SignalTracker
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            signal_tracker_path = f"reports/signal_tracking_report_{timestamp}.csv"
            self.signal_tracker = SignalTracker(signal_tracker_path)
            
            # 初始化DynamicPositionManager
            self.dynamic_position_manager = DynamicPositionManager(
                self.config.get('strategy_params', self.config)
            )
            
            self.logger.info(f"✅ 数据准备完成，共 {len(self.stock_data)} 只股票")
            return True
            
        except Exception as e:
            self.logger.error(f"❌ 数据准备失败: {e}")
            import traceback
            self.logger.error(traceback.format_exc())
            return False
    
    def _initialize_portfolio(self) -> bool:
        """
        初始化投资组合（使用与BacktestEngine相同的逻辑）
        
        Returns:
            bool: 初始化是否成功
        """
        try:
            self.logger.info("📊 初始化投资组合...")
            
            # 获取回测开始日期的价格
            start_date = pd.Timestamp(self.start_date)
            initial_prices = {}
            
            for stock_code in self.stock_pool:
                if stock_code not in self.stock_data:
                    continue
                    
                stock_weekly = self.stock_data[stock_code]['weekly']
                
                # 找到开始日期或之后的第一个价格
                valid_dates = stock_weekly.index[stock_weekly.index >= start_date]
                if len(valid_dates) > 0:
                    first_date = valid_dates[0]
                    initial_prices[stock_code] = stock_weekly.loc[first_date, 'close']
            
            # 计算初始持仓和现金
            initial_positions = {}
            cash_value = 0
            
            for code, shares in self.initial_holdings.items():
                if code == 'cash':
                    cash_value = shares
                else:
                    if code in initial_prices:
                        initial_positions[code] = shares
            
            # 创建PortfolioManager
            self.portfolio_manager = PortfolioManager(
                total_capital=self.total_capital,
                initial_holdings={}
            )
            
            # 直接设置持仓和现金
            self.portfolio_manager.holdings = initial_positions.copy()
            self.portfolio_manager.cash = cash_value
            self.portfolio_manager.positions = initial_positions.copy()
            
            # 初始化PortfolioDataManager
            self.portfolio_data_manager = PortfolioDataManager(self.total_capital)
            
            self.logger.info(f"✅ 投资组合初始化完成")
            self.logger.info(f"   初始资金: ¥{self.total_capital:,.0f}")
            self.logger.info(f"   初始现金: ¥{cash_value:,.0f}")
            self.logger.info(f"   初始持仓: {len(initial_positions)} 只股票")
            
            return True
            
        except Exception as e:
            self.logger.error(f"投资组合初始化失败: {e}")
            import traceback
            self.logger.error(traceback.format_exc())
            return False
    
    def _initialize_portfolio_service(self):
        """初始化PortfolioService"""
        if self.portfolio_service is None:
            self.portfolio_service = PortfolioService(
                self.config,
                self.data_service.dcf_values,
                self.signal_tracker
            )
            self.portfolio_service.initialize()
            
            # 使用已创建的managers
            self.portfolio_service.portfolio_manager = self.portfolio_manager
            self.portfolio_service.portfolio_data_manager = self.portfolio_data_manager
            self.portfolio_service.dynamic_position_manager = self.dynamic_position_manager
            
            self.logger.info("✅ PortfolioService 初始化完成")
    
    def _run_backtest_loop(self):
        """执行回测循环"""
        self.logger.info("🔄 开始回测循环...")
        
        # 获取交易日期列表
        trading_dates = self._get_trading_dates()
        
        self.logger.info(f"📅 回测期间: {trading_dates[0]} 至 {trading_dates[-1]}")
        self.logger.info(f"📊 交易周数: {len(trading_dates)}")
        
        # 逐周回测
        for i, current_date in enumerate(trading_dates, 1):
            if i % 20 == 0:
                self.logger.info(f"进度: {i}/{len(trading_dates)} ({i/len(trading_dates)*100:.1f}%)")
            
            # 1. 处理分红配股
            self.portfolio_service.process_dividend_events(self.stock_data, current_date)
            
            # 2. 生成交易信号
            signals = self._generate_signals(current_date)
            
            # 3. 执行交易
            if signals:
                self._execute_trades(signals, current_date)
            
            # 4. 记录投资组合状态
            self._record_portfolio_state(current_date)
        
        self.logger.info("✅ 回测循环完成")
    
    def _get_trading_dates(self) -> List[pd.Timestamp]:
        """
        获取交易日期列表
        
        Returns:
            交易日期列表
        """
        # 从第一只股票的周线数据中获取日期
        first_stock = next(iter(self.stock_data.values()))
        weekly_data = first_stock['weekly']
        
        # 筛选在回测期间内的日期
        start = pd.Timestamp(self.start_date)
        end = pd.Timestamp(self.end_date)
        
        trading_dates = [
            date for date in weekly_data.index
            if start <= date <= end
        ]
        
        return trading_dates
    
    def _generate_signals(self, current_date: pd.Timestamp) -> Dict[str, str]:
        """
        生成交易信号
        
        Args:
            current_date: 当前日期
            
        Returns:
            股票代码到信号的映射
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
            if current_idx < 120:  # 需要足够的历史数据
                continue
            
            # 获取历史数据用于信号生成
            historical_data = stock_weekly.iloc[:current_idx+1]
            
            # 确保有足够的数据
            if len(historical_data) < 120:
                continue
            
            # 生成信号
            try:
                signal_result = self.signal_generator.generate_signal(stock_code, historical_data)
                if signal_result and isinstance(signal_result, dict):
                    signal = signal_result.get('signal', 'HOLD')
                    
                    # 记录BUY/SELL信号
                    if signal in ['BUY', 'SELL']:
                        self.signal_tracker.record_signal({
                            'date': current_date,
                            'stock_code': stock_code,
                            'signal_result': signal_result
                        })
                    
                    if signal and signal != 'HOLD':
                        signals[stock_code] = signal
                        # 记录信号详情用于报告
                        self.signal_details[f"{stock_code}_{current_date.strftime('%Y-%m-%d')}"] = signal_result
                        
            except Exception as e:
                self.logger.warning(f"{stock_code} 信号生成失败: {e}")
                continue
        
        return signals
    
    def _execute_trades(self, signals: Dict[str, str], current_date: pd.Timestamp):
        """
        执行交易
        
        Args:
            signals: 交易信号
            current_date: 当前日期
        """
        # 使用PortfolioService执行交易
        executed_trades = self.portfolio_service.execute_trades(
            signals,
            self.stock_data,
            current_date,
            self.signal_details
        )
        
        # 更新transaction_history
        self.transaction_history = self.portfolio_service.get_transaction_history()
    
    def _record_portfolio_state(self, current_date: pd.Timestamp):
        """
        记录投资组合状态
        
        Args:
            current_date: 当前日期
        """
        # 获取当前价格
        current_prices = {}
        for stock_code in self.stock_pool:
            if stock_code in self.stock_data:
                stock_weekly = self.stock_data[stock_code]['weekly']
                if current_date in stock_weekly.index:
                    current_prices[stock_code] = stock_weekly.loc[current_date, 'close']
        
        # 记录到PortfolioDataManager
        self.portfolio_data_manager.record_portfolio_state(
            current_date,
            self.portfolio_manager.positions.copy(),
            self.portfolio_manager.cash,
            current_prices
        )
    
    def _calculate_final_results(self):
        """计算最终结果"""
        self.logger.info("📊 计算回测结果...")
        
        # 最终结果会在get_backtest_results中计算
        # 这里只是占位，实际计算逻辑在BacktestEngine中
        pass
    
    def get_backtest_results(self) -> Dict[str, Any]:
        """
        获取回测结果
        
        Returns:
            回测结果字典
        """
        # 这个方法会委托给BacktestEngine的get_backtest_results
        # 因为结果计算逻辑比较复杂，暂时保留在BacktestEngine中
        return {}
    
    def generate_reports(self) -> Dict[str, str]:
        """
        生成所有报告
        
        Returns:
            报告文件路径字典
        """
        try:
            self.logger.info("📝 开始生成报告...")
            
            # 使用ReportService生成所有报告
            report_paths = self.report_service.generate_all_reports(
                {},  # backtest_results会在实际使用时传入
                self.stock_data,
                self.transaction_history,
                self.signal_tracker,
                self.portfolio_manager
            )
            
            return report_paths
            
        except Exception as e:
            self.logger.error(f"生成报告失败: {e}")
            return {}
