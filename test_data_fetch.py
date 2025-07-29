#!/usr/bin/env python3
"""
数据获取测试脚本
用于诊断和解决数据获取问题
"""

import sys
import logging
from datetime import datetime, timedelta
from data.data_fetcher import AkshareDataFetcher

# 设置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

def test_single_stock(code, days_back=30):
    """测试单只股票数据获取"""
    print(f"\n🔍 测试股票 {code} 数据获取...")
    
    fetcher = AkshareDataFetcher()
    
    # 设置日期范围
    end_date = datetime.now().strftime('%Y-%m-%d')
    start_date = (datetime.now() - timedelta(days=days_back)).strftime('%Y-%m-%d')
    
    try:
        # 测试日线数据
        print(f"📊 获取日线数据: {start_date} 到 {end_date}")
        daily_data = fetcher.get_stock_data(code, start_date, end_date, 'daily')
        print(f"✅ 成功获取日线数据: {len(daily_data)} 条记录")
        print(f"   数据范围: {daily_data.index[0]} 到 {daily_data.index[-1]}")
        print(f"   最新收盘价: {daily_data['close'].iloc[-1]:.2f}")
        
        # 测试周线数据
        print(f"📈 获取周线数据: {start_date} 到 {end_date}")
        weekly_data = fetcher.get_stock_data(code, start_date, end_date, 'weekly')
        print(f"✅ 成功获取周线数据: {len(weekly_data)} 条记录")
        print(f"   数据范围: {weekly_data.index[0]} 到 {weekly_data.index[-1]}")
        
        return True
        
    except Exception as e:
        print(f"❌ 获取股票 {code} 数据失败: {e}")
        return False

def test_connection():
    """测试akshare连接"""
    print("🌐 测试akshare连接...")
    
    fetcher = AkshareDataFetcher()
    
    if fetcher.test_connection():
        print("✅ akshare连接正常")
        return True
    else:
        print("❌ akshare连接失败")
        return False

def main():
    """主测试函数"""
    print("=" * 60)
    print("📋 数据获取诊断测试")
    print("=" * 60)
    
    # 测试连接
    if not test_connection():
        print("\n❌ 连接测试失败，请检查网络连接")
        return
    
    # 测试股票列表（从投资组合中选择几只）
    test_stocks = [
        ('600900', '长江电力'),
        ('601088', '中国神华'),
        ('002738', '中矿资源'),
        ('002460', '赣锋锂业'),
        ('000933', '神火股份')
    ]
    
    success_count = 0
    total_count = len(test_stocks)
    
    for code, name in test_stocks:
        print(f"\n{'='*40}")
        print(f"测试 {code} ({name})")
        print(f"{'='*40}")
        
        if test_single_stock(code):
            success_count += 1
        
        # 添加延迟避免请求过快
        import time
        time.sleep(2)
    
    # 总结
    print(f"\n{'='*60}")
    print(f"📊 测试总结")
    print(f"{'='*60}")
    print(f"成功: {success_count}/{total_count}")
    print(f"失败: {total_count - success_count}/{total_count}")
    
    if success_count == total_count:
        print("🎉 所有测试通过！数据获取正常")
    elif success_count > 0:
        print("⚠️ 部分测试通过，可能存在网络波动")
    else:
        print("❌ 所有测试失败，请检查网络连接或akshare状态")
    
    print(f"\n💡 建议:")
    print("1. 如果部分股票获取失败，可能是akshare数据源问题")
    print("2. 可以尝试稍后重新运行回测")
    print("3. 检查网络连接是否稳定")
    print("4. 确认akshare版本是否为最新")

if __name__ == "__main__":
    main()