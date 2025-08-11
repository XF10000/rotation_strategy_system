#!/usr/bin/env python3
"""
测试脚本：调试基准持仓数据传递问题
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from backtest.backtest_engine import BacktestEngine
from config.csv_config_loader import create_csv_config

def test_benchmark_portfolio_data():
    """测试基准持仓数据是否被正确收集和传递"""
    print("🔍 开始测试基准持仓数据...")
    
    # 获取配置
    config = create_csv_config()
    
    # 创建回测引擎
    engine = BacktestEngine(config)
    
    # 运行回测
    print("📊 运行回测...")
    success = engine.run_backtest()
    
    if not success:
        print("❌ 回测失败")
        return
    
    print("✅ 回测完成，检查基准持仓数据...")
    
    # 检查基准持仓数据是否存在
    benchmark_portfolio_data = getattr(engine, 'benchmark_portfolio_data', {})
    print(f"🔍 基准持仓数据: {list(benchmark_portfolio_data.keys()) if benchmark_portfolio_data else 'None'}")
    
    if benchmark_portfolio_data:
        print(f"  总资产: ¥{benchmark_portfolio_data.get('total_value', 0):,.2f}")
        print(f"  现金: ¥{benchmark_portfolio_data.get('cash', 0):,.2f}")
        print(f"  股票市值: ¥{benchmark_portfolio_data.get('stock_value', 0):,.2f}")
        print(f"  分红收入: ¥{benchmark_portfolio_data.get('dividend_income', 0):,.2f}")
        positions = benchmark_portfolio_data.get('positions', {})
        print(f"  持仓数量: {len(positions)}只股票")
        
        for stock_code, position in positions.items():
            print(f"    {stock_code}: {position.get('current_shares', 0):,.0f}股, 市值¥{position.get('end_value', 0):,.0f}")
    else:
        print("❌ 基准持仓数据为空")
    
    # 获取回测结果
    backtest_results = engine.get_backtest_results()
    benchmark_data_in_results = backtest_results.get('benchmark_portfolio_data', {})
    print(f"🔍 回测结果中的基准持仓数据: {list(benchmark_data_in_results.keys()) if benchmark_data_in_results else 'None'}")
    
    # 准备集成结果
    integrated_results = engine._prepare_integrated_results(backtest_results)
    benchmark_data_in_integrated = integrated_results.get('benchmark_portfolio_data', {})
    print(f"🔍 集成结果中的基准持仓数据: {list(benchmark_data_in_integrated.keys()) if benchmark_data_in_integrated else 'None'}")

if __name__ == "__main__":
    test_benchmark_portfolio_data()
