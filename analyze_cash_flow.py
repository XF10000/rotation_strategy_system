#!/usr/bin/env python3
"""
现金流和仓位状态分析工具
分析特定日期的现金状况和买入决策
"""

import pandas as pd
import sys
import os
from datetime import datetime

sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from backtest.backtest_engine import BacktestEngine
from config.csv_config_loader import create_csv_config

def analyze_cash_and_positions(target_date: str):
    """分析特定日期的现金和仓位状态"""
    
    print(f"🔍 分析 {target_date} 的现金流和仓位状态")
    print("=" * 60)
    
    try:
        # 运行完整回测到目标日期
        config = create_csv_config()
        engine = BacktestEngine(config)
        
        # 运行回测
        print("🏃 运行完整回测...")
        success = engine.run_backtest()
        
        if not success:
            print("❌ 回测运行失败")
            return
        
        # 获取回测结果
        results = engine.get_backtest_results()
        portfolio_history = results['portfolio_history']
        transaction_history = results['transaction_history']
        
        print("✅ 回测完成，分析结果...")
        print()
        
        # 查找目标日期附近的数据
        target_dt = pd.to_datetime(target_date)
        
        # 分析交易历史
        print("📊 交易历史摘要:")
        if not transaction_history.empty:
            for _, trade in transaction_history.iterrows():
                trade_date = pd.to_datetime(trade['date'])
                print(f"   {trade_date.strftime('%Y-%m-%d')}: {trade['type']} {trade['stock_code']} "
                      f"{trade['shares']:,}股 @ {trade['price']:.2f}元")
        
        print()
        
        # 查看portfolio_history的结构
        print("📋 Portfolio History 结构:")
        print(f"   列名: {list(portfolio_history.columns)}")
        print(f"   数据行数: {len(portfolio_history)}")
        if len(portfolio_history) > 0:
            print(f"   索引类型: {type(portfolio_history.index)}")
            print(f"   前几行索引: {portfolio_history.index[:5].tolist()}")
        print()
        
        # 检查索引是否是日期
        if hasattr(portfolio_history.index, 'strftime'):
            # 索引是日期
            date_index = portfolio_history.index
        elif 'date' in portfolio_history.columns:
            # 有date列
            portfolio_history['date'] = pd.to_datetime(portfolio_history['date'])
            date_index = portfolio_history['date']
        else:
            print("❌ 未找到日期信息")
            return
        
        # 查找目标日期前后的记录
        date_range = portfolio_history[
            (portfolio_history['date'] >= target_dt - pd.Timedelta(days=14)) &
            (portfolio_history['date'] <= target_dt + pd.Timedelta(days=14))
        ].copy()
        
        if date_range.empty:
            print("   ❌ 未找到目标日期附近的数据")
            return
        
        # 显示目标日期前后的状态
        for _, row in date_range.iterrows():
            date_str = row['date'].strftime('%Y-%m-%d')
            total_value = row['total_value']
            cash = row['cash']
            cash_ratio = (cash / total_value * 100) if total_value > 0 else 0
            
            marker = "🎯" if row['date'].strftime('%Y-%m-%d') == target_date else "  "
            print(f"{marker} {date_str}: 总资产 ¥{total_value:,.0f}, "
                  f"现金 ¥{cash:,.0f} ({cash_ratio:.1f}%)")
        
        print()
        
        # 分析长江电力的具体情况
        print("🔍 长江电力(600900)买入可行性分析:")
        
        # 找到最接近目标日期的记录
        target_row = date_range.loc[
            (date_range['date'] - target_dt).abs().idxmin()
        ]
        
        target_cash = target_row['cash']
        target_total = target_row['total_value']
        
        # 长江电力的买入需求
        changjiang_price = 27.63  # 2025-08-15的价格
        dcf_value = 39.00
        value_ratio = changjiang_price / dcf_value
        
        # 计算买入金额（5%总资产）
        required_amount = target_total * 0.05
        required_shares = int(required_amount / changjiang_price / 100) * 100
        actual_amount = required_shares * changjiang_price
        
        print(f"   当日现金: ¥{target_cash:,.0f}")
        print(f"   总资产: ¥{target_total:,.0f}")
        print(f"   长江电力价格: ¥{changjiang_price:.2f}")
        print(f"   价值比: {value_ratio:.3f} ({value_ratio*100:.1f}%)")
        print(f"   需要金额: ¥{required_amount:,.0f} (5%总资产)")
        print(f"   计算股数: {required_shares:,}股")
        print(f"   实际金额: ¥{actual_amount:,.0f}")
        print(f"   资金充足: {'✅ 是' if target_cash >= actual_amount else '❌ 否'}")
        
        if target_cash >= actual_amount:
            shortage = 0
            print(f"   剩余现金: ¥{target_cash - actual_amount:,.0f}")
        else:
            shortage = actual_amount - target_cash
            print(f"   资金缺口: ¥{shortage:,.0f}")
        
        print()
        
        # 分析当时的持仓状况
        print("📈 当时持仓状况:")
        
        # 检查portfolio_history中的持仓列
        stock_columns = [col for col in target_row.index if col.startswith('position_') and col != 'position_cash']
        
        total_stock_value = 0
        for col in stock_columns:
            if target_row[col] > 0:
                stock_code = col.replace('position_', '')
                shares = target_row[col]
                
                # 尝试获取当天价格（简化处理）
                if stock_code in ['601088', '601225', '600985', '002738', '002460', 
                                 '000933', '000807', '600079', '603345', '601898', '600900', '601919']:
                    # 使用一些估算价格
                    estimated_prices = {
                        '601088': 36, '601225': 19, '600985': 12, '002738': 40, 
                        '002460': 35, '000933': 18, '000807': 15, '600079': 20,
                        '603345': 110, '601898': 10, '600900': 28, '601919': 8
                    }
                    price = estimated_prices.get(stock_code, 20)
                    value = shares * price
                    total_stock_value += value
                    value_ratio = value / target_total * 100
                    
                    print(f"   {stock_code}: {shares:,}股, 估值¥{value:,.0f} ({value_ratio:.1f}%)")
        
        stock_ratio = total_stock_value / target_total * 100
        print(f"   总持仓比例: {stock_ratio:.1f}%")
        print(f"   现金比例: {target_cash/target_total*100:.1f}%")
        
        print()
        print("🎯 结论:")
        if target_cash >= actual_amount:
            print("   ✅ 资金充足，应该可以买入长江电力")
            print("   🤔 需要进一步分析为什么系统没有买入")
        else:
            print("   ❌ 资金不足，无法买入长江电力")
        
    except Exception as e:
        print(f"❌ 分析失败: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    if len(sys.argv) != 2:
        print("用法: python3 analyze_cash_flow.py YYYY-MM-DD")
        print("例如: python3 analyze_cash_flow.py 2025-08-15")
        sys.exit(1)
    
    target_date = sys.argv[1]
    analyze_cash_and_positions(target_date)