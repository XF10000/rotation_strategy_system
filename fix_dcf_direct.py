#!/usr/bin/env python3
"""
直接在回测引擎初始化时设置DCF数据
"""

def fix_dcf_direct():
    """直接设置DCF数据"""
    
    # 读取原文件
    with open('backtest/backtest_engine.py', 'r', encoding='utf-8') as f:
        content = f.read()
    
    # 查找初始化DCF数据的位置
    dcf_init_line = 'self.dcf_values = self._load_dcf_values()'
    if dcf_init_line in content:
        # 替换为直接设置DCF数据
        dcf_data = '''self.dcf_values = {
            '601088': 40.0,
            '601225': 40.0,
            '600985': 20.0,
            '002738': 50.0,
            '002460': 50.0,
            '000933': 37.0,
            '000807': 25.0,
            '600079': 28.0,
            '603345': 126.0,
            '601898': 20.0
        }'''
        
        new_content = content.replace(dcf_init_line, dcf_data)
        
        # 写回文件
        with open('backtest/backtest_engine.py', 'w', encoding='utf-8') as f:
            f.write(new_content)
        
        print("✅ DCF数据直接设置完成")
        return True
    else:
        print("❌ 未找到DCF初始化行")
        return False

if __name__ == "__main__":
    fix_dcf_direct()