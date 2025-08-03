"""
股票代码到名称的映射工具
从 portfolio_config.csv 读取股票名称映射
"""

import pandas as pd
from typing import Dict
import os

def load_stock_name_mapping(config_path: str = 'Input/portfolio_config.csv') -> Dict[str, str]:
    """
    从配置文件加载股票代码到名称的映射
    
    Args:
        config_path: 配置文件路径
        
    Returns:
        Dict[str, str]: 股票代码到名称的映射 {代码: 名称}
    """
    try:
        if not os.path.exists(config_path):
            print(f"警告: 配置文件不存在: {config_path}")
            return {}
            
        df = pd.read_csv(config_path, encoding='utf-8-sig')
        
        # 创建代码到名称的映射，排除现金行
        stock_mapping = {}
        for _, row in df.iterrows():
            stock_code = str(row['Stock_number']).strip()
            stock_name = str(row['Stock_name']).strip()
            
            # 跳过现金和无效行
            if stock_code != 'CASH' and stock_code != 'nan' and stock_name != 'nan':
                stock_mapping[stock_code] = stock_name
                
        print(f"✅ 成功加载 {len(stock_mapping)} 只股票的名称映射")
        return stock_mapping
        
    except Exception as e:
        print(f"❌ 加载股票名称映射失败: {e}")
        return {}

def get_stock_display_name(stock_code: str, stock_mapping: Dict[str, str] = None) -> str:
    """
    获取股票的显示名称
    
    Args:
        stock_code: 股票代码
        stock_mapping: 股票名称映射字典，如果为None则重新加载
        
    Returns:
        str: 股票显示名称，格式为 "名称(代码)" 或仅代码（如果找不到名称）
    """
    if stock_mapping is None:
        stock_mapping = load_stock_name_mapping()
    
    stock_name = stock_mapping.get(stock_code)
    if stock_name:
        return f"{stock_name}({stock_code})"
    else:
        return stock_code

# 全局缓存，避免重复读取文件
_cached_stock_mapping = None

def get_cached_stock_mapping() -> Dict[str, str]:
    """获取缓存的股票名称映射"""
    global _cached_stock_mapping
    if _cached_stock_mapping is None:
        _cached_stock_mapping = load_stock_name_mapping()
    return _cached_stock_mapping

if __name__ == "__main__":
    # 测试功能
    mapping = load_stock_name_mapping()
    print("股票名称映射:")
    for code, name in mapping.items():
        print(f"  {code}: {name}")
    
    # 测试显示名称
    test_codes = ['601088', '002738', '603345']
    print("\n显示名称测试:")
    for code in test_codes:
        display_name = get_stock_display_name(code, mapping)
        print(f"  {code} -> {display_name}")
