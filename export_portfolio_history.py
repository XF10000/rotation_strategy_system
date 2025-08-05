#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from config.backtest_configs import get_config
from backtest.backtest_engine import BacktestEngine
import pandas as pd
from datetime import datetime

def export_portfolio_history():
    """导出portfolio_history的所有记录到CSV文件"""
    print("🔍 开始导出portfolio_history记录...")
    
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
    
    # 2. 获取portfolio_history
    print("\n📊 获取portfolio_history...")
    backtest_results = engine.get_backtest_results()
    portfolio_history = backtest_results.get('portfolio_history')
    
    if portfolio_history is None or portfolio_history.empty:
        print("❌ portfolio_history为空")
        return
    
    print(f"📊 Portfolio历史记录总数: {len(portfolio_history)}")
    print(f"📊 Portfolio历史列: {list(portfolio_history.columns)}")
    
    # 3. 准备导出数据
    print("\n📝 准备导出数据...")
    export_data = []
    
    for i, (date_idx, row) in enumerate(portfolio_history.iterrows()):
        # 获取日期
        if hasattr(date_idx, 'strftime'):
            date_str = date_idx.strftime('%Y-%m-%d')
        else:
            date_str = str(date_idx)
        
        # 获取基本信息
        total_value = row.get('total_value', 0)
        cash = row.get('cash', 0)
        stock_value = row.get('stock_value', 0)
        positions = row.get('positions', {})
        
        # 创建基础记录
        base_record = {
            '序号': i + 1,
            '日期': date_str,
            '总资产': total_value,
            '现金': cash,
            '股票市值': stock_value,
        }
        
        # 添加各股票持仓信息
        stock_codes = ['601088', '601225', '600985', '002738', '000933', '000807', '601898', '002460', '600079', '603345']
        for stock_code in stock_codes:
            shares = positions.get(stock_code, 0) if isinstance(positions, dict) else 0
            base_record[f'{stock_code}_持股'] = shares
        
        export_data.append(base_record)
    
    # 4. 创建DataFrame并导出
    print("\n💾 导出到CSV文件...")
    df = pd.DataFrame(export_data)
    
    # 生成文件名
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    filename = f'portfolio_history_export_{timestamp}.csv'
    
    # 导出到CSV
    df.to_csv(filename, index=False, encoding='utf-8-sig')
    print(f"✅ 已导出到文件: {filename}")
    
    # 5. 显示摘要信息
    print(f"\n📊 导出摘要:")
    print(f"   总记录数: {len(df)}")
    print(f"   日期范围: {df['日期'].iloc[0]} 到 {df['日期'].iloc[-1]}")
    print(f"   列数: {len(df.columns)}")
    
    # 6. 显示云铝股份的持股变化摘要
    print(f"\n📈 云铝股份(000807)持股变化摘要:")
    yunlv_column = '000807_持股'
    if yunlv_column in df.columns:
        initial_shares = df[yunlv_column].iloc[0]
        final_shares = df[yunlv_column].iloc[-1]
        unique_values = df[yunlv_column].unique()
        
        print(f"   初始持股: {initial_shares:,}股")
        print(f"   最终持股: {final_shares:,}股")
        print(f"   变化次数: {len(unique_values) - 1}次")
        print(f"   所有持股数量: {sorted(unique_values)}")
        
        # 找出变化的日期
        changes = []
        prev_shares = None
        for idx, row in df.iterrows():
            current_shares = row[yunlv_column]
            if prev_shares is not None and current_shares != prev_shares:
                changes.append({
                    '日期': row['日期'],
                    '从': prev_shares,
                    '到': current_shares,
                    '变化': current_shares - prev_shares
                })
            prev_shares = current_shares
        
        if changes:
            print(f"   持股变化详情:")
            for change in changes:
                print(f"     {change['日期']}: {change['从']:,} → {change['到']:,} ({change['变化']:+,})")
        else:
            print(f"   ✅ 持股数量在整个回测期间保持不变")
    
    # 7. 显示前5行和后5行数据预览
    print(f"\n📋 数据预览 (前5行):")
    print(df.head().to_string(index=False))
    
    print(f"\n📋 数据预览 (后5行):")
    print(df.tail().to_string(index=False))
    
    print(f"\n🎉 Portfolio历史记录导出完成!")
    print(f"📁 文件位置: {os.path.abspath(filename)}")

if __name__ == "__main__":
    export_portfolio_history()