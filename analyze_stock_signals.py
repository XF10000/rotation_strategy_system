#!/usr/bin/env python3
"""
股票信号分析工具
完全复用main.py的数据获取和计算逻辑，确保结果一致性
支持分析指定股票在特定日期范围内的4维信号详情

升级内容：
- 同步主系统的日志配置
- 添加缓存验证功能
- 改进错误处理机制
- 保持工具的简洁性和专注性
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

# 导入与main.py完全相同的核心组件
from backtest.backtest_engine import BacktestEngine
from strategy.signal_generator import SignalGenerator
from data.data_processor import DataProcessor
from config.csv_config_loader import create_csv_config
from utils.industry_classifier import get_stock_industry_auto
from config.settings import LOGGING_CONFIG
from data.cache_validator import validate_cache_before_backtest

def setup_logging():
    """设置日志系统 - 与main.py完全相同"""
    os.makedirs('logs', exist_ok=True)
    
    logging.basicConfig(
        level=getattr(logging, str(LOGGING_CONFIG['level'])),
        format=str(LOGGING_CONFIG['format']),
        handlers=[
            logging.FileHandler(str(LOGGING_CONFIG['file_path']), encoding='utf-8'),
            logging.StreamHandler(sys.stdout)
        ]
    )
    
    return logging.getLogger(__name__)

class StockSignalAnalyzer:
    """股票信号分析器 - 完全复用BacktestEngine的逻辑"""
    
    def __init__(self):
        """初始化分析器"""
        self.config = None
        self.backtest_engine = None
        self.dcf_values = {}
        self.portfolio_df = None
        self.logger = setup_logging()  # 使用与main.py相同的日志配置
        
    def load_config(self):
        """加载配置 - 与main.py完全相同"""
        try:
            # 加载CSV配置
            self.config = create_csv_config()
            self.logger.info("✅ 配置加载成功")
            
            # 读取投资组合配置，获取DCF估值
            self.portfolio_df = pd.read_csv('Input/portfolio_config.csv', encoding='utf-8-sig')
            
            # 解析DCF估值数据
            for _, row in self.portfolio_df.iterrows():
                stock_code = str(row['Stock_number'])
                if len(stock_code) < 6:
                    stock_code = stock_code.zfill(6)
                self.dcf_values[stock_code] = float(row['DCF_value_per_share'])
            
            self.logger.info(f"✅ 加载了 {len(self.dcf_values)} 只股票的DCF估值")
            return True
            
        except Exception as e:
            self.logger.error(f"❌ 配置加载失败: {e}")
            return False
    

    def validate_cache(self, stock_codes: List[str]):
        """验证缓存数据 - 与main.py完全相同"""
        try:
            self.logger.info("🔍 执行缓存数据验证...")
            cache_validation_passed = validate_cache_before_backtest(stock_codes, 'weekly')
            
            if not cache_validation_passed:
                self.logger.error("❌ 缓存验证失败")
                self.logger.error("💡 建议检查数据缓存或重新获取数据")
                return False
            
            self.logger.info("✅ 缓存验证通过")
            return True
            
        except Exception as e:
            self.logger.error(f"❌ 缓存验证失败: {e}")
            return False
    
    def initialize_backtest_engine(self):
        """初始化回测引擎 - 与main.py完全相同"""
        try:
            self.backtest_engine = BacktestEngine(self.config)
            self.logger.info("✅ 回测引擎初始化成功")
            return True
            
        except Exception as e:
            self.logger.error(f"❌ 回测引擎初始化失败: {e}")
            return False
    
    def get_stock_data(self, stock_code: str, start_date: str, end_date: str) -> Optional[pd.DataFrame]:
        """获取股票数据 - 完全复用BacktestEngine的逻辑"""
        try:
            self.logger.info(f"📊 获取股票 {stock_code} 数据...")
            
            # 使用回测引擎的数据获取逻辑
            stock_data = self.backtest_engine._get_cached_or_fetch_data(
                stock_code=stock_code,
                start_date=start_date,
                end_date=end_date,
                period='weekly'
            )
            
            if stock_data is None or stock_data.empty:
                self.logger.error(f"❌ 无法获取股票 {stock_code} 的数据")
                return None
            
            self.logger.info(f"✅ 成功获取 {len(stock_data)} 条数据记录")
            return stock_data
            
        except Exception as e:
            self.logger.error(f"❌ 获取股票数据失败: {e}")
            return None
    
    def analyze_signals(self, stock_code: str, stock_data: pd.DataFrame, target_dates: List[str]) -> List[Dict]:
        """分析信号 - 完全复用BacktestEngine的逻辑"""
        results = []
        
        try:
            for date_str in target_dates:
                self.logger.info(f"🔍 分析日期: {date_str}")
                
                # 转换为日期对象
                target_date = pd.to_datetime(date_str)
                
                # 找到目标日期或最接近的交易日
                available_dates = stock_data[stock_data.index <= target_date].index
                
                if available_dates.empty:
                    self.logger.warning(f"⚠️ 日期 {date_str} 之前没有可用数据")
                    continue
                
                analysis_date = available_dates.max()
                self.logger.info(f"📅 实际分析日期: {analysis_date.strftime('%Y-%m-%d')}")
                
                # 获取到分析日期为止的所有历史数据
                historical_data = stock_data[stock_data.index <= analysis_date].copy()
                
                if len(historical_data) < 50:  # 确保有足够历史数据计算技术指标
                    self.logger.warning(f"⚠️ 历史数据不足 ({len(historical_data)} 条)，跳过")
                    continue
                
                # 获取当前行数据
                current_row = historical_data.iloc[-1]
                
                # 获取DCF估值
                dcf_value = self.dcf_values.get(stock_code, 0)
                
                # 计算价值比
                current_price = current_row['close']
                price_value_ratio = (current_price / dcf_value * 100) if dcf_value > 0 else 0
                
                # 获取行业
                stock_industry = get_stock_industry_auto(stock_code)
                
                # 使用信号生成器分析 - 完全复用BacktestEngine的逻辑
                signal_result = self.backtest_engine.signal_generator.generate_signal(
                    stock_code, historical_data
                )
                
                # 提取技术指标
                indicators = signal_result.get('technical_indicators', {})
                
                # 提取信号详情 - 修复：scores在顶层，不在signal_details中
                signal_details = signal_result.get('details', {})
                scores = signal_result.get('scores', {})  # scores在顶层
                # 修复：RSI阈值信息在signal_result的rsi_thresholds字段中
                rsi_thresholds = signal_result.get('rsi_thresholds', {})
                divergence_info = signal_details.get('divergence_info', {})
                
                # 构建结果
                result = {
                    'analysis_date': analysis_date.strftime('%Y-%m-%d'),
                    'target_date': date_str,
                    'stock_code': stock_code,
                    'stock_industry': stock_industry,
                    'current_price': current_price,
                    'dcf_value': dcf_value,
                    'price_value_ratio': price_value_ratio,
                    'volume': current_row.get('volume', 0),
                    'signal_result': signal_result,
                    'scores': scores,
                    'rsi_thresholds': rsi_thresholds,
                    'divergence_info': divergence_info,
                    'indicators': indicators
                }
                
                results.append(result)
                self.logger.info(f"✅ 完成分析: {analysis_date.strftime('%Y-%m-%d')} - 信号: {signal_result.get('signal', 'UNKNOWN')}")
            
            return results
            
        except Exception as e:
            self.logger.error(f"❌ 信号分析失败: {e}")
            import traceback
            traceback.print_exc()
            return []
    
    def format_terminal_output(self, results: List[Dict]) -> str:
        """格式化终端输出 - 可视化信号判断逻辑"""
        output = []
        output.append("\n" + "="*80)
        output.append("📊 股票信号分析结果")
        output.append("="*80)
        
        for i, result in enumerate(results, 1):
            signal_result = result['signal_result']
            scores = result['scores']
            rsi_thresholds = result['rsi_thresholds']
            indicators = result['indicators']
            
            # 基本信息
            output.append(f"\n【分析 {i}】")
            output.append(f"📅 日期: {result['analysis_date']} (目标: {result['target_date']})")
            output.append(f"📈 股票: {result['stock_code']} - {result['stock_industry']}")
            output.append(f"💰 价格: {result['current_price']:.2f} 元 | DCF估值: {result['dcf_value']:.2f} 元 | 价值比: {result['price_value_ratio']:.1f}%")
            
            # 信号结论 - 突出显示
            signal_type = signal_result.get('signal', 'UNKNOWN')
            confidence = signal_result.get('confidence', 0)
            if signal_type == 'BUY':
                signal_icon = "🟢 买入信号"
            elif signal_type == 'SELL':
                signal_icon = "🔴 卖出信号"
            else:
                signal_icon = "⚪ 持有/观望"
            
            output.append(f"\n{'='*60}")
            output.append(f"🎯 {signal_icon} | 置信度: {confidence:.0f} | {signal_result.get('reason', '无')}")
            output.append(f"{'='*60}")
            
            # 4维度判断逻辑 - 可视化展示
            output.append(f"\n📊 4维度信号判断逻辑:")
            output.append("")
            
            # 1. 价值比过滤器
            pvr = result['price_value_ratio']
            pvr_buy = scores.get('trend_filter_low', 0)
            pvr_sell = scores.get('trend_filter_high', 0)
            if pvr_buy > 0:
                pvr_status = f"✅ 低估 ({pvr:.1f}% < 80%)  → 买入条件满足"
            elif pvr_sell > 0:
                pvr_status = f"❌ 高估 ({pvr:.1f}% > 100%) → 卖出条件满足"
            else:
                pvr_status = f"⚪ 合理 ({pvr:.1f}% 在80%-100%) → 无信号"
            output.append(f"  1️⃣ 价值比过滤器: {pvr_status}")
            
            # 2. 超买超卖 (RSI)
            rsi = indicators.get('rsi_14w', 0)
            rsi_buy_th = rsi_thresholds.get('buy_threshold', 30)
            rsi_sell_th = rsi_thresholds.get('sell_threshold', 70)
            rsi_extreme_buy = rsi_thresholds.get('extreme_buy_threshold', 20)
            rsi_extreme_sell = rsi_thresholds.get('extreme_sell_threshold', 80)
            rsi_buy = scores.get('overbought_oversold_low', 0)
            rsi_sell = scores.get('overbought_oversold_high', 0)
            
            if rsi <= rsi_extreme_buy:
                rsi_status = f"✅ 极端超卖 (RSI={rsi:.1f} ≤ {rsi_extreme_buy:.1f}) → 强烈买入信号"
            elif rsi <= rsi_buy_th:
                rsi_status = f"✅ 超卖 (RSI={rsi:.1f} ≤ {rsi_buy_th:.1f}) → 买入信号"
            elif rsi >= rsi_extreme_sell:
                rsi_status = f"❌ 极端超买 (RSI={rsi:.1f} ≥ {rsi_extreme_sell:.1f}) → 强烈卖出信号"
            elif rsi >= rsi_sell_th:
                rsi_status = f"❌ 超买 (RSI={rsi:.1f} ≥ {rsi_sell_th:.1f}) → 卖出信号"
            else:
                rsi_status = f"⚪ 正常 (RSI={rsi:.1f} 在{rsi_buy_th:.1f}-{rsi_sell_th:.1f}之间) → 无信号"
            output.append(f"  2️⃣ 超买超卖(RSI): {rsi_status}")
            
            # RSI背离
            top_div = result['divergence_info'].get('top_divergence', False)
            bottom_div = result['divergence_info'].get('bottom_divergence', False)
            if top_div:
                output.append(f"     ⚠️ RSI顶背离 → 卖出信号加强")
            if bottom_div:
                output.append(f"     ⚠️ RSI底背离 → 买入信号加强")
            
            # 3. 动能确认 (MACD)
            macd_hist = indicators.get('macd_hist', 0)
            macd_dif = indicators.get('macd_dif', 0)
            macd_dea = indicators.get('macd_dea', 0)
            price = result['current_price']
            ema20 = indicators.get('ema_20w', 0)
            momentum_buy = scores.get('momentum_low', 0)
            momentum_sell = scores.get('momentum_high', 0)
            
            macd_signal = "金叉" if macd_hist > 0 else "死叉"
            price_position = "上方" if price > ema20 else "下方"
            
            if momentum_buy > 0:
                momentum_status = f"✅ 买入动能 (MACD {macd_signal}, 价格在EMA20{price_position}) → 买入信号"
            elif momentum_sell > 0:
                momentum_status = f"❌ 卖出动能 (MACD {macd_signal}, 价格在EMA20{price_position}) → 卖出信号"
            else:
                momentum_status = f"⚪ 动能不足 (MACD={macd_hist:.4f}) → 无信号"
            output.append(f"  3️⃣ 动能确认(MACD): {momentum_status}")
            
            # 4. 极端价格量能
            bb_upper = indicators.get('bb_upper', 0)
            bb_lower = indicators.get('bb_lower', 0)
            volume_ratio = indicators.get('volume_ratio', 0)
            extreme_buy = scores.get('extreme_price_volume_low', 0)
            extreme_sell = scores.get('extreme_price_volume_high', 0)
            
            if extreme_buy > 0:
                extreme_status = f"✅ 极端低价+放量 (价格≤布林下轨{bb_lower:.2f}, 量比={volume_ratio:.2f}) → 抄底信号"
            elif extreme_sell > 0:
                extreme_status = f"❌ 极端高价+放量 (价格≥布林上轨{bb_upper:.2f}, 量比={volume_ratio:.2f}) → 逃顶信号"
            else:
                extreme_status = f"⚪ 无极端情况 (价格在布林带内) → 无信号"
            output.append(f"  4️⃣ 极端价格量能: {extreme_status}")
            
            # 信号汇总
            output.append(f"\n💡 信号汇总:")
            buy_count = sum([pvr_buy > 0, rsi_buy > 0, momentum_buy > 0, extreme_buy > 0])
            sell_count = sum([pvr_sell > 0, rsi_sell > 0, momentum_sell > 0, extreme_sell > 0])
            output.append(f"   买入维度: {buy_count}/4 个满足 {'✅' if buy_count >= 2 else '❌'}")
            output.append(f"   卖出维度: {sell_count}/4 个满足 {'✅' if sell_count >= 2 else '❌'}")
            output.append(f"   最终信号: {signal_icon} (需要≥2个维度支持)")
            
            # 关键技术指标快速参考
            output.append(f"\n📈 关键指标快速参考:")
            output.append(f"   价格: {price:.2f} | EMA20: {ema20:.2f} | 布林带: [{bb_lower:.2f}, {bb_upper:.2f}]")
            output.append(f"   RSI: {rsi:.1f} | MACD柱: {macd_hist:.4f} | 成交量比: {volume_ratio:.2f}")
            
            if i < len(results):
                output.append("\n" + "-"*80)
        
        output.append("\n" + "="*80)
        return "\n".join(output)
    
    def save_csv_report(self, results: List[Dict], output_file: str):
        """保存CSV报告"""
        try:
            csv_data = []
            
            for result in results:
                signal_result = result['signal_result']
                scores = result['scores']
                rsi_thresholds = result['rsi_thresholds']
                divergence_info = result['divergence_info']
                indicators = result['indicators']
                
                row = {
                    '分析日期': result['analysis_date'],
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
                    'RSI超买阈值': rsi_thresholds.get('sell_threshold', 70),
                    'RSI超卖阈值': rsi_thresholds.get('buy_threshold', 30),
                    'RSI极端超买阈值': rsi_thresholds.get('extreme_sell_threshold', 80),
                    'RSI极端超卖阈值': rsi_thresholds.get('extreme_buy_threshold', 20),
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
            self.logger.info(f"✅ CSV报告已保存: {output_file}")
            
        except Exception as e:
            self.logger.error(f"❌ 保存CSV报告失败: {e}")

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
    """主函数 - 专注于信号分析，保持工具的简洁性"""
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
                print(f"❌ 无效的日期格式: {date_str}")
                return 1
        
        # 创建分析器
        analyzer = StockSignalAnalyzer()
        
        analyzer.logger.info(f"🚀 开始分析股票 {args.stock}")
        analyzer.logger.info(f"📅 分析日期: {', '.join(date_list)}")
        analyzer.logger.info(f"📄 输出格式: {args.output}")
        
        # 加载配置
        if not analyzer.load_config():
            return 1
        
        # 缓存验证
        if not analyzer.validate_cache([args.stock]):
            analyzer.logger.warning("⚠️ 缓存验证失败，但继续分析...")
        
        # 初始化回测引擎
        if not analyzer.initialize_backtest_engine():
            return 1
        
        # 获取股票数据
        # 为了确保有足够的历史数据计算技术指标，我们需要从更早的日期开始获取
        min_date = pd.to_datetime(min(date_list))
        max_date = pd.to_datetime(max(date_list))
        
        # 向前获取2年的历史数据以确保技术指标计算准确
        extended_start = (min_date - timedelta(days=730)).strftime('%Y-%m-%d')
        end_date = max_date.strftime('%Y-%m-%d')
        
        stock_data = analyzer.get_stock_data(args.stock, extended_start, end_date)
        if stock_data is None:
            return 1
        
        # 分析信号
        results = analyzer.analyze_signals(args.stock, stock_data, date_list)
        
        if not results:
            analyzer.logger.error("❌ 没有生成任何分析结果")
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
        
        analyzer.logger.info("✅ 分析完成")
        return 0
        
    except KeyboardInterrupt:
        print("❌ 用户中断")
        return 1
    except Exception as e:
        print(f"❌ 程序执行失败: {e}")
        import traceback
        traceback.print_exc()
        return 1

if __name__ == "__main__":
    exit(main())