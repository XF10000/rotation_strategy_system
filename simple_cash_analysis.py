#!/usr/bin/env python3
"""
简化的现金分析工具
"""

import pandas as pd
import sys
import os

sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from backtest.backtest_engine import BacktestEngine
from config.csv_config_loader import create_csv_config

def simple_analysis():
    """简单分析最终现金状态"""
    
    print("🔍 简化现金状态分析")
    print("=" * 40)
    
    try:
        # 运行回测
        config = create_csv_config()
        engine = BacktestEngine(config)
        success = engine.run_backtest()
        
        if not success:
            print("❌ 回测失败")
            return
        
        results = engine.get_backtest_results()
        portfolio_history = results['portfolio_history']
        
        print("📊 Portfolio History 基本信息:")
        print(f"   数据类型: {type(portfolio_history)}")
        print(f"   形状: {portfolio_history.shape}")
        print(f"   索引类型: {type(portfolio_history.index)}")
        print(f"   列名: {list(portfolio_history.columns)}")
        
        if len(portfolio_history) > 0:
            print(f"   索引样例: {portfolio_history.index[:3].tolist()}")
            
            # 显示最后几行数据
            print("\n📈 最后几行数据:")
            last_rows = portfolio_history.tail(3)
            for idx, row in last_rows.iterrows():
                if hasattr(idx, 'strftime'):
                    date_str = idx.strftime('%Y-%m-%d')
                else:
                    date_str = str(idx)
                    
                total_value = row.get('total_value', 0)
                cash = row.get('cash', 0)
                cash_ratio = (cash / total_value * 100) if total_value > 0 else 0
                
                print(f"   {date_str}: 总资产¥{total_value:,.0f}, 现金¥{cash:,.0f} ({cash_ratio:.1f}%)")
            
            # 分析最终状态
            final_row = portfolio_history.iloc[-1]
            final_cash = final_row.get('cash', 0)
            final_total = final_row.get('total_value', 0)
            
            # 长江电力买入需求
            changjiang_price = 27.63
            required_5pct = final_total * 0.05
            required_shares = int(required_5pct / changjiang_price / 100) * 100
            actual_cost = required_shares * changjiang_price
            
            print(f"\n🎯 长江电力买入分析:")
            print(f"   最终现金: ¥{final_cash:,.0f}")
            print(f"   最终总资产: ¥{final_total:,.0f}")
            print(f"   5%资产需求: ¥{required_5pct:,.0f}")
            print(f"   实际买入成本: ¥{actual_cost:,.0f}")
            print(f"   资金充足性: {'✅ 充足' if final_cash >= actual_cost else '❌ 不足'}")
            
            if final_cash >= actual_cost:
                print(f"   剩余现金: ¥{final_cash - actual_cost:,.0f}")
            else:
                print(f"   资金缺口: ¥{actual_cost - final_cash:,.0f}")
        
    except Exception as e:
        print(f"❌ 分析失败: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    simple_analysis()