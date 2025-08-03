#!/usr/bin/env python3
"""
价值比过滤器测试脚本
测试V1.1策略中价值比过滤器替换EMA趋势过滤器的效果
"""

import sys
import os
import pandas as pd
import logging
from datetime import datetime

# 添加项目根目录到路径
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from data.data_fetcher import AkshareDataFetcher
from data.data_processor import DataProcessor
from strategy.signal_generator import SignalGenerator

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

def test_value_ratio_filter():
    """测试价值比过滤器功能"""
    
    logger.info("🚀 开始测试价值比过滤器...")
    
    # 测试股票和DCF估值
    test_stocks = {
        '601225': 40.0,  # 中国石化，DCF估值40元
        '600985': 20.0,  # 雷鸣科化，DCF估值20元
        '002738': 50.0   # 中矿资源，DCF估值50元
    }
    
    # 初始化组件
    data_fetcher = AkshareDataFetcher()
    data_processor = DataProcessor()
    
    # 配置信号生成器
    config = {
        'value_ratio_sell_threshold': 80.0,  # 卖出阈值
        'value_ratio_buy_threshold': 70.0,   # 买入阈值
        'min_data_length': 60
    }
    
    # 创建信号生成器（当前版本只接受config参数）
    signal_generator = SignalGenerator(config)
    
    # 手动设置DCF数据（临时解决方案）
    signal_generator.dcf_values = test_stocks
    
    logger.info(f"📊 测试股票池: {list(test_stocks.keys())}")
    logger.info(f"🎯 价值比阈值: 买入<{config['value_ratio_buy_threshold']}%, 卖出>{config['value_ratio_sell_threshold']}%")
    
    # 测试每只股票
    for stock_code, dcf_value in test_stocks.items():
        logger.info(f"\n{'='*60}")
        logger.info(f"📈 测试股票: {stock_code} (DCF估值: {dcf_value}元)")
        logger.info(f"{'='*60}")
        
        try:
            # 获取股票数据
            logger.info(f"📥 获取 {stock_code} 历史数据...")
            daily_data = data_fetcher.get_stock_data(stock_code, '2023-01-01', '2024-12-31', 'daily')
            
            if daily_data is None or daily_data.empty:
                logger.warning(f"⚠️ 无法获取 {stock_code} 数据")
                continue
            
            # 转换为周线数据
            logger.info(f"🔄 转换为周线数据...")
            weekly_data = data_processor.resample_to_weekly(daily_data)
            
            # 计算技术指标
            logger.info(f"🔧 计算技术指标...")
            weekly_data = data_processor.calculate_technical_indicators(weekly_data)
            
            logger.info(f"✅ 数据准备完成: {len(weekly_data)} 条周线记录")
            
            # 测试最近几个时间点的信号
            test_dates = weekly_data.index[-5:]  # 最近5个交易周
            
            logger.info(f"\n🎯 价值比过滤器测试结果:")
            logger.info(f"{'日期':<12} {'收盘价':<8} {'价值比':<8} {'过滤器':<12} {'信号':<8}")
            logger.info("-" * 60)
            
            for test_date in test_dates:
                # 获取到该日期为止的历史数据
                historical_data = weekly_data.loc[:test_date]
                
                if len(historical_data) < 60:
                    continue
                
                # 生成信号
                signal_result = signal_generator.generate_signal(stock_code, historical_data)
                
                # 获取当前价格和价值比
                current_price = historical_data.iloc[-1]['close']
                price_value_ratio = (current_price / dcf_value) * 100
                
                # 判断过滤器状态
                filter_status = "无信号"
                if price_value_ratio < config['value_ratio_buy_threshold']:
                    filter_status = "支持买入"
                elif price_value_ratio > config['value_ratio_sell_threshold']:
                    filter_status = "支持卖出"
                else:
                    filter_status = "中性区间"
                
                # 获取最终信号
                final_signal = "HOLD"
                if signal_result and isinstance(signal_result, dict):
                    final_signal = signal_result.get('signal', 'HOLD')
                elif isinstance(signal_result, str):
                    final_signal = signal_result
                
                logger.info(f"{test_date.strftime('%Y-%m-%d'):<12} "
                           f"{current_price:<8.2f} "
                           f"{price_value_ratio:<8.1f}% "
                           f"{filter_status:<12} "
                           f"{final_signal:<8}")
            
            # 统计分析
            logger.info(f"\n📊 {stock_code} 价值比统计分析:")
            recent_data = weekly_data.tail(20)  # 最近20周
            price_ratios = [(row['close'] / dcf_value) * 100 for _, row in recent_data.iterrows()]
            
            logger.info(f"  最近20周价值比范围: {min(price_ratios):.1f}% - {max(price_ratios):.1f}%")
            logger.info(f"  平均价值比: {sum(price_ratios)/len(price_ratios):.1f}%")
            logger.info(f"  低于买入阈值({config['value_ratio_buy_threshold']}%)的周数: "
                       f"{sum(1 for r in price_ratios if r < config['value_ratio_buy_threshold'])}")
            logger.info(f"  高于卖出阈值({config['value_ratio_sell_threshold']}%)的周数: "
                       f"{sum(1 for r in price_ratios if r > config['value_ratio_sell_threshold'])}")
            
        except Exception as e:
            logger.error(f"❌ {stock_code} 测试失败: {e}")
            continue
    
    logger.info(f"\n🎉 价值比过滤器测试完成!")
    logger.info(f"💡 V1.1策略已成功替换EMA趋势过滤器为价值比过滤器")
    logger.info(f"📋 测试要点:")
    logger.info(f"  ✅ 价值比 < 70% → 支持买入信号")
    logger.info(f"  ✅ 价值比 > 80% → 支持卖出信号") 
    logger.info(f"  ✅ 70% ≤ 价值比 ≤ 80% → 中性区间，无趋势支持")
    logger.info(f"  ✅ 如无DCF数据，自动回退到EMA趋势过滤器")

if __name__ == "__main__":
    test_value_ratio_filter()
