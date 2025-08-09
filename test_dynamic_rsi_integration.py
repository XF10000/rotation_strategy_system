#!/usr/bin/env python3
"""
测试动态RSI阈值集成功能
验证BacktestEngine和SignalGenerator是否能正确加载和使用动态RSI阈值
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

import logging
import pandas as pd
from datetime import datetime

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

def test_data_loading():
    """测试数据加载功能"""
    print("=" * 60)
    print("🧪 测试动态RSI阈值集成功能")
    print("=" * 60)
    
    # 1. 测试BacktestEngine的数据加载
    print("\n📊 测试1: BacktestEngine数据加载")
    try:
        from backtest.backtest_engine import BacktestEngine
        
        # 创建最小配置
        config = {
            'start_date': '2023-01-01',
            'end_date': '2023-12-31',
            'total_capital': 1000000,
            'initial_holdings': {'600036': 1000, 'cash': 500000},
            'strategy_params': {'rotation_percentage': 0.1},
            'cost_config': {}
        }
        
        # 初始化回测引擎
        engine = BacktestEngine(config)
        
        # 检查数据加载状态
        print(f"✅ BacktestEngine初始化成功")
        print(f"📊 DCF估值数据: {len(engine.dcf_values)} 只股票")
        print(f"📈 RSI阈值数据: {len(engine.rsi_thresholds)} 个行业")
        print(f"🏭 股票-行业映射: {len(engine.stock_industry_map)} 只股票")
        
        # 显示一些示例数据
        if engine.rsi_thresholds:
            print("\n📈 RSI阈值示例:")
            for i, (code, info) in enumerate(engine.rsi_thresholds.items()):
                if i >= 3: break
                print(f"  {info['industry_name']}({code}): "
                      f"买入≤{info['buy_threshold']:.1f}, 卖出≥{info['sell_threshold']:.1f}, "
                      f"波动率={info['volatility_level']}")
        
        if engine.stock_industry_map:
            print("\n🏭 股票-行业映射示例:")
            for i, (stock, info) in enumerate(engine.stock_industry_map.items()):
                if i >= 5: break
                print(f"  {stock}: {info['industry_name']}({info['industry_code']})")
        
        return engine
        
    except Exception as e:
        print(f"❌ BacktestEngine测试失败: {e}")
        return None

def test_signal_generator(engine):
    """测试SignalGenerator的动态RSI功能"""
    print("\n📊 测试2: SignalGenerator动态RSI功能")
    
    if not engine:
        print("❌ 跳过测试，BacktestEngine未初始化")
        return
    
    try:
        # 获取SignalGenerator实例
        signal_gen = engine.signal_generator
        
        # 检查数据传递状态
        print(f"✅ SignalGenerator初始化成功")
        print(f"📈 RSI阈值数据: {len(signal_gen.rsi_thresholds)} 个行业")
        print(f"🏭 股票-行业映射: {len(signal_gen.stock_industry_map)} 只股票")
        
        # 测试特定股票的RSI阈值获取
        test_stocks = ['600036', '000001', '601318', '000858']
        
        print("\n🔍 测试股票RSI阈值获取:")
        for stock_code in test_stocks:
            if stock_code in signal_gen.stock_industry_map:
                industry_info = signal_gen.stock_industry_map[stock_code]
                industry_code = industry_info['industry_code']
                industry_name = industry_info['industry_name']
                
                if industry_code in signal_gen.rsi_thresholds:
                    threshold_info = signal_gen.rsi_thresholds[industry_code]
                    print(f"  ✅ {stock_code}: {industry_name}")
                    print(f"     买入阈值: {threshold_info['buy_threshold']:.2f}")
                    print(f"     卖出阈值: {threshold_info['sell_threshold']:.2f}")
                    print(f"     波动率等级: {threshold_info['volatility_level']}")
                else:
                    print(f"  ⚠️  {stock_code}: {industry_name} (未找到RSI阈值)")
            else:
                print(f"  ❌ {stock_code}: 未找到行业映射")
        
        return True
        
    except Exception as e:
        print(f"❌ SignalGenerator测试失败: {e}")
        return False

def test_rsi_threshold_lookup():
    """测试RSI阈值查找逻辑"""
    print("\n📊 测试3: RSI阈值查找逻辑")
    
    try:
        # 直接测试数据文件
        import json
        import pandas as pd
        
        # 加载映射文件
        with open('data_cache/stock_to_industry_map.json', 'r', encoding='utf-8') as f:
            cache_data = json.load(f)
        stock_map = cache_data['mapping']
        
        # 加载RSI阈值文件
        rsi_df = pd.read_csv('sw_rsi_thresholds/output/sw2_rsi_threshold.csv', encoding='utf-8-sig')
        rsi_thresholds = {}
        for _, row in rsi_df.iterrows():
            industry_code = str(row['行业代码']).strip()
            rsi_thresholds[industry_code] = {
                'industry_name': row['行业名称'],
                'buy_threshold': float(row['普通超卖']),
                'sell_threshold': float(row['普通超买']),
                'volatility_level': row['layer']
            }
        
        print(f"✅ 直接加载数据成功")
        print(f"📊 股票映射: {len(stock_map)} 只股票")
        print(f"📈 RSI阈值: {len(rsi_thresholds)} 个行业")
        
        # 统计覆盖率
        covered_stocks = 0
        total_stocks = len(stock_map)
        
        for stock_code, industry_info in stock_map.items():
            industry_code = industry_info['industry_code']
            if industry_code in rsi_thresholds:
                covered_stocks += 1
        
        coverage_rate = (covered_stocks / total_stocks) * 100 if total_stocks > 0 else 0
        print(f"📊 RSI阈值覆盖率: {covered_stocks}/{total_stocks} ({coverage_rate:.1f}%)")
        
        return True
        
    except Exception as e:
        print(f"❌ 阈值查找测试失败: {e}")
        return False

def main():
    """主测试函数"""
    print(f"🕐 测试开始时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    
    # 执行测试
    engine = test_data_loading()
    signal_success = test_signal_generator(engine)
    lookup_success = test_rsi_threshold_lookup()
    
    # 测试结果汇总
    print("\n" + "=" * 60)
    print("📋 测试结果汇总")
    print("=" * 60)
    
    if engine:
        print("✅ BacktestEngine数据加载: 成功")
    else:
        print("❌ BacktestEngine数据加载: 失败")
    
    if signal_success:
        print("✅ SignalGenerator动态RSI: 成功")
    else:
        print("❌ SignalGenerator动态RSI: 失败")
    
    if lookup_success:
        print("✅ RSI阈值查找逻辑: 成功")
    else:
        print("❌ RSI阈值查找逻辑: 失败")
    
    # 总体评估
    all_success = engine is not None and signal_success and lookup_success
    if all_success:
        print("\n🎉 所有测试通过！动态RSI阈值集成成功！")
        print("💡 现在可以运行完整的回测来验证实际效果")
    else:
        print("\n⚠️  部分测试失败，需要进一步调试")
    
    print(f"\n🕐 测试结束时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    return all_success

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
