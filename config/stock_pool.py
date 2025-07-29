"""
股票池配置
基于中线轮动策略文档中的示例股票池
"""

# 主要股票池配置
STOCK_POOL = {
    '煤炭': {
        'code': '601088',
        'name': '中国神华',
        'sector': '煤炭开采',
        'dcf_valuation': None,  # DCF估值，需要用户自行填入
        'safety_margin': 0.2    # 安全边际：20%
    },
    '电解铝': {
        'code': '000807', 
        'name': '云铝股份',
        'sector': '有色金属',
        'dcf_valuation': None,
        'safety_margin': 0.2
    },
    '锂矿': {
        'code': '002460',
        'name': '赣锋锂业', 
        'sector': '有色金属',
        'dcf_valuation': None,
        'safety_margin': 0.2
    },
    '麻醉药': {
        'code': '002262',
        'name': '恩华药业',
        'sector': '医药制造',
        'dcf_valuation': None,
        'safety_margin': 0.2
    },
    '预制菜': {
        'code': '002330',
        'name': '得利斯',
        'sector': '食品制造',
        'dcf_valuation': None,
        'safety_margin': 0.2
    }
}

# 获取股票代码列表
def get_stock_codes():
    """返回所有股票代码列表"""
    return [info['code'] for info in STOCK_POOL.values()]

# 获取股票名称映射
def get_stock_names():
    """返回代码到名称的映射"""
    return {info['code']: name for name, info in STOCK_POOL.items()}

# 获取完整股票信息
def get_stock_info(identifier):
    """
    根据股票代码或名称获取完整信息
    
    Args:
        identifier: 股票代码或名称
        
    Returns:
        dict: 股票完整信息
    """
    # 如果是代码
    for name, info in STOCK_POOL.items():
        if info['code'] == identifier:
            return {**info, 'alias': name}
    
    # 如果是名称
    if identifier in STOCK_POOL:
        return {**STOCK_POOL[identifier], 'alias': identifier}
    
    return None

# DCF估值更新函数
def update_dcf_valuation(stock_name, valuation):
    """
    更新股票的DCF估值
    
    Args:
        stock_name: 股票名称
        valuation: DCF估值
    """
    if stock_name in STOCK_POOL:
        STOCK_POOL[stock_name]['dcf_valuation'] = valuation
        print(f"已更新 {stock_name} 的DCF估值为: {valuation}")
    else:
        print(f"未找到股票: {stock_name}")

# 验证股票池配置
def validate_stock_pool():
    """验证股票池配置的完整性"""
    issues = []
    
    for name, info in STOCK_POOL.items():
        if not info.get('code'):
            issues.append(f"{name}: 缺少股票代码")
        
        if info.get('dcf_valuation') is None:
            issues.append(f"{name}: 缺少DCF估值")
    
    if issues:
        print("股票池配置问题:")
        for issue in issues:
            print(f"  - {issue}")
        return False
    
    print("股票池配置验证通过")
    return True

if __name__ == "__main__":
    # 测试配置
    print("当前股票池:")
    for name, info in STOCK_POOL.items():
        print(f"  {name}: {info['code']} - {info['name']}")
    
    print(f"\n股票代码列表: {get_stock_codes()}")
    print(f"股票名称映射: {get_stock_names()}")
    
    # 验证配置
    validate_stock_pool()