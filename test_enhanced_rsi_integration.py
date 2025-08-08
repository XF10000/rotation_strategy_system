"""
测试增强版RSI阈值加载器的集成
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from config.enhanced_industry_rsi_loader import get_enhanced_rsi_loader
from config.industry_rsi_loader import get_rsi_loader
import logging

# 设置日志
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def test_enhanced_rsi_loader():
    """测试增强版RSI阈值加载器"""
    print("=" * 60)
    print("测试增强版RSI阈值加载器")
    print("=" * 60)
    
    # 获取加载器实例
    loader = get_enhanced_rsi_loader()
    
    # 1. 测试统计信息
    print("\n1. 阈值数据统计信息：")
    stats = loader.get_statistics()
    for key, value in stats.items():
        print(f"   {key}: {value}")
    
    # 2. 测试可用行业列表
    print("\n2. 可用行业列表（前10个）：")
    industries = loader.list_available_industries()
    for i, industry in enumerate(industries[:10]):
        print(f"   {i+1}. {industry['code']} - {industry['name']} ({industry['volatility_layer']})")
    
    # 3. 测试具体行业的阈值获取
    print("\n3. 测试具体行业阈值获取：")
    test_industries = ['白酒', '340500', '电力', '410100', '半导体', '270100']
    
    for industry in test_industries:
        print(f"\n   行业: {industry}")
        
        # 普通阈值
        normal_thresholds = loader.get_rsi_thresholds(industry, use_extreme=False)
        print(f"   普通阈值: 超卖={normal_thresholds['oversold']:.2f}, 超买={normal_thresholds['overbought']:.2f}")
        
        # 极端阈值
        extreme_thresholds = loader.get_rsi_thresholds(industry, use_extreme=True)
        print(f"   极端阈值: 超卖={extreme_thresholds['oversold']:.2f}, 超买={extreme_thresholds['overbought']:.2f}")
        
        # 完整信息
        info = loader.get_industry_info(industry)
        if info:
            print(f"   波动率: {info.get('volatility', 'N/A'):.3f}, 分层: {info.get('layer', 'N/A')}")
            print(f"   当前RSI: {info.get('current_rsi', 'N/A'):.2f}, 数据点: {info.get('data_points', 'N/A')}")

def compare_with_original():
    """对比原始加载器和增强版加载器"""
    print("\n" + "=" * 60)
    print("对比原始加载器和增强版加载器")
    print("=" * 60)
    
    # 获取两个加载器
    original_loader = get_rsi_loader()
    enhanced_loader = get_enhanced_rsi_loader()
    
    # 测试一些共同的行业
    test_industries = ['煤炭', '电力', '银行', '白酒']
    
    print(f"\n{'行业':<10} {'原始超卖':<10} {'增强超卖':<10} {'原始超买':<10} {'增强超买':<10}")
    print("-" * 60)
    
    for industry in test_industries:
        # 原始加载器
        try:
            original_thresholds = original_loader.get_rsi_thresholds(industry)
            orig_oversold = original_thresholds['oversold']
            orig_overbought = original_thresholds['overbought']
        except:
            orig_oversold = orig_overbought = "N/A"
        
        # 增强版加载器
        try:
            enhanced_thresholds = enhanced_loader.get_rsi_thresholds(industry)
            enh_oversold = enhanced_thresholds['oversold']
            enh_overbought = enhanced_thresholds['overbought']
        except:
            enh_oversold = enh_overbought = "N/A"
        
        print(f"{industry:<10} {orig_oversold:<10} {enh_oversold:<10.2f} {orig_overbought:<10} {enh_overbought:<10.2f}")

def test_signal_generator_integration():
    """测试与信号生成器的集成"""
    print("\n" + "=" * 60)
    print("测试与信号生成器的集成")
    print("=" * 60)
    
    # 模拟信号生成器中的使用方式
    from config.enhanced_industry_rsi_loader import get_enhanced_rsi_loader
    
    loader = get_enhanced_rsi_loader()
    
    # 模拟一些行业的RSI值
    test_cases = [
        {'industry': '白酒', 'current_rsi': 45.0},
        {'industry': '电力', 'current_rsi': 35.0},
        {'industry': '半导体', 'current_rsi': 75.0},
        {'industry': '煤炭开采', 'current_rsi': 25.0},
    ]
    
    print("\n模拟信号生成场景：")
    for case in test_cases:
        industry = case['industry']
        current_rsi = case['current_rsi']
        
        # 获取阈值
        thresholds = loader.get_rsi_thresholds(industry)
        extreme_thresholds = loader.get_rsi_thresholds(industry, use_extreme=True)
        
        # 判断信号
        is_oversold = current_rsi <= thresholds['oversold']
        is_overbought = current_rsi >= thresholds['overbought']
        is_extreme_oversold = current_rsi <= extreme_thresholds['oversold']
        is_extreme_overbought = current_rsi >= extreme_thresholds['overbought']
        
        print(f"\n   {industry} (RSI: {current_rsi})")
        print(f"   普通阈值: {thresholds['oversold']:.2f} / {thresholds['overbought']:.2f}")
        print(f"   极端阈值: {extreme_thresholds['oversold']:.2f} / {extreme_thresholds['overbought']:.2f}")
        
        signals = []
        if is_extreme_oversold:
            signals.append("极端超卖")
        elif is_oversold:
            signals.append("普通超卖")
        
        if is_extreme_overbought:
            signals.append("极端超买")
        elif is_overbought:
            signals.append("普通超买")
        
        if not signals:
            signals.append("正常区间")
        
        print(f"   信号: {', '.join(signals)}")

if __name__ == "__main__":
    try:
        # 运行所有测试
        test_enhanced_rsi_loader()
        compare_with_original()
        test_signal_generator_integration()
        
        print("\n" + "=" * 60)
        print("✅ 所有测试完成")
        print("=" * 60)
        
    except Exception as e:
        print(f"\n❌ 测试失败: {e}")
        import traceback
        traceback.print_exc()