#!/usr/bin/env python3
"""
回测数据获取测试脚本
模拟实际回测场景的数据获取
"""

import sys
import logging
from datetime import datetime
from data.data_fetcher import AkshareDataFetcher

# 设置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

def test_backtest_scenario():
    """测试回测场景的数据获取"""
    print("🔍 测试回测场景数据获取...")
    
    # 从投资组合配置中获取股票列表
    portfolio_stocks = [
        ('601088', '中国神华'),
        ('601225', '陕西煤业'),
        ('600985', '淮北矿业'),
        ('002738', '中矿资源'),
        ('002460', '赣锋锂业'),
        ('000933', '神火股份'),
        ('000807', '云铝股份'),
        ('600079', '人福医药'),
        ('603345', '安井食品'),
        ('601898', '中煤能源'),
        ('600900', '长江电力')
    ]
    
    # 回测日期范围（与实际回测相同）
    start_date = "2021-01-08"
    end_date = "2025-07-25"
    
    fetcher = AkshareDataFetcher()
    
    success_count = 0
    failed_stocks = []
    
    print(f"📊 测试期间: {start_date} 到 {end_date}")
    print(f"📈 股票数量: {len(portfolio_stocks)}")
    print("-" * 60)
    
    for i, (code, name) in enumerate(portfolio_stocks, 1):
        print(f"\n[{i}/{len(portfolio_stocks)}] 测试 {code} ({name})")
        
        try:
            # 获取日线数据
            daily_data = fetcher.get_stock_data(code, start_date, end_date, 'daily')
            
            if daily_data is not None and not daily_data.empty:
                print(f"✅ 成功获取 {code} 数据: {len(daily_data)} 条记录")
                print(f"   数据范围: {daily_data.index[0].strftime('%Y-%m-%d')} 到 {daily_data.index[-1].strftime('%Y-%m-%d')}")
                success_count += 1
            else:
                print(f"❌ {code} 数据为空")
                failed_stocks.append((code, name, "数据为空"))
                
        except Exception as e:
            print(f"❌ {code} 获取失败: {str(e)}")
            failed_stocks.append((code, name, str(e)))
        
        # 添加延迟避免请求过快
        import time
        time.sleep(1)
    
    # 总结结果
    print(f"\n{'='*60}")
    print(f"📊 回测数据获取测试总结")
    print(f"{'='*60}")
    print(f"成功: {success_count}/{len(portfolio_stocks)}")
    print(f"失败: {len(failed_stocks)}/{len(portfolio_stocks)}")
    
    if failed_stocks:
        print(f"\n❌ 失败的股票:")
        for code, name, error in failed_stocks:
            print(f"   {code} ({name}): {error}")
    
    if success_count == len(portfolio_stocks):
        print("\n🎉 所有股票数据获取成功！回测可以正常运行")
    elif success_count > len(portfolio_stocks) * 0.8:
        print(f"\n⚠️ 大部分股票数据获取成功，回测可以继续运行")
        print(f"   建议：失败的股票将被跳过，不影响整体回测")
    else:
        print(f"\n❌ 多数股票数据获取失败，建议检查网络连接或稍后重试")
    
    return success_count, failed_stocks

def main():
    """主函数"""
    print("=" * 60)
    print("📋 回测数据获取诊断")
    print("=" * 60)
    
    success_count, failed_stocks = test_backtest_scenario()
    
    print(f"\n💡 解决建议:")
    if len(failed_stocks) == 0:
        print("✅ 数据获取正常，可以直接运行回测")
    else:
        print("1. 网络连接问题：检查网络是否稳定")
        print("2. akshare限制：等待几分钟后重试")
        print("3. 数据源问题：某些股票可能暂时无法获取")
        print("4. 系统会自动跳过无法获取数据的股票")
        print("5. 可以尝试重新运行回测，系统有重试机制")

if __name__ == "__main__":
    main()