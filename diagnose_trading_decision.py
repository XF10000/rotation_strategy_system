#!/usr/bin/env python3
"""
交易决策诊断工具
专门分析回测系统在特定日期的完整决策过程
"""

import pandas as pd
import numpy as np
import logging
import sys
import os
from datetime import datetime

# 添加项目路径
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from backtest.backtest_engine import BacktestEngine
from config.csv_config_loader import create_csv_config
from utils.industry_classifier import get_stock_industry_auto
from config.settings import LOGGING_CONFIG

def setup_logging():
    """设置日志系统"""
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

def diagnose_trading_decision(target_date: str):
    """诊断特定日期的交易决策"""
    logger = setup_logging()
    
    logger.info(f"🔍 开始诊断 {target_date} 的交易决策过程")
    
    try:
        # 初始化回测引擎
        config = create_csv_config()
        engine = BacktestEngine(config)
        
        # 获取目标日期
        target_dt = pd.to_datetime(target_date)
        
        logger.info("🏃 运行回测到目标日期...")
        
        # 准备数据
        engine.prepare_data()
        
        # 模拟回测运行到目标日期（不包含目标日期）
        current_date = pd.to_datetime(engine.start_date)
        end_date = target_dt - pd.Timedelta(days=1)  # 运行到目标日期前一天
        
        while current_date <= end_date:
            # 检查是否是交易日
            if current_date.weekday() == 0:  # 周一进行交易
                # 获取当前价格
                current_prices = {}
                for stock_code in engine.stock_pool:
                    if stock_code in engine.stock_data:
                        stock_weekly = engine.stock_data[stock_code]['weekly']
                        if current_date in stock_weekly.index:
                            current_prices[stock_code] = stock_weekly.loc[current_date, 'close']
                
                if current_prices:
                    # 生成信号并执行交易
                    signals = engine._generate_signals(current_date)
                    if signals:
                        executed_trades = engine._execute_trades(signals, current_date)
                        if executed_trades:
                            logger.info(f"{current_date.strftime('%Y-%m-%d')} 执行了 {len(executed_trades)} 笔交易")
            
            current_date += pd.Timedelta(days=7)  # 每周检查一次
        
        logger.info(f"✅ 回测运行完成，当前日期前状态: {end_date.strftime('%Y-%m-%d')}")
        
        # 现在分析目标日期的决策
        logger.info(f"🎯 分析目标日期 {target_date} 的决策...")
        
        # 分析所有股票的信号
        all_signals = {}
        all_prices = {}
        all_positions = {}
        
        logger.info("📊 分析所有股票的信号状态...")
        
        for stock_code in engine.stock_pool:
            if stock_code not in engine.stock_data:
                continue
                
            stock_weekly = engine.stock_data[stock_code]['weekly']
            
            # 找到目标日期的数据
            available_dates = stock_weekly[stock_weekly.index <= target_dt].index
            if available_dates.empty:
                continue
                
            analysis_date = available_dates.max()
            
            if analysis_date not in stock_weekly.index:
                continue
                
            # 获取当前价格
            current_price = stock_weekly.loc[analysis_date, 'close']
            all_prices[stock_code] = current_price
            
            # 获取当前持仓
            current_position = engine.portfolio_manager.positions.get(stock_code, 0)
            all_positions[stock_code] = current_position
            
            # 获取历史数据
            current_idx = stock_weekly.index.get_loc(analysis_date)
            if current_idx < 120:
                continue
                
            historical_data = stock_weekly.iloc[:current_idx + 1].copy()
            
            # 生成信号
            try:
                signal_result = engine.signal_generator.generate_signal(stock_code, historical_data)
                all_signals[stock_code] = signal_result
                
                # 打印详细信号信息
                logger.info(f"\n📈 {stock_code} 信号分析:")
                logger.info(f"   当前价格: {current_price:.2f} 元")
                logger.info(f"   当前持仓: {current_position} 股")
                logger.info(f"   信号类型: {signal_result.get('signal', 'UNKNOWN')}")
                logger.info(f"   置信度: {signal_result.get('confidence', 0)}")
                logger.info(f"   触发原因: {signal_result.get('reason', '无')}")
                
                # DCF估值信息
                dcf_value = engine.dcf_values.get(stock_code, 0)
                if dcf_value > 0:
                    value_ratio = (current_price / dcf_value) * 100
                    logger.info(f"   DCF估值: {dcf_value:.2f} 元")
                    logger.info(f"   价值比: {value_ratio:.1f}%")
                
                # 信号详情
                signal_details = signal_result.get('signal_details', {})
                scores = signal_details.get('scores', {})
                logger.info(f"   4维度得分: {scores}")
                
            except Exception as e:
                logger.error(f"   ❌ 信号生成失败: {e}")
                all_signals[stock_code] = {'signal': 'ERROR', 'reason': str(e)}
        
        # 分析买入信号的竞争情况
        buy_signals = {k: v for k, v in all_signals.items() if v.get('signal') == 'BUY'}
        
        logger.info(f"\n🎯 买入信号汇总 ({len(buy_signals)} 个):")
        
        if not buy_signals:
            logger.info("   ❌ 没有任何股票产生买入信号")
            return
        
        # 按置信度排序
        sorted_signals = sorted(buy_signals.items(), 
                              key=lambda x: x[1].get('confidence', 0), 
                              reverse=True)
        
        for i, (stock_code, signal) in enumerate(sorted_signals, 1):
            dcf_value = engine.dcf_values.get(stock_code, 0)
            current_price = all_prices.get(stock_code, 0)
            value_ratio = (current_price / dcf_value * 100) if dcf_value > 0 else 0
            
            logger.info(f"   {i}. {stock_code}: 置信度={signal.get('confidence', 0)}, "
                       f"价值比={value_ratio:.1f}%, 原因={signal.get('reason', '无')}")
        
        # 分析现金和仓位状况
        total_assets = engine.portfolio_manager.get_total_value(all_prices)
        cash_ratio = engine.portfolio_manager.cash / total_assets if total_assets > 0 else 0
        
        logger.info(f"\n💰 资金状况:")
        logger.info(f"   总资产: {total_assets:,.0f} 元")
        logger.info(f"   现金: {engine.portfolio_manager.cash:,.0f} 元")
        logger.info(f"   现金比例: {cash_ratio:.1%}")
        
        # 分析具体的买入决策
        logger.info(f"\n🔍 买入决策分析:")
        
        for stock_code, signal in buy_signals.items():
            current_price = all_prices[stock_code]
            current_position = all_positions[stock_code]
            dcf_value = engine.dcf_values.get(stock_code, 0)
            
            if dcf_value > 0:
                value_price_ratio = current_price / dcf_value
                
                # 检查动态仓位管理决策
                can_buy, buy_shares, buy_value, reason = engine.portfolio_manager.can_buy_dynamic(
                    stock_code, value_price_ratio, current_price, 
                    engine.dynamic_position_manager, all_prices
                )
                
                logger.info(f"   {stock_code}:")
                logger.info(f"     价值比: {value_price_ratio:.3f}")
                logger.info(f"     当前持仓: {current_position} 股")
                logger.info(f"     可以买入: {can_buy}")
                logger.info(f"     买入股数: {buy_shares}")
                logger.info(f"     买入金额: {buy_value:,.0f} 元")
                logger.info(f"     决策原因: {reason}")
                
                if can_buy and buy_shares > 0:
                    logger.info(f"     ✅ 符合买入条件")
                else:
                    logger.info(f"     ❌ 不符合买入条件")
            else:
                logger.info(f"   {stock_code}: ❌ 无DCF估值数据")
        
        logger.info("🔍 诊断完成")
        
    except Exception as e:
        logger.error(f"❌ 诊断失败: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    if len(sys.argv) != 2:
        print("用法: python3 diagnose_trading_decision.py YYYY-MM-DD")
        print("例如: python3 diagnose_trading_decision.py 2025-08-15")
        sys.exit(1)
    
    target_date = sys.argv[1]
    diagnose_trading_decision(target_date)