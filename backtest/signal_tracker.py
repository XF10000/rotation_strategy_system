"""
信号跟踪器模块
负责记录和导出4维信号分析框架的买卖信号详细信息
只记录BUY/SELL信号，不记录HOLD信号和动态仓位管理信息
"""

import pandas as pd
import csv
import os
import logging
from datetime import datetime
from typing import Dict, List, Any, Optional

logger = logging.getLogger(__name__)

class SignalTracker:
    """
    4维买卖信号跟踪器
    
    功能：
    - 记录通过4维信号确认的高质量买卖信号
    - 包含32个字段的详细信号分析信息
    - 导出标准化CSV格式报告
    """
    
    def __init__(self, output_path: Optional[str] = None):
        """
        初始化信号跟踪器
        
        Args:
            output_path: CSV输出文件路径，如果为None则自动生成
        """
        self.logger = logging.getLogger("backtest.SignalTracker")
        
        # 设置输出路径
        if output_path is None:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            output_path = f"reports/signal_tracking_report_{timestamp}.csv"
        
        self.output_path = output_path
        self.signal_records = []
        
        # 定义41个字段的标准化数据结构（32个基础字段 + 9个执行及仓位相关字段）
        self.field_definitions = [
            # 1️⃣ 基础信息 (5个字段)
            'date', 'stock_code', 'stock_name', 'signal_type', 'current_price',
            
            # 2️⃣ 4维信号综合决策 (5个字段) + 执行状态信息 (4个字段) + 仓位变化信息 (4个字段)
            'dimension_1_status', 'tech_dimensions_satisfied', 'three_choose_two_result',
            'signal_strength', 'final_decision_basis',
            # 执行状态信息 (4个字段) - 移动到决策依据后面
            'execution_status', 'execution_reason', 'execution_date', 'execution_price',
            # 仓位变化信息 (5个字段) - 新增
            'position_before_signal', 'position_weight_before', 'trade_shares', 'position_after_trade', 'position_weight_after',
            
            # 3️⃣ 维度一：价值准入过滤器 (3个字段)
            'dcf_value', 'value_ratio', 'value_filter_status',
            
            # 4️⃣ 维度二：超买超卖 (9个字段)
            'industry_name', 'rsi_14w', 'industry_buy_threshold', 'industry_sell_threshold',
            'industry_extreme_buy', 'industry_extreme_sell', 'rsi_signal_type',
            'price_divergence', 'dimension_2_status',
            
            # 5️⃣ 维度三：动能确认 (7个字段)
            'macd_dif', 'macd_dea', 'macd_histogram', 'macd_color',
            'histogram_trend', 'golden_cross_status', 'dimension_3_status',
            
            # 6️⃣ 维度四：极端放量 (9个字段)
            'bb_middle', 'bb_upper', 'bb_lower', 'price_bb_position',
            'current_volume', 'volume_baseline', 'volume_ratio',
            'significant_volume', 'dimension_4_status',
            
            # 7️⃣ 技术指标原始数据 (4个字段)
            'recent_5w_prices', 'recent_5w_volumes', 'data_quality', 'calculation_errors',
            
            # 8️⃣ 信号ID (1个字段) - 保持在最后
            'signal_id'
        ]
        
        # 未执行原因常量定义
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
        
        # 用于存储信号ID到记录索引的映射
        self.signal_id_to_index = {}
        
        self.logger.info(f"信号跟踪器初始化完成，输出路径: {self.output_path}")
        self.logger.info(f"将记录 {len(self.field_definitions)} 个字段的详细信号信息（32个基础字段 + 4个执行状态字段 + 4个仓位变化字段 + 1个信号ID字段）")
    
    def record_signal(self, signal_data: Dict[str, Any]) -> None:
        """
        记录单个买卖信号
        
        Args:
            signal_data: 包含信号详细信息的字典
                - date: 信号生成日期
                - stock_code: 股票代码
                - signal_result: SignalGenerator返回的信号结果
        """
        try:
            signal_result = signal_data.get('signal_result', {})
            signal_type = signal_result.get('signal', '')
            
            # 🆕 新增调试日志
            self.logger.info(f"🔍 收到信号记录请求: {signal_data.get('stock_code')} - {signal_data.get('date')} - {signal_type}")
            
            # 只记录BUY/SELL信号，跳过HOLD信号
            if signal_type not in ['BUY', 'SELL']:
                self.logger.debug(f"跳过非买卖信号: {signal_type}")
                return
            
            # 验证信号质量 - 只记录通过4维确认的高质量信号
            if not self._validate_signal_quality(signal_result):
                self.logger.debug(f"跳过未通过4维确认的信号: {signal_type}")
                return
            
            # 格式化信号记录为32字段标准格式
            formatted_record = self._format_signal_record(signal_data)
            
            if formatted_record:
                self.signal_records.append(formatted_record)
                self.logger.info(f"✅ 记录 {signal_type} 信号: {signal_data.get('stock_code')} - {signal_data.get('date')}")
                self.logger.debug(f"当前已记录信号数量: {len(self.signal_records)}")
            
        except Exception as e:
            self.logger.error(f"记录信号失败: {str(e)}", exc_info=True)
    
    def _validate_signal_quality(self, signal_result: Dict) -> bool:
        """
        验证信号质量（4维确认）
        
        Args:
            signal_result: 信号生成器返回的结果
            
        Returns:
            bool: 是否通过4维确认的高质量信号
        """
        try:
            # 检查信号详情
            # 从 signal_result 中直接获取 scores，或者从 signal_details 中获取
            scores = signal_result.get('scores', {})
            if not scores:
                # 如果直接获取不到，尝试从 signal_details 中获取
                signal_details = signal_result.get('signal_details', {})
                scores = signal_details.get('scores', {})
            
            signal_type = signal_result.get('signal', '').upper()
            
            # 🆕 新增调试日志
            self.logger.info(f"🔍 验证信号质量: {signal_type}")
            self.logger.info(f"🔍 scores: {scores}")
            
            if signal_type == 'BUY':
                # 买入信号验证
                # 1. 价值准入过滤器（硬性前提）
                value_filter_pass = scores.get('trend_filter_low', False)
                
                # 2. 技术维度满足至少2个
                tech_dimensions = [
                    scores.get('overbought_oversold_low', False),   # 超买超卖
                    scores.get('momentum_low', False),              # 动能确认
                    scores.get('extreme_price_volume_low', False)   # 极端放量
                ]
                tech_satisfied = sum(tech_dimensions)
                
                # 🆕 新增调试日志
                self.logger.info(f"🔍 BUY信号验证:")
                self.logger.info(f"   价值过滤器: {value_filter_pass}")
                self.logger.info(f"   技术维度: {tech_dimensions} -> 满足{tech_satisfied}个")
                
                # 4维确认：价值过滤器 + 至少2个技术维度
                is_valid = value_filter_pass and tech_satisfied >= 2
                
            elif signal_type == 'SELL':
                # 卖出信号验证
                # 1. 价值准入过滤器（硬性前提）
                value_filter_pass = scores.get('trend_filter_high', False)
                
                # 2. 技术维度满足至少2个
                tech_dimensions = [
                    scores.get('overbought_oversold_high', False),  # 超买超卖
                    scores.get('momentum_high', False),             # 动能确认
                    scores.get('extreme_price_volume_high', False)  # 极端放量
                ]
                tech_satisfied = sum(tech_dimensions)
                
                # 🆕 新增调试日志
                self.logger.info(f"🔍 SELL信号验证:")
                self.logger.info(f"   价值过滤器: {value_filter_pass}")
                self.logger.info(f"   技术维度: {tech_dimensions} -> 满足{tech_satisfied}个")
                
                # 4维确认：价值过滤器 + 至少2个技术维度
                is_valid = value_filter_pass and tech_satisfied >= 2
                
            else:
                is_valid = False
                
            if is_valid:
                self.logger.info(f"✅ 信号质量验证通过: {signal_type}")
            else:
                self.logger.info(f"❌ 信号质量验证失败: {signal_type}")
            
            return is_valid
            
        except Exception as e:
            self.logger.error(f"信号质量验证异常: {str(e)}")
            return False
    
    def _format_signal_record(self, signal_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        格式化信号记录为37字段标准格式（32个基础字段 + 5个执行状态字段）
        
        Args:
            signal_data: 原始信号数据
            
        Returns:
            Dict: 格式化后的37字段记录
        """
        try:
            date = signal_data.get('date', '')
            stock_code = signal_data.get('stock_code', '')
            signal_result = signal_data.get('signal_result', {})
            
            # 基础信息
            signal_type = signal_result.get('signal', '')
            current_price = signal_result.get('current_price', 0.0)
            
            # 生成唯一信号ID
            timestamp = int(pd.Timestamp(date).timestamp())
            signal_id = f"{stock_code}_{date.strftime('%Y%m%d') if hasattr(date, 'strftime') else str(date).replace('-', '').replace(' ', '').replace(':', '')[:8]}_{signal_type}_{timestamp}"
            
            # 从signal_result中提取详细信息
            technical_indicators = signal_result.get('technical_indicators', {})
            detailed_info = signal_result.get('detailed_info', {})
            scores = signal_result.get('scores', {})
            rsi_thresholds = signal_result.get('rsi_thresholds', {})
            
            # 计算4维信号综合决策信息
            tech_satisfied_count = self._calculate_tech_dimensions_satisfied(scores, signal_type)
            three_choose_two = '是' if tech_satisfied_count >= 2 else '否'
            dimension_1_status = self._get_dimension_1_status(scores, signal_type)
            
            # 1️⃣ 基础信息 (5个字段)
            record = {
                'date': str(date),
                'stock_code': str(stock_code),
                'stock_name': self._get_stock_name(stock_code),
                'signal_type': signal_type,
                'current_price': round(float(current_price), 2) if current_price else 0.0
            }
            
            # 2️⃣ 4维信号综合决策 (5个字段)
            record.update({
                'dimension_1_status': dimension_1_status,
                'tech_dimensions_satisfied': tech_satisfied_count,
                'three_choose_two_result': three_choose_two,
                'signal_strength': signal_result.get('confidence', 0) * 20,  # 将0-4分转换为0-80分
                'final_decision_basis': signal_result.get('reason', '4维信号确认完成')
            })
            
            # 3️⃣ 维度一：价值准入过滤器 (3个字段)
            dcf_value = signal_result.get('dcf_value', 0.0)
            value_ratio = signal_result.get('value_price_ratio', 0.0)
            record.update({
                'dcf_value': round(float(dcf_value), 2) if dcf_value else 0.0,
                'value_ratio': round(float(value_ratio), 2) if value_ratio else 0.0,
                'value_filter_status': dimension_1_status
            })
            
            # 4️⃣ 维度二：超买超卖 (9个字段)
            industry_name = detailed_info.get('industry_name', '未知行业')
            rsi_14w = technical_indicators.get('rsi_14w', 50.0)
            rsi_signal_type = detailed_info.get('rsi_signal_type', '无信号')
            price_divergence = detailed_info.get('price_divergence', '无背离')
            dimension_2_status = self._get_dimension_status(scores, 'overbought_oversold', signal_type)
            
            record.update({
                'industry_name': industry_name,
                'rsi_14w': round(float(rsi_14w), 2) if rsi_14w else 50.0,
                'industry_buy_threshold': rsi_thresholds.get('buy_threshold', 30.0),
                'industry_sell_threshold': rsi_thresholds.get('sell_threshold', 70.0),
                'industry_extreme_buy': rsi_thresholds.get('extreme_buy_threshold', 20.0),
                'industry_extreme_sell': rsi_thresholds.get('extreme_sell_threshold', 80.0),
                'rsi_signal_type': rsi_signal_type,
                'price_divergence': price_divergence,
                'dimension_2_status': dimension_2_status
            })
            
            # 5️⃣ 维度三：动能确认 (7个字段)
            macd_dif = technical_indicators.get('macd_dif', 0.0)
            macd_dea = technical_indicators.get('macd_dea', 0.0)
            macd_histogram = technical_indicators.get('macd_hist', 0.0)
            macd_color = '红色' if macd_histogram > 0 else '绿色'
            histogram_trend = detailed_info.get('histogram_trend', '无变化')
            golden_cross_status = detailed_info.get('golden_cross_status', '无交叉')
            dimension_3_status = self._get_dimension_status(scores, 'momentum', signal_type)
            
            record.update({
                'macd_dif': round(float(macd_dif), 4) if macd_dif else 0.0,
                'macd_dea': round(float(macd_dea), 4) if macd_dea else 0.0,
                'macd_histogram': round(float(macd_histogram), 4) if macd_histogram else 0.0,
                'macd_color': macd_color,
                'histogram_trend': histogram_trend,
                'golden_cross_status': golden_cross_status,
                'dimension_3_status': dimension_3_status
            })
            
            # 6️⃣ 维度四：极端放量 (9个字段)
            bb_middle = technical_indicators.get('bb_middle', current_price)
            bb_upper = technical_indicators.get('bb_upper', current_price * 1.02)
            bb_lower = technical_indicators.get('bb_lower', current_price * 0.98)
            price_bb_position = detailed_info.get('price_bb_position', '区间内')
            current_volume = technical_indicators.get('volume', 0)
            volume_baseline = technical_indicators.get('volume_ma', current_volume)
            volume_ratio = technical_indicators.get('volume_ratio', 1.0)
            significant_volume = detailed_info.get('significant_volume', '否')
            dimension_4_status = self._get_dimension_status(scores, 'extreme_price_volume', signal_type)
            
            record.update({
                'bb_middle': round(float(bb_middle), 2) if bb_middle else 0.0,
                'bb_upper': round(float(bb_upper), 2) if bb_upper else 0.0,
                'bb_lower': round(float(bb_lower), 2) if bb_lower else 0.0,
                'price_bb_position': price_bb_position,
                'current_volume': int(current_volume) if current_volume else 0,
                'volume_baseline': int(volume_baseline) if volume_baseline else 0,
                'volume_ratio': round(float(volume_ratio), 2) if volume_ratio else 1.0,
                'significant_volume': significant_volume,
                'dimension_4_status': dimension_4_status
            })
            
            # 7️⃣ 技术指标原始数据 (4个字段)
            recent_5w_prices = detailed_info.get('recent_5w_prices', [])
            recent_5w_volumes = detailed_info.get('recent_5w_volumes', [])
            data_quality = detailed_info.get('data_quality', '正常')
            calculation_errors = detailed_info.get('calculation_errors', '无')
            
            record.update({
                'recent_5w_prices': str(recent_5w_prices) if recent_5w_prices else '[]',
                'recent_5w_volumes': str(recent_5w_volumes) if recent_5w_volumes else '[]',
                'data_quality': data_quality,
                'calculation_errors': calculation_errors
            })
            
            # 8️⃣ 执行状态信息 (4个字段) + 仓位变化信息 (4个字段) - 新增
            record.update({
                'signal_id': signal_id,
                'execution_status': '待执行',  # 初始状态
                'execution_reason': '',
                'execution_date': '',
                'execution_price': 0.0,
                # 仓位变化信息 (5个字段) - 新增
                'position_before_signal': 0,  # 信号前持仓数量
                'position_weight_before': 0.0,  # 信号前持仓占比
                'trade_shares': 0,  # 交易数量
                'position_after_trade': 0,  # 交易后持仓数量
                'position_weight_after': 0.0  # 交易后持仓占比
            })
            
            # 将信号ID和记录索引的映射存储起来
            record_index = len(self.signal_records)
            self.signal_id_to_index[signal_id] = record_index
            
            return record
            
        except Exception as e:
            self.logger.error(f"格式化信号记录失败: {str(e)}")
            return {}
    
    def _calculate_tech_dimensions_satisfied(self, scores: Dict, signal_type: str) -> int:
        """计算满足的技术维度数量"""
        try:
            if signal_type == 'BUY':
                dimensions = [
                    scores.get('overbought_oversold_low', False),
                    scores.get('momentum_low', False),
                    scores.get('extreme_price_volume_low', False)
                ]
            elif signal_type == 'SELL':
                dimensions = [
                    scores.get('overbought_oversold_high', False),
                    scores.get('momentum_high', False),
                    scores.get('extreme_price_volume_high', False)
                ]
            else:
                return 0
            return sum(dimensions)
        except Exception:
            return 0
    
    def _get_dimension_1_status(self, scores: Dict, signal_type: str) -> str:
        """获取维度一（价值过滤器）状态"""
        try:
            if signal_type == 'BUY':
                return '满足' if scores.get('trend_filter_low', False) else '不满足'
            elif signal_type == 'SELL':
                return '满足' if scores.get('trend_filter_high', False) else '不满足'
            else:
                return '不满足'
        except Exception:
            return '不满足'
    
    def _get_dimension_status(self, scores: Dict, dimension: str, signal_type: str) -> str:
        """获取指定维度的状态"""
        try:
            if signal_type == 'BUY':
                key = f'{dimension}_low'
                return '买入' if scores.get(key, False) else '无'
            elif signal_type == 'SELL':
                key = f'{dimension}_high'
                return '卖出' if scores.get(key, False) else '无'
            else:
                return '无'
        except Exception:
            return '无'

    def update_execution_status(self, signal_id: str, execution_status: str, 
                               execution_date: str = '', execution_price: float = 0.0, 
                               execution_reason: str = '', position_before_signal: int = 0,
                               position_weight_before: float = 0.0, trade_shares: int = 0,
                               position_after_trade: int = 0, position_weight_after: float = 0.0) -> bool:
        """
        更新信号的执行状态和仓位变化信息
        
        Args:
            signal_id: 信号唯一ID
            execution_status: 执行状态 (已执行/未执行/部分执行)
            execution_date: 实际执行日期
            execution_price: 实际执行价格
            execution_reason: 未执行原因
            position_before_signal: 信号前持仓数量
            position_weight_before: 信号前持仓占比
            trade_shares: 交易数量
            position_after_trade: 交易后持仓数量
            position_weight_after: 交易后持仓占比
            
        Returns:
            bool: 是否更新成功
        """
        try:
            if signal_id not in self.signal_id_to_index:
                self.logger.warning(f"未找到信号ID: {signal_id}")
                return False
            
            record_index = self.signal_id_to_index[signal_id]
            if record_index >= len(self.signal_records):
                self.logger.error(f"信号记录索引超出范围: {record_index}")
                return False
            
            # 更新执行状态信息
            record = self.signal_records[record_index]
            record['execution_status'] = execution_status
            record['execution_reason'] = execution_reason
            record['execution_date'] = str(execution_date)
            record['execution_price'] = round(float(execution_price), 2) if execution_price else 0.0
            
            # 更新仓位变化信息
            record['position_before_signal'] = int(position_before_signal)
            record['position_weight_before'] = round(float(position_weight_before), 4) if position_weight_before else 0.0
            record['trade_shares'] = int(trade_shares)
            record['position_after_trade'] = int(position_after_trade)
            record['position_weight_after'] = round(float(position_weight_after), 4) if position_weight_after else 0.0
            
            # 计算信号到执行的延迟
            if execution_date and execution_status == '已执行':
                try:
                    signal_date = pd.to_datetime(record['date'])
                    exec_date = pd.to_datetime(execution_date)
                    delay_days = (exec_date - signal_date).days
                    record['signal_to_execution_delay'] = delay_days
                except Exception as e:
                    self.logger.warning(f"计算执行延迟失败: {str(e)}")
                    record['signal_to_execution_delay'] = 0
            
            self.logger.info(f"✅ 更新信号执行状态: {signal_id} -> {execution_status}")
            if execution_reason:
                self.logger.info(f"   原因: {execution_reason}")
            if trade_shares != 0:
                self.logger.info(f"   交易: {trade_shares}股, 仓位: {position_before_signal} -> {position_after_trade}")
            
            return True
            
        except Exception as e:
            self.logger.error(f"更新信号执行状态失败: {str(e)}")
            return False
    
    def get_signal_id(self, stock_code: str, date: str, signal_type: str) -> str:
        """
        生成信号ID（用于外部调用）
        
        Args:
            stock_code: 股票代码
            date: 信号日期
            signal_type: 信号类型
            
        Returns:
            str: 信号唯一ID
        """
        try:
            if isinstance(date, str):
                timestamp = int(pd.Timestamp(date).timestamp())
                date_str = date.replace('-', '').replace(' ', '').replace(':', '')[:8]
            else:
                timestamp = int(pd.Timestamp(date).timestamp())
                date_str = date.strftime('%Y%m%d')
            
            return f"{stock_code}_{date_str}_{signal_type}_{timestamp}"
        except Exception as e:
            self.logger.error(f"生成信号ID失败: {str(e)}")
            return f"{stock_code}_{signal_type}_{int(pd.Timestamp.now().timestamp())}"

    def _get_stock_name(self, stock_code: str) -> str:
        """获取股票名称"""
        try:
            from utils.stock_name_mapper import get_cached_stock_mapping, get_stock_display_name
            stock_mapping = get_cached_stock_mapping()
            return get_stock_display_name(stock_code, stock_mapping)
        except Exception:
            return stock_code
    
    def export_to_csv(self) -> str:
        """
        导出CSV报告
        
        Returns:
            str: CSV文件路径
        """
        try:
            # 确保输出目录存在
            output_dir = os.path.dirname(self.output_path)
            if output_dir:  # 只有当有目录路径时才创建
                os.makedirs(output_dir, exist_ok=True)
            
            if not self.signal_records:
                self.logger.warning("没有信号记录可导出")
                return ""
            
            # 生成完整字段的CSV表头（中文）- 严格按照field_names顺序
            csv_headers = [
                # 1️⃣ 基础信息 (5个字段)
                '日期', '股票代码', '股票名称', '信号类型', '当前价格',
                
                # 2️⃣ 4维信号综合决策 (5个字段)
                '维度一状态', '技术维度满足数', '三者取二', '信号强度', '决策依据',
                
                # 执行状态信息 (4个字段)
                '执行状态', '未执行原因', '执行日期', '执行价格',
                
                # 仓位变化信息 (5个字段)
                '信号前持仓数量', '信号前持仓占比', '交易数量', '交易后持仓数量', '交易后持仓占比',
                
                # 3️⃣ 维度一：价值准入过滤器 (3个字段)
                'DCF估值', '价值比率', '价值过滤器状态',
                
                # 4️⃣ 维度二：超买超卖 (9个字段)
                '行业名称', '14周RSI', '行业买入阈值', '行业卖出阈值', 
                '行业极端买入', '行业极端卖出', 'RSI信号类型', '价格背离', '维度二状态',
                
                # 5️⃣ 维度三：动能确认 (7个字段)
                'MACD_DIF', 'MACD_DEA', 'MACD柱体', 'MACD颜色', 
                '柱体趋势', '金叉死叉状态', '维度三状态',
                
                # 6️⃣ 维度四：极端放量 (9个字段)
                '布林中轨', '布林上轨', '布林下轨', '价格布林位置',
                '当前成交量', '成交量基准', '成交量比率', '显著放量', '维度四状态',
                
                # 7️⃣ 技术指标原始数据 (4个字段)
                '最近5周价格', '最近5周成交量', '数据质量', '计算异常',
                
                # 8️⃣ 信号ID (1个字段)
                '信号ID'
            ]
            
            # 写入CSV文件
            with open(self.output_path, 'w', newline='', encoding='utf-8-sig') as csvfile:
                writer = csv.writer(csvfile)
                
                # 写入表头
                writer.writerow(csv_headers)
                
                # 写入数据行 - 严格按照field_names顺序
                for record in self.signal_records:
                    row_data = [
                        # 1️⃣ 基础信息 (5个字段)
                        record.get('date', ''),
                        record.get('stock_code', ''),
                        record.get('stock_name', ''),
                        record.get('signal_type', ''),
                        record.get('current_price', 0.0),
                        
                        # 2️⃣ 4维信号综合决策 (5个字段)
                        record.get('dimension_1_status', ''),
                        record.get('tech_dimensions_satisfied', 0),
                        record.get('three_choose_two_result', ''),
                        record.get('signal_strength', 0),
                        record.get('final_decision_basis', ''),
                        
                        # 执行状态信息 (4个字段)
                        record.get('execution_status', ''),
                        record.get('execution_reason', ''),
                        record.get('execution_date', ''),
                        record.get('execution_price', 0.0),
                        
                        # 仓位变化信息 (5个字段)
                        record.get('position_before_signal', 0),
                        record.get('position_weight_before', 0.0),
                        record.get('trade_shares', 0),
                        record.get('position_after_trade', 0),
                        record.get('position_weight_after', 0.0),
                        
                        # 3️⃣ 维度一：价值准入过滤器 (3个字段)
                        record.get('dcf_value', 0.0),
                        record.get('value_ratio', 0.0),
                        record.get('value_filter_status', ''),
                        
                        # 4️⃣ 维度二：超买超卖 (9个字段)
                        record.get('industry_name', ''),
                        record.get('rsi_14w', 0.0),
                        record.get('industry_buy_threshold', 0.0),
                        record.get('industry_sell_threshold', 0.0),
                        record.get('industry_extreme_buy', 0.0),
                        record.get('industry_extreme_sell', 0.0),
                        record.get('rsi_signal_type', ''),
                        record.get('price_divergence', ''),
                        record.get('dimension_2_status', ''),
                        
                        # 5️⃣ 维度三：动能确认
                        record.get('macd_dif', 0.0),
                        record.get('macd_dea', 0.0),
                        record.get('macd_histogram', 0.0),
                        record.get('macd_color', ''),
                        record.get('histogram_trend', ''),
                        record.get('golden_cross_status', ''),
                        record.get('dimension_3_status', ''),
                        
                        # 6️⃣ 维度四：极端放量
                        record.get('bb_middle', 0.0),
                        record.get('bb_upper', 0.0),
                        record.get('bb_lower', 0.0),
                        record.get('price_bb_position', ''),
                        record.get('current_volume', 0),
                        record.get('volume_baseline', 0),
                        record.get('volume_ratio', 0.0),
                        record.get('significant_volume', ''),
                        record.get('dimension_4_status', ''),
                        
                        # 7️⃣ 技术指标原始数据
                        record.get('recent_5w_prices', ''),
                        record.get('recent_5w_volumes', ''),
                        record.get('data_quality', ''),
                        record.get('calculation_errors', ''),
                        
                        # 8️⃣ 信号ID - 保持在最后
                        record.get('signal_id', '')
                    ]
                    writer.writerow(row_data)
            
            self.logger.info(f"📊 信号跟踪报告已生成: {self.output_path}")
            self.logger.info(f"包含 {len(self.signal_records)} 条高质量买卖信号记录，42个详细字段（32个基础字段 + 4个执行状态字段 + 5个仓位变化字段 + 1个信号ID字段）")
            
            return self.output_path
            
        except Exception as e:
            self.logger.error(f"导出CSV失败: {str(e)}")
            return ""

    def get_statistics(self) -> Dict:
        """获取信号统计信息"""
        try:
            total_signals = len(self.signal_records)
            buy_signals = sum(1 for r in self.signal_records if r.get('signal_type') == 'BUY')
            sell_signals = sum(1 for r in self.signal_records if r.get('signal_type') == 'SELL')
            
            return {
                'total_signals': total_signals,
                'buy_signals': buy_signals,
                'sell_signals': sell_signals,
                'buy_ratio': round(buy_signals / total_signals * 100, 2) if total_signals > 0 else 0,
                'sell_ratio': round(sell_signals / total_signals * 100, 2) if total_signals > 0 else 0
            }
        except Exception:
            return {'total_signals': 0, 'buy_signals': 0, 'sell_signals': 0, 'buy_ratio': 0, 'sell_ratio': 0}