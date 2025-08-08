"""
测试信号生成器与增强版RSI阈值加载器的集成
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

import pandas as pd
import numpy as np
import logging
from datetime import datetime, timedelta

# 设置日志
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def create_test_data(stock_code: str, periods: int = 100) -> pd.DataFrame:
    """创建测试用的股票数据"""
    
    # 生成日期序列
    end_date = datetime.now()
    start_date = end_date - timedelta(days=periods * 7)  # 假设每周7天
    date_range = pd.date_range(start=start_date, end=end_date, freq='W')
    
    # 生成模拟价格数据
    np.random.seed(42)  # 确保可重复性
    
    # 基础价格
    base_price = 10.0
    prices = []
    volumes = []
    
    current_price = base_price
    for i in range(len(date_range)):
        # 价格随机游走
        change = np.random.normal(0, 0.02)  # 2%的标准差
        current_price = current_price * (1 + change)
        
        # 生成OHLC
        high = current_price * (1 + abs(np.random.normal(0, 0.01)))
        low = current_price * (1 - abs(np.random.normal(0, 0.01)))
        open_price = current_price * (1 + np.random.normal(0, 0.005))
        close = current_price
        
        prices.append({
            'open': open_price,
            'high': high,
            'low': low,
            'close': close
        })
        
        # 生成成交量
        volume = np.random.randint(1000000, 10000000)
        volumes.append(volume)
    
    # 创建DataFrame
    data = pd.DataFrame(prices, index=date_range)
    data['volume'] = volumes
    
    return data

def test_signal_generator_with_enhanced_rsi():
    """测试信号生成器使用增强版RSI阈值"""
    
    print("=" * 60)
    print("测试信号生成器与增强版RSI阈值加载器的集成")
    print("=" * 60)
    
    try:
        # 导入必要的模块
        from strategy.signal_generator import SignalGenerator
        from config.enhanced_industry_rsi_loader import get_enhanced_rsi_loader
        
        # 测试配置
        config = {
            'ema_period': 20,
            'rsi_period': 14,
            'rsi_overbought': 70,
            'rsi_oversold': 30,
            'min_data_length': 50
        }
        
        # 创建信号生成器
        signal_gen = SignalGenerator(config)
        
        # 获取增强版加载器用于对比
        enhanced_loader = get_enhanced_rsi_loader()
        
        # 测试不同行业的股票
        test_cases = [
            {'stock_code': '000858', 'industry': '白酒'},  # 五粮液
            {'stock_code': '600036', 'industry': '银行'},  # 招商银行  
            {'stock_code': '000002', 'industry': '房地产'}, # 万科A
            {'stock_code': '600519', 'industry': '白酒'},  # 茅台
        ]
        
        print(f"\n📊 测试 {len(test_cases)} 只股票的信号生成:")
        print("-" * 60)
        
        for i, case in enumerate(test_cases):
            stock_code = case['stock_code']
            expected_industry = case['industry']
            
            print(f"\n{i+1}. 测试股票: {stock_code} (预期行业: {expected_industry})")
            
            # 创建测试数据
            test_data = create_test_data(stock_code, periods=80)
            print(f"   生成测试数据: {len(test_data)} 条记录")
            
            try:
                # 生成信号
                signal_result = signal_gen.generate_signal(stock_code, test_data)
                
                print(f"   信号结果: {signal_result['signal']}")
                print(f"   置信度: {signal_result['confidence']:.2f}")
                print(f"   原因: {signal_result['reason']}")
                
                # 检查是否使用了动态阈值
                if 'technical_indicators' in signal_result:
                    rsi_value = signal_result['technical_indicators'].get('rsi_14w', 0)
                    print(f"   当前RSI: {rsi_value:.2f}")
                
                # 获取该股票应该使用的动态阈值
                try:
                    # 尝试获取行业信息
                    industry = signal_gen._get_stock_industry_cached(stock_code)
                    if industry:
                        thresholds = enhanced_loader.get_rsi_thresholds(industry)
                        print(f"   检测到行业: {industry}")
                        print(f"   动态阈值: 超卖={thresholds['oversold']:.2f}, 超买={thresholds['overbought']:.2f}")
                        
                        # 获取行业详细信息
                        industry_info = enhanced_loader.get_industry_info(industry)
                        if industry_info:
                            print(f"   波动率分层: {industry_info.get('layer', 'N/A')}")
                            print(f"   波动率数值: {industry_info.get('volatility', 'N/A'):.3f}")
                    else:
                        print(f"   未检测到行业信息，使用默认阈值")
                        
                except Exception as e:
                    print(f"   获取动态阈值失败: {e}")
                
                print(f"   ✅ 信号生成成功")
                
            except Exception as e:
                print(f"   ❌ 信号生成失败: {e}")
                import traceback
                traceback.print_exc()
        
        # 测试阈值对比
        print(f"\n📈 动态阈值 vs 静态阈值对比:")
        print("-" * 60)
        
        # 获取一些行业的阈值对比
        test_industries = ['白酒', '电力', '半导体', '煤炭开采']
        
        print(f"{'行业':<12} {'动态超卖':<10} {'动态超买':<10} {'静态超卖':<10} {'静态超买':<10} {'差异':<10}")
        print("-" * 70)
        
        for industry in test_industries:
            try:
                # 动态阈值
                dynamic_thresholds = enhanced_loader.get_rsi_thresholds(industry)
                dynamic_oversold = dynamic_thresholds['oversold']
                dynamic_overbought = dynamic_thresholds['overbought']
                
                # 静态阈值（默认）
                static_oversold = 30
                static_overbought = 70
                
                # 计算差异
                oversold_diff = dynamic_oversold - static_oversold
                overbought_diff = dynamic_overbought - static_overbought
                
                print(f"{industry:<12} {dynamic_oversold:<10.2f} {dynamic_overbought:<10.2f} {static_oversold:<10} {static_overbought:<10} {oversold_diff:+.1f}/{overbought_diff:+.1f}")
                
            except Exception as e:
                print(f"{industry:<12} {'N/A':<10} {'N/A':<10} {static_oversold:<10} {static_overbought:<10} {'N/A':<10}")
        
        print(f"\n✅ 集成测试完成")
        
    except Exception as e:
        print(f"❌ 集成测试失败: {e}")
        import traceback
        traceback.print_exc()

def test_enhanced_loader_performance():
    """测试增强版加载器的性能"""
    
    print(f"\n🚀 性能测试:")
    print("-" * 30)
    
    try:
        from config.enhanced_industry_rsi_loader import get_enhanced_rsi_loader
        import time
        
        loader = get_enhanced_rsi_loader()
        
        # 测试查询性能
        test_queries = ['白酒', '340500', '电力', '410100', '半导体', '270100'] * 100
        
        start_time = time.time()
        for query in test_queries:
            thresholds = loader.get_rsi_thresholds(query)
        end_time = time.time()
        
        total_time = end_time - start_time
        avg_time = total_time / len(test_queries) * 1000  # 转换为毫秒
        
        print(f"   查询次数: {len(test_queries)}")
        print(f"   总耗时: {total_time:.3f}秒")
        print(f"   平均耗时: {avg_time:.3f}毫秒/次")
        print(f"   QPS: {len(test_queries)/total_time:.0f}")
        
        if avg_time < 1.0:
            print(f"   ✅ 性能良好")
        else:
            print(f"   ⚠️  性能需要优化")
            
    except Exception as e:
        print(f"   ❌ 性能测试失败: {e}")

if __name__ == "__main__":
    try:
        test_signal_generator_with_enhanced_rsi()
        test_enhanced_loader_performance()
        
        print("\n" + "=" * 60)
        print("🎉 所有测试完成")
        print("=" * 60)
        
    except Exception as e:
        print(f"\n❌ 测试执行失败: {e}")
        import traceback
        traceback.print_exc()