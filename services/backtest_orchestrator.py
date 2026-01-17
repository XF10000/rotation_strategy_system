"""
回测协调器
负责协调各个服务完成回测流程
"""

from typing import Any, Dict, List, Optional

import pandas as pd

from .base_service import BaseService
from .data_service import DataService
from .portfolio_service import PortfolioService
from .report_service import ReportService
from .signal_service import SignalService


class BacktestOrchestrator(BaseService):
    """
    回测协调器 - 协调各个服务完成回测
    
    职责：
    1. 协调服务初始化顺序
    2. 管理回测主循环
    3. 协调服务之间的数据流
    4. 收集和整理回测结果
    """
    
    def __init__(self, config: Dict[str, Any], logger=None):
        """
        初始化回测协调器
        
        Args:
            config: 配置字典
            logger: 日志记录器
        """
        super().__init__(logger)
        self.config = config
        self.start_date = config.get('start_date')
        self.end_date = config.get('end_date')
        
        # 初始化各个服务
        self.data_service = None
        self.signal_service = None
        self.portfolio_service = None
        self.report_service = None
        self.backtest_engine = None  # 🔧 添加：保存backtest_engine引用
        
        # 存储股票数据
        self.stock_data = {}
        self.transaction_history = []
        self.signal_details = {}
    
    def initialize(self) -> bool:
        """
        初始化协调器和所有服务
        
        Returns:
            bool: 初始化是否成功
        """
        try:
            self.logger.info("🚀 开始初始化回测协调器...")
            
            # 1. 初始化DataService
            self.logger.info("📊 初始化DataService...")
            self.data_service = DataService(self.config)
            if not self.data_service.initialize():
                self.logger.error("DataService初始化失败")
                return False
            
            # 2. 准备回测数据
            self.logger.info("📈 准备回测数据...")
            if not self.data_service.prepare_backtest_data():
                self.logger.error("数据准备失败")
                return False
            
            # 获取准备好的数据
            self.stock_data = self.data_service.stock_data
            dcf_values = self.data_service.dcf_values
            rsi_thresholds = self.data_service.rsi_thresholds
            stock_industry_map = self.data_service.stock_industry_map
            
            # 3. 创建SignalTracker
            from backtest.signal_tracker import SignalTracker
            signal_tracker = SignalTracker()
            self.logger.info(f"✅ SignalTracker已创建: {signal_tracker.output_path}")
            
            # 4. 初始化SignalService
            self.logger.info("🎯 初始化SignalService...")
            # 传递完整config，让SignalService自己处理strategy_params合并
            self.signal_service = SignalService(
                self.config,
                dcf_values,
                rsi_thresholds,
                stock_industry_map,
                self.data_service.stock_pool,
                signal_tracker  # 传递signal_tracker
            )
            if not self.signal_service.initialize():
                self.logger.error("SignalService初始化失败")
                return False
            
            # 5. 创建并初始化PortfolioService
            self.logger.info("📊 初始化PortfolioService...")
            self.portfolio_service = PortfolioService(self.config, dcf_values)
            start_date = pd.Timestamp(self.start_date)
            if not self.portfolio_service.initialize(
                self.stock_data,
                start_date,
                dcf_values,
                self.signal_service.signal_tracker
            ):
                self.logger.error("PortfolioService初始化失败")
                return False
            
            # 6. 初始化ReportService
            self.logger.info("📄 初始化ReportService...")
            self.report_service = ReportService(self.config)
            if not self.report_service.initialize():
                self.logger.error("ReportService初始化失败")
                return False
            
            self._initialized = True
            self.logger.info("✅ 回测协调器初始化完成")
            return True
            
        except Exception as e:
            self.logger.error(f"回测协调器初始化失败: {e}")
            import traceback
            self.logger.error(traceback.format_exc())
            return False
    
    def run_backtest(self) -> bool:
        """
        运行回测主循环
        
        Returns:
            bool: 回测是否成功
        """
        try:
            if not self._initialized:
                self.logger.error("协调器未初始化")
                return False
            
            self.logger.info("🏃 开始运行回测...")
            
            # 获取所有交易日期
            trading_dates = self._get_trading_dates()
            self.logger.info(f"📅 回测期间: {self.start_date} 至 {self.end_date}")
            self.logger.info(f"📊 有效回测周期数: {len(trading_dates)}")
            
            # 主回测循环
            for i, current_date in enumerate(trading_dates):
                if i % 10 == 0:
                    self.logger.info(f"⏳ 回测进度: {i+1}/{len(trading_dates)} ({current_date.strftime('%Y-%m-%d')})")
                
                # 1. 更新当前价格
                current_prices = self._get_current_prices(current_date)
                if i == 0:
                    self.logger.info(f"📊 第一天价格数量: {len(current_prices)}")
                
                # 2. 更新投资组合价格（关键！BacktestEngine有这一步）
                self.portfolio_service.portfolio_manager.update_prices(current_prices)
                
                # 🔧 修复：记录投资组合价值历史（用于计算最大回撤）
                total_value = self.portfolio_service.portfolio_manager.get_total_value(current_prices)
                self.portfolio_service.portfolio_manager.portfolio_history.append({
                    'date': current_date,
                    'total_value': total_value,
                    'cash': self.portfolio_service.portfolio_manager.cash
                })
                
                # 3. 处理分红配股事件
                self.portfolio_service.process_dividend_events(self.stock_data, current_date)
                
                # 4. 生成交易信号
                signals = self.signal_service.generate_signals(self.stock_data, current_date)
                if i == 0:
                    self.logger.info(f"🎯 第一天信号数量: {len(signals) if signals else 0}")
                    if signals:
                        self.logger.info(f"   信号: {signals}")
                
                # 5. 执行交易
                if signals:
                    # 记录交易前的交易历史长度
                    txn_count_before = len(self.portfolio_service.portfolio_manager.transaction_history)
                    
                    executed_trades = self.portfolio_service.execute_trades(
                        signals,
                        self.stock_data,
                        current_date,
                        self.signal_service.signal_details
                    )
                    
                    # 获取新增的交易记录
                    txn_count_after = len(self.portfolio_service.portfolio_manager.transaction_history)
                    new_txns = self.portfolio_service.portfolio_manager.transaction_history[txn_count_before:]
                    
                    if new_txns:
                        self.logger.info(f"💰 {current_date.strftime('%Y-%m-%d')} 执行了 {len(new_txns)} 笔交易")
                        self.transaction_history.extend(new_txns)
                    else:
                        if i < 5:  # 只在前5天记录
                            self.logger.info(f"⚠️ {current_date.strftime('%Y-%m-%d')} 有信号但未执行交易")
            
            self.logger.info("✅ 回测完成")
            return True
            
        except Exception as e:
            self.logger.error(f"回测运行失败: {e}")
            import traceback
            self.logger.error(traceback.format_exc())
            return False
    
    def generate_reports(self, output_dir: str = 'reports') -> Dict[str, str]:
        """
        生成回测报告
        
        Args:
            output_dir: 输出目录
            
        Returns:
            Dict[str, str]: 生成的报告文件路径
        """
        try:
            self.logger.info("📊 开始生成回测报告...")
            
            # 准备回测结果
            backtest_results = self._prepare_backtest_results()
            
            # 🔧 修复：使用portfolio_manager的transaction_history，而不是空的self.transaction_history
            transaction_history = self.portfolio_service.portfolio_manager.transaction_history
            self.logger.info(f"📋 交易记录数量: {len(transaction_history)}")
            
            # 🔧 修复：确保backtest_results包含完整的kline_data
            # backtest_engine的_prepare_backtest_results已经准备了kline_data
            self.logger.info(f"🔍 backtest_results包含的键: {list(backtest_results.keys())}")
            self.logger.info(f"🔍 kline_data包含的股票: {list(backtest_results.get('kline_data', {}).keys())}")
            
            # 使用ReportService生成所有报告（包括HTML、CSV、信号跟踪等）
            report_paths = self.report_service.generate_all_reports(
                backtest_results=backtest_results,
                stock_data=self.stock_data,
                transaction_history=transaction_history,
                signal_tracker=self.signal_service.signal_tracker,
                portfolio_manager=self.portfolio_service.portfolio_manager
            )
            
            self.logger.info("✅ 报告生成完成")
            return report_paths
            
        except Exception as e:
            self.logger.error(f"报告生成失败: {e}")
            import traceback
            self.logger.error(traceback.format_exc())
            return {}
    
    def _get_trading_dates(self) -> pd.DatetimeIndex:
        """
        获取回测期间的所有交易日期
        
        Returns:
            pd.DatetimeIndex: 交易日期列表
        """
        # 收集所有股票的交易日期
        all_trading_dates = set()
        for stock_code in self.stock_data.keys():
            stock_dates = self.stock_data[stock_code]['weekly'].index
            all_trading_dates.update(stock_dates)
        
        # 转换为排序的DatetimeIndex
        all_trading_dates = pd.DatetimeIndex(sorted(all_trading_dates))
        
        # 过滤日期范围
        start_date = pd.to_datetime(self.start_date)
        end_date = pd.to_datetime(self.end_date)
        
        trading_dates = all_trading_dates[
            (all_trading_dates >= start_date) & (all_trading_dates <= end_date)
        ]
        
        return trading_dates
    
    def _get_current_prices(self, current_date: pd.Timestamp) -> Dict[str, float]:
        """
        获取当前日期的股票价格
        
        Args:
            current_date: 当前日期
            
        Returns:
            Dict[str, float]: 股票代码到价格的映射
        """
        current_prices = {}
        for stock_code in self.data_service.stock_pool:
            if stock_code in self.stock_data:
                stock_weekly = self.stock_data[stock_code]['weekly']
                if current_date in stock_weekly.index:
                    current_prices[stock_code] = stock_weekly.loc[current_date, 'close']
        
        return current_prices
    
    def _prepare_backtest_results(self) -> Dict[str, Any]:
        """
        准备回测结果数据
        
        Returns:
            Dict[str, Any]: 回测结果
        """
        # 计算基本指标
        portfolio_manager = self.portfolio_service.portfolio_manager
        
        # 获取实际的最后交易日（而不是配置的end_date）
        trading_dates = self._get_trading_dates()
        if len(trading_dates) == 0:
            self.logger.error("没有交易日期")
            return {}
        
        final_date = trading_dates[-1]
        final_prices = self._get_current_prices(final_date)
        
        # 🔧 修复：获取交易记录
        transaction_history = portfolio_manager.transaction_history
        self.logger.info(f"📋 准备回测结果，交易记录数量: {len(transaction_history)}")
        
        # 计算收益
        initial_value = self.config.get('total_capital', 1000000)
        final_value = portfolio_manager.get_total_value(final_prices)
        total_return = (final_value - initial_value) / initial_value
        
        # 计算年化收益
        start_date = pd.to_datetime(self.start_date)
        end_date = pd.to_datetime(self.end_date)
        years = (end_date - start_date).days / 365.25
        annual_return = (1 + total_return) ** (1 / years) - 1 if years > 0 else 0
        
        # 🔧 修复：计算策略最大回撤
        max_drawdown = self._calculate_strategy_max_drawdown(portfolio_manager)
        
        # 🔧 修复：从backtest_engine获取基准持仓数据
        benchmark_portfolio_data = None
        benchmark_return = 0.0
        benchmark_annual_return = 0.0
        benchmark_max_drawdown = 0.0
        
        if hasattr(self, 'backtest_engine') and self.backtest_engine:
            # 确保backtest_engine有必要的数据
            self.backtest_engine.stock_data = self.stock_data
            self.backtest_engine.start_date = self.start_date
            self.backtest_engine.end_date = self.end_date
            self.backtest_engine.total_capital = initial_value
            
            # 计算买入持有基准
            try:
                benchmark_return, benchmark_annual_return, benchmark_max_drawdown = self.backtest_engine._calculate_buy_and_hold_benchmark()
                self.logger.info(f"📊 基准收益率: {benchmark_return:.2f}%, 年化: {benchmark_annual_return:.2f}%")
                
                # 获取基准持仓数据
                benchmark_portfolio_data = getattr(self.backtest_engine, 'benchmark_portfolio_data', {})
                self.logger.info(f"🔍 基准持仓数据: {list(benchmark_portfolio_data.keys()) if benchmark_portfolio_data else 'None'}")
            except Exception as e:
                self.logger.error(f"计算基准数据失败: {e}")
                import traceback
                self.logger.error(traceback.format_exc())
        
        # 🔧 修复：从交易记录中提取信号统计
        signal_analysis = self._extract_signal_analysis(transaction_history)
        
        # 🔧 修复：构建完整的最终持仓状态
        final_portfolio = self._build_final_portfolio_state(portfolio_manager, final_prices, final_date)
        
        # 🔧 修复：获取完整的K线数据（包含所有技术指标和买卖点）
        # 如果有backtest_engine，使用它的_prepare_kline_data方法
        kline_data = {}
        if hasattr(self, 'backtest_engine') and self.backtest_engine:
            try:
                # 🔧 修复：设置portfolio_manager引用，以便_prepare_kline_data可以访问交易记录
                self.backtest_engine.portfolio_manager = portfolio_manager
                # 🔧 修复：将transaction_history传递给backtest_engine
                self.backtest_engine.transaction_history = transaction_history
                kline_data = self.backtest_engine._prepare_kline_data()
                self.logger.info(f"✅ 从backtest_engine获取K线数据，包含 {len(kline_data)} 只股票")
                
                # 🔍 调试：检查600900的数据完整性
                if '600900' in kline_data:
                    self.logger.info(f"🔍 _prepare_backtest_results中600900的keys: {list(kline_data['600900'].keys())}")
                    self.logger.info(f"🔍 _prepare_backtest_results中600900的trades数量: {len(kline_data['600900'].get('trades', []))}")
            except Exception as e:
                self.logger.error(f"从backtest_engine获取K线数据失败: {e}")
                import traceback
                self.logger.error(traceback.format_exc())
        
        return {
            'initial_value': initial_value,
            'final_value': final_value,
            'total_return': total_return * 100,  # 转换为百分比
            'annual_return': annual_return * 100,
            'transaction_count': len(transaction_history),
            'transactions': transaction_history,  # 🔧 修复：添加交易记录
            'performance_metrics': {  # 🔧 修复：添加performance_metrics
                'initial_capital': initial_value,
                'final_value': final_value,
                'total_return': total_return * 100,
                'annual_return': annual_return * 100,
                'max_drawdown': max_drawdown,  # 策略最大回撤
                'benchmark_return': benchmark_return,  # 基准总收益率
                'benchmark_annual_return': benchmark_annual_return,  # 基准年化收益率
                'benchmark_max_drawdown': benchmark_max_drawdown,  # 基准最大回撤
            },
            'benchmark_portfolio_data': benchmark_portfolio_data,  # 🔧 修复：添加基准持仓数据
            'signal_analysis': signal_analysis,  # 🔧 修复：添加信号分析
            'final_portfolio': final_portfolio,  # 🔧 修复：添加最终持仓状态
            'start_date': self.start_date,
            'end_date': self.end_date,
            'kline_data': kline_data  # 🔧 修复：使用完整的K线数据
        }
    
    def _extract_signal_analysis(self, transaction_history: List[Dict]) -> Dict[str, Any]:
        """
        从交易记录中提取信号统计
        
        Args:
            transaction_history: 交易记录列表
            
        Returns:
            Dict[str, Any]: 信号分析数据
        """
        buy_count = 0
        sell_count = 0
        stock_signals = {}
        
        for trade in transaction_history:
            action = trade.get('action', '')
            stock_code = trade.get('stock_code', '')
            
            if action == 'buy':
                buy_count += 1
            elif action == 'sell':
                sell_count += 1
            
            # 统计每只股票的信号
            if stock_code not in stock_signals:
                stock_signals[stock_code] = {'buy': 0, 'sell': 0}
            
            if action == 'buy':
                stock_signals[stock_code]['buy'] += 1
            elif action == 'sell':
                stock_signals[stock_code]['sell'] += 1
        
        return {
            'total_buy_signals': buy_count,
            'total_sell_signals': sell_count,
            'stock_signals': stock_signals
        }
    
    def _build_final_portfolio_state(self, portfolio_manager, final_prices: Dict[str, float], 
                                    final_date) -> Dict[str, Any]:
        """
        构建完整的最终持仓状态
        
        Args:
            portfolio_manager: 投资组合管理器
            final_prices: 最终价格字典
            final_date: 最终日期
            
        Returns:
            Dict[str, Any]: 完整的持仓状态
        """
        total_value = portfolio_manager.get_total_value(final_prices)
        cash = portfolio_manager.cash
        
        # 计算股票总市值
        stock_value = 0
        positions = {}
        
        for stock_code, shares in portfolio_manager.holdings.items():
            if shares > 0 and stock_code in final_prices:
                current_price = final_prices[stock_code]
                current_value = shares * current_price
                stock_value += current_value
                
                # 获取初始持仓价格（回测开始时的价格）
                initial_price = self._get_initial_holding_price(stock_code)
                
                # 计算收益率：(当前价格 - 初始价格) / 初始价格
                return_pct = ((current_price - initial_price) / initial_price * 100) if initial_price > 0 else 0
                
                positions[stock_code] = {
                    'shares': shares,
                    'price': current_price,
                    'current_price': current_price,  # 添加current_price字段供报告生成器使用
                    'value': current_value,
                    'return': return_pct,
                    'initial_price': initial_price
                }
        
        return {
            'total_value': total_value,
            'cash': cash,
            'stock_value': stock_value,
            'end_date': final_date.strftime('%Y-%m-%d') if hasattr(final_date, 'strftime') else str(final_date),
            'positions': positions
        }
    
    def _get_initial_holding_price(self, stock_code: str) -> float:
        """
        获取股票的初始持仓价格（回测开始时的价格）
        
        Args:
            stock_code: 股票代码
            
        Returns:
            float: 初始价格
        """
        # 从股票数据中获取回测开始日期的价格
        if stock_code in self.stock_data:
            weekly_data = self.stock_data[stock_code]['weekly']
            start_date = pd.to_datetime(self.start_date)
            
            # 找到回测开始日期或之后的第一个交易日
            valid_dates = weekly_data.index[weekly_data.index >= start_date]
            if len(valid_dates) > 0:
                first_date = valid_dates[0]
                return weekly_data.loc[first_date, 'close']
        
        # 如果没有找到，尝试从第一笔买入交易获取
        portfolio_manager = self.portfolio_service.portfolio_manager
        for trade in portfolio_manager.transaction_history:
            if trade.get('stock_code') == stock_code and trade.get('action') == 'buy':
                return trade.get('price', 0)
        
        # 如果都没有找到，返回0
        return 0
    
    def _calculate_strategy_max_drawdown(self, portfolio_manager) -> float:
        """
        计算策略的最大回撤
        
        Args:
            portfolio_manager: 投资组合管理器
            
        Returns:
            float: 最大回撤（百分比，如-15.24表示-15.24%）
        """
        try:
            # 从portfolio_history中提取总价值序列
            if not hasattr(portfolio_manager, 'portfolio_history') or not portfolio_manager.portfolio_history:
                self.logger.warning("没有投资组合历史记录，无法计算最大回撤")
                return 0.0
            
            # 提取每个时间点的总价值
            values = []
            for record in portfolio_manager.portfolio_history:
                if isinstance(record, dict) and 'total_value' in record:
                    values.append(record['total_value'])
            
            if len(values) < 2:
                self.logger.warning(f"投资组合历史记录不足（{len(values)}条），无法计算最大回撤")
                return 0.0
            
            # 计算最大回撤
            peak = values[0]
            max_drawdown = 0
            
            for value in values:
                if value > peak:
                    peak = value
                drawdown = (value - peak) / peak * 100  # 转换为百分比
                if drawdown < max_drawdown:
                    max_drawdown = drawdown
            
            self.logger.info(f"📉 策略最大回撤计算完成: {max_drawdown:.2f}% (基于{len(values)}个数据点)")
            return max_drawdown
            
        except Exception as e:
            self.logger.error(f"计算策略最大回撤失败: {e}")
            import traceback
            self.logger.error(traceback.format_exc())
            return 0.0
    
    def get_results(self) -> Dict[str, Any]:
        """
        获取回测结果
        
        Returns:
            Dict[str, Any]: 回测结果
        """
        return {
            'backtest_results': self._prepare_backtest_results(),
            'transaction_history': self.transaction_history,
            'signal_details': self.signal_service.signal_details if self.signal_service else {},
            'stock_data': self.stock_data
        }
