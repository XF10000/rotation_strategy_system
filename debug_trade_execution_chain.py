#!/usr/bin/env python3
"""
深入调查2024-04-12神火股份SELL信号的交易执行链路
模拟完整的回测执行流程，跟踪每一步的决策逻辑
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

def investigate_trade_execution_chain():
    """调查交易执行链路"""
    
    print("=" * 80)
    print("深入调查2024-04-12神火股份SELL信号的交易执行链路")
    print("=" * 80)
    
    # 加载配置
    config = create_csv_config()
    
    # 创建回测引擎
    engine = BacktestEngine(config)
    
    target_date = '2024-04-12'
    stock_code = '000933'  # 神火股份
    
    try:
        # 1. 数据准备
        print("1. 准备数据...")
        success = engine.prepare_data()
        if not success:
            print("❌ 数据准备失败")
            return
        
        # 2. 模拟回测到目标日期前的状态
        print(f"\n2. 模拟回测到{target_date}前的投资组合状态:")
        print("-" * 60)
        
        # 获取交易日期序列
        first_stock = list(engine.stock_data.keys())[0]
        all_trading_dates = engine.stock_data[first_stock]['weekly'].index
        start_date = pd.to_datetime(engine.start_date)
        end_date = pd.to_datetime(engine.end_date)
        trading_dates = all_trading_dates[(all_trading_dates >= start_date) & (all_trading_dates <= end_date)]
        
        target_datetime = pd.to_datetime(target_date)
        
        # 找到目标日期在交易序列中的位置
        if target_datetime not in trading_dates:
            print(f"❌ {target_date}不在交易日期序列中")
            return
        
        target_idx = trading_dates.get_loc(target_datetime)
        print(f"✅ {target_date}是第{target_idx + 1}个交易日")
        
        # 3. 运行回测到目标日期前一天
        print(f"\n3. 运行回测到{target_date}前一天:")
        print("-" * 60)
        
        # 获取目标日期前一个交易日
        if target_idx == 0:
            print("❌ 目标日期是第一个交易日，无法获取前一天状态")
            return
        
        prev_date = trading_dates[target_idx - 1]
        print(f"前一个交易日: {prev_date.strftime('%Y-%m-%d')}")
        
        # 运行回测到前一天（模拟投资组合状态）
        # 这里我们需要手动模拟，因为完整回测太复杂
        print("模拟投资组合状态（基于交易记录分析）:")
        
        # 从之前的交易记录分析，我们知道：
        # 2023/06/21 - 神火股份买入73000股
        # 2023/06/30 - 神火股份加仓6900股  
        # 总计：79900股
        
        simulated_positions = {
            stock_code: {
                'shares': 79900,
                'avg_cost': 13.01,  # 从交易记录获取
                'current_value': 0
            }
        }
        
        # 获取前一天的价格来计算持仓价值
        prev_data = engine.stock_data[stock_code]['weekly'].loc[prev_date]
        prev_price = prev_data['close']
        simulated_positions[stock_code]['current_value'] = simulated_positions[stock_code]['shares'] * prev_price
        
        print(f"模拟持仓状态:")
        print(f"  {stock_code}: {simulated_positions[stock_code]['shares']}股")
        print(f"  平均成本: {simulated_positions[stock_code]['avg_cost']:.2f}元")
        print(f"  前一日价格: {prev_price:.2f}元")
        print(f"  持仓价值: {simulated_positions[stock_code]['current_value']:,.2f}元")
        
        # 4. 分析目标日期的信号生成
        print(f"\n4. 分析{target_date}的信号生成:")
        print("-" * 60)
        
        target_data = engine.stock_data[stock_code]['weekly'].loc[target_datetime]
        target_price = target_data['close']
        
        print(f"目标日期价格: {target_price:.2f}元")
        print(f"价格变化: {target_price - prev_price:.2f}元 ({(target_price/prev_price-1)*100:.1f}%)")
        
        # 生成信号
        historical_data = engine.stock_data[stock_code]['weekly'].loc[:target_datetime]
        signal_result = engine.signal_generator.generate_signal(stock_code, historical_data)
        
        print(f"✅ 生成信号: {signal_result['signal']}")
        print(f"✅ 信号原因: {signal_result.get('reason', 'N/A')}")
        
        # 5. 分析交易决策逻辑
        print(f"\n5. 分析交易决策逻辑:")
        print("-" * 60)
        
        if signal_result['signal'] == 'SELL':
            print("🎯 确认产生SELL信号，分析为什么没有执行交易:")
            
            # 检查持仓
            if simulated_positions[stock_code]['shares'] > 0:
                print(f"✅ 有持仓可卖: {simulated_positions[stock_code]['shares']}股")
                
                # 计算潜在卖出价值
                potential_sell_value = simulated_positions[stock_code]['shares'] * target_price
                print(f"✅ 潜在卖出价值: {potential_sell_value:,.2f}元")
                
                # 计算盈亏
                cost_basis = simulated_positions[stock_code]['shares'] * simulated_positions[stock_code]['avg_cost']
                profit_loss = potential_sell_value - cost_basis
                profit_loss_pct = (profit_loss / cost_basis) * 100
                
                print(f"📊 成本基础: {cost_basis:,.2f}元")
                print(f"📊 盈亏金额: {profit_loss:,.2f}元")
                print(f"📊 盈亏比例: {profit_loss_pct:.1f}%")
                
                # 检查可能的约束条件
                print(f"\n检查可能的交易约束:")
                
                # 1. 检查轮动策略约束
                print(f"1. 轮动策略约束检查:")
                rotation_config = config.get('strategy_params', {})
                rotation_pct = rotation_config.get('rotation_percentage', 0.1)
                print(f"   轮动比例: {rotation_pct}")
                
                # 2. 检查风险管理约束
                print(f"2. 风险管理约束检查:")
                max_single_ratio = rotation_config.get('max_single_stock_ratio', 0.15)
                print(f"   单股最大比例: {max_single_ratio}")
                
                # 3. 检查动态仓位管理
                print(f"3. 动态仓位管理检查:")
                value_ratio = signal_result.get('value_price_ratio', 'N/A')
                print(f"   价值比: {value_ratio}")
                
                if isinstance(value_ratio, (int, float)):
                    # 根据价值比确定卖出比例
                    if value_ratio >= 1.2:  # 轻度高估
                        sell_ratio = rotation_config.get('slight_overvalue_sell_ratio', 0.8)
                        print(f"   轻度高估，建议卖出比例: {sell_ratio}")
                    elif value_ratio >= 1.0:  # 公允价值
                        sell_ratio = rotation_config.get('fair_value_sell_ratio', 0.5)
                        print(f"   公允价值，建议卖出比例: {sell_ratio}")
                    elif value_ratio >= 0.8:  # 轻度低估
                        sell_ratio = rotation_config.get('slight_undervalue_sell_ratio', 0.2)
                        print(f"   轻度低估，建议卖出比例: {sell_ratio}")
                    else:
                        sell_ratio = 0
                        print(f"   明显低估，不建议卖出")
                    
                    if sell_ratio > 0:
                        suggested_sell_shares = int(simulated_positions[stock_code]['shares'] * sell_ratio)
                        suggested_sell_value = suggested_sell_shares * target_price
                        print(f"   建议卖出股数: {suggested_sell_shares}股")
                        print(f"   建议卖出价值: {suggested_sell_value:,.2f}元")
                    else:
                        print(f"   ❌ 动态仓位管理阻止了卖出！")
                        print(f"   原因: 价值比{value_ratio:.3f}表明股票仍被低估")
                
            else:
                print(f"❌ 没有持仓可卖")
        
        # 6. 检查回测引擎的实际执行逻辑
        print(f"\n6. 检查回测引擎的实际执行逻辑:")
        print("-" * 60)
        
        print("建议检查以下模块:")
        print("1. 📁 backtest/portfolio_manager.py - 投资组合管理器")
        print("2. 📁 strategy/rotation_strategy.py - 轮动策略")
        print("3. 📁 strategy/position_manager.py - 仓位管理器")
        print("4. 📁 backtest/backtest_engine.py 的交易执行部分")
        
        # 7. 总结可能的原因
        print(f"\n7. 总结可能的原因:")
        print("-" * 60)
        print("基于分析，SELL信号没有执行的可能原因:")
        print("1. 🔍 动态仓位管理阻止 - 价值比显示股票仍被低估")
        print("2. 🔍 轮动策略频率限制 - 可能有最小持有期或轮动间隔")
        print("3. 🔍 投资组合管理器bug - 持仓记录不准确")
        print("4. 🔍 交易执行逻辑bug - 信号传递到执行环节有问题")
        
        print(f"\n下一步建议:")
        print("1. 检查动态仓位管理的价值比计算逻辑")
        print("2. 验证轮动策略的交易频率控制")
        print("3. 运行完整回测并启用详细日志")
        
    except Exception as e:
        print(f"调查过程中出错: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    investigate_trade_execution_chain()
