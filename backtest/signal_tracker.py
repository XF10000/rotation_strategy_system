"""
信号跟踪器模块
负责记录和导出鹿鼎公区域信号策略的买卖信号详细信息
只记录BUY/SELL信号，不记录HOLD信号
"""

import csv
import logging
from datetime import datetime
from typing import Any, Dict, Optional

import pandas as pd

from config.path_manager import get_path_manager

logger = logging.getLogger(__name__)

class SignalTracker:
    """
    鹿鼎公信号跟踪器

    功能：
    - 记录通过三层递进确认的买卖信号
    - 包含~33个字段的详细区域信号信息
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
        
        # 鹿鼎公信号字段（~33个字段）
        self.field_definitions = [
            # 1. 基础信息
            'date', 'stock_code', 'stock_name', 'signal_type', 'current_price',

            # 2. 鹿鼎公区域信号核心字段
            'zone', 'valuation_zone', 'permission',
            'buy_level', 'sell_step', 'trigger_reason',

            # 3. 估值信息
            'dcf_value', 'value_ratio',

            # 4. 技术指标快照
            'rsi_14w', 'macd_dif', 'macd_dea', 'macd_histogram',
            'bb_upper', 'bb_middle', 'bb_lower', 'volume',

            # 5. 行业RSI阈值
            'industry_name', 'industry_buy_threshold', 'industry_sell_threshold',
            'industry_extreme_buy', 'industry_extreme_sell',

            # 6. 执行状态
            'execution_status', 'execution_reason', 'execution_date', 'execution_price',

            # 7. 仓位变化
            'position_before_signal', 'position_weight_before',
            'trade_shares', 'position_after_trade', 'position_weight_after',

            # 8. 信号ID
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
        self.logger.info(f"将记录 {len(self.field_definitions)} 个字段的鹿鼎公区域信号信息")
    
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
        鹿鼎公信号质量验证 — 区域确认即通过
        鹿鼎公信号已经过估值区间→价格/RSI→MACD三层递进确认，
        只需检查 signal 类型和 zone 字段有效即可。
        """
        try:
            signal_type = signal_result.get('signal', '').upper()
            zone = signal_result.get('zone', '')
            if signal_type not in ('BUY', 'SELL'):
                return False
            if not zone or zone == 'zone4_hold':
                return False
            return True
        except Exception:
            return False
    
    def _format_signal_record(self, signal_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        格式化信号记录为鹿鼎公字段格式

        Args:
            signal_data: 原始信号数据，signal_result 包含 ZoneResult 兼容字段
        """
        try:
            date = signal_data.get('date', '')
            stock_code = signal_data.get('stock_code', '')
            signal_result = signal_data.get('signal_result', {})

            signal_type = signal_result.get('signal', '')
            current_price = signal_result.get('current_price', 0.0)

            timestamp = int(pd.Timestamp(date).timestamp())
            signal_id = f"{stock_code}_{date.strftime('%Y%m%d') if hasattr(date, 'strftime') else str(date).replace('-', '').replace(' ', '').replace(':', '')[:8]}_{signal_type}_{timestamp}"

            technical_indicators = signal_result.get('technical_indicators', {})
            rsi_thresholds = signal_result.get('rsi_thresholds', {})

            # 基础信息
            record = {
                'date': str(date),
                'stock_code': str(stock_code),
                'stock_name': self._get_stock_name(stock_code),
                'signal_type': signal_type,
                'current_price': round(float(current_price), 2) if current_price else 0.0,
            }

            # 鹿鼎公区域信号核心
            record.update({
                'zone': signal_result.get('zone', ''),
                'valuation_zone': signal_result.get('valuation_zone', ''),
                'permission': signal_result.get('permission', ''),
                'buy_level': signal_result.get('buy_level') or '',
                'sell_step': signal_result.get('sell_step') or '',
                'trigger_reason': signal_result.get('reason', ''),
            })

            # 估值信息
            dcf_value = signal_result.get('dcf_value', 0.0)
            value_ratio = signal_result.get('value_price_ratio', 0.0)
            record.update({
                'dcf_value': round(float(dcf_value), 2) if dcf_value else 0.0,
                'value_ratio': round(float(value_ratio), 4) if value_ratio else 0.0,
            })

            # 技术指标快照
            rsi_14w = technical_indicators.get('rsi_14w', 50.0)
            macd_dif = technical_indicators.get('macd_dif', 0.0)
            macd_dea = technical_indicators.get('macd_dea', 0.0)
            macd_histogram = technical_indicators.get('macd_hist', 0.0)
            bb_upper = technical_indicators.get('bb_upper', current_price)
            bb_middle = technical_indicators.get('bb_middle', current_price)
            bb_lower = technical_indicators.get('bb_lower', current_price)
            volume = technical_indicators.get('volume', 0)

            record.update({
                'rsi_14w': round(float(rsi_14w), 2) if rsi_14w else 50.0,
                'macd_dif': round(float(macd_dif), 4) if macd_dif else 0.0,
                'macd_dea': round(float(macd_dea), 4) if macd_dea else 0.0,
                'macd_histogram': round(float(macd_histogram), 4) if macd_histogram else 0.0,
                'bb_upper': round(float(bb_upper), 2) if bb_upper else 0.0,
                'bb_middle': round(float(bb_middle), 2) if bb_middle else 0.0,
                'bb_lower': round(float(bb_lower), 2) if bb_lower else 0.0,
                'volume': int(volume) if volume else 0,
            })

            # 行业RSI阈值
            industry_name = signal_result.get('detailed_info', {}).get('industry_name', '')
            record.update({
                'industry_name': industry_name or '',
                'industry_buy_threshold': rsi_thresholds.get('buy_threshold', 30.0),
                'industry_sell_threshold': rsi_thresholds.get('sell_threshold', 70.0),
                'industry_extreme_buy': rsi_thresholds.get('extreme_buy_threshold', 20.0),
                'industry_extreme_sell': rsi_thresholds.get('extreme_sell_threshold', 80.0),
            })

            # 执行状态（初始为待执行）和仓位变化
            record.update({
                'signal_id': signal_id,
                'execution_status': '待执行',
                'execution_reason': '',
                'execution_date': '',
                'execution_price': 0.0,
                'position_before_signal': 0,
                'position_weight_before': 0.0,
                'trade_shares': 0,
                'position_after_trade': 0,
                'position_weight_after': 0.0,
            })

            record_index = len(self.signal_records)
            self.signal_id_to_index[signal_id] = record_index

            return record

        except Exception as e:
            self.logger.error(f"格式化信号记录失败: {str(e)}")
            return {}
    
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
    
    def export_to_csv(self, output_path: str = None) -> str:
        """
        导出CSV报告
        
        Args:
            output_path: 输出文件路径（可选，如果不提供则使用初始化时的路径）
        
        Returns:
            str: CSV文件路径
        """
        try:
            # 使用传入的路径或默认路径
            if output_path:
                self.output_path = output_path
            
            # 确保输出目录存在
            get_path_manager().get_reports_dir().mkdir(parents=True, exist_ok=True)
            
            if not self.signal_records:
                self.logger.warning("没有信号记录可导出")
                return ""
            
            # 生成完整字段的CSV表头（中文）- 鹿鼎公区域信号格式
            csv_headers = [
                # 1. 基础信息
                '日期', '股票代码', '股票名称', '信号类型', '当前价格',

                # 2. 鹿鼎公区域信号核心
                '区域', '估值区间', '操作权限', '买入级别', '卖出步骤', '触发原因',

                # 3. 估值信息
                'DCF估值', '价值比率',

                # 4. 技术指标快照
                '14周RSI', 'MACD_DIF', 'MACD_DEA', 'MACD柱体',
                '布林上轨', '布林中轨', '布林下轨', '成交量',

                # 5. 行业RSI阈值
                '行业名称', '行业买入阈值', '行业卖出阈值', '行业极端买入', '行业极端卖出',

                # 6. 执行状态
                '执行状态', '未执行原因', '执行日期', '执行价格',

                # 7. 仓位变化
                '信号前持仓数', '信号前持仓占比', '交易股数', '交易后持仓数', '交易后持仓占比',

                # 8. 信号ID
                '信号ID'
            ]
            
            # 写入CSV文件
            with open(self.output_path, 'w', newline='', encoding='utf-8-sig') as csvfile:
                writer = csv.writer(csvfile)
                
                # 写入表头
                writer.writerow(csv_headers)
                
                # 写入数据行 - 鹿鼎公字段顺序
                for record in self.signal_records:
                    row_data = [
                        # 1. 基础信息
                        record.get('date', ''),
                        record.get('stock_code', ''),
                        record.get('stock_name', ''),
                        record.get('signal_type', ''),
                        record.get('current_price', 0.0),

                        # 2. 鹿鼎公区域信号核心
                        record.get('zone', ''),
                        record.get('valuation_zone', ''),
                        record.get('permission', ''),
                        record.get('buy_level') or '',
                        record.get('sell_step') or '',
                        record.get('trigger_reason', ''),

                        # 3. 估值信息
                        record.get('dcf_value', 0.0),
                        record.get('value_ratio', 0.0),

                        # 4. 技术指标快照
                        record.get('rsi_14w', 0.0),
                        record.get('macd_dif', 0.0),
                        record.get('macd_dea', 0.0),
                        record.get('macd_histogram', 0.0),
                        record.get('bb_upper', 0.0),
                        record.get('bb_middle', 0.0),
                        record.get('bb_lower', 0.0),
                        record.get('volume', 0),

                        # 5. 行业RSI阈值
                        record.get('industry_name', ''),
                        record.get('industry_buy_threshold', 0.0),
                        record.get('industry_sell_threshold', 0.0),
                        record.get('industry_extreme_buy', 0.0),
                        record.get('industry_extreme_sell', 0.0),

                        # 6. 执行状态
                        record.get('execution_status', ''),
                        record.get('execution_reason', ''),
                        record.get('execution_date', ''),
                        record.get('execution_price', 0.0),

                        # 7. 仓位变化
                        record.get('position_before_signal', 0),
                        record.get('position_weight_before', 0.0),
                        record.get('trade_shares', 0),
                        record.get('position_after_trade', 0),
                        record.get('position_weight_after', 0.0),

                        # 8. 信号ID
                        record.get('signal_id', '')
                    ]
                    writer.writerow(row_data)
            
            self.logger.info(f"📊 信号跟踪报告已生成: {self.output_path}")
            self.logger.info(f"包含 {len(self.signal_records)} 条鹿鼎公信号记录，{len(csv_headers)}个字段")
            
            return self.output_path
            
        except Exception as e:
            self.logger.error(f"导出CSV失败: {str(e)}")
            return ""

    def get_statistics(self) -> Dict:
        """获取信号统计信息（鹿鼎公区域信号）"""
        try:
            total_signals = len(self.signal_records)
            buy_signals = sum(1 for r in self.signal_records if r.get('signal_type') == 'BUY')
            sell_signals = sum(1 for r in self.signal_records if r.get('signal_type') == 'SELL')
            executed = sum(1 for r in self.signal_records if r.get('execution_status') == '已执行')

            # 区域分布统计
            zones = {'zone1_stop_falling': 0, 'zone2_accumulate': 0, 'zone3_excited': 0, 'zone4_hold': 0}
            for r in self.signal_records:
                z = r.get('zone', '')
                if z in zones:
                    zones[z] += 1

            # 估值区间分布
            valuations = {}
            for r in self.signal_records:
                vz = r.get('valuation_zone', '')
                if vz:
                    valuations[vz] = valuations.get(vz, 0) + 1

            # 买入级别/卖出步骤分布
            buy_levels = {'normal': 0, 'urgent': 0}
            sell_steps = {'pre_sell': 0, 'first_sell': 0, 'second_sell': 0}
            for r in self.signal_records:
                bl = r.get('buy_level')
                if bl:
                    buy_levels[bl] = buy_levels.get(bl, 0) + 1
                ss = r.get('sell_step')
                if ss:
                    sell_steps[ss] = sell_steps.get(ss, 0) + 1

            return {
                'total_signals': total_signals,
                'buy_signals': buy_signals,
                'sell_signals': sell_signals,
                'executed': executed,
                'buy_ratio': round(buy_signals / total_signals * 100, 2) if total_signals > 0 else 0,
                'sell_ratio': round(sell_signals / total_signals * 100, 2) if total_signals > 0 else 0,
                'zones': zones,
                'valuations': valuations,
                'buy_levels': buy_levels,
                'sell_steps': sell_steps
            }
        except Exception:
            return {'total_signals': 0, 'buy_signals': 0, 'sell_signals': 0, 'buy_ratio': 0, 'sell_ratio': 0}