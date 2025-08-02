#!/usr/bin/env python3
"""
修复回测引擎中的DCF估值数据加载问题
"""

def fix_dcf_method():
    """修复 _load_dcf_values 方法"""
    
    # 读取原文件
    with open('backtest/backtest_engine.py', 'r', encoding='utf-8') as f:
        content = f.read()
    
    # 查找 _load_dcf_values 方法的位置
    method_start = content.find('def _load_dcf_values(self) -> Dict[str, float]:')
    if method_start == -1:
        print("❌ 未找到 _load_dcf_values 方法")
        return False
    
    # 查找方法结束位置（下一个 def 或类结束）
    method_end = content.find('\n    def ', method_start + 1)
    if method_end == -1:
        method_end = content.find('\nclass ', method_start + 1)
    if method_end == -1:
        method_end = len(content)
    
    # 新的方法实现
    new_method = '''def _load_dcf_values(self) -> Dict[str, float]:
        """
        从CSV配置文件加载DCF估值数据
        
        Returns:
            Dict[str, float]: 股票代码到DCF估值的映射
        """
        try:
            import pandas as pd
            df = pd.read_csv('Input/portfolio_config.csv', encoding='utf-8-sig')
            dcf_values = {}
            
            for _, row in df.iterrows():
                stock_code = row['Stock_number']
                if stock_code != 'CASH':  # 排除现金
                    dcf_value = row.get('DCF_value_per_share', None)
                    if dcf_value is not None and pd.notna(dcf_value):
                        dcf_values[stock_code] = float(dcf_value)
            
            return dcf_values
        except Exception as e:
            self.logger.warning(f"DCF估值数据加载失败: {e}")
            return {}

    '''
    
    # 替换方法
    new_content = content[:method_start] + new_method + content[method_end:]
    
    # 写回文件
    with open('backtest/backtest_engine.py', 'w', encoding='utf-8') as f:
        f.write(new_content)
    
    print("✅ DCF估值数据加载方法修复完成")
    return True

if __name__ == "__main__":
    fix_dcf_method()