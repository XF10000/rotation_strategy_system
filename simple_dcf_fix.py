#!/usr/bin/env python3
"""
简单直接的DCF数据修复
"""

def simple_dcf_fix():
    """简单直接修复DCF数据"""
    
    # 读取原文件
    with open('backtest/backtest_engine.py', 'r', encoding='utf-8') as f:
        content = f.read()
    
    # 查找初始化方法中的位置，在股票池设置之后添加DCF数据
    stock_pool_line = "self.stock_pool = [code for code in self.initial_holdings.keys() if code != 'cash']"
    
    if stock_pool_line in content:
        # 在股票池设置之后添加DCF数据
        dcf_init = '''
        
        # DCF估值数据
        self.dcf_values = {
            '601088': 40.0, '601225': 40.0, '600985': 20.0, '002738': 50.0, '002460': 50.0,
            '000933': 37.0, '000807': 25.0, '600079': 28.0, '603345': 126.0, '601898': 20.0
        }'''
        
        new_content = content.replace(stock_pool_line, stock_pool_line + dcf_init)
        
        # 写回文件
        with open('backtest/backtest_engine.py', 'w', encoding='utf-8') as f:
            f.write(new_content)
        
        print("✅ DCF数据简单修复完成")
        return True
    else:
        print("❌ 未找到股票池设置行")
        return False

if __name__ == "__main__":
    simple_dcf_fix()