#!/usr/bin/env python3
"""
调查实际回测中为什么没有产生卖出信号
对比理论分析和实际回测的差异
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
logging.basicConfig(level=logging.DEBUG, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def investigate_backtest_signal_issue():
    """调查实际回测中的信号生成问题"""
    
    print("=" * 80)
    print("调查实际回测中神火股份2024-04-12卖出信号缺失问题")
    print("=" * 80)
    
    # 加载配置
    config = create_csv_config()
    
    # 创建回测引擎
    engine = BacktestEngine(config)
    
    stock_code = '000933'  # 神火股份
    target_date = '2024-04-12'
    
    print(f"调查股票: {stock_code}")
    print(f"目标日期: {target_date}")
    
    try:
        # 1. 检查实际回测中的持仓状态
        print(f"\n1. 检查2024-04-12前后的持仓状态")
        
        # 运行一个小范围的回测来观察信号生成
        print(f"运行小范围回测来观察信号生成过程...")
        
        # 修改配置为小范围回测
        test_config = config.copy()
        test_config['start_date'] = '2024-03-01'
        test_config['end_date'] = '2024-05-01'
        
        # 创建测试回测引擎
        test_engine = BacktestEngine(test_config)
        
        # 运行回测
        success = test_engine.run_backtest()
        
        if success:
            # 获取回测结果
            results = test_engine.get_backtest_results()
            transaction_history = results['transaction_history']
            
            print(f"\n2. 分析交易记录")
            print(f"总交易记录数: {len(transaction_history)}")
            print(f"交易记录类型: {type(transaction_history)}")
            
            if len(transaction_history) > 0:
                print(f"交易记录列名: {transaction_history.columns.tolist()}")
                
                # 查找神火股份相关的交易
                if 'stock_code' in transaction_history.columns:
                    shenhuo_transactions = transaction_history[
                        transaction_history['stock_code'] == stock_code
                    ]
                else:
                    print(f"❌ 交易记录中没有'stock_code'列")
                    shenhuo_transactions = pd.DataFrame()
            else:
                print(f"❌ 没有任何交易记录")
                shenhuo_transactions = pd.DataFrame()
            
            print(f"神火股份交易记录数: {len(shenhuo_transactions)}")
            
            if len(shenhuo_transactions) > 0:
                print(f"\n神火股份交易记录:")
                for idx, row in shenhuo_transactions.iterrows():
                    print(f"  {row['date']} - {row['action']} - 价格:{row['price']:.2f} - 数量:{row['shares']}")
            else:
                print(f"❌ 没有找到神火股份的任何交易记录")
            
            # 查找2024-04-12前后的所有交易
            target_datetime = pd.to_datetime(target_date)
            nearby_transactions = transaction_history[
                (pd.to_datetime(transaction_history['date']) >= target_datetime - pd.Timedelta(days=14)) &
                (pd.to_datetime(transaction_history['date']) <= target_datetime + pd.Timedelta(days=14))
            ]
            
            print(f"\n3. 2024-04-12前后两周的所有交易:")
            if len(nearby_transactions) > 0:
                for idx, row in nearby_transactions.iterrows():
                    print(f"  {row['date']} - {row['stock_code']} - {row['action']} - 价格:{row['price']:.2f}")
            else:
                print(f"❌ 2024-04-12前后两周没有任何交易")
            
            # 4. 检查持仓历史
            portfolio_history = results['portfolio_history']
            
            # 查找2024-04-12的持仓状态
            target_portfolio = None
            for date_str, portfolio_data in portfolio_history.items():
                if target_date in date_str:
                    target_portfolio = portfolio_data
                    break
            
            if target_portfolio:
                print(f"\n4. 2024-04-12的持仓状态:")
                print(f"现金: {target_portfolio['cash']:,.2f}")
                print(f"总市值: {target_portfolio['total_value']:,.2f}")
                
                if 'positions' in target_portfolio:
                    positions = target_portfolio['positions']
                    if stock_code in positions:
                        position = positions[stock_code]
                        print(f"神火股份持仓: {position['shares']} 股, 市值: {position['market_value']:,.2f}")
                    else:
                        print(f"❌ 2024-04-12没有持有神火股份")
                        
                        # 检查是否曾经持有过
                        print(f"\n5. 检查历史持仓记录:")
                        ever_held = False
                        for date_str, hist_portfolio in portfolio_history.items():
                            if 'positions' in hist_portfolio and stock_code in hist_portfolio['positions']:
                                ever_held = True
                                position = hist_portfolio['positions'][stock_code]
                                print(f"  {date_str}: {position['shares']} 股, 市值: {position['market_value']:,.2f}")
                        
                        if not ever_held:
                            print(f"❌ 整个回测期间从未持有过神火股份")
                            print(f"🔍 这可能是问题的根源：没有持仓就不会有卖出信号")
            else:
                print(f"❌ 未找到2024-04-12的持仓记录")
        
        else:
            print(f"❌ 回测运行失败")
            
        # 6. 检查信号生成的前提条件
        print(f"\n6. 检查信号生成的前提条件")
        
        # 检查股票是否在股票池中
        stock_pool = config.get('stock_pool', [])
        if stock_code in stock_pool:
            print(f"✅ {stock_code} 在股票池中")
        else:
            print(f"❌ {stock_code} 不在股票池中: {stock_pool}")
        
        # 检查DCF估值数据
        dcf_values = test_engine._load_dcf_values()
        if stock_code in dcf_values:
            print(f"✅ {stock_code} 有DCF估值数据: {dcf_values[stock_code]}")
        else:
            print(f"❌ {stock_code} 没有DCF估值数据")
        
        # 7. 深入分析信号生成逻辑
        print(f"\n7. 深入分析信号生成逻辑")
        
        # 获取2024-04-12的数据
        weekly_data = test_engine._get_cached_or_fetch_data(stock_code, '2024-01-01', '2024-05-01', 'weekly')
        
        if weekly_data is not None and not weekly_data.empty:
            # 找到目标日期
            target_datetime = pd.to_datetime(target_date)
            weekly_data_with_date = weekly_data.copy()
            weekly_data_with_date['date'] = weekly_data_with_date.index
            
            closest_idx = (weekly_data_with_date['date'] - target_datetime).abs().idxmin()
            target_row = weekly_data.loc[closest_idx]
            
            print(f"目标日期数据:")
            print(f"  日期: {closest_idx.strftime('%Y-%m-%d')}")
            print(f"  收盘价: {target_row['close']:.2f}")
            print(f"  RSI: {target_row['rsi']:.2f}")
            print(f"  成交量: {target_row['volume']:,.0f}")
            
            # 检查是否满足轮动条件
            print(f"\n8. 检查轮动策略的选股逻辑")
            
            # 模拟轮动策略的选股过程
            rotation_percentage = config.get('rotation_percentage', 0.1)
            print(f"轮动比例: {rotation_percentage * 100}%")
            
            # 检查在2024-04-12时，神火股份是否在轮动选股的候选列表中
            print(f"🔍 关键问题：神火股份是否满足轮动策略的选股条件？")
            print(f"   - 如果不在选股候选列表中，就不会被买入")
            print(f"   - 如果从未被买入，就不会有卖出信号")
            
    except Exception as e:
        print(f"调查过程中出错: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    investigate_backtest_signal_issue()
