#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from main import main
import pandas as pd
import logging

# 设置日志记录
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

def track_yunlv_changes():
    """跟踪云铝股份(000807)在整个回测过程中的持股数量变化"""
    print("🔍 开始跟踪云铝股份(000807)在回测过程中的持股数量变化...")
    
    # 运行回测
    try:
        print("\n🚀 运行回测...")
        main()
        print("✅ 回测完成")
    except Exception as e:
        print(f"❌ 回测失败: {e}")
        return
    
    # 读取最新的交易记录CSV文件
    print("\n📊 读取交易记录...")
    csv_files = []
    for file in os.listdir('reports'):
        if file.startswith('detailed_trading_records_') and file.endswith('.csv'):
            csv_files.append(file)
    
    if not csv_files:
        print("❌ 未找到交易记录文件")
        return
    
    # 使用最新的CSV文件
    latest_csv = sorted(csv_files)[-1]
    csv_path = os.path.join('reports', latest_csv)
    print(f"📄 使用交易记录文件: {latest_csv}")
    
    try:
        # 读取交易记录
        df = pd.read_csv(csv_path, encoding='utf-8')
        print(f"📈 总交易记录数: {len(df)}")
        
        # 筛选云铝股份的交易记录
        yunlv_trades = df[df['股票代码'] == '000807'].copy()
        print(f"📈 云铝股份交易记录数: {len(yunlv_trades)}")
        
        if len(yunlv_trades) == 0:
            print("ℹ️ 云铝股份在回测期间没有发生交易")
            print("📊 持股数量保持不变: 224,200股")
            return
        
        # 按日期排序
        yunlv_trades['交易日期'] = pd.to_datetime(yunlv_trades['交易日期'])
        yunlv_trades = yunlv_trades.sort_values('交易日期')
        
        print(f"\n📊 云铝股份交易详情:")
        print("=" * 80)
        
        # 初始持股数量
        current_position = 224200  # 从之前的计算得出
        print(f"🏁 初始持股数量: {current_position:,}股")
        print("-" * 80)
        
        # 逐笔跟踪交易变化
        for idx, trade in yunlv_trades.iterrows():
            trade_date = trade['交易日期'].strftime('%Y-%m-%d')
            trade_type = trade['交易类型']
            shares = int(trade['交易数量'])
            price = float(trade['交易价格'])
            position_after = int(trade['交易后持仓'])
            
            # 计算持股变化
            if trade_type == '买入':
                position_change = shares
                current_position += shares
                change_symbol = "+"
            else:  # 卖出
                position_change = -shares
                current_position -= shares
                change_symbol = "-"
            
            print(f"📅 {trade_date}")
            print(f"   交易类型: {trade_type}")
            print(f"   交易数量: {change_symbol}{shares:,}股")
            print(f"   交易价格: ¥{price:.2f}")
            print(f"   交易后持仓: {position_after:,}股")
            print(f"   计算持仓: {current_position:,}股")
            
            # 验证数据一致性
            if current_position != position_after:
                print(f"   ⚠️ 数据不一致! 计算值({current_position:,}) != 记录值({position_after:,})")
            else:
                print(f"   ✅ 数据一致")
            
            print("-" * 80)
        
        # 最终持股统计
        final_position = yunlv_trades.iloc[-1]['交易后持仓'] if len(yunlv_trades) > 0 else 224200
        total_change = final_position - 224200
        
        print(f"\n📊 云铝股份持股变化总结:")
        print("=" * 50)
        print(f"🏁 初始持股: 224,200股")
        print(f"🏆 最终持股: {final_position:,}股")
        print(f"📈 总变化: {total_change:+,}股")
        print(f"📊 变化率: {(total_change/224200)*100:+.2f}%")
        
        # 交易统计
        buy_trades = yunlv_trades[yunlv_trades['交易类型'] == '买入']
        sell_trades = yunlv_trades[yunlv_trades['交易类型'] == '卖出']
        
        print(f"\n📊 交易统计:")
        print(f"   买入次数: {len(buy_trades)}次")
        if len(buy_trades) > 0:
            total_buy_shares = buy_trades['交易数量'].sum()
            avg_buy_price = (buy_trades['交易数量'] * buy_trades['交易价格']).sum() / total_buy_shares
            print(f"   买入总量: {total_buy_shares:,}股")
            print(f"   平均买入价: ¥{avg_buy_price:.2f}")
        
        print(f"   卖出次数: {len(sell_trades)}次")
        if len(sell_trades) > 0:
            total_sell_shares = sell_trades['交易数量'].sum()
            avg_sell_price = (sell_trades['交易数量'] * sell_trades['交易价格']).sum() / total_sell_shares
            print(f"   卖出总量: {total_sell_shares:,}股")
            print(f"   平均卖出价: ¥{avg_sell_price:.2f}")
        
        print("\n🎉 云铝股份持股变化跟踪完成!")
        
    except Exception as e:
        print(f"❌ 读取交易记录失败: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    track_yunlv_changes()