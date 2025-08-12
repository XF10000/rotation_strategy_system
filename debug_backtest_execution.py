#!/usr/bin/env python3
"""
调查2024-04-12的回测执行情况
检查为什么这个日期没有进行交易检测
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

def investigate_backtest_execution():
    """调查回测执行情况"""
    
    print("=" * 80)
    print("调查2024-04-12的回测执行情况")
    print("=" * 80)
    
    # 加载配置
    config = create_csv_config()
    
    # 创建回测引擎
    engine = BacktestEngine(config)
    
    stock_code = '000933'  # 神火股份
    target_date = '2024-04-12'
    
    try:
        # 1. 检查回测日期范围
        print(f"1. 检查回测配置:")
        print(f"  开始日期: {config.get('start_date')}")
        print(f"  结束日期: {config.get('end_date')}")
        print(f"  目标日期: {target_date}")
        
        start_date = pd.to_datetime(config.get('start_date'))
        end_date = pd.to_datetime(config.get('end_date'))
        target_datetime = pd.to_datetime(target_date)
        
        if target_datetime < start_date:
            print(f"  ❌ 目标日期早于回测开始日期")
        elif target_datetime > end_date:
            print(f"  ❌ 目标日期晚于回测结束日期")
        else:
            print(f"  ✅ 目标日期在回测范围内")
        
        # 2. 检查数据准备
        print(f"\n2. 检查数据准备:")
        success = engine.prepare_data()
        if not success:
            print(f"  ❌ 数据准备失败")
            return
        
        print(f"  ✅ 数据准备成功")
        
        # 3. 检查神火股份的数据
        if stock_code not in engine.stock_data:
            print(f"  ❌ 没有找到{stock_code}的数据")
            return
        
        stock_weekly = engine.stock_data[stock_code]['weekly']
        print(f"  ✅ {stock_code}周线数据: {len(stock_weekly)}条记录")
        print(f"  数据范围: {stock_weekly.index[0].strftime('%Y-%m-%d')} 到 {stock_weekly.index[-1].strftime('%Y-%m-%d')}")
        
        # 4. 检查目标日期是否在数据中
        target_datetime = pd.to_datetime(target_date)
        
        if target_datetime in stock_weekly.index:
            print(f"  ✅ {target_date}在{stock_code}的数据中")
            target_data = stock_weekly.loc[target_datetime]
            print(f"    收盘价: {target_data['close']:.2f}")
            print(f"    RSI: {target_data.get('rsi', 'N/A')}")
        else:
            print(f"  ❌ {target_date}不在{stock_code}的数据中")
            
            # 找最接近的日期
            closest_idx = (stock_weekly.index - target_datetime).abs().idxmin()
            closest_date = closest_idx.strftime('%Y-%m-%d')
            print(f"  最接近的日期: {closest_date}")
            
            target_data = stock_weekly.loc[closest_idx]
            print(f"    收盘价: {target_data['close']:.2f}")
            print(f"    RSI: {target_data.get('rsi', 'N/A')}")
        
        # 5. 检查回测的交易日期生成逻辑
        print(f"\n3. 检查回测交易日期生成:")
        
        # 获取所有交易日期（使用第一只股票的日期）
        first_stock = list(engine.stock_data.keys())[0]
        all_trading_dates = engine.stock_data[first_stock]['weekly'].index
        
        print(f"  第一只股票: {first_stock}")
        print(f"  总交易日期数: {len(all_trading_dates)}")
        
        # 过滤日期范围
        start_date = pd.to_datetime(engine.start_date)
        end_date = pd.to_datetime(engine.end_date)
        
        trading_dates = all_trading_dates[
            (all_trading_dates >= start_date) & (all_trading_dates <= end_date)
        ]
        
        print(f"  回测期间交易日期数: {len(trading_dates)}")
        print(f"  回测日期范围: {trading_dates[0].strftime('%Y-%m-%d')} 到 {trading_dates[-1].strftime('%Y-%m-%d')}")
        
        # 6. 检查目标日期是否在回测交易日期中
        if target_datetime in trading_dates:
            print(f"  ✅ {target_date}在回测交易日期中")
            
            # 找到目标日期的位置
            target_idx = trading_dates.get_loc(target_datetime)
            print(f"  目标日期位置: {target_idx + 1}/{len(trading_dates)}")
            
        else:
            print(f"  ❌ {target_date}不在回测交易日期中")
            
            # 找最接近的回测日期
            closest_trading_idx = (trading_dates - target_datetime).abs().idxmin()
            closest_trading_date = closest_trading_idx.strftime('%Y-%m-%d')
            print(f"  最接近的回测日期: {closest_trading_date}")
        
        # 7. 检查2024年4月前后的回测日期
        print(f"\n4. 检查2024年4月前后的回测日期:")
        
        april_2024_start = pd.to_datetime('2024-04-01')
        april_2024_end = pd.to_datetime('2024-04-30')
        
        april_dates = trading_dates[
            (trading_dates >= april_2024_start) & (trading_dates <= april_2024_end)
        ]
        
        print(f"  2024年4月的回测日期数: {len(april_dates)}")
        if len(april_dates) > 0:
            print(f"  2024年4月回测日期:")
            for date in april_dates:
                print(f"    {date.strftime('%Y-%m-%d')}")
        else:
            print(f"  ❌ 2024年4月没有任何回测日期")
        
        # 8. 检查2024年3月到6月的回测日期
        print(f"\n5. 检查2024年3月到6月的回测日期:")
        
        march_june_start = pd.to_datetime('2024-03-01')
        march_june_end = pd.to_datetime('2024-06-30')
        
        march_june_dates = trading_dates[
            (trading_dates >= march_june_start) & (trading_dates <= march_june_end)
        ]
        
        print(f"  2024年3-6月的回测日期数: {len(march_june_dates)}")
        if len(march_june_dates) > 0:
            print(f"  2024年3-6月回测日期:")
            for date in march_june_dates[:10]:  # 只显示前10个
                print(f"    {date.strftime('%Y-%m-%d')}")
            if len(march_june_dates) > 10:
                print(f"    ... 还有{len(march_june_dates) - 10}个日期")
        else:
            print(f"  ❌ 2024年3-6月没有任何回测日期")
        
        # 9. 分析可能的原因
        print(f"\n6. 可能的原因分析:")
        print(f"  如果2024年4月12日不在回测交易日期中，可能的原因:")
        print(f"  1. 该日期不是交易日（周末或节假日）")
        print(f"  2. 数据源没有该日期的数据")
        print(f"  3. 数据处理过程中该日期被过滤掉了")
        print(f"  4. 周线数据的日期对齐问题")
        
    except Exception as e:
        print(f"调查过程中出错: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    investigate_backtest_execution()
