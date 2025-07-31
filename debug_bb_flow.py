"""
布林带数据流调试脚本
用于追踪布林带数据在各个处理阶段的状态
"""

import pandas as pd
import numpy as np
import sys
import os

# 添加项目路径
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from data.data_processor import DataProcessor
from data.data_storage import DataStorage

def debug_bb_flow():
    """调试布林带数据流"""
    print("=== 布林带数据流调试 ===")
    
    # 初始化处理器和存储
    processor = DataProcessor()
    storage = DataStorage()
    
    # 测试股票代码
    stock_code = "601088"
    
    # 1. 检查缓存中的周线数据
    print("\n1. 检查缓存中的周线数据...")
    cached_weekly = storage.load_data(stock_code, 'weekly')
    if cached_weekly is not None:
        print(f"   缓存数据形状: {cached_weekly.shape}")
        print(f"   布林带列存在: bb_upper={'bb_upper' in cached_weekly.columns}, bb_middle={'bb_middle' in cached_weekly.columns}, bb_lower={'bb_lower' in cached_weekly.columns}")
        if 'bb_upper' in cached_weekly.columns:
            nan_count = cached_weekly['bb_upper'].isna().sum()
            total_count = len(cached_weekly)
            print(f"   bb_upper NaN比例: {nan_count}/{total_count} ({nan_count/total_count*100:.1f}%)")
            print(f"   bb_upper 前5个值: {cached_weekly['bb_upper'].head().tolist()}")
    else:
        print("   未找到缓存数据")
    
    # 2. 重新计算技术指标
    print("\n2. 重新计算技术指标...")
    if cached_weekly is not None:
        # 复制数据以避免修改缓存
        test_data = cached_weekly.copy()
        print(f"   原始数据形状: {test_data.shape}")
        print(f"   原始列: {list(test_data.columns)}")
        
        # 计算技术指标
        with_indicators = processor.calculate_technical_indicators(test_data)
        print(f"   计算后数据形状: {with_indicators.shape}")
        print(f"   计算后列: {list(with_indicators.columns)}")
        
        if 'bb_upper' in with_indicators.columns:
            nan_count = with_indicators['bb_upper'].isna().sum()
            total_count = len(with_indicators)
            print(f"   bb_upper NaN比例: {nan_count}/{total_count} ({nan_count/total_count*100:.1f}%)")
            print(f"   bb_upper 前10个值: {with_indicators['bb_upper'].head(10).tolist()}")
            print(f"   bb_upper 后10个值: {with_indicators['bb_upper'].tail(10).tolist()}")
            
            # 检查非NaN值
            non_nan_values = with_indicators['bb_upper'].dropna()
            if len(non_nan_values) > 0:
                print(f"   bb_upper 非NaN值范围: {non_nan_values.min():.3f} - {non_nan_values.max():.3f}")
        
        # 保存测试数据
        print("\n3. 保存测试数据...")
        storage.save_data(with_indicators, f"{stock_code}_test", 'weekly')
        print("   测试数据已保存")
    
    print("\n=== 调试完成 ===")

if __name__ == "__main__":
    debug_bb_flow()
