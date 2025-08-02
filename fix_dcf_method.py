# 这是一个临时文件，用于修复 _load_dcf_values 方法
def _load_dcf_values(self) -> Dict[str, float]:
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