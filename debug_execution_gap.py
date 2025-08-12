#!/usr/bin/env python3
"""
深入调查2024年3月-6月回测执行中断问题
分析为什么这4个月期间没有任何交易
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

import pandas as pd
import numpy as np
from datetime import datetime
import logging

from backtest.backtest_engine import BacktestEngine
from config.csv_config_loader import create_csv_config

# 设置详细日志
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def investigate_execution_gap():
    """调查执行中断问题"""
    
    print("=" * 80)
    print("深入调查2024年3月-6月回测执行中断问题")
    print("=" * 80)
    
    # 加载配置
    config = create_csv_config()
    
    # 创建回测引擎
    engine = BacktestEngine(config)
    
    try:
        # 1. 数据准备
        print("1. 准备数据...")
        success = engine.prepare_data()
        if not success:
            print("❌ 数据准备失败")
            return
        
        # 2. 分析关键日期的信号生成
        key_dates = [
            '2024-03-08',  # 最后一次交易
            '2024-04-12',  # 目标日期
            '2024-05-10',  # 中间日期
            '2024-06-28',  # 下一次交易
        ]
        
        stock_code = '000933'  # 神火股份
        
        print(f"\n2. 分析关键日期的信号生成 ({stock_code}):")
        print("-" * 60)
        
        for date_str in key_dates:
            print(f"\n📅 {date_str}:")
            
            try:
                date = pd.to_datetime(date_str)
                
                # 检查是否在回测日期中
                first_stock = list(engine.stock_data.keys())[0]
                trading_dates = engine.stock_data[first_stock]['weekly'].index
                start_date = pd.to_datetime(engine.start_date)
                end_date = pd.to_datetime(engine.end_date)
                valid_dates = trading_dates[(trading_dates >= start_date) & (trading_dates <= end_date)]
                
                if date not in valid_dates:
                    print(f"  ❌ 不在回测交易日期中")
                    continue
                
                # 获取股票数据
                if stock_code not in engine.stock_data:
                    print(f"  ❌ 没有{stock_code}数据")
                    continue
                
                stock_weekly = engine.stock_data[stock_code]['weekly']
                if date not in stock_weekly.index:
                    print(f"  ❌ 该日期没有股票数据")
                    continue
                
                # 获取当日数据
                current_data = stock_weekly.loc[date]
                print(f"  📊 收盘价: {current_data['close']:.2f}")
                print(f"  📊 RSI: {current_data.get('rsi', 'N/A'):.2f}")
                
                # 生成信号 - 需要传入完整的历史数据到当前日期
                historical_data = stock_weekly.loc[:date]
                signal_result = engine.signal_generator.generate_signal(
                    stock_code, 
                    historical_data
                )
                
                print(f"  🎯 信号: {signal_result['signal']}")
                print(f"  📝 原因: {signal_result.get('reason', 'N/A')}")
                
                # 详细分析4D得分
                if 'scores' in signal_result:
                    scores = signal_result['scores']
                    print(f"  📈 4D得分:")
                    print(f"    价值比过滤器: 高={scores.get('trend_filter_high', False)}, 低={scores.get('trend_filter_low', False)}")
                    print(f"    超买超卖: 高={scores.get('overbought_oversold_high', False)}, 低={scores.get('overbought_oversold_low', False)}")
                    print(f"    动能确认: 高={scores.get('momentum_high', False)}, 低={scores.get('momentum_low', False)}")
                    print(f"    极端价量: 高={scores.get('extreme_price_volume_high', False)}, 低={scores.get('extreme_price_volume_low', False)}")
                
                # 检查投资组合状态
                print(f"  💼 投资组合检查:")
                
                # 模拟到该日期的投资组合状态
                portfolio_value = 0
                cash = engine.initial_capital
                positions = {}
                
                # 这里需要模拟到该日期的投资组合状态
                # 简化版本：检查是否有持仓
                print(f"    现金: {cash:.2f}")
                print(f"    持仓数: {len(positions)}")
                
            except Exception as e:
                print(f"  ❌ 分析{date_str}时出错: {e}")
        
        # 3. 检查轮动策略的约束条件
        print(f"\n3. 检查轮动策略约束条件:")
        print("-" * 40)
        
        rotation_config = config.get('rotation_strategy', {})
        print(f"  最大持仓数: {rotation_config.get('max_positions', 'N/A')}")
        print(f"  单股票最大权重: {rotation_config.get('max_single_weight', 'N/A')}")
        print(f"  轮动频率: {rotation_config.get('rebalance_frequency', 'N/A')}")
        
        # 4. 检查风险控制设置
        print(f"\n4. 检查风险控制设置:")
        print("-" * 40)
        
        risk_config = config.get('risk_management', {})
        print(f"  止损阈值: {risk_config.get('stop_loss_threshold', 'N/A')}")
        print(f"  止盈阈值: {risk_config.get('take_profit_threshold', 'N/A')}")
        print(f"  最大回撤: {risk_config.get('max_drawdown', 'N/A')}")
        
        # 5. 分析可能的执行中断原因
        print(f"\n5. 可能的执行中断原因分析:")
        print("-" * 40)
        print(f"  可能原因:")
        print(f"  1. 💰 现金不足 - 无法买入新股票")
        print(f"  2. 📊 持仓已满 - 达到最大持仓数限制")
        print(f"  3. 🎯 信号不足 - 所有股票都没有产生有效信号")
        print(f"  4. 🔒 风险控制 - 触发了某种风险控制机制")
        print(f"  5. ⚙️ 轮动限制 - 轮动频率或其他策略限制")
        print(f"  6. 🐛 代码逻辑 - 回测引擎的执行逻辑问题")
        
        # 6. 建议的调试步骤
        print(f"\n6. 建议的调试步骤:")
        print("-" * 40)
        print(f"  1. 运行完整回测并启用详细日志")
        print(f"  2. 检查2024-04-12当天的完整执行流程")
        print(f"  3. 验证投资组合管理器的状态")
        print(f"  4. 检查轮动策略的决策逻辑")
        print(f"  5. 分析风险管理模块的干预")
        
    except Exception as e:
        print(f"调查过程中出错: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    investigate_execution_gap()
