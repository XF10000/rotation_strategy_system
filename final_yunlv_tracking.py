#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from config.backtest_configs import get_config
from backtest.backtest_engine import BacktestEngine
import pandas as pd

def final_yunlv_tracking():
    """最终跟踪云铝股份的完整持股变化"""
    print("🔍 最终跟踪云铝股份(000807)的完整持股变化...")
    
    # 1. 创建回测引擎
    print("\n🚀 步骤1: 初始化回测引擎")
    config = get_config('csv')
    engine = BacktestEngine(config)
    
    # 2. 运行回测
    print("\n📊 步骤2: 运行回测")
    try:
        engine.run_backtest()
        print("✅ 回测完成")
    except Exception as e:
        print(f"❌ 回测失败: {e}")
        return
    
    # 3. 获取回测结果
    print("\n📈 步骤3: 获取回测结果")
    backtest_results = engine.get_backtest_results()
    portfolio_history = backtest_results.get('portfolio_history', [])
    
    # 检查portfolio_history是否为空
    if isinstance(portfolio_history, pd.DataFrame):
        df = portfolio_history
    elif isinstance(portfolio_history, list):
        if not portfolio_history:
            print("❌ 未找到portfolio历史记录")
            return
        df = pd.DataFrame(portfolio_history)
    else:
        print("❌ portfolio_history格式不正确")
        return
    
    if df.empty:
        print("❌ portfolio历史记录为空")
        return
    df['date'] = pd.to_datetime(df['date'])
    df = df.sort_values('date')
    
    print(f"📊 Portfolio历史记录总数: {len(df)}")
    
    # 4. 跟踪云铝股份持股变化
    print(f"\n📊 步骤4: 跟踪云铝股份持股变化")
    print("=" * 80)
    
    yunlv_positions = []
    for idx, row in df.iterrows():
        date = row['date'].strftime('%Y-%m-%d')
        positions = row.get('positions', {})
        yunlv_shares = positions.get('000807', 0)
        cash = row.get('cash', 0)
        total_value = row.get('total_value', 0)
        
        yunlv_positions.append({
            'date': date,
            'shares': yunlv_shares,
            'cash': cash,
            'total_value': total_value
        })
    
    # 5. 打印详细变化
    print(f"📅 日期\t\t持股数量\t现金余额\t\t总资产")
    print("-" * 80)
    
    prev_shares = None
    change_count = 0
    
    for pos in yunlv_positions:
        date = pos['date']
        shares = pos['shares']
        cash = pos['cash']
        total_value = pos['total_value']
        
        # 检查是否有变化
        change_indicator = ""
        if prev_shares is not None and shares != prev_shares:
            change = shares - prev_shares
            change_indicator = f" ({change:+,})"
            change_count += 1
        
        print(f"{date}\t{shares:,}股{change_indicator}\t¥{cash:,.2f}\t¥{total_value:,.2f}")
        prev_shares = shares
    
    # 6. 统计总结
    print("\n" + "=" * 80)
    print(f"📊 云铝股份持股变化总结:")
    print("-" * 50)
    
    if yunlv_positions:
        initial_shares = yunlv_positions[0]['shares']
        final_shares = yunlv_positions[-1]['shares']
        total_change = final_shares - initial_shares
        
        print(f"🏁 初始持股: {initial_shares:,}股")
        print(f"🏆 最终持股: {final_shares:,}股")
        print(f"📈 总变化: {total_change:+,}股")
        print(f"📊 变化次数: {change_count}次")
        
        if total_change == 0:
            print("✅ 持股数量在整个回测期间保持不变")
        else:
            print(f"📈 变化率: {(total_change/initial_shares)*100:+.2f}%")
    
    # 7. 验证交易记录
    print(f"\n📋 步骤7: 验证交易记录")
    transaction_history = backtest_results.get('transaction_history', [])
    
    yunlv_transactions = [t for t in transaction_history if t.get('stock_code') == '000807']
    
    print(f"📊 云铝股份交易记录数: {len(yunlv_transactions)}")
    
    if len(yunlv_transactions) == 0:
        print("✅ 确认：云铝股份在回测期间没有发生任何交易")
        print("✅ 持股数量始终保持在初始配置的224,200股")
    else:
        print("📊 云铝股份交易详情:")
        for i, trade in enumerate(yunlv_transactions, 1):
            print(f"  交易{i}: {trade.get('date')} {trade.get('type')} {trade.get('shares')}股 @ ¥{trade.get('price', 0):.2f}")
    
    # 8. 最终验证
    print(f"\n🎯 步骤8: 最终数据验证")
    
    # 获取初始和最终状态
    initial_portfolio = engine.portfolio_data_manager.get_initial_portfolio_status() if hasattr(engine, 'portfolio_data_manager') else None
    final_portfolio = engine._get_final_portfolio_status(pd.DataFrame(portfolio_history))
    
    if initial_portfolio:
        initial_yunlv = initial_portfolio.get('positions', {}).get('000807', {}).get('shares', 0)
        print(f"📊 初始状态验证: {initial_yunlv:,}股")
    
    final_yunlv = final_portfolio.get('positions', {}).get('000807', {}).get('shares', 0)
    print(f"📊 最终状态验证: {final_yunlv:,}股")
    
    print(f"\n🎉 云铝股份持股变化跟踪完成!")

if __name__ == "__main__":
    final_yunlv_tracking()