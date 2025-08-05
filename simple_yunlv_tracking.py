#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from config.backtest_configs import get_config
from backtest.backtest_engine import BacktestEngine
import pandas as pd

def simple_yunlv_tracking():
    """简化版云铝股份持股变化跟踪"""
    print("🔍 跟踪云铝股份(000807)的持股变化...")
    
    # 1. 创建回测引擎并运行
    print("\n🚀 运行回测...")
    config = get_config('csv')
    engine = BacktestEngine(config)
    
    try:
        engine.run_backtest()
        print("✅ 回测完成")
    except Exception as e:
        print(f"❌ 回测失败: {e}")
        return
    
    # 2. 获取回测结果
    print("\n📊 获取回测结果...")
    backtest_results = engine.get_backtest_results()
    
    # 检查数据结构
    print(f"📋 回测结果类型: {type(backtest_results)}")
    if isinstance(backtest_results, dict):
        print(f"📋 回测结果键: {list(backtest_results.keys())}")
    
    # 3. 获取portfolio历史
    portfolio_history = backtest_results.get('portfolio_history')
    print(f"📊 Portfolio历史类型: {type(portfolio_history)}")
    
    if isinstance(portfolio_history, pd.DataFrame):
        print(f"📊 Portfolio历史记录数: {len(portfolio_history)}")
        print(f"📊 Portfolio历史列: {list(portfolio_history.columns)}")
        
        # 检查索引是否是日期
        if hasattr(portfolio_history.index, 'name'):
            print(f"📊 索引名称: {portfolio_history.index.name}")
        
        # 显示前几行数据结构
        print(f"\n📊 前3行数据结构:")
        for i in range(min(3, len(portfolio_history))):
            row = portfolio_history.iloc[i]
            print(f"  行{i}: 索引={row.name}, 列数={len(row)}")
            if 'positions' in row:
                positions = row['positions']
                yunlv_shares = positions.get('000807', 0) if isinstance(positions, dict) else 0
                print(f"    云铝股份持股: {yunlv_shares}")
    
    # 4. 跟踪云铝股份变化
    print(f"\n📈 云铝股份持股变化跟踪:")
    print("=" * 60)
    
    if isinstance(portfolio_history, pd.DataFrame) and not portfolio_history.empty:
        yunlv_changes = []
        
        for i, (date_idx, row) in enumerate(portfolio_history.iterrows()):
            # 获取日期
            if hasattr(date_idx, 'strftime'):
                date_str = date_idx.strftime('%Y-%m-%d')
            else:
                date_str = str(date_idx)
            
            # 获取持股数量
            positions = row.get('positions', {})
            if isinstance(positions, dict):
                yunlv_shares = positions.get('000807', 0)
            else:
                yunlv_shares = 0
            
            # 获取其他信息
            cash = row.get('cash', 0)
            total_value = row.get('total_value', 0)
            
            yunlv_changes.append({
                'date': date_str,
                'shares': yunlv_shares,
                'cash': cash,
                'total_value': total_value
            })
        
        # 打印变化记录
        print(f"{'日期':<12} {'持股数量':<12} {'现金余额':<15} {'总资产':<15}")
        print("-" * 60)
        
        prev_shares = None
        change_count = 0
        
        for record in yunlv_changes:
            date = record['date']
            shares = record['shares']
            cash = record['cash']
            total_value = record['total_value']
            
            # 检查变化
            change_indicator = ""
            if prev_shares is not None and shares != prev_shares:
                change = shares - prev_shares
                change_indicator = f" ({change:+,})"
                change_count += 1
            
            print(f"{date:<12} {shares:,}股{change_indicator:<8} ¥{cash:,.0f}{'':>6} ¥{total_value:,.0f}")
            prev_shares = shares
        
        # 5. 总结
        print("\n" + "=" * 60)
        print("📊 云铝股份持股变化总结:")
        
        if yunlv_changes:
            initial_shares = yunlv_changes[0]['shares']
            final_shares = yunlv_changes[-1]['shares']
            total_change = final_shares - initial_shares
            
            print(f"🏁 初始持股: {initial_shares:,}股")
            print(f"🏆 最终持股: {final_shares:,}股")
            print(f"📈 总变化: {total_change:+,}股")
            print(f"📊 变化次数: {change_count}次")
            
            if total_change == 0:
                print("✅ 持股数量在整个回测期间保持不变")
            else:
                change_rate = (total_change / initial_shares) * 100 if initial_shares > 0 else 0
                print(f"📈 变化率: {change_rate:+.2f}%")
    
    # 6. 验证交易记录
    print(f"\n📋 验证交易记录:")
    transaction_history = backtest_results.get('transaction_history', [])
    
    if isinstance(transaction_history, list):
        yunlv_transactions = [t for t in transaction_history if t.get('stock_code') == '000807']
        print(f"📊 云铝股份交易记录数: {len(yunlv_transactions)}")
        
        if len(yunlv_transactions) == 0:
            print("✅ 确认：云铝股份在回测期间没有发生任何交易")
        else:
            print("📊 云铝股份交易详情:")
            for i, trade in enumerate(yunlv_transactions, 1):
                date = trade.get('date', 'N/A')
                trade_type = trade.get('type', 'N/A')
                shares = trade.get('shares', 0)
                price = trade.get('price', 0)
                print(f"  交易{i}: {date} {trade_type} {shares:,}股 @ ¥{price:.2f}")
    
    print(f"\n🎉 云铝股份持股变化跟踪完成!")

if __name__ == "__main__":
    simple_yunlv_tracking()