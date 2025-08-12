#!/usr/bin/env python3
"""
测试信号生成过程，找出为什么没有产生交易信号
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

def test_signal_generation():
    """测试信号生成过程"""
    
    print("=" * 80)
    print("测试神火股份2024-04-12的信号生成过程")
    print("=" * 80)
    
    # 加载配置
    config = create_csv_config()
    
    # 创建回测引擎
    engine = BacktestEngine(config)
    
    stock_code = '000933'  # 神火股份
    target_date = '2024-04-12'
    
    try:
        # 1. 准备数据
        print(f"1. 准备数据...")
        success = engine.prepare_data()
        if not success:
            print(f"❌ 数据准备失败")
            return
        
        print(f"✅ 数据准备成功")
        
        # 2. 获取神火股份的数据
        if stock_code not in engine.stock_data:
            print(f"❌ 没有找到{stock_code}的数据")
            return
        
        stock_weekly = engine.stock_data[stock_code]['weekly']
        print(f"✅ 获取到{stock_code}的周线数据，共{len(stock_weekly)}条记录")
        
        # 3. 找到目标日期
        target_datetime = pd.to_datetime(target_date)
        
        if target_datetime not in stock_weekly.index:
            # 找最接近的日期
            closest_idx = (stock_weekly.index - target_datetime).abs().idxmin()
            print(f"⚠️ 目标日期{target_date}不在数据中，使用最接近的日期: {closest_idx.strftime('%Y-%m-%d')}")
            target_datetime = closest_idx
        
        # 4. 检查数据完整性
        current_idx = stock_weekly.index.get_loc(target_datetime)
        print(f"目标日期在数据中的位置: {current_idx}/{len(stock_weekly)}")
        
        if current_idx < 20:
            print(f"❌ 历史数据不足，需要至少20条记录，当前只有{current_idx}条")
            return
        
        # 获取历史数据
        historical_data = stock_weekly.iloc[:current_idx+1]
        print(f"✅ 历史数据充足，共{len(historical_data)}条记录")
        
        if len(historical_data) < 60:
            print(f"❌ 历史数据不足60条，当前只有{len(historical_data)}条")
            return
        
        # 5. 测试信号生成
        print(f"\n2. 测试信号生成...")
        
        try:
            signal_result = engine.signal_generator.generate_signal(stock_code, historical_data)
            
            print(f"信号生成结果类型: {type(signal_result)}")
            print(f"信号生成结果: {signal_result}")
            
            if signal_result and isinstance(signal_result, dict):
                signal = signal_result.get('signal', 'HOLD')
                print(f"提取的信号: {signal}")
                
                if signal and signal != 'HOLD':
                    print(f"✅ 产生了有效信号: {signal}")
                    
                    # 显示详细信息
                    if 'details' in signal_result:
                        details = signal_result['details']
                        print(f"信号详情:")
                        for key, value in details.items():
                            print(f"  {key}: {value}")
                else:
                    print(f"❌ 没有产生有效信号，返回HOLD")
            elif isinstance(signal_result, str):
                print(f"信号结果（字符串）: {signal_result}")
                if signal_result and signal_result != 'HOLD':
                    print(f"✅ 产生了有效信号: {signal_result}")
                else:
                    print(f"❌ 没有产生有效信号")
            else:
                print(f"❌ 信号生成返回了无效结果: {signal_result}")
                
        except Exception as e:
            print(f"❌ 信号生成过程中出错: {e}")
            import traceback
            traceback.print_exc()
        
        # 6. 分析为什么没有信号
        print(f"\n3. 分析信号生成的详细过程...")
        
        # 获取当前数据点
        current_row = stock_weekly.loc[target_datetime]
        print(f"当前数据点 ({target_datetime.strftime('%Y-%m-%d')}):")
        print(f"  收盘价: {current_row['close']:.2f}")
        print(f"  RSI: {current_row.get('rsi', 'N/A')}")
        print(f"  成交量: {current_row['volume']:,.0f}")
        
        # 检查DCF估值
        dcf_value = engine.dcf_values.get(stock_code)
        if dcf_value:
            value_ratio = current_row['close'] / dcf_value
            print(f"  DCF估值: {dcf_value:.2f}")
            print(f"  价值比: {value_ratio:.3f}")
            
            # 检查价值比过滤器
            buy_threshold = config.get('value_ratio_buy_threshold', 0.7)
            sell_threshold = config.get('value_ratio_sell_threshold', 0.65)
            
            print(f"  价值比过滤器:")
            print(f"    买入阈值: {buy_threshold}")
            print(f"    卖出阈值: {sell_threshold}")
            
            if value_ratio < buy_threshold:
                print(f"    ✅ 支持买入 ({value_ratio:.3f} < {buy_threshold})")
            else:
                print(f"    ❌ 不支持买入 ({value_ratio:.3f} >= {buy_threshold})")
            
            if value_ratio > sell_threshold:
                print(f"    ✅ 支持卖出 ({value_ratio:.3f} > {sell_threshold})")
            else:
                print(f"    ❌ 不支持卖出 ({value_ratio:.3f} <= {sell_threshold})")
        
        # 7. 检查是否有持仓
        print(f"\n4. 检查持仓状态...")
        
        # 初始化投资组合来检查持仓
        engine.initialize_portfolio()
        
        current_position = engine.portfolio_manager.positions.get(stock_code, 0)
        print(f"{stock_code}当前持仓: {current_position} 股")
        
        if current_position > 0:
            print(f"✅ 有持仓，可以产生卖出信号")
        else:
            print(f"❌ 没有持仓，不会产生卖出信号")
            print(f"🔍 这可能是关键问题：没有持仓就不会有卖出信号")
        
        # 8. 模拟完整的信号生成流程
        print(f"\n5. 模拟完整的信号生成流程...")
        
        signals = engine._generate_signals(target_datetime)
        print(f"生成的信号: {signals}")
        
        if stock_code in signals:
            print(f"✅ {stock_code}产生了信号: {signals[stock_code]}")
        else:
            print(f"❌ {stock_code}没有产生信号")
            
            # 分析可能的原因
            print(f"\n可能的原因:")
            print(f"  1. 历史数据不足（需要≥60条）")
            print(f"  2. 信号生成器内部逻辑阻止了信号产生")
            print(f"  3. 价值比过滤器阻止了信号")
            print(f"  4. 其他技术指标不满足条件")
            print(f"  5. 没有持仓（对于卖出信号）")
        
    except Exception as e:
        print(f"测试过程中出错: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    test_signal_generation()
