#!/usr/bin/env python3
"""
测试脚本：验证基准持仓状态替换方法是否正常工作
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from backtest.enhanced_report_generator_integrated_fixed import IntegratedReportGenerator

def test_benchmark_replacement():
    """测试基准持仓状态替换方法"""
    print("🔍 测试基准持仓状态替换方法...")
    
    # 创建报告生成器
    generator = IntegratedReportGenerator()
    
    # 创建测试模板
    test_template = """
    <div>
        <span>总资产: ¥BENCHMARK_TOTAL_VALUE</span>
        <span>现金: ¥BENCHMARK_CASH (BENCHMARK_CASH_RATIO%)</span>
        <span>股票市值: ¥BENCHMARK_STOCK_VALUE (BENCHMARK_STOCK_RATIO%)</span>
        <table>
            <tbody>
                BENCHMARK_POSITION_COMPARISON_TABLE
            </tbody>
        </table>
    </div>
    """
    
    # 创建测试基准持仓数据
    test_benchmark_data = {
        'total_value': 30000000.0,
        'cash': 4500000.0,
        'stock_value': 25500000.0,
        'dividend_income': 500000.0,
        'positions': {
            '601088': {
                'initial_shares': 80000,
                'current_shares': 85000,
                'start_price': 18.5,
                'end_price': 38.43,
                'start_value': 1480000,
                'end_value': 3266550,
                'dividend_income': 50000,
                'return_rate': 0.25
            },
            '600985': {
                'initial_shares': 120000,
                'current_shares': 125000,
                'start_price': 12.0,
                'end_price': 13.27,
                'start_value': 1440000,
                'end_value': 1658750,
                'dividend_income': 30000,
                'return_rate': 0.18
            }
        }
    }
    
    print(f"📊 测试数据: {len(test_benchmark_data.get('positions', {}))}只股票")
    
    # 调用替换方法
    try:
        result_template = generator._replace_benchmark_portfolio_safe(test_template, test_benchmark_data)
        
        print("✅ 替换方法执行成功")
        print("📋 替换结果:")
        print(result_template)
        
        # 检查是否替换成功
        if "BENCHMARK_TOTAL_VALUE" in result_template:
            print("❌ 总资产占位符未被替换")
        else:
            print("✅ 总资产占位符已替换")
            
        if "BENCHMARK_POSITION_COMPARISON_TABLE" in result_template:
            print("❌ 持仓表格占位符未被替换")
        else:
            print("✅ 持仓表格占位符已替换")
            
    except Exception as e:
        print(f"❌ 替换方法执行失败: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    test_benchmark_replacement()
