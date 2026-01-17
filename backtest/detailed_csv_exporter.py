import csv
import logging
import os
import sys
from datetime import datetime

# 添加项目根目录到Python路径
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from config.industry_rsi_loader import get_rsi_loader
from utils.industry_classifier import get_stock_industry_auto
from utils.stock_name_mapper import get_cached_stock_mapping, get_stock_display_name

logger = logging.getLogger(__name__)

class DetailedCSVExporter:
    """详细CSV交易记录导出器"""
    
    def __init__(self, dcf_values=None):
        """初始化CSV导出器
        
        Args:
            dcf_values: DCF估值字典 {股票代码: 估值}
        """
        # 加载股票名称映射
        self.stock_mapping = get_cached_stock_mapping()
        self.dcf_values = dcf_values or {}
        self.csv_headers = [
            '日期', '交易类型', '股票名称', '交易股票数量', '交易后持仓数量', 
            '交易价格', 'DCF估值', '价值比(%)', '估值状态', '价值比描述',
            '交易金额', '手续费', '交易原因', '收盘价',
            'RSI14', 'MACD_DIF', 'MACD_DEA', 'MACD_HIST',
            '布林上轨', '布林中轨', '布林下轨', '成交量', '量能倍数', '布林带位置',
            '价值比过滤器', '超买超卖信号', 'RSI 极端信号', '动能确认', '极端价格量能', '满足维度数', '触发原因',
            '行业', 'RSI超买阈值', 'RSI超卖阈值', 'RSI极端超买阈值', 'RSI极端超卖阈值'
        ]
        logger.info(f"详细CSV导出器初始化完成，DCF估值数量: {len(self.dcf_values)}")
        
        # 分红配股事件CSV表头
        self.dividend_csv_headers = [
            '日期', '股票代码', '股票名称', '事件类型', '映射日期',
            '分红金额(元/股)', '送股比例(10送X)', '转增比例(10转X)', '配股比例(10配X)', '配股价格(元)',
            '事件前持股数', '事件后持股数', '现金变化(元)', '备注'
        ]
    
    def export_trading_records(self, trading_records, output_dir='reports'):
        """
        导出详细的交易记录到CSV文件
        
        Args:
            trading_records: 交易记录列表
            output_dir: 输出目录
            
        Returns:
            str: CSV文件路径
        """
        try:
            # 确保输出目录存在
            os.makedirs(output_dir, exist_ok=True)
            
            # 生成文件名
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            csv_filename = f"detailed_trading_records_{timestamp}.csv"
            csv_path = os.path.join(output_dir, csv_filename)
            
            logger.info(f"开始导出CSV，交易记录数量: {len(trading_records)}")
            
            # 写入CSV文件
            with open(csv_path, 'w', newline='', encoding='utf-8-sig') as csvfile:
                writer = csv.writer(csvfile)
                
                # 写入表头
                writer.writerow(self.csv_headers)
                
                # 写入交易记录
                valid_records = 0
                for i, record in enumerate(trading_records):
                    try:
                        logger.info(f"处理第{i+1}条记录: {record.get('date', 'N/A')} {record.get('type', 'N/A')} {record.get('stock_code', 'N/A')}")
                        row_data = self._format_trading_record(record)
                        if row_data and any(row_data):  # 确保不是空行
                            writer.writerow(row_data)
                            valid_records += 1
                    except Exception as e:
                        logger.error(f"处理第{i+1}条记录失败: {str(e)}")
                        continue
            
            logger.info(f"详细CSV文件已生成: {csv_path}")
            logger.info(f"包含 {valid_records} 条详细交易记录")
            
            return csv_path
            
        except Exception as e:
            logger.error(f"CSV导出失败: {str(e)}")
            return None
    
    def _format_trading_record(self, record):
        """格式化单条交易记录"""
        try:
            # 基础交易信息 - 适配transactions数据格式
            date = record.get('date', '')
            if isinstance(date, str):
                # 如果是字符串，尝试转换为日期格式
                try:
                    from datetime import datetime
                    date_obj = datetime.strptime(date, '%Y-%m-%d')
                    date = date_obj.strftime('%Y/%m/%d')
                except:
                    date = date.replace('-', '/')
            else:
                date = str(date)
            
            action = '买入' if record.get('type') == 'BUY' else '卖出'
            stock_code = record.get('stock_code', '')
            # 使用股票名称显示
            symbol = get_stock_display_name(stock_code, self.stock_mapping)
            quantity = record.get('shares', 0)
            price = round(record.get('price', 0), 2)
            amount = round(record.get('gross_amount', price * quantity), 2)
            commission = round(record.get('transaction_cost', record.get('fee', 0)), 2)
            reason = record.get('reason', '策略信号')
            close_price = price  # 使用交易价格作为收盘价
            
            # 从record中获取技术指标数据 - 直接使用已计算的数据
            indicators = record.get('technical_indicators', {})
            signal_details = record.get('signal_details', {})
            
            logger.info(f"🔍 交易记录技术指标: {indicators}")
            logger.info(f"🔍 交易记录信号详情: {signal_details}")
            
            # 技术指标 - 智能获取，优先使用真实计算值
            def safe_get_indicator(key, default=0.0, decimal_places=2):
                """智能获取技术指标值，优先保持真实计算数据"""
                try:
                    value = indicators.get(key, None)
                    logger.info(f"🔍 获取指标 {key}: 原始值={value}, 类型={type(value)}")
                    
                    # 如果有有效的数值，直接使用
                    if value is not None:
                        # 检查是否为NaN
                        import numpy as np
                        import pandas as pd

                        # 字符串'nan'的情况
                        if isinstance(value, str) and value.lower() == 'nan':
                            logger.warning(f"指标 {key} 为字符串'nan'，使用默认值 {default}")
                            return default
                        
                        # 数值类型的NaN检查
                        try:
                            float_value = float(value)
                            if pd.isna(float_value) or np.isnan(float_value):
                                logger.warning(f"指标 {key} 为数值NaN，使用默认值 {default}")
                                return default
                            
                            # 有效数值，保持原值
                            result = round(float_value, decimal_places)
                            logger.info(f"✅ 指标 {key} 使用真实值: {result}")
                            return result
                            
                        except (ValueError, TypeError):
                            logger.warning(f"指标 {key} 无法转换为数值，使用默认值 {default}")
                            return default
                    
                    # 完全没有数据的情况
                    logger.warning(f"指标 {key} 为None，使用默认值 {default}")
                    return default
                    
                except Exception as e:
                    logger.error(f"获取指标 {key} 时发生异常: {e}，使用默认值 {default}")
                    return default
            
            # EMA20和EMA60字段已移除（V1.1策略不再使用EMA趋势过滤器）
            rsi14 = safe_get_indicator('rsi_14w', 50, 2)
            macd_dif = safe_get_indicator('macd_dif', 0, 4)
            macd_dea = safe_get_indicator('macd_dea', 0, 4)
            macd_hist = safe_get_indicator('macd_hist', 0, 4)
            bb_upper = safe_get_indicator('bb_upper', 0, 2)
            bb_middle = safe_get_indicator('bb_middle', 0, 2)
            bb_lower = safe_get_indicator('bb_lower', 0, 2)
            volume = int(safe_get_indicator('volume', 0, 0))
            
            # 计算量能倍数 - 安全处理
            volume_4w_avg = safe_get_indicator('volume_4w_avg', 1, 0)  # 默认为1避免除零
            volume_ratio = round(volume / volume_4w_avg, 2) if volume_4w_avg > 0 else 0
            
            # 布林带位置
            bb_position = self._get_bb_position(close_price, bb_upper, bb_middle, bb_lower)
            
            # 信号分析 - 根据交易类型匹配对应的信号方向
            scores = signal_details.get('scores', {})
            action = record['type'].upper()
            
            if action == 'BUY':
                # 买入交易：只计算支持买入的信号
                trend_filter = '✓' if scores.get('trend_filter_low') else '✗'
                overbought_oversold = '✓' if scores.get('overbought_oversold_low') else '✗'
                momentum_confirm = '✓' if scores.get('momentum_low') else '✗'
                extreme_price_volume = '✓' if scores.get('extreme_price_volume_low') else '✗'
                
                # 计算满足维度数 - 只计算支持买入的维度
                actual_dimensions_met = sum([
                    1 if scores.get('trend_filter_low') else 0,
                    1 if scores.get('overbought_oversold_low') else 0,
                    1 if scores.get('momentum_low') else 0,
                    1 if scores.get('extreme_price_volume_low') else 0
                ])
            else:  # SELL
                # 卖出交易：只计算支持卖出的信号
                trend_filter = '✓' if scores.get('trend_filter_high') else '✗'
                overbought_oversold = '✓' if scores.get('overbought_oversold_high') else '✗'
                momentum_confirm = '✓' if scores.get('momentum_high') else '✗'
                extreme_price_volume = '✓' if scores.get('extreme_price_volume_high') else '✗'
                
                # 计算满足维度数 - 只计算支持卖出的维度
                actual_dimensions_met = sum([
                    1 if scores.get('trend_filter_high') else 0,
                    1 if scores.get('overbought_oversold_high') else 0,
                    1 if scores.get('momentum_high') else 0,
                    1 if scores.get('extreme_price_volume_high') else 0
                ])
            dimensions_text = f"{actual_dimensions_met}/4"
            
            # 触发原因 - 直接使用已有的原因
            trigger_reason = signal_details.get('reason', f"{action}信号：满足{actual_dimensions_met}个维度")
            
            # 获取交易后持仓数量
            position_after = record.get('position_after_trade', 0)
            
            # 获取价值比相关数据
            # 优先从technical_indicators获取DCF估值（最准确）
            dcf_value = indicators.get('dcf_value', 0)
            if not dcf_value or dcf_value <= 0:
                # 回退到self.dcf_values
                dcf_value = self.dcf_values.get(symbol, 0)
            if not dcf_value or dcf_value <= 0:
                # 最后回退到record
                dcf_value = record.get('dcf_value', 0)
            
            # 计算价值比
            if dcf_value > 0:
                pvr = (close_price / dcf_value) * 100
                pvr_display = f"{pvr:.1f}"
                dcf_value_display = f"{dcf_value:.2f}"
                
                # 判断估值状态
                pvr_ratio = close_price / dcf_value
                if pvr_ratio <= 0.6:
                    pvr_status = "极度低估"
                elif pvr_ratio <= 0.7:
                    pvr_status = "明显低估"
                elif pvr_ratio <= 0.8:
                    pvr_status = "轻度低估"
                elif pvr_ratio <= 1.0:
                    pvr_status = "合理区间"
                elif pvr_ratio <= 1.2:
                    pvr_status = "轻度高估"
                else:
                    pvr_status = "极度高估"
                pvr_description = f"价值比{pvr_ratio:.2f}"
            else:
                pvr_display = "无数据"
                dcf_value_display = "无数据"
                pvr_status = record.get('pvr_status', '')
                pvr_description = record.get('pvr_description', '')
            
            # 获取行业信息和RSI阈值 - 使用动态RSI阈值系统
            try:
                # 优先从technical_indicators获取行业信息
                industry = indicators.get('industry', '')
                
                # 从交易记录中获取实际使用的RSI阈值（如果有的话）
                actual_thresholds = record.get('rsi_thresholds', {})
                if actual_thresholds:
                    # 使用实际交易时使用的阈值
                    overbought_threshold = actual_thresholds.get('sell_threshold', 70)
                    oversold_threshold = actual_thresholds.get('buy_threshold', 30)
                    extreme_overbought_threshold = actual_thresholds.get('extreme_sell_threshold', 80)
                    extreme_oversold_threshold = actual_thresholds.get('extreme_buy_threshold', 20)
                    if not industry:
                        industry = actual_thresholds.get('industry_name', '未知')
                    logger.info(f"✅ 使用交易记录中的动态RSI阈值: 买入≤{oversold_threshold}, 卖出≥{overbought_threshold}, 极端买入≤{extreme_oversold_threshold}, 极端卖出≥{extreme_overbought_threshold}, 行业={industry}")
                else:
                    # 回退到旧方法
                    if not industry:
                        industry = get_stock_industry_auto(symbol)
                    if not industry:
                        industry = '未知'
                    
                    # 获取RSI阈值 - 使用旧的配置加载器作为回退
                    rsi_loader = get_rsi_loader()
                    rsi_thresholds = rsi_loader.get_rsi_thresholds(industry)
                    overbought_threshold = rsi_thresholds.get('overbought', 70)
                    oversold_threshold = rsi_thresholds.get('oversold', 30)
                    extreme_overbought_threshold = rsi_thresholds.get('extreme_overbought', 80)
                    extreme_oversold_threshold = rsi_thresholds.get('extreme_oversold', 20)
                    logger.warning(f"⚠️ 交易记录中无动态RSI阈值，使用回退方法: {overbought_threshold}/{oversold_threshold}, 极端: {extreme_overbought_threshold}/{extreme_oversold_threshold}")
                
            except Exception as e:
                logger.warning(f"获取股票{symbol}行业信息或RSI阈值失败: {str(e)}")
                industry = '未知'
                overbought_threshold = 70
                oversold_threshold = 30
                extreme_overbought_threshold = 80
                extreme_oversold_threshold = 20
            
            # 计算RSI极端信号
            rsi_extreme_signal = '✗'
            if rsi14 is not None and rsi14 != '':
                try:
                    rsi_value = float(rsi14)
                    if rsi_value >= extreme_overbought_threshold or rsi_value <= extreme_oversold_threshold:
                        rsi_extreme_signal = '✓'
                        logger.debug(f"RSI极端信号触发: RSI={rsi_value:.2f}, 极端阈值=[{extreme_oversold_threshold}, {extreme_overbought_threshold}]")
                except (ValueError, TypeError):
                    logger.warning(f"RSI值格式错误，无法判断极端信号: {rsi14}")
            
            return [
                date, action, symbol, quantity, position_after, 
                price, dcf_value, pvr_display, pvr_status, pvr_description,
                amount, commission, reason, close_price,
                rsi14, macd_dif, macd_dea, macd_hist,
                bb_upper, bb_middle, bb_lower, volume, volume_ratio, bb_position,
                trend_filter, overbought_oversold, rsi_extreme_signal, momentum_confirm, extreme_price_volume, 
                dimensions_text, trigger_reason,
                industry, overbought_threshold, oversold_threshold, extreme_overbought_threshold, extreme_oversold_threshold
            ]
            
        except Exception as e:
            logger.error(f"格式化交易记录失败: {str(e)}")
            logger.error(f"记录内容: {record}")
            # 返回空行以避免程序崩溃
            return [''] * len(self.csv_headers)
    
    def _calculate_trend_filter(self, price, ema20):
        """计算趋势过滤器信号"""
        if price > 0 and ema20 > 0:
            return '✓' if price > ema20 else '✗'
        return '✗'
    
    def _calculate_rsi_signal(self, rsi, action):
        """计算RSI信号"""
        if action == '买入':
            return '✓' if rsi < 30 else '✗'
        else:
            return '✓' if rsi > 70 else '✗'
    
    def _calculate_macd_signal(self, macd_dif, macd_dea):
        """计算MACD信号"""
        if macd_dif != 0 and macd_dea != 0:
            return '✓' if macd_dif > macd_dea else '✗'
        return '✗'
    
    def _calculate_volume_signal(self, volume_ratio):
        """计算量能信号"""
        return '✓' if volume_ratio > 1.2 else '✗'
    
    def _get_bb_position(self, price, bb_upper, bb_middle, bb_lower):
        """判断价格在布林带中的位置"""
        if price == 0 or bb_upper == 0:
            return '未知'
        
        if price > bb_upper:
            return '上轨之上'
        elif price < bb_lower:
            return '下轨之下'
        else:
            return '轨道之间'
    
    def export_dividend_events(self, dividend_events, output_dir='reports'):
        """
        导出分红配股事件到CSV文件
        
        Args:
            dividend_events: 分红配股事件列表
            output_dir: 输出目录
            
        Returns:
            str: CSV文件路径
        """
        try:
            # 确保输出目录存在
            os.makedirs(output_dir, exist_ok=True)
            
            # 生成文件名
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            csv_filename = f"dividend_allotment_events_{timestamp}.csv"
            csv_path = os.path.join(output_dir, csv_filename)
            
            logger.info(f"开始导出分红配股事件CSV，事件数量: {len(dividend_events)}")
            
            # 写入CSV文件
            with open(csv_path, 'w', newline='', encoding='utf-8-sig') as csvfile:
                writer = csv.writer(csvfile)
                
                # 写入表头
                writer.writerow(self.dividend_csv_headers)
                
                # 写入分红配股事件
                valid_events = 0
                for i, event in enumerate(dividend_events):
                    try:
                        logger.debug(f"处理第{i+1}个事件: {event.get('date', 'N/A')} {event.get('stock_code', 'N/A')}")
                        row_data = self._format_dividend_event(event)
                        if row_data and any(str(x).strip() for x in row_data):  # 确保不是空行
                            writer.writerow(row_data)
                            valid_events += 1
                    except Exception as e:
                        logger.error(f"处理第{i+1}个事件失败: {str(e)}")
                        continue
            
            logger.info(f"分红配股事件CSV文件已生成: {csv_path}")
            logger.info(f"包含 {valid_events} 个有效事件记录")
            
            return csv_path
            
        except Exception as e:
            logger.error(f"分红配股事件CSV导出失败: {str(e)}")
            return None
    
    def _format_dividend_event(self, event):
        """
        格式化分红配股事件为CSV行数据
        
        Args:
            event: 分红配股事件字典
            
        Returns:
            list: CSV行数据
        """
        try:
            # 获取基本信息
            date = event.get('date', '')
            stock_code = event.get('stock_code', '')
            mapped_date = event.get('mapped_date', '')
            
            # 获取股票名称
            stock_name = get_stock_display_name(stock_code, self.stock_mapping)
            
            # 分红配股信息
            dividend_amount = event.get('dividend_amount', 0)
            bonus_ratio = event.get('bonus_ratio', 0)
            transfer_ratio = event.get('transfer_ratio', 0)
            allotment_ratio = event.get('allotment_ratio', 0)
            allotment_price = event.get('allotment_price', 0)
            
            # 持股数变化
            shares_before = event.get('shares_before', 0)
            shares_after = event.get('shares_after', 0)
            cash_change = event.get('cash_change', 0)
            
            # 确定事件类型
            event_types = []
            if dividend_amount > 0:
                event_types.append('分红')
            if bonus_ratio > 0:
                event_types.append('送股')
            if transfer_ratio > 0:
                event_types.append('转增')
            if allotment_ratio > 0:
                event_types.append('配股')
            
            event_type = '+'.join(event_types) if event_types else '无事件'
            
            # 生成备注
            remarks = []
            if dividend_amount > 0:
                remarks.append(f'每股分红{dividend_amount:.3f}元')
            if bonus_ratio > 0:
                remarks.append(f'10送{bonus_ratio}股')
            if transfer_ratio > 0:
                remarks.append(f'10转{transfer_ratio}股')
            if allotment_ratio > 0:
                remarks.append(f'10配{allotment_ratio}股，配股价{allotment_price:.2f}元')
            
            remark = '; '.join(remarks) if remarks else '无特殊事件'
            
            # 返回格式化的行数据
            return [
                date, stock_code, stock_name, event_type, mapped_date,
                f'{dividend_amount:.3f}' if dividend_amount > 0 else '0.000',
                f'{bonus_ratio:.1f}' if bonus_ratio > 0 else '0.0',
                f'{transfer_ratio:.1f}' if transfer_ratio > 0 else '0.0',
                f'{allotment_ratio:.1f}' if allotment_ratio > 0 else '0.0',
                f'{allotment_price:.2f}' if allotment_price > 0 else '0.00',
                f'{shares_before:.0f}',
                f'{shares_after:.0f}',
                f'{cash_change:.2f}',
                remark
            ]
            
        except Exception as e:
            logger.error(f"格式化分红配股事件失败: {str(e)}")
            logger.error(f"事件内容: {event}")
            # 返回空行以避免程序崩溃
            return [''] * len(self.dividend_csv_headers)