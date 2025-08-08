"""
测试akshare API的可用性
"""

import akshare as ak
import pandas as pd

def test_akshare_apis():
    """测试各种akshare API"""
    
    print("测试akshare可用的API...")
    
    # 测试申万行业相关API
    sw_apis = [attr for attr in dir(ak) if 'sw' in attr.lower()]
    print(f"申万相关API: {sw_apis}")
    
    # 测试指数相关API
    index_apis = [attr for attr in dir(ak) if 'index' in attr.lower()]
    print(f"指数相关API (前10个): {index_apis[:10]}")
    
    # 测试具体的API调用
    try:
        print("\n测试 tool_trade_date_hist_sina...")
        dates = ak.tool_trade_date_hist_sina()
        print(f"获取到 {len(dates)} 个交易日")
        
        print("\n测试 index_zh_a_hist...")
        # 测试获取上证指数数据
        df = ak.index_zh_a_hist(symbol="000001", period="weekly", start_date="20240101")
        print(f"上证指数周线数据: {len(df)} 条记录")
        print(f"列名: {list(df.columns)}")
        
        # 测试申万行业指数
        print("\n测试申万行业指数...")
        df_sw = ak.index_zh_a_hist(symbol="801010", period="weekly", start_date="20240101")
        print(f"申万农业指数周线数据: {len(df_sw)} 条记录")
        print(df_sw.head())
        
    except Exception as e:
        print(f"API调用失败: {e}")

if __name__ == "__main__":
    test_akshare_apis()