#!/usr/bin/env python3
"""
股票信号分析工具
完全复用main.py的数据获取和计算逻辑，确保结果一致性
支持分析指定股票在特定日期范围内的4维信号详情
"""

import pandas as pd
import numpy as np
import logging
import argparse
import sys
import os
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple

# 添加项目路径
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

# 导入与main.py完全相同的组件
from backtest.backtest_engine import BacktestEngine
from strategy.signal_generator import SignalGenerator
from data.data_processor import DataProcessor
from config.csv_config_loader import create_csv_config
from utils.industry_classifier import get_stock_industry_auto

# 设置日志
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

class StockSignalAnalyzer:
    """股票信号分析器 - 完全复用BacktestEngine的逻辑"""
    
    def __init__(self):
        """初始化分析器"""
        self.config = None
        self.backtest_engine = None
        self.dcf_values = {}
        self.portfolio_df = None
        
    def load_config(self):
        """加载配置 - 与main.py完全相同"""
        try:
            # 加载CSV配置
            self.config = create_csv_config()
            logger.info("✅ 配置加载成功")
            
            # 读取投资组合配置，获取DCF估值
            self.portfolio_df = pd.read_csv('Input/portfolio_config.csv', encoding='utf-8-sig')
            
            # 提取DCF估值数据
            for _, row in self.portfolio_df.iterrows():
                stock_code = str(row['Stock_number']).strip()
                if stock_code != 'CASH' and pd.notna(row['DCF_value_per_share']):
                    self.dcf_values[stock_code] = float(row['DCF_value_per_share'])
            logger.info(f"✅ 加载DCF估值数据: {len(self.dcf_values)} 只股票")
            
            return True
            
        except Exception as e:
            logger.error(f"❌ 配置加载失败: {e}")
            return False
    
    def initialize_backtest_engine(self) -> bool:
        """初始化回测引擎"""
        try:
            # DCF数据会在BacktestEngine内部自动加载
            self.backtest_engine = BacktestEngine(config=self.config)
            logger.info("✅ 回测引擎初始化成功")
            return True
            
        except Exception as e:
            logger.error(f"❌ 回测引擎初始化失败: {e}")
            return False
    
    def _analyze_macd_momentum_detail(self, signal_result: Dict, signal_type: str) -> str:
        """分析MACD动能确认的详细原因"""
        try:
            indicators = signal_result.get('technical_indicators', {})
            macd_hist = indicators.get('macd_hist', 0)
            macd_dif = indicators.get('macd_dif', 0)
            macd_dea = indicators.get('macd_dea', 0)
            
            if signal_type == 'sell':
                # 卖出信号分析
                if macd_hist < 0:
                    return f"MACD前期红柱缩短+当前转绿 (HIST={macd_hist:.4f})"
                elif macd_dif < macd_dea:
                    return f"MACD死叉 (DIF={macd_dif:.4f} < DEA={macd_dea:.4f})"
                else:
                    return f"MACD红柱连续缩短 (HIST={macd_hist:.4f})"
            
            else:  # buy
                # 买入信号分析
                if macd_hist > 0:
                    return f"MACD前期绿柱缩短+当前转红 (HIST={macd_hist:.4f})"
                elif macd_dif > macd_dea:
                    return f"MACD金叉 (DIF={macd_dif:.4f} > DEA={macd_dea:.4f})"
                else:
                    return f"MACD绿柱连续缩短 (HIST={macd_hist:.4f})"
                    
        except Exception as e:
            return f"MACD分析错误: {e}"
    
    def get_stock_data(self, stock_code: str, start_date: str, end_date: str) -> Optional[pd.DataFrame]:
        """获取股票数据 - 完全复用BacktestEngine的数据获取逻辑"""
        try:
            # 扩展时间范围以确保技术指标计算有足够数据
            start_dt = pd.to_datetime(start_date)
            extended_start = start_dt - timedelta(weeks=80)  # 向前扩展80周，确保有足够数据
            
            logger.info(f"📊 获取股票 {stock_code} 数据...")
            logger.info(f"   原始时间范围: {start_date} 至 {end_date}")
            logger.info(f"   扩展时间范围: {extended_start.date()} 至 {end_date}")
            
            # 使用BacktestEngine的数据获取方法
            stock_data = self.backtest_engine._get_cached_or_fetch_data(
                stock_code, 
                str(extended_start.date()), 
                end_date,
                period='weekly'  # 使用周线数据，与主程序保持一致
            )
            
            if stock_data is None or stock_data.empty:
                logger.error(f"❌ 未能获取股票 {stock_code} 的数据")
                return None
            
            logger.info(f"✅ 获取数据成功: {len(stock_data)} 条记录")
            logger.info(f"   数据时间范围: {stock_data.index[0].date()} 至 {stock_data.index[-1].date()}")
            
            return stock_data
            
        except Exception as e:
            logger.error(f"❌ 获取股票数据失败: {e}")
            import traceback
            traceback.print_exc()
            return None
    
    def analyze_signals(self, stock_code: str, stock_data: pd.DataFrame, 
                       target_dates: List[str]) -> List[Dict]:
        """分析信号 - 完全复用SignalGenerator的逻辑"""
        results = []
        
        try:
            # 获取股票的DCF估值
            dcf_value = self.dcf_values.get(stock_code, 0)
            if dcf_value == 0:
                logger.warning(f"⚠️ 股票 {stock_code} 未找到DCF估值")
            
            # 获取股票行业信息
            stock_industry = None
            for _, row in self.portfolio_df.iterrows():
                if str(row['Stock_number']).strip() == stock_code:
                    stock_industry = row['Industry']
                    break
            
            logger.info(f"📈 股票信息: {stock_code}")
            logger.info(f"   DCF估值: {dcf_value} 元/股")
            logger.info(f"   所属行业: {stock_industry}")
            
            # 使用与BacktestEngine相同的SignalGenerator初始化逻辑
            signal_generator = self.backtest_engine.signal_generator
            
            for target_date in target_dates:
                logger.info(f"\n🎯 分析日期: {target_date}")
                
                # 找到目标日期或最接近的日期
                target_dt = pd.to_datetime(target_date)
                available_dates = stock_data.index[stock_data.index <= target_dt]
                
                if len(available_dates) == 0:
                    logger.warning(f"❌ 没有找到 {target_date} 之前的数据")
                    continue
                
                actual_date = available_dates[-1]
                logger.info(f"   实际分析日期: {actual_date.date()}")
                
                # 获取到该日期为止的所有数据
                data_until_date = stock_data.loc[:actual_date].copy()
                
                if len(data_until_date) < 60:
                    logger.warning(f"❌ 数据不足，只有 {len(data_until_date)} 条记录")
                    continue
                
                # 生成信号 - 使用与main.py完全相同的方法
                signal_result = signal_generator.generate_signal(stock_code, data_until_date)
                
                # 获取当日数据
                current_data = data_until_date.iloc[-1]
                
                # 计算价值比
                price_value_ratio = 0
                if dcf_value > 0:
                    price_value_ratio = (current_data['close'] / dcf_value) * 100
                
                # 整理分析结果
                analysis_result = {
                    'date': actual_date.date(),
                    'target_date': target_date,
                    'stock_code': stock_code,
                    'stock_industry': stock_industry,
                    'current_price': current_data['close'],
                    'volume': current_data['volume'],
                    'dcf_value': dcf_value,
                    'price_value_ratio': price_value_ratio,
                    'signal_result': signal_result
                }
                
                results.append(analysis_result)
                
        except Exception as e:
            logger.error(f"❌ 信号分析失败: {e}")
            import traceback
            traceback.print_exc()
        
        return results
    
    def format_terminal_output(self, results: List[Dict]) -> str:
        """格式化终端输出"""
        if not results:
            return "❌ 没有分析结果"
        
        output_lines = []
        output_lines.append("=" * 100)
        output_lines.append("🔍 股票信号分析报告")
        output_lines.append("=" * 100)
        
        for result in results:
            signal_result = result['signal_result']
            
            output_lines.append(f"\n📅 分析日期: {result['date']} (目标: {result['target_date']})")
            output_lines.append(f"📊 股票: {result['stock_code']} ({result['stock_industry']})")
            output_lines.append(f"💰 当前价格: {result['current_price']:.2f} 元")
            output_lines.append(f"📈 DCF估值: {result['dcf_value']:.2f} 元/股")
            output_lines.append(f"📊 价值比: {result['price_value_ratio']:.1f}%")
            output_lines.append(f"📦 成交量: {result['volume']:,.0f}")
            
            output_lines.append(f"\n🎯 信号分析:")
            output_lines.append(f"   信号类型: {signal_result['signal']}")
            output_lines.append(f"   置信度: {signal_result['confidence']:.2f}")
            output_lines.append(f"   触发原因: {signal_result['reason']}")
            
            # 4维度评分详情
            scores = signal_result['scores']
            output_lines.append(f"\n📊 4维度评分详情:")
            # 获取实际的价值比阈值
            signal_generator = self.backtest_engine.signal_generator
            buy_threshold = signal_generator.params.get('value_ratio_buy_threshold', 0.8)
            sell_threshold = signal_generator.params.get('value_ratio_sell_threshold', 0.7)
            
            output_lines.append(f"   1. 价值比过滤器:")
            output_lines.append(f"      支持卖出: {'✅' if scores['trend_filter_high'] else '❌'} (价值比 > {sell_threshold*100:.0f}%)")
            output_lines.append(f"      支持买入: {'✅' if scores['trend_filter_low'] else '❌'} (价值比 < {buy_threshold*100:.0f}%)")
            
            # 获取技术指标详情
            indicators = signal_result.get('technical_indicators', {})
            rsi_info = signal_result.get('rsi_thresholds', {})
            divergence_info = indicators.get('rsi_divergence', {})
            
            output_lines.append(f"   2. 超买超卖信号:")
            output_lines.append(f"      支持卖出: {'✅' if scores['overbought_oversold_high'] else '❌'}")
            if scores['overbought_oversold_high']:
                output_lines.append(f"        → RSI={indicators.get('rsi_14w', 0):.1f} >= 极端超买{rsi_info.get('extreme_sell_threshold', 80):.1f} (强制信号)")
            elif indicators.get('rsi_14w', 0) >= rsi_info.get('sell_threshold', 70):
                if divergence_info.get('top_divergence', False):
                    output_lines.append(f"        → RSI={indicators.get('rsi_14w', 0):.1f} >= 超买{rsi_info.get('sell_threshold', 70):.1f} + 顶背离✅")
                else:
                    output_lines.append(f"        → RSI={indicators.get('rsi_14w', 0):.1f} >= 超买{rsi_info.get('sell_threshold', 70):.1f} 但无顶背离❌")
            else:
                output_lines.append(f"        → RSI={indicators.get('rsi_14w', 0):.1f} < 超买{rsi_info.get('sell_threshold', 70):.1f}")
            
            output_lines.append(f"      支持买入: {'✅' if scores['overbought_oversold_low'] else '❌'}")
            if scores['overbought_oversold_low']:
                if indicators.get('rsi_14w', 0) <= rsi_info.get('extreme_buy_threshold', 20):
                    output_lines.append(f"        → RSI={indicators.get('rsi_14w', 0):.1f} <= 极端超卖{rsi_info.get('extreme_buy_threshold', 20):.1f} (强制信号)")
                else:
                    output_lines.append(f"        → RSI={indicators.get('rsi_14w', 0):.1f} <= 超卖{rsi_info.get('buy_threshold', 30):.1f} + 底背离✅")
            elif indicators.get('rsi_14w', 0) <= rsi_info.get('buy_threshold', 30):
                output_lines.append(f"        → RSI={indicators.get('rsi_14w', 0):.1f} <= 超卖{rsi_info.get('buy_threshold', 30):.1f} 但无底背离❌")
            else:
                output_lines.append(f"        → RSI={indicators.get('rsi_14w', 0):.1f} > 超卖{rsi_info.get('buy_threshold', 30):.1f}")
            
            output_lines.append(f"   3. 动能确认:")
            output_lines.append(f"      支持卖出: {'✅' if scores['momentum_high'] else '❌'}")
            macd_hist = indicators.get('macd_hist', 0)
            macd_dif = indicators.get('macd_dif', 0)
            macd_dea = indicators.get('macd_dea', 0)
            
            # 获取MACD历史数据进行更详细的分析
            macd_detail = self._analyze_macd_momentum_detail(signal_result, 'sell')
            if scores['momentum_high']:
                output_lines.append(f"        → {macd_detail}")
            else:
                output_lines.append(f"        → MACD无卖出信号 (HIST={macd_hist:.4f}, DIF={macd_dif:.4f}, DEA={macd_dea:.4f})")
            
            output_lines.append(f"      支持买入: {'✅' if scores['momentum_low'] else '❌'}")
            macd_detail = self._analyze_macd_momentum_detail(signal_result, 'buy')
            if scores['momentum_low']:
                output_lines.append(f"        → {macd_detail}")
            else:
                output_lines.append(f"        → MACD无买入信号 (HIST={macd_hist:.4f}, DIF={macd_dif:.4f}, DEA={macd_dea:.4f})")
            
            output_lines.append(f"   4. 极端价格+量能:")
            output_lines.append(f"      支持卖出: {'✅' if scores['extreme_price_volume_high'] else '❌'}")
            bb_upper = indicators.get('bb_upper', 0)
            volume_ratio = indicators.get('volume_ratio', 0)
            current_price = result['current_price']
            if scores['extreme_price_volume_high']:
                output_lines.append(f"        → 价格={current_price:.2f} >= 布林上轨{bb_upper:.2f} + 成交量放大{volume_ratio:.2f}x >= 1.3")
            else:
                if current_price >= bb_upper:
                    output_lines.append(f"        → 价格={current_price:.2f} >= 布林上轨{bb_upper:.2f} 但成交量{volume_ratio:.2f}x < 1.3")
                else:
                    output_lines.append(f"        → 价格={current_price:.2f} < 布林上轨{bb_upper:.2f}")
            
            output_lines.append(f"      支持买入: {'✅' if scores['extreme_price_volume_low'] else '❌'}")
            bb_lower = indicators.get('bb_lower', 0)
            if scores['extreme_price_volume_low']:
                output_lines.append(f"        → 价格={current_price:.2f} <= 布林下轨{bb_lower:.2f} + 成交量放大{volume_ratio:.2f}x >= 0.8")
            else:
                if current_price <= bb_lower:
                    output_lines.append(f"        → 价格={current_price:.2f} <= 布林下轨{bb_lower:.2f} 但成交量{volume_ratio:.2f}x < 0.8")
                else:
                    output_lines.append(f"        → 价格={current_price:.2f} > 布林下轨{bb_lower:.2f}")
            
            # RSI详细信息
            if 'rsi_thresholds' in signal_result:
                rsi_info = signal_result['rsi_thresholds']
                output_lines.append(f"\n📈 RSI详细信息:")
                output_lines.append(f"   当前RSI: {signal_result.get('technical_indicators', {}).get('rsi_14w', 0):.2f}")
                output_lines.append(f"   普通阈值: 超买={rsi_info.get('sell_threshold', 70):.1f}, 超卖={rsi_info.get('buy_threshold', 30):.1f}")
                output_lines.append(f"   极端阈值: 极端超买={rsi_info.get('extreme_sell_threshold', 80):.1f}, 极端超卖={rsi_info.get('extreme_buy_threshold', 20):.1f}")
                
                # 背离信息
                if 'technical_indicators' in signal_result:
                    divergence_info = signal_result['technical_indicators'].get('rsi_divergence', {})
                    output_lines.append(f"   背离信号: 顶背离={'✅' if divergence_info.get('top_divergence', False) else '❌'}, 底背离={'✅' if divergence_info.get('bottom_divergence', False) else '❌'}")
            
            # 技术指标详情
            if 'technical_indicators' in signal_result:
                indicators = signal_result['technical_indicators']
                output_lines.append(f"\n📈 技术指标:")
                output_lines.append(f"   EMA(20): {indicators.get('ema_20w', 0):.2f}")
                output_lines.append(f"   MACD DIF: {indicators.get('macd_dif', 0):.4f}")
                output_lines.append(f"   MACD DEA: {indicators.get('macd_dea', 0):.4f}")
                output_lines.append(f"   MACD HIST: {indicators.get('macd_hist', 0):.4f}")
                output_lines.append(f"   布林上轨: {indicators.get('bb_upper', 0):.2f}")
                output_lines.append(f"   布林下轨: {indicators.get('bb_lower', 0):.2f}")
                output_lines.append(f"   成交量比率: {indicators.get('volume_ratio', 0):.2f}")
            
            output_lines.append("-" * 80)
        
        return "\n".join(output_lines)
    
    def save_csv_report(self, results: List[Dict], output_file: str):
        """保存CSV报告"""
        if not results:
            logger.warning("❌ 没有数据可保存")
            return
        
        try:
            csv_data = []
            
            for result in results:
                signal_result = result['signal_result']
                scores = signal_result['scores']
                indicators = signal_result.get('technical_indicators', {})
                rsi_info = signal_result.get('rsi_thresholds', {})
                divergence_info = indicators.get('rsi_divergence', {})
                
                row = {
                    '分析日期': result['date'],
                    '目标日期': result['target_date'],
                    '股票代码': result['stock_code'],
                    '行业': result['stock_industry'],
                    '当前价格': result['current_price'],
                    'DCF估值': result['dcf_value'],
                    '价值比(%)': result['price_value_ratio'],
                    '成交量': result['volume'],
                    '信号类型': signal_result['signal'],
                    '置信度': signal_result['confidence'],
                    '触发原因': signal_result['reason'],
                    
                    # 4维度评分
                    '价值比过滤器_卖出': scores['trend_filter_high'],
                    '价值比过滤器_买入': scores['trend_filter_low'],
                    '超买超卖_卖出': scores['overbought_oversold_high'],
                    '超买超卖_买入': scores['overbought_oversold_low'],
                    '动能确认_卖出': scores['momentum_high'],
                    '动能确认_买入': scores['momentum_low'],
                    '极端价格量能_卖出': scores['extreme_price_volume_high'],
                    '极端价格量能_买入': scores['extreme_price_volume_low'],
                    
                    # RSI详细信息
                    'RSI当前值': indicators.get('rsi_14w', 0),
                    'RSI超买阈值': rsi_info.get('sell_threshold', 70),
                    'RSI超卖阈值': rsi_info.get('buy_threshold', 30),
                    'RSI极端超买阈值': rsi_info.get('extreme_sell_threshold', 80),
                    'RSI极端超卖阈值': rsi_info.get('extreme_buy_threshold', 20),
                    'RSI顶背离': divergence_info.get('top_divergence', False),
                    'RSI底背离': divergence_info.get('bottom_divergence', False),
                    
                    # 技术指标
                    'EMA20': indicators.get('ema_20w', 0),
                    'MACD_DIF': indicators.get('macd_dif', 0),
                    'MACD_DEA': indicators.get('macd_dea', 0),
                    'MACD_HIST': indicators.get('macd_hist', 0),
                    '布林上轨': indicators.get('bb_upper', 0),
                    '布林下轨': indicators.get('bb_lower', 0),
                    '成交量比率': indicators.get('volume_ratio', 0)
                }
                
                csv_data.append(row)
            
            df = pd.DataFrame(csv_data)
            df.to_csv(output_file, index=False, encoding='utf-8-sig')
            logger.info(f"✅ CSV报告已保存: {output_file}")
            
        except Exception as e:
            logger.error(f"❌ 保存CSV报告失败: {e}")

def parse_arguments():
    """解析命令行参数"""
    parser = argparse.ArgumentParser(
        description="股票信号分析工具 - 完全复用main.py的数据获取和计算逻辑",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
使用示例:
  # 简写形式，输出到终端
  python3 analyze_stock_signals.py -s 601225 -d 2025-02-28,2025-03-07
  
  # 完整形式，保存为CSV
  python3 analyze_stock_signals.py --stock 601225 --dates 2025-02-28,2025-03-07 --output csv
  
  # 分析多个日期
  python3 analyze_stock_signals.py -s 002738 -d 2022-02-25,2022-03-04,2022-03-11 -o csv
        """
    )
    
    parser.add_argument('-s', '--stock', required=True,
                       help='股票代码 (例如: 601225)')
    
    parser.add_argument('-d', '--dates', required=True,
                       help='分析日期，多个日期用逗号分隔 (例如: 2025-02-28,2025-03-07)')
    
    parser.add_argument('-o', '--output', choices=['csv', 'terminal'], default='terminal',
                       help='输出格式: csv=保存CSV文件, terminal=终端显示 (默认: terminal)')
    
    return parser.parse_args()

def main():
    """主函数"""
    try:
        # 解析命令行参数
        args = parse_arguments()
        
        # 解析日期列表
        date_list = [date.strip() for date in args.dates.split(',')]
        
        # 验证日期格式
        for date_str in date_list:
            try:
                pd.to_datetime(date_str)
            except:
                logger.error(f"❌ 无效的日期格式: {date_str}")
                return 1
        
        logger.info(f"🚀 开始分析股票 {args.stock}")
        logger.info(f"📅 分析日期: {', '.join(date_list)}")
        logger.info(f"📄 输出格式: {args.output}")
        
        # 创建分析器
        analyzer = StockSignalAnalyzer()
        
        # 加载配置
        if not analyzer.load_config():
            return 1
        
        # 初始化回测引擎
        if not analyzer.initialize_backtest_engine():
            return 1
        
        # 获取股票数据
        start_date = min(date_list)
        end_date = max(date_list)
        
        stock_data = analyzer.get_stock_data(args.stock, start_date, end_date)
        if stock_data is None:
            return 1
        
        # 分析信号
        results = analyzer.analyze_signals(args.stock, stock_data, date_list)
        
        if not results:
            logger.error("❌ 没有生成任何分析结果")
            return 1
        
        # 输出结果
        if args.output == 'csv':
            # 生成输出文件名
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            output_file = f"stock_signal_analysis_{args.stock}_{timestamp}.csv"
            analyzer.save_csv_report(results, output_file)
        else:
            # 终端输出
            terminal_output = analyzer.format_terminal_output(results)
            print(terminal_output)
        
        logger.info("✅ 分析完成")
        return 0
        
    except KeyboardInterrupt:
        logger.info("❌ 用户中断")
        return 1
    except Exception as e:
        logger.error(f"❌ 程序执行失败: {e}")
        import traceback
        traceback.print_exc()
        return 1

def _analyze_macd_momentum_detail(signal_result: Dict, signal_type: str) -> str:
        """分析MACD动能确认的详细原因"""
        try:
            indicators = signal_result.get('technical_indicators', {})
            macd_hist = indicators.get('macd_hist', 0)
            macd_dif = indicators.get('macd_dif', 0)
            macd_dea = indicators.get('macd_dea', 0)
            
            # 获取历史MACD数据（如果可用）
            macd_data = signal_result.get('macd_history', {})
            
            if signal_type == 'sell':
                # 卖出信号分析
                if macd_hist < 0:
                    # 检查是否是前期红柱缩短后转绿
                    if 'hist_prev1' in macd_data and 'hist_prev2' in macd_data:
                        hist_prev1 = macd_data['hist_prev1']
                        hist_prev2 = macd_data['hist_prev2']
                        if (hist_prev1 > 0 and hist_prev2 > 0 and hist_prev1 < hist_prev2):
                            return f"前期红柱缩短({hist_prev2:.3f}→{hist_prev1:.3f})+当前转绿({macd_hist:.3f})"
                    return f"MACD柱体转为绿色 (HIST={macd_hist:.4f})"
                elif macd_dif < macd_dea:
                    return f"MACD死叉 (DIF={macd_dif:.4f} < DEA={macd_dea:.4f})"
                else:
                    return f"MACD红柱连续缩短 (HIST={macd_hist:.4f})"
            
            else:  # buy
                # 买入信号分析
                if macd_hist > 0:
                    # 检查是否是前期绿柱缩短后转红
                    if 'hist_prev1' in macd_data and 'hist_prev2' in macd_data:
                        hist_prev1 = macd_data['hist_prev1']
                        hist_prev2 = macd_data['hist_prev2']
                        if (hist_prev1 < 0 and hist_prev2 < 0 and abs(hist_prev1) < abs(hist_prev2)):
                            return f"前期绿柱缩短({hist_prev2:.3f}→{hist_prev1:.3f})+当前转红({macd_hist:.3f})"
                    return f"MACD柱体转为红色 (HIST={macd_hist:.4f})"
                elif macd_dif > macd_dea:
                    return f"MACD金叉 (DIF={macd_dif:.4f} > DEA={macd_dea:.4f})"
                else:
                    return f"MACD绿柱连续缩短 (HIST={macd_hist:.4f})"
                    
        except Exception as e:
            return f"MACD分析错误: {e}"

if __name__ == "__main__":
    exit(main())
