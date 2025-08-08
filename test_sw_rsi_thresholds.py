"""
测试申万二级行业RSI阈值计算功能
"""

import sys
import os
sys.path.append('.')

from indicators.sw_industry_rsi_thresholds import SWIndustryRSIThresholds
import pandas as pd
import logging

# 设置日志级别
logging.basicConfig(level=logging.INFO)

def test_single_industry():
    """测试单个行业的数据获取"""
    print("测试单个行业数据获取...")
    
    calculator = SWIndustryRSIThresholds()
    
    # 测试获取电力行业数据
    test_code = '801360'  # 电力
    df = calculator.get_industry_weekly_data(test_code)
    
    if not df.empty:
        print(f"成功获取 {test_code} 数据，共 {len(df)} 周")
        print(f"RSI范围: {df['rsi14'].min():.2f} - {df['rsi14'].max():.2f}")
        print(f"最新RSI: {df['rsi14'].iloc[-1]:.2f}")
        return True
    else:
        print(f"获取 {test_code} 数据失败")
        return False

def test_industry_codes():
    """测试行业代码获取"""
    print("测试行业代码获取...")
    
    calculator = SWIndustryRSIThresholds()
    industry_df = calculator.get_sw_industry_codes()
    
    print(f"获取到 {len(industry_df)} 个申万二级行业")
    print("前10个行业:")
    print(industry_df.head(10))
    
    return len(industry_df) > 0

def test_full_calculation():
    """测试完整计算流程（少量行业）"""
    print("测试完整计算流程...")
    
    # 创建一个测试用的计算器，只处理几个行业
    calculator = SWIndustryRSIThresholds()
    
    # 手动指定几个测试行业
    test_industries = pd.DataFrame({
        '指数代码': ['801360', '801010', '801220'],  # 电力、农业、钢铁
        '指数名称': ['电力', '农业', '钢铁']
    })
    
    # 临时替换获取行业代码的方法
    original_method = calculator.get_sw_industry_codes
    calculator.get_sw_industry_codes = lambda: test_industries
    
    try:
        result_df = calculator.run(save_file=False)
        print(f"成功计算 {len(result_df)} 个行业的阈值")
        print("\n计算结果:")
        print(result_df.to_string())
        return True
    except Exception as e:
        print(f"计算失败: {e}")
        return False
    finally:
        # 恢复原方法
        calculator.get_sw_industry_codes = original_method

def main():
    """运行所有测试"""
    print("开始测试申万二级行业RSI阈值计算功能")
    print("="*60)
    
    tests = [
        ("行业代码获取", test_industry_codes),
        ("单个行业数据", test_single_industry),
        ("完整计算流程", test_full_calculation),
    ]
    
    results = []
    for test_name, test_func in tests:
        print(f"\n{test_name}测试:")
        print("-" * 30)
        try:
            success = test_func()
            results.append((test_name, success))
            print(f"✓ {test_name}测试{'成功' if success else '失败'}")
        except Exception as e:
            print(f"✗ {test_name}测试出错: {e}")
            results.append((test_name, False))
    
    print("\n" + "="*60)
    print("测试结果汇总:")
    for test_name, success in results:
        status = "✓ 成功" if success else "✗ 失败"
        print(f"  {test_name}: {status}")
    
    all_passed = all(success for _, success in results)
    print(f"\n总体结果: {'所有测试通过' if all_passed else '部分测试失败'}")

if __name__ == "__main__":
    main()