"""
报告服务
负责生成各类回测报告（HTML、CSV、信号跟踪等）
"""

import os
from datetime import datetime
from typing import Any, Dict, List, Optional

import pandas as pd

from backtest.detailed_csv_exporter import DetailedCSVExporter
from backtest.enhanced_report_generator_integrated_fixed import IntegratedReportGenerator

from config.path_manager import get_path_manager

from .base_service import BaseService


class ReportService(BaseService):
    """
    报告服务 - 回测报告生成
    
    职责：
    1. HTML报告生成
    2. CSV详细交易记录
    3. 信号跟踪报告
    4. 分红配股报告
    """
    
    def __init__(self, config: Dict[str, Any], dcf_values: Dict[str, float] = None):
        """
        初始化报告服务
        
        Args:
            config: 配置字典
            dcf_values: DCF估值字典
        """
        super().__init__(config)
        
        # 报告生成器
        self.html_generator = None
        self.csv_exporter = None
        self.dcf_values = dcf_values or {}
        
        # 报告输出目录
        self.report_dir = config.get('report_dir', 'reports')
        
        # 确保报告目录存在
        get_path_manager().get_reports_dir().mkdir(parents=True, exist_ok=True)
    
    def initialize(self) -> bool:
        """
        初始化报告服务
        
        Returns:
            bool: 初始化是否成功
        """
        try:
            # 初始化HTML报告生成器
            self.html_generator = IntegratedReportGenerator()
            
            # 初始化CSV导出器，传递DCF估值数据
            self.csv_exporter = DetailedCSVExporter(dcf_values=self.dcf_values)
            
            self._initialized = True
            self.logger.info(f"ReportService 初始化成功，DCF估值数量: {len(self.dcf_values)}")
            return True
        except Exception as e:
            self.logger.error(f"ReportService 初始化失败: {e}")
            return False
    
    def generate_all_reports(self, backtest_results: Dict[str, Any],
                            stock_data: Dict[str, Dict[str, pd.DataFrame]],
                            transaction_history: List[Dict],
                            signal_tracker=None,
                            portfolio_manager=None) -> Dict[str, str]:
        """
        生成所有报告
        
        Args:
            backtest_results: 回测结果
            stock_data: 股票数据
            transaction_history: 交易历史
            signal_tracker: 信号跟踪器
            portfolio_manager: 投资组合管理器
            
        Returns:
            报告文件路径字典
        """
        report_paths = {}
        
        # 1. 生成HTML报告
        html_path = self.generate_html_report(backtest_results, stock_data, signal_tracker)
        if html_path:
            report_paths['html_report'] = html_path
        
        # 2. 生成CSV详细交易记录
        csv_path = self.generate_csv_report(
            transaction_history, 
            backtest_results.get('signal_details', {})
        )
        if csv_path:
            report_paths['detailed_csv_report'] = csv_path
        
        # 3. 生成信号跟踪报告
        if signal_tracker:
            signal_path = self.generate_signal_tracking_report(signal_tracker)
            if signal_path:
                report_paths['signal_tracking_report'] = signal_path
        
        # 4. 生成分红配股报告
        if portfolio_manager and hasattr(portfolio_manager, 'dividend_history'):
            dividend_path = self.generate_dividend_report(portfolio_manager)
            if dividend_path:
                report_paths['dividend_csv_report'] = dividend_path
        
        return report_paths
    
    def generate_html_report(self, backtest_results: Dict[str, Any], 
                            stock_data: Dict[str, Dict[str, pd.DataFrame]] = None,
                            signal_tracker=None) -> Optional[str]:
        """
        生成HTML格式的回测报告
        
        Args:
            backtest_results: 回测结果数据
            stock_data: 股票数据（可选）
            signal_tracker: 信号跟踪器（可选）
            
        Returns:
            str: 报告文件路径，失败返回None
        """
        try:
            self.logger.info("开始生成HTML报告...")
            
            # 🔧 修复：直接使用backtest_results中已准备好的kline_data
            # backtest_engine已经完整准备了所有技术指标数据
            kline_data = backtest_results.get('kline_data', {})
            
            if not kline_data:
                self.logger.warning("⚠️ K线数据为空，报告中将不显示K线图")
            else:
                self.logger.info(f"✅ 使用已准备的K线数据，包含 {len(kline_data)} 只股票")
                # 🔍 调试：检查600900的trades字段
                if '600900' in kline_data:
                    data_600900 = kline_data['600900']
                    self.logger.info(f"🔍 600900数据keys: {list(data_600900.keys())}")
                    self.logger.info(f"🔍 600900 trades数量: {len(data_600900.get('trades', []))}")
            
            # 确保K线数据在回测结果中
            backtest_results['kline_data'] = kline_data
            
            # 🆕 准备signal_tracker数据
            signal_tracker_data = None
            if signal_tracker and hasattr(signal_tracker, 'signal_records'):
                signal_tracker_data = {
                    'signal_records': signal_tracker.signal_records
                }
                self.logger.info(f"✅ 传递signal_tracker数据，包含 {len(signal_tracker.signal_records)} 条信号记录")
            
            # 将signal_tracker_data添加到backtest_results
            backtest_results['signal_tracker_data'] = signal_tracker_data
            
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            output_path = os.path.join(
                self.report_dir,
                f'integrated_backtest_report_{timestamp}.html'
            )
            
            # 生成报告
            self.html_generator.generate_report(backtest_results, output_path)
            
            self.logger.info(f"✅ HTML报告已生成: {output_path}")
            return output_path
            
        except Exception as e:
            self.logger.error(f"HTML报告生成失败: {e}")
            return None
    
    def generate_csv_report(self, transaction_history: List[Dict],
                           signal_details: Dict = None) -> Optional[str]:
        """
        生成CSV详细交易记录
        
        Args:
            transaction_history: 交易历史
            signal_details: 信号详情
            
        Returns:
            报告文件路径
        """
        try:
            if not transaction_history:
                self.logger.info("无交易记录，跳过CSV报告生成")
                return None
            
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            output_path = os.path.join(
                self.report_dir,
                f'detailed_trading_records_{timestamp}.csv'
            )
            
            # 导出CSV
            csv_path = self.csv_exporter.export_trading_records(
                transaction_history,
                output_dir=self.report_dir
            )
            
            if not csv_path:
                self.logger.error("CSV报告生成失败")
                return None
            
            self.logger.info(f"✅ CSV报告已生成: {csv_path}")
            return csv_path
            
        except Exception as e:
            self.logger.error(f"CSV报告生成失败: {e}")
            return None
    
    def generate_signal_tracking_report(self, signal_tracker) -> Optional[str]:
        """
        生成信号跟踪报告
        
        Args:
            signal_tracker: 信号跟踪器
            
        Returns:
            报告文件路径
        """
        try:
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            output_path = os.path.join(
                self.report_dir,
                f'signal_tracking_report_{timestamp}.csv'
            )
            
            # 导出信号跟踪报告
            signal_tracker.export_to_csv(output_path)
            
            self.logger.info(f"✅ 信号跟踪报告已生成: {output_path}")
            return output_path
            
        except Exception as e:
            self.logger.error(f"信号跟踪报告生成失败: {e}")
            return None
    
    def generate_dividend_report(self, portfolio_manager) -> Optional[str]:
        """
        生成分红配股报告
        
        Args:
            portfolio_manager: 投资组合管理器
            
        Returns:
            报告文件路径
        """
        try:
            if not hasattr(portfolio_manager, 'dividend_history'):
                return None
            
            dividend_history = portfolio_manager.dividend_history
            if not dividend_history:
                self.logger.info("无分红配股记录，跳过分红报告生成")
                return None
            
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            output_path = os.path.join(
                self.report_dir,
                f'dividend_records_{timestamp}.csv'
            )
            
            # 转换为DataFrame并导出
            df = pd.DataFrame(dividend_history)
            df.to_csv(output_path, index=False, encoding='utf-8-sig')
            
            self.logger.info(f"✅ 分红配股报告已生成: {output_path}")
            return output_path
            
        except Exception as e:
            self.logger.error(f"分红配股报告生成失败: {e}")
            return None
    
    def _prepare_kline_data(self, stock_data: Dict[str, Dict[str, pd.DataFrame]],
                           backtest_results: Dict[str, Any]) -> Dict[str, Any]:
        """
        准备K线数据用于HTML报告
        
        Args:
            stock_data: 股票数据
            backtest_results: 回测结果
            
        Returns:
            K线数据字典
        """
        kline_data = {}
        
        try:
            # 🔧 修复：使用正确的字段名
            transaction_history = backtest_results.get('transactions', [])
            
            # 如果transactions不存在，尝试从旧字段名获取
            if not transaction_history:
                transaction_history = backtest_results.get('transaction_history', [])
            
            self.logger.info(f"📋 准备K线数据，交易记录数量: {len(transaction_history)}")
            
            # 获取有交易的股票列表
            traded_stocks = set()
            for trade in transaction_history:
                traded_stocks.add(trade.get('stock_code'))
            
            # 为每只交易过的股票准备K线数据
            for stock_code in traded_stocks:
                if stock_code not in stock_data:
                    continue
                
                weekly_data = stock_data[stock_code]['weekly']
                
                # 准备K线数据
                kline_list = []
                rsi_list = []
                macd_dif_list = []
                macd_dea_list = []
                macd_histogram_list = []
                bb_upper_list = []
                bb_middle_list = []
                bb_lower_list = []
                pvr_list = []  # 价值比数据
                
                for idx, row in weekly_data.iterrows():
                    timestamp = int(idx.timestamp() * 1000)
                    
                    # K线数据 [timestamp, open, close, low, high]
                    kline_list.append([
                        timestamp,
                        float(row['open']),
                        float(row['close']),
                        float(row['low']),
                        float(row['high'])
                    ])
                    
                    # RSI数据
                    if 'rsi' in row and pd.notna(row['rsi']):
                        rsi_list.append([timestamp, float(row['rsi'])])
                    
                    # MACD数据 - 分别存储DIF、DEA和柱状图
                    if 'macd' in row and pd.notna(row['macd']):
                        macd_dif_list.append([timestamp, float(row['macd'])])
                    if 'macd_signal' in row and pd.notna(row['macd_signal']):
                        macd_dea_list.append([timestamp, float(row['macd_signal'])])
                    if 'macd_histogram' in row and pd.notna(row['macd_histogram']):
                        macd_histogram_list.append([timestamp, float(row['macd_histogram'])])
                    
                    # 布林带数据
                    if 'bb_upper' in row and pd.notna(row['bb_upper']):
                        bb_upper_list.append([timestamp, float(row['bb_upper'])])
                    if 'bb_middle' in row and pd.notna(row['bb_middle']):
                        bb_middle_list.append([timestamp, float(row['bb_middle'])])
                    if 'bb_lower' in row and pd.notna(row['bb_lower']):
                        bb_lower_list.append([timestamp, float(row['bb_lower'])])
                    
                    # 价值比数据（如果有DCF估值）
                    if 'price_value_ratio' in row and pd.notna(row['price_value_ratio']):
                        pvr_list.append([timestamp, float(row['price_value_ratio'])])
                
                # 准备交易标记 - 使用模板期望的格式
                trades_list = []
                
                for trade in transaction_history:
                    if trade.get('stock_code') != stock_code:
                        continue
                    
                    trade_date = trade.get('date')
                    if trade_date in weekly_data.index:
                        timestamp = int(trade_date.timestamp() * 1000)
                        price = float(trade.get('price', 0))
                        action = trade.get('action', '')
                        
                        trades_list.append({
                            'timestamp': timestamp,
                            'type': 'BUY' if action == 'buy' else 'SELL',
                            'price': price,
                            'shares': trade.get('shares', 0)
                        })
                
                kline_data[stock_code] = {
                    'kline': kline_list,
                    'rsi': rsi_list,
                    'macd': {
                        'dif': macd_dif_list,
                        'dea': macd_dea_list,
                        'histogram': macd_histogram_list
                    },
                    'bb_upper': bb_upper_list,
                    'bb_middle': bb_middle_list,
                    'bb_lower': bb_lower_list,
                    'pvr': pvr_list,  # 价值比数据
                    'trades': trades_list
                }
            
            self.logger.info(f"✅ 已准备 {len(kline_data)} 只股票的K线数据")
            
        except Exception as e:
            self.logger.error(f"K线数据准备失败: {e}")
        
        return kline_data
