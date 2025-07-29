"""
中线轮动策略主类
整合信号生成、仓位管理和轮动逻辑
"""

import pandas as pd
import numpy as np
from typing import Dict, List, Tuple, Optional
import logging
from datetime import datetime, timedelta

import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from strategy.base_strategy import BaseStrategy
from strategy.signal_generator import SignalGenerator
from strategy.position_manager import PositionManager
from strategy.exceptions import StrategyError, InsufficientDataError

logger = logging.getLogger(__name__)

class RotationStrategy(BaseStrategy):
    """
    中线轮动策略
    实现基于4维度评分的股票轮动策略
    """
    
    def __init__(self, config: Dict):
        """
        初始化轮动策略
        
        Args:
            config: 策略配置参数
        """
        super().__init__(config)
        
        # 策略特定参数
        self.strategy_params = {
            'rebalance_frequency': 'weekly',    # 调仓频率
            'min_hold_period': 7,              # 最小持有天数
            'max_turnover_rate': 0.5,          # 最大换手率
            'signal_threshold': 0.6,           # 信号阈值
            'stop_loss_ratio': -0.15,          # 止损比例
            'take_profit_ratio': 0.30,         # 止盈比例
        }
        
        # 更新配置
        self.strategy_params.update(config.get('strategy_params', {}))
        
        # 初始化子模块
        self.signal_generator = SignalGenerator(config.get('signal_config', {}))
        self.position_manager = PositionManager(config.get('position_config', {}))
        
        # 策略状态
        self.last_rebalance_date = None
        self.stock_pool = config.get('stock_pool', [])
        self.current_signals = {}
        
        self.logger.info(f"中线轮动策略初始化完成，股票池: {len(self.stock_pool)}只")
    
    def run_strategy(self, data_dict: Dict[str, pd.DataFrame], 
                    current_date: datetime) -> Dict:
        """
        运行策略主逻辑
        
        Args:
            data_dict: 股票数据字典 {stock_code: DataFrame}
            current_date: 当前日期
            
        Returns:
            Dict: 策略运行结果
        """
        try:
            self.logger.info(f"开始运行策略，日期: {current_date.strftime('%Y-%m-%d')}")
            
            # 1. 检查是否需要调仓
            if not self._should_rebalance(current_date):
                return self._get_status_report(current_date, "无需调仓")
            
            # 2. 生成所有股票的信号
            self.current_signals = self.signal_generator.generate_batch_signals(data_dict)
            
            # 3. 筛选有效信号
            valid_signals = self._filter_valid_signals(self.current_signals)
            
            # 4. 风险检查
            risk_check = self._risk_check(data_dict, current_date)
            if not risk_check['passed']:
                return self._get_status_report(current_date, f"风险检查未通过: {risk_check['reason']}")
            
            # 5. 执行轮动交易
            trade_results = self._execute_rotation(valid_signals, data_dict, current_date)
            
            # 6. 更新策略状态
            self._update_strategy_state(current_date)
            
            # 7. 生成策略报告
            return self._get_strategy_report(current_date, trade_results)
            
        except Exception as e:
            self.logger.error(f"策略运行失败: {str(e)}")
            raise StrategyError(f"策略运行失败: {str(e)}") from e
    
    def _should_rebalance(self, current_date: datetime) -> bool:
        """判断是否需要调仓"""
        try:
            # 首次运行
            if self.last_rebalance_date is None:
                return True
            
            # 根据调仓频率判断
            if self.strategy_params['rebalance_frequency'] == 'daily':
                return True
            elif self.strategy_params['rebalance_frequency'] == 'weekly':
                days_since_last = (current_date - self.last_rebalance_date).days
                return days_since_last >= 7
            elif self.strategy_params['rebalance_frequency'] == 'monthly':
                return current_date.month != self.last_rebalance_date.month
            
            return False
            
        except Exception as e:
            self.logger.warning(f"调仓判断失败: {str(e)}")
            return False
    
    def _filter_valid_signals(self, signals: Dict[str, Dict]) -> Dict[str, Dict]:
        """筛选有效信号"""
        try:
            valid_signals = {}
            
            for stock_code, signal_data in signals.items():
                # 跳过错误信号
                if 'error' in signal_data:
                    self.logger.warning(f"股票 {stock_code} 信号生成错误: {signal_data['error']}")
                    continue
                
                signal = signal_data['signal']
                confidence = signal_data['confidence']
                
                # 信号强度筛选
                if signal in ['BUY', 'SELL'] and confidence >= self.strategy_params['signal_threshold']:
                    valid_signals[stock_code] = signal_data
                    self.logger.debug(f"有效信号: {stock_code} {signal} (置信度: {confidence:.2f})")
            
            self.logger.info(f"筛选出 {len(valid_signals)} 个有效信号")
            return valid_signals
            
        except Exception as e:
            raise StrategyError(f"信号筛选失败: {str(e)}") from e
    
    def _risk_check(self, data_dict: Dict[str, pd.DataFrame], 
                   current_date: datetime) -> Dict:
        """风险检查"""
        try:
            # 基础风险检查
            checks = {
                'data_quality': True,
                'market_condition': True,
                'position_risk': True
            }
            
            # 1. 数据质量检查
            for stock_code, data in data_dict.items():
                if data is None or data.empty or len(data) < 60:
                    checks['data_quality'] = False
                    return {
                        'passed': False,
                        'reason': f'股票 {stock_code} 数据质量不足'
                    }
            
            # 2. 市场状况检查 (简化版)
            # 这里可以添加更复杂的市场风险判断逻辑
            
            # 3. 持仓风险检查
            current_positions = self.position_manager.get_position_summary()
            if current_positions['total_return'] < -0.20:  # 总亏损超过20%
                return {
                    'passed': False,
                    'reason': f'总亏损过大: {current_positions["total_return"]:.2%}'
                }
            
            return {'passed': True, 'reason': '风险检查通过'}
            
        except Exception as e:
            return {'passed': False, 'reason': f'风险检查异常: {str(e)}'}
    
    def _execute_rotation(self, valid_signals: Dict[str, Dict], 
                         data_dict: Dict[str, pd.DataFrame], 
                         current_date: datetime) -> List[Dict]:
        """执行轮动交易"""
        try:
            trade_results = []
            current_prices = {}
            
            # 获取当前价格
            for stock_code, data in data_dict.items():
                if not data.empty:
                    current_prices[stock_code] = data['close'].iloc[-1]
            
            # 更新总资产
            self.position_manager.update_total_value(current_prices)
            
            # 1. 处理卖出信号
            sell_signals = {k: v for k, v in valid_signals.items() if v['signal'] == 'SELL'}
            for stock_code, signal_data in sell_signals.items():
                if stock_code in current_prices:
                    price = current_prices[stock_code]
                    confidence = signal_data['confidence']
                    
                    # 计算卖出数量
                    sell_size = self.position_manager.calculate_position_size(
                        stock_code, 'SELL', price, confidence
                    )
                    
                    if sell_size < 0:  # 有卖出需求
                        result = self.position_manager.execute_trade(
                            stock_code, sell_size, price, current_date
                        )
                        trade_results.append(result)
                        self.logger.info(f"执行卖出: {stock_code} {abs(sell_size)}股")
            
            # 2. 处理买入信号
            buy_signals = {k: v for k, v in valid_signals.items() if v['signal'] == 'BUY'}
            
            # 按信号强度排序
            sorted_buy_signals = sorted(
                buy_signals.items(), 
                key=lambda x: x[1]['confidence'], 
                reverse=True
            )
            
            for stock_code, signal_data in sorted_buy_signals:
                if stock_code in current_prices:
                    price = current_prices[stock_code]
                    confidence = signal_data['confidence']
                    
                    # 计算买入数量
                    buy_size = self.position_manager.calculate_position_size(
                        stock_code, 'BUY', price, confidence
                    )
                    
                    if buy_size > 0:  # 有买入需求
                        result = self.position_manager.execute_trade(
                            stock_code, buy_size, price, current_date
                        )
                        trade_results.append(result)
                        self.logger.info(f"执行买入: {stock_code} {buy_size}股")
            
            return trade_results
            
        except Exception as e:
            raise StrategyError(f"轮动交易执行失败: {str(e)}") from e
    
    def _update_strategy_state(self, current_date: datetime):
        """更新策略状态"""
        self.last_rebalance_date = current_date
        
        # 更新性能指标
        summary = self.position_manager.get_position_summary()
        self.update_performance(
            total_return=summary['total_return'],
            position_count=summary['position_count'],
            cash_ratio=summary['cash_ratio']
        )
    
    def _get_status_report(self, current_date: datetime, message: str) -> Dict:
        """生成状态报告"""
        summary = self.position_manager.get_position_summary()
        
        return {
            'date': current_date,
            'status': 'no_action',
            'message': message,
            'portfolio_summary': summary,
            'signals_count': len(self.current_signals),
            'performance': self.get_performance()
        }
    
    def _get_strategy_report(self, current_date: datetime, 
                           trade_results: List[Dict]) -> Dict:
        """生成策略报告"""
        summary = self.position_manager.get_position_summary()
        
        # 统计交易结果
        successful_trades = [t for t in trade_results if t.get('status') == 'success']
        buy_trades = [t for t in successful_trades if t.get('action') == 'BUY']
        sell_trades = [t for t in successful_trades if t.get('action') == 'SELL']
        
        return {
            'date': current_date,
            'status': 'rebalanced',
            'message': f'完成调仓，执行 {len(successful_trades)} 笔交易',
            'trades': {
                'total': len(trade_results),
                'successful': len(successful_trades),
                'buy_count': len(buy_trades),
                'sell_count': len(sell_trades),
                'details': trade_results
            },
            'signals': {
                'total': len(self.current_signals),
                'buy': len([s for s in self.current_signals.values() if s.get('signal') == 'BUY']),
                'sell': len([s for s in self.current_signals.values() if s.get('signal') == 'SELL']),
                'hold': len([s for s in self.current_signals.values() if s.get('signal') == 'HOLD'])
            },
            'portfolio_summary': summary,
            'performance': self.get_performance()
        }
    
    def generate_signals(self, data: Dict[str, pd.DataFrame]) -> Dict[str, str]:
        """实现基类的抽象方法"""
        signals = self.signal_generator.generate_batch_signals(data)
        return {k: v.get('signal', 'HOLD') for k, v in signals.items()}
    
    def calculate_position_size(self, stock_code: str, signal: str, 
                              current_price: float, account_value: float) -> float:
        """实现基类的抽象方法"""
        confidence = self.current_signals.get(stock_code, {}).get('confidence', 0.5)
        return self.position_manager.calculate_position_size(
            stock_code, signal, current_price, confidence
        )
    
    def should_exit_position(self, stock_code: str, data: pd.DataFrame) -> bool:
        """实现基类的抽象方法"""
        try:
            if stock_code not in self.position_manager.positions:
                return False
            
            current_price = data['close'].iloc[-1]
            position = self.position_manager.positions[stock_code]
            
            # 计算盈亏比例
            pnl_ratio = (current_price - position['avg_price']) / position['avg_price']
            
            # 止损检查
            if pnl_ratio <= self.strategy_params['stop_loss_ratio']:
                self.logger.info(f"触发止损: {stock_code} 亏损 {pnl_ratio:.2%}")
                return True
            
            # 止盈检查
            if pnl_ratio >= self.strategy_params['take_profit_ratio']:
                self.logger.info(f"触发止盈: {stock_code} 盈利 {pnl_ratio:.2%}")
                return True
            
            return False
            
        except Exception as e:
            self.logger.warning(f"退出判断失败 {stock_code}: {str(e)}")
            return False
    
    def get_detailed_report(self) -> Dict:
        """获取详细报告"""
        try:
            summary = self.position_manager.get_position_summary()
            trade_history = self.position_manager.get_trade_history()
            
            return {
                'strategy_name': self.name,
                'last_rebalance': self.last_rebalance_date,
                'portfolio_summary': summary,
                'current_signals': self.current_signals,
                'trade_history': trade_history[-10:],  # 最近10笔交易
                'performance': self.get_performance(),
                'config': self.get_config()
            }
            
        except Exception as e:
            raise StrategyError(f"生成详细报告失败: {str(e)}") from e

if __name__ == "__main__":
    # 测试代码
    import sys
    import os
    sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    
    from data.data_fetcher import AkshareDataFetcher
    from data.data_processor import DataProcessor
    
    logging.basicConfig(level=logging.INFO)
    
    # 测试配置
    config = {
        'name': 'TestRotationStrategy',
        'stock_pool': ['000001', '000002', '601088'],
        'signal_config': {
            'ema_period': 20,
            'rsi_period': 14
        },
        'position_config': {
            'initial_capital': 1000000,
            'position_size': 0.2,
            'max_positions': 3
        },
        'strategy_params': {
            'rebalance_frequency': 'weekly',
            'signal_threshold': 0.5
        }
    }
    
    print("🚀 中线轮动策略测试")
    print("=" * 60)
    
    try:
        # 创建策略
        strategy = RotationStrategy(config)
        
        # 获取测试数据
        fetcher = AkshareDataFetcher()
        processor = DataProcessor()
        
        print("获取测试数据...")
        data_dict = {}
        
        for stock_code in ['601088']:  # 简化测试，只用一只股票
            try:
                daily_data = fetcher.get_stock_data(stock_code, '2023-01-01', '2025-01-01')
                if daily_data is not None and not daily_data.empty:
                    weekly_data = processor.resample_to_weekly(daily_data)
                    data_dict[stock_code] = weekly_data
                    print(f"✅ {stock_code}: {len(weekly_data)}条周线数据")
            except Exception as e:
                print(f"❌ {stock_code}: {str(e)}")
        
        if data_dict:
            # 运行策略
            current_date = datetime(2024, 12, 1)
            result = strategy.run_strategy(data_dict, current_date)
            
            print("\n📊 策略运行结果:")
            print(f"状态: {result['status']}")
            print(f"消息: {result['message']}")
            
            if 'trades' in result:
                print(f"交易统计: {result['trades']}")
            
            if 'portfolio_summary' in result:
                portfolio = result['portfolio_summary']
                print(f"总资产: {portfolio['total_value']:.2f}")
                print(f"总收益率: {portfolio['total_return']:.2%}")
        
        print("✅ 中线轮动策略测试完成")
        
    except Exception as e:
        print(f"❌ 测试失败: {e}")
        import traceback
        traceback.print_exc()