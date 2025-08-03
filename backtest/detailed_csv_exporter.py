import csv
import os
import sys
from datetime import datetime
import logging

# 添加项目根目录到Python路径
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from utils.industry_classifier import get_stock_industry_auto
from config.industry_rsi_loader import get_rsi_loader
from utils.stock_name_mapper import get_cached_stock_mapping, get_stock_display_name

logger = logging.getLogger(__name__)

class DetailedCSVExporter:
    """详细CSV交易记录导出器"""
    
    def __init__(self):
        """初始化CSV导出器"""
        # 加载股票名称映射
        self.stock_mapping = get_cached_stock_mapping()
        self.csv_headers = [
            '日期', '交易类型', '股票名称', '交易股票数量', '交易后持仓数量', 
            '交易价格', 'DCF估值', '价值比(%)', '估值状态', '价值比描述',
            '交易金额', '手续费', '交易原因', '收盘价',
            'RSI14', 'MACD_DIF', 'MACD_DEA', 'MACD_HIST',
            '布林上轨', '布林中轨', '布林下轨', '成交量', '量能倍数', '布林带位置',
            '价值比过滤器', '超买超卖信号', '动能确认', '极端价格量能', '满足维度数', '触发原因',
            '行业', 'RSI超买阈值', 'RSI超卖阈值'
        ]
        logger.info("详细CSV导出器初始化完成")
    
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
                        import pandas as pd
                        import numpy as np
                        
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
            
            # 信号分析 - 直接使用已有的信号详情
            dimension_status = signal_details.get('dimension_status', {})
            trend_filter = dimension_status.get('trend_filter', '✗')
            overbought_oversold = dimension_status.get('rsi_signal', '✗')
            momentum_confirm = dimension_status.get('macd_signal', '✗')
            extreme_price_volume = dimension_status.get('bollinger_volume', '✗')
            
            # 计算满足维度数
            dimensions = [trend_filter, overbought_oversold, momentum_confirm, extreme_price_volume]
            dimensions_met = sum(1 for d in dimensions if d == '✓')
            dimensions_text = f"{dimensions_met}/4"
            
            # 触发原因 - 直接使用已有的原因
            trigger_reason = signal_details.get('reason', f"{action}信号：满足{dimensions_met}个维度")
            
            # 获取交易后持仓数量
            position_after = record.get('position_after_trade', 0)
            
            # 获取价值比相关数据
            dcf_value = record.get('dcf_value', 0)
            pvr = record.get('price_to_value_ratio')
            pvr_status = record.get('pvr_status', '')
            pvr_description = record.get('pvr_description', '')
            
            # 格式化价值比显示
            if pvr is not None:
                pvr_display = f"{pvr:.1f}"
            else:
                pvr_display = "无数据"
            
            if not dcf_value:
                dcf_value = "无数据"
            else:
                dcf_value = f"{dcf_value:.2f}"
            
            # 获取行业信息和RSI阈值
            try:
                industry = get_stock_industry_auto(symbol)
                if not industry:
                    industry = '未知'
                
                # 获取RSI阈值 - 使用新的CSV配置加载器
                rsi_loader = get_rsi_loader()
                rsi_thresholds = rsi_loader.get_rsi_thresholds(industry)
                overbought_threshold = rsi_thresholds.get('overbought', 70)
                oversold_threshold = rsi_thresholds.get('oversold', 30)
                
            except Exception as e:
                logger.warning(f"获取股票{symbol}行业信息或RSI阈值失败: {str(e)}")
                industry = '未知'
                overbought_threshold = 70
                oversold_threshold = 30
            
            return [
                date, action, symbol, quantity, position_after, 
                price, dcf_value, pvr_display, pvr_status, pvr_description,
                amount, commission, reason, close_price,
                rsi14, macd_dif, macd_dea, macd_hist,
                bb_upper, bb_middle, bb_lower, volume, volume_ratio, bb_position,
                trend_filter, overbought_oversold, momentum_confirm, extreme_price_volume, 
                dimensions_text, trigger_reason,
                industry, overbought_threshold, oversold_threshold
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