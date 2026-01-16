"""
信号服务
负责交易信号生成和分析
"""

from typing import Any, Dict, List, Optional

import pandas as pd

from strategy.signal_generator import SignalGenerator

from .base_service import BaseService


class SignalService(BaseService):
    """
    信号服务 - 交易信号生成
    
    职责：
    1. 4维度信号生成
    2. 信号详情记录
    3. 信号统计分析
    """
    
    def __init__(self, config: Dict[str, Any], dcf_values: Dict[str, float],
                 rsi_thresholds: Dict[str, Dict[str, float]],
                 stock_industry_map: Dict[str, Dict[str, str]],
                 stock_pool: List[str],
                 signal_tracker=None):
        """
        初始化信号服务
        
        Args:
            config: 配置字典
            dcf_values: DCF估值数据
            rsi_thresholds: RSI阈值数据
            stock_industry_map: 股票-行业映射
            stock_pool: 股票池列表
            signal_tracker: 信号跟踪器（可选）
        """
        super().__init__(config)
        
        self.dcf_values = dcf_values
        self.rsi_thresholds = rsi_thresholds
        self.stock_industry_map = stock_industry_map
        self.stock_pool = stock_pool  # 使用传入的stock_pool，不自己创建
        self.signal_tracker = signal_tracker
        
        # 信号生成器将在initialize中创建
        self.signal_generator = None
        
        # 信号详情存储
        self.signal_details = {}
    
    def initialize(self) -> bool:
        """
        初始化信号服务
        
        Returns:
            bool: 初始化是否成功
        """
        try:
            # 合并config和strategy_params
            signal_config = self.config.copy()
            if 'strategy_params' in self.config:
                signal_config.update(self.config['strategy_params'])
            
            # 初始化信号生成器
            self.signal_generator = SignalGenerator(
                signal_config,
                self.dcf_values,
                self.rsi_thresholds,
                self.stock_industry_map
            )
            
            self._initialized = True
            self.logger.info("SignalService 初始化成功")
            return True
        except Exception as e:
            self.logger.error(f"SignalService 初始化失败: {e}")
            return False
    
    def generate_signals(self, stock_data: Dict[str, Dict[str, pd.DataFrame]],
                        current_date: pd.Timestamp) -> Dict[str, str]:
        """
        生成交易信号
        
        Args:
            stock_data: 股票数据字典
            current_date: 当前日期
            
        Returns:
            股票代码到信号的映射 ('buy', 'sell', 'hold')
        """
        signals = {}
        
        for stock_code in self.stock_pool:
            if stock_code not in stock_data:
                self.logger.debug(f"{stock_code} 不在stock_data中，跳过")
                continue
            
            stock_weekly = stock_data[stock_code]['weekly']
            if current_date not in stock_weekly.index:
                self.logger.debug(f"{stock_code} 在{current_date}无数据，跳过")
                continue
            
            # 获取当前数据点索引
            current_idx = stock_weekly.index.get_loc(current_date)
            if current_idx < 120:  # 需要足够的历史数据
                self.logger.debug(f"{stock_code} 历史数据不足({current_idx}<120)，跳过")
                continue
            
            # 获取历史数据用于信号生成
            historical_data = stock_weekly.iloc[:current_idx+1]
            
            # 确保有足够的数据
            if len(historical_data) < 120:
                self.logger.debug(f"{stock_code} 历史数据长度不足({len(historical_data)}<120)，跳过")
                continue
            
            # 生成信号
            try:
                signal_result = self.signal_generator.generate_signal(
                    stock_code,
                    historical_data
                )
                
                if signal_result and isinstance(signal_result, dict):
                    signal = signal_result.get('signal', 'HOLD')
                    
                    # 记录BUY/SELL信号到signal_tracker
                    if signal in ['BUY', 'SELL'] and self.signal_tracker:
                        self.signal_tracker.record_signal({
                            'date': current_date,
                            'stock_code': stock_code,
                            'signal_result': signal_result
                        })
                    
                    if signal and signal != 'HOLD':
                        signals[stock_code] = signal
                        
                        # 记录信号详情用于报告
                        self.signal_details[f"{stock_code}_{current_date.strftime('%Y-%m-%d')}"] = signal_result
                        
                        # 记录信号详情
                        value_ratio = signal_result.get('value_price_ratio', 0)
                        self.logger.debug(
                            f"{current_date.strftime('%Y-%m-%d')} {stock_code} "
                            f"信号: {signal}, 价值比: {value_ratio:.2f}"
                        )
                else:
                    self.logger.debug(f"{stock_code} 信号生成返回None或非字典")
            except Exception as e:
                self.logger.error(f"{stock_code} 信号生成失败: {e}")
                import traceback
                self.logger.error(traceback.format_exc())
                continue
        
        return signals
    
    def get_signal_details(self, stock_code: str, stock_data: pd.DataFrame,
                          current_date: pd.Timestamp) -> Optional[Dict]:
        """
        获取信号详情
        
        Args:
            stock_code: 股票代码
            stock_data: 股票数据
            current_date: 当前日期
            
        Returns:
            信号详情字典
        """
        try:
            if current_date not in stock_data.index:
                return None
            
            current_idx = stock_data.index.get_loc(current_date)
            if current_idx < 120:
                return None
            
            historical_data = stock_data.iloc[:current_idx+1]
            
            signal_result = self.signal_generator.generate_signal(
                stock_code,
                historical_data
            )
            
            if signal_result and isinstance(signal_result, dict):
                return {
                    'signal_type': signal_result.get('signal', 'HOLD'),
                    'value_ratio': signal_result.get('value_price_ratio', 0),
                    'scores': signal_result.get('scores', {}),
                    'technical_indicators': signal_result.get('technical_indicators', {}),
                    'trigger_reason': signal_result.get('trigger_reason', '')
                }
            
            return None
            
        except Exception as e:
            self.logger.error(f"获取信号详情失败: {e}")
            return None
    
    def get_signal_statistics(self, transaction_history: pd.DataFrame) -> Dict[str, Any]:
        """
        获取信号统计
        
        Args:
            transaction_history: 交易历史DataFrame
            
        Returns:
            信号统计字典
        """
        try:
            signal_analysis = {}
            
            # 全局信号统计
            buy_signals = transaction_history[transaction_history['trade_type'] == 'buy']
            sell_signals = transaction_history[transaction_history['trade_type'] == 'sell']
            
            signal_analysis['global_stats'] = {
                'total_buy_signals': len(buy_signals),
                'total_sell_signals': len(sell_signals),
                'total_signals': len(transaction_history)
            }
            
            # 各维度触发频率
            dimension_stats = {
                'trend_filter': 0,
                'rsi_oversold': 0,
                'macd_momentum': 0,
                'bollinger_volume': 0
            }
            
            for _, row in transaction_history.iterrows():
                if pd.notna(row.get('trend_filter_met')):
                    if row['trend_filter_met']:
                        dimension_stats['trend_filter'] += 1
                if pd.notna(row.get('rsi_oversold_met')):
                    if row['rsi_oversold_met']:
                        dimension_stats['rsi_oversold'] += 1
                if pd.notna(row.get('macd_momentum_met')):
                    if row['macd_momentum_met']:
                        dimension_stats['macd_momentum'] += 1
                if pd.notna(row.get('bollinger_volume_met')):
                    if row['bollinger_volume_met']:
                        dimension_stats['bollinger_volume'] += 1
            
            signal_analysis['dimension_stats'] = dimension_stats
            
            # 个股信号分析
            stock_signals = {}
            for stock_code in transaction_history['stock_code'].unique():
                stock_trades = transaction_history[transaction_history['stock_code'] == stock_code]
                stock_signals[stock_code] = {
                    'buy_count': len(stock_trades[stock_trades['trade_type'] == 'buy']),
                    'sell_count': len(stock_trades[stock_trades['trade_type'] == 'sell']),
                    'total_count': len(stock_trades)
                }
            
            signal_analysis['stock_signals'] = stock_signals
            
            return signal_analysis
            
        except Exception as e:
            self.logger.error(f"信号统计分析失败: {e}")
            return {}
