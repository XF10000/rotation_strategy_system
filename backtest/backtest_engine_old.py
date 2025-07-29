"""
回测引擎
负责执行完整的策略回测流程
"""

import pandas as pd
import numpy as np
from typing import Dict, List, Tuple, Optional
import logging
from datetime import datetime, timedelta
import sys
import os

# 添加项目根目录到路径
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from data.data_fetcher import AkshareDataFetcher
from data.data_processor import DataProcessor
from strategy.signal_generator import SignalGenerator
from .portfolio_manager import PortfolioManager
from .transaction_cost import TransactionCostCalculator

logger = logging.getLogger(__name__)

class BacktestEngine:
    """
    回测引擎
    
    功能：
    1. 数据准备和预处理
    2. 信号生成和策略执行
    3. 投资组合管理和交易执行
    4. 绩效计算和结果输出
    """
    
    def __init__(self, config: Dict):
        """
        初始化回测引擎
        
        Args:
            config: 回测配置字典
        """
        self.config = config
        
        # 基础参数
        self.total_capital = config['total_capital']
        self.initial_holdings = config['initial_holdings']
        self.start_date = config['start_date']
        self.end_date = config['end_date']
        self.stock_pool = [code for code in self.initial_holdings.keys() if code != 'cash']
        
        # 策略参数
        self.strategy_params = config.get('strategy_params', {})
        self.rotation_percentage = self.strategy_params.get('rotation_percentage', 0.10)
        
        # 初始化组件
        self.data_fetcher = AkshareDataFetcher()
        self.data_processor = DataProcessor()
        self.signal_generator = SignalGenerator(self.strategy_params)
        self.cost_calculator = TransactionCostCalculator(config.get('cost_config'))
        
        # 数据存储
        self.stock_data = {}  # {股票代码: DataFrame}
        self.weekly_data = {}  # {股票代码: DataFrame}
        self.signals_history = {}  # {股票代码: [信号记录]}
        
        # 回测结果
        self.portfolio_manager = None
        self.backtest_results = {}
        
        logger.info("回测引擎初始化完成")
        logger.info(f"回测期间: {self.start_date} 至 {self.end_date}")
        logger.info(f"股票池: {self.stock_pool}")
        logger.info(f"轮动比例: {self.rotation_percentage:.1%}")
    
    def prepare_data(self) -> bool:
        """
        准备回测数据
        
        Returns:
            是否成功准备数据
        """
        logger.info("开始准备回测数据...")
        
        try:
            # 获取所有股票的日线数据
            for stock_code in self.stock_pool:
                logger.info(f"获取 {stock_code} 的历史数据...")
                
                daily_data = self.data_fetcher.get_stock_data(
                    stock_code, self.start_date, self.end_date
                )
                
                if daily_data is None or daily_data.empty:
                    logger.error(f"无法获取 {stock_code} 的数据")
                    return False
                
                # 转换为周线数据
                weekly_data = self.data_processor.resample_to_weekly(daily_data)
                
                if len(weekly_data) < 60:  # 确保有足够的数据计算指标
                    logger.warning(f"{stock_code} 数据不足，只有 {len(weekly_data)} 条记录")
                
                self.stock_data[stock_code] = daily_data
                self.weekly_data[stock_code] = weekly_data
                
                logger.info(f"{stock_code} 数据准备完成: 日线 {len(daily_data)} 条, 周线 {len(weekly_data)} 条")
            
            logger.info("所有股票数据准备完成")
            return True
            
        except Exception as e:
            logger.error(f"数据准备失败: {e}")
            return False
    
    def initialize_portfolio(self) -> bool:
        """
        初始化投资组合
        
        Returns:
            是否成功初始化
        """
        try:
            # 获取初始价格（回测开始日期的价格）
            initial_prices = {}
            
            for stock_code in self.stock_pool:
                weekly_data = self.weekly_data[stock_code]
                if not weekly_data.empty:
                    initial_prices[stock_code] = weekly_data['close'].iloc[0]
                else:
                    logger.error(f"无法获取 {stock_code} 的初始价格")
                    return False
            
            # 创建投资组合管理器
            self.portfolio_manager = PortfolioManager(
                self.total_capital, self.initial_holdings
            )
            
            # 初始化投资组合
            self.portfolio_manager.initialize_portfolio(initial_prices)
            
            logger.info("投资组合初始化完成")
            return True
            
        except Exception as e:
            logger.error(f"投资组合初始化失败: {e}")
            return False
    
    def generate_signals_for_period(self, end_date: datetime) -> Dict[str, Dict]:
        """
        为指定日期生成所有股票的信号
        
        Args:
            end_date: 截止日期
            
        Returns:
            信号字典 {股票代码: 信号结果}
        """
        signals = {}
        
        for stock_code in self.stock_pool:
            try:
                # 获取截止到指定日期的数据
                weekly_data = self.weekly_data[stock_code]
                mask = weekly_data.index <= end_date
                period_data = weekly_data[mask]
                
                if len(period_data) < 60:  # 数据不足
                    continue
                
                # 生成信号
                signal_result = self.signal_generator.generate_signal(stock_code, period_data)
                signals[stock_code] = signal_result
                
            except Exception as e:
                logger.warning(f"生成 {stock_code} 信号失败: {e}")
                continue
        
        return signals
    
    def execute_rotation_logic(self, signals: Dict[str, Dict], current_prices: Dict[str, float],
                             current_date: datetime) -> List[str]:
        """
        执行轮动逻辑
        
        Args:
            signals: 信号字典
            current_prices: 当前价格字典
            current_date: 当前日期
            
        Returns:
            执行记录列表
        """
        execution_log = []
        
        # 分离买入和卖出信号
        sell_candidates = []
        buy_candidates = []
        
        for stock_code, signal_result in signals.items():
            signal = signal_result.get('signal', 'HOLD')
            confidence = signal_result.get('confidence', 0)
            
            if signal == 'SELL' and confidence >= 2:
                sell_candidates.append((stock_code, confidence, signal_result))
            elif signal == 'BUY' and confidence >= 2:
                buy_candidates.append((stock_code, confidence, signal_result))
        
        # 按置信度排序
        sell_candidates.sort(key=lambda x: x[1], reverse=True)
        buy_candidates.sort(key=lambda x: x[1], reverse=True)
        
        # 执行轮动交易
        executed_rotations = 0
        max_rotations = 3  # 限制每周最多轮动次数
        
        for sell_stock, sell_conf, sell_signal_result in sell_candidates:
            if executed_rotations >= max_rotations:
                break
                
            # 寻找买入目标
            for buy_stock, buy_conf, buy_signal_result in buy_candidates:
                if buy_stock == sell_stock:  # 不能自己轮动自己
                    continue
                
                # 计算交易成本
                sell_cost_detail = self.cost_calculator.calculate_sell_cost(
                    sell_stock, 1000, current_prices[sell_stock]  # 临时计算
                )
                buy_cost_detail = self.cost_calculator.calculate_buy_cost(
                    buy_stock, 1000, current_prices[buy_stock]  # 临时计算
                )
                
                transaction_costs = {
                    f"{sell_stock}_sell": sell_cost_detail['total_cost'],
                    f"{buy_stock}_buy": buy_cost_detail['total_cost']
                }
                
                # 提取详细的技术指标和信号状态
                sell_indicators = self._extract_detailed_indicators(sell_stock, current_date, sell_signal_result)
                sell_signal_details = self._extract_signal_details(sell_signal_result, 'SELL')
                buy_indicators = self._extract_detailed_indicators(buy_stock, current_date, buy_signal_result)
                buy_signal_details = self._extract_signal_details(buy_signal_result, 'BUY')
                
                # 执行轮动
                success, message = self.portfolio_manager.execute_rotation_with_indicators(
                    sell_stock, buy_stock, self.rotation_percentage,
                    current_prices, transaction_costs, current_date,
                    sell_indicators, sell_signal_details,
                    buy_indicators, buy_signal_details
                )
                
                if success:
                    execution_log.append(f"轮动成功: {message}")
                    buy_candidates.remove((buy_stock, buy_conf, buy_signal_result))  # 移除已买入的股票
                    executed_rotations += 1
                    break
                else:
                    execution_log.append(f"轮动失败: {message}")
        
        # 处理只有卖出信号的情况（转现金）
        for sell_stock, sell_conf, sell_signal_result in sell_candidates[executed_rotations:]:
            if executed_rotations >= max_rotations:
                break
                
            # 检查是否可以卖出
            can_sell, sell_shares, sell_value = self.portfolio_manager.can_sell(
                sell_stock, self.rotation_percentage, current_prices[sell_stock]
            )
            
            if can_sell:
                sell_cost_detail = self.cost_calculator.calculate_sell_cost(
                    sell_stock, sell_shares, current_prices[sell_stock]
                )
                
                # 提取详细的技术指标和信号状态
                sell_indicators = self._extract_detailed_indicators(sell_stock, current_date, sell_signal_result)
                sell_signal_details = self._extract_signal_details(sell_signal_result, 'SELL')
                
                success = self.portfolio_manager.execute_sell(
                    sell_stock, sell_shares, current_prices[sell_stock],
                    sell_cost_detail['total_cost'], current_date, "转现金",
                    sell_indicators, sell_signal_details
                )
                
                if success:
                    execution_log.append(f"卖出转现金: {sell_stock} {sell_shares}股")
                    executed_rotations += 1
        
        # 处理只有买入信号的情况（现金买入）
        remaining_buy_slots = max_rotations - executed_rotations
        for buy_stock, buy_conf, buy_signal_result in buy_candidates[:remaining_buy_slots]:
            # 检查是否可以买入
            can_buy, buy_shares, buy_value = self.portfolio_manager.can_buy(
                buy_stock, self.rotation_percentage, current_prices[buy_stock]
            )
            
            if can_buy:
                buy_cost_detail = self.cost_calculator.calculate_buy_cost(
                    buy_stock, buy_shares, current_prices[buy_stock]
                )
                
                # 提取详细的技术指标和信号状态
                buy_indicators = self._extract_detailed_indicators(buy_stock, current_date, buy_signal_result)
                buy_signal_details = self._extract_signal_details(buy_signal_result, 'BUY')
                
                success = self.portfolio_manager.execute_buy(
                    buy_stock, buy_shares, current_prices[buy_stock],
                    buy_cost_detail['total_cost'], current_date, "现金买入",
                    buy_indicators, buy_signal_details
                )
                
                if success:
                    execution_log.append(f"现金买入: {buy_stock} {buy_shares}股")
        
        return execution_log
    
    def _extract_detailed_indicators(self, stock_code: str, current_date: datetime, signal_result: Dict = None) -> Dict:
        """从信号生成器结果中提取详细的技术指标数据"""
        try:
            # 优先从信号结果中获取技术指标
            if signal_result and 'details' in signal_result:
                details = signal_result['details']
                return {
                    'close': float(details.get('ema', 0)),  # 使用EMA作为收盘价的近似
                    'volume': 0,  # 信号结果中没有成交量，设为0
                    'ema_20w': float(details.get('ema', 0)),
                    'ema_60w': 0,  # 信号结果中没有60周EMA
                    'rsi_14w': float(details.get('rsi', 0)),
                    'macd_dif': float(details.get('macd_dif', 0)),
                    'macd_dea': float(details.get('macd_dea', 0)),
                    'macd_hist': float(details.get('macd_hist', 0)),
                    'bb_upper': float(details.get('bb_upper', 0)),
                    'bb_middle': float(details.get('bb_middle', 0)),
                    'bb_lower': float(details.get('bb_lower', 0)),
                    'volume_4w_avg': float(details.get('volume_ma', 0)),
                }
            
            # 如果信号结果中没有详细信息，从原始数据中获取
            if stock_code not in self.weekly_data:
                return {}
            
            weekly_data = self.weekly_data[stock_code]
            mask = weekly_data.index <= current_date
            if not mask.any():
                return {}
            
            latest_data = weekly_data[mask].iloc[-1]
            
            return {
                'close': float(latest_data.get('close', 0)),
                'volume': int(latest_data.get('volume', 0)),
                'ema_20w': 0,  # 原始数据中没有计算好的技术指标
                'ema_60w': 0,
                'rsi_14w': 0,
                'macd_dif': 0,
                'macd_dea': 0,
                'macd_hist': 0,
                'bb_upper': 0,
                'bb_middle': 0,
                'bb_lower': 0,
                'volume_4w_avg': 0,
            }
            
        except Exception as e:
            logger.warning(f"提取 {stock_code} 技术指标失败: {e}")
            return {}
    
    def _extract_signal_details(self, signal_result: Dict, trade_type: str) -> Dict:
        """提取信号详情和各维度状态"""
        signal_details = signal_result.get('signal_details', {})
        
        # 分析各维度状态
        dimension_status = {
            'trend_filter': '✗',
            'rsi_signal': '✗', 
            'macd_signal': '✗',
            'bollinger_volume': '✗'
        }
        
        # 根据信号结果分析各维度
        if 'scores' in signal_result:
            scores = signal_result['scores']
            
            # 趋势过滤器
            if trade_type == 'SELL' and scores.get('trend_filter_high', False):
                dimension_status['trend_filter'] = '✓'
            elif trade_type == 'BUY' and scores.get('trend_filter_low', False):
                dimension_status['trend_filter'] = '✓'
            
            # RSI信号
            if trade_type == 'SELL' and scores.get('overbought_oversold_high', False):
                dimension_status['rsi_signal'] = '✓'
            elif trade_type == 'BUY' and scores.get('overbought_oversold_low', False):
                dimension_status['rsi_signal'] = '✓'
            
            # MACD信号
            if trade_type == 'SELL' and scores.get('momentum_high', False):
                dimension_status['macd_signal'] = '✓'
            elif trade_type == 'BUY' and scores.get('momentum_low', False):
                dimension_status['macd_signal'] = '✓'
            
            # 布林带+量能信号
            if trade_type == 'SELL' and scores.get('extreme_price_volume_high', False):
                dimension_status['bollinger_volume'] = '✓'
            elif trade_type == 'BUY' and scores.get('extreme_price_volume_low', False):
                dimension_status['bollinger_volume'] = '✓'
        
        return {
            'dimension_status': dimension_status,
            'confidence': signal_result.get('confidence', 0),
            'reason': signal_result.get('reason', ''),
            'scores': signal_result.get('scores', {})
        }
    
    def run_backtest(self) -> bool:
        """
        运行完整回测
        
        Returns:
            是否成功完成回测
        """
        logger.info("开始运行回测...")
        
        try:
            # 1. 准备数据
            if not self.prepare_data():
                return False
            
            # 2. 初始化投资组合
            if not self.initialize_portfolio():
                return False
            
            # 3. 获取回测日期序列（每周五）
            start_dt = pd.to_datetime(self.start_date)
            end_dt = pd.to_datetime(self.end_date)
            
            # 生成周五日期序列
            date_range = pd.date_range(start=start_dt, end=end_dt, freq='W-FRI')
            
            logger.info(f"回测周期数: {len(date_range)}")
            
            # 4. 逐周执行回测
            for i, current_date in enumerate(date_range):
                if i % 10 == 0:
                    logger.info(f"回测进度: {i+1}/{len(date_range)} ({current_date.strftime('%Y-%m-%d')})")
                
                # 获取当前价格
                current_prices = {}
                for stock_code in self.stock_pool:
                    weekly_data = self.weekly_data[stock_code]
                    mask = weekly_data.index <= current_date
                    if mask.any():
                        current_prices[stock_code] = weekly_data[mask]['close'].iloc[-1]
                
                if len(current_prices) != len(self.stock_pool):
                    continue  # 数据不完整，跳过
                
                # 生成信号
                signals = self.generate_signals_for_period(current_date)
                
                # 记录信号
                for stock_code, signal_result in signals.items():
                    if stock_code not in self.signals_history:
                        self.signals_history[stock_code] = []
                    
                    signal_record = {
                        'date': current_date,
                        'signal': signal_result.get('signal', 'HOLD'),
                        'confidence': signal_result.get('confidence', 0),
                        'reason': signal_result.get('reason', ''),
                        'price': current_prices.get(stock_code, 0)
                    }
                    self.signals_history[stock_code].append(signal_record)
                
                # 执行轮动逻辑
                execution_log = self.execute_rotation_logic(signals, current_prices, current_date)
                
                # 记录投资组合快照
                self.portfolio_manager.record_portfolio_snapshot(current_date, current_prices)
                
                # 记录执行日志
                if execution_log:
                    logger.info(f"{current_date.strftime('%Y-%m-%d')} 执行记录:")
                    for log_entry in execution_log:
                        logger.info(f"  {log_entry}")
            
            logger.info("回测完成")
            return True
            
        except Exception as e:
            logger.error(f"回测执行失败: {e}")
            import traceback
            traceback.print_exc()
            return False
    
    def get_backtest_results(self) -> Dict:
        """
        获取回测结果
        
        Returns:
            回测结果字典
        """
        if not self.portfolio_manager:
            return {}
        
        # 获取投资组合历史
        portfolio_df = self.portfolio_manager.get_portfolio_summary()
        transaction_df = self.portfolio_manager.get_transaction_summary()
        
        # 计算基础指标
        if not portfolio_df.empty:
            initial_value = portfolio_df['total_value'].iloc[0]
            final_value = portfolio_df['total_value'].iloc[-1]
            total_return = (final_value - initial_value) / initial_value
            
            # 计算年化收益率
            days = (portfolio_df['date'].iloc[-1] - portfolio_df['date'].iloc[0]).days
            years = days / 365.25
            annual_return = (final_value / initial_value) ** (1/years) - 1 if years > 0 else 0
            
            # 计算最大回撤
            portfolio_df['cumulative_return'] = portfolio_df['total_value'] / initial_value
            portfolio_df['running_max'] = portfolio_df['cumulative_return'].expanding().max()
            portfolio_df['drawdown'] = (portfolio_df['cumulative_return'] - portfolio_df['running_max']) / portfolio_df['running_max']
            max_drawdown = portfolio_df['drawdown'].min()
            
        else:
            total_return = 0
            annual_return = 0
            max_drawdown = 0
        
        # 交易统计
        if not transaction_df.empty:
            total_trades = len(transaction_df)
            buy_trades = len(transaction_df[transaction_df['type'] == 'BUY'])
            sell_trades = len(transaction_df[transaction_df['type'] == 'SELL'])
            total_cost = transaction_df['transaction_cost'].sum()
        else:
            total_trades = 0
            buy_trades = 0
            sell_trades = 0
            total_cost = 0
        
        results = {
            'basic_metrics': {
                'initial_value': self.total_capital,
                'final_value': portfolio_df['total_value'].iloc[-1] if not portfolio_df.empty else self.total_capital,
                'total_return': total_return,
                'annual_return': annual_return,
                'max_drawdown': max_drawdown
            },
            'trading_metrics': {
                'total_trades': total_trades,
                'buy_trades': buy_trades,
                'sell_trades': sell_trades,
                'total_cost': total_cost,
                'cost_ratio': total_cost / self.total_capital
            },
            'portfolio_history': portfolio_df,
            'transaction_history': transaction_df,
            'signals_history': self.signals_history
        }
        
        return results

if __name__ == "__main__":
    # 测试代码
    logging.basicConfig(level=logging.INFO)
    
    # 测试配置
    config = {
        'total_capital': 1000000,
        'initial_holdings': {
            "601088": 0.20,  # 中国神华
            "000807": 0.15,  # 云铝股份
            "002460": 0.25,  # 赣锋锂业
            "cash": 0.40
        },
        'start_date': '2023-01-01',
        'end_date': '2024-01-01',
        'strategy_params': {
            'rotation_percentage': 0.10
        }
    }
    
    # 创建回测引擎
    engine = BacktestEngine(config)
    
    # 运行回测
    success = engine.run_backtest()
    
    if success:
        results = engine.get_backtest_results()
        print("\n回测结果:")
        print(f"总收益率: {results['basic_metrics']['total_return']:.2%}")
        print(f"年化收益率: {results['basic_metrics']['annual_return']:.2%}")
        print(f"最大回撤: {results['basic_metrics']['max_drawdown']:.2%}")
        print(f"总交易次数: {results['trading_metrics']['total_trades']}")