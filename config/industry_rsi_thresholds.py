"""
不同申万二级行业的RSI阈值配置
基于行业特性和历史数据分析设定个性化阈值
"""

# 申万二级行业RSI阈值配置
INDUSTRY_RSI_THRESHOLDS = {
    # 公用事业类 - 相对稳定，波动较小
    '电力': {
        'overbought': 75,    # 超买阈值
        'oversold': 35,      # 超卖阈值（放宽到35）
        'reason': '电力行业相对稳定，RSI很少到达极端值，适当放宽阈值'
    },
    '水务': {
        'overbought': 75,
        'oversold': 35,
        'reason': '公用事业类，波动相对较小'
    },
    '燃气': {
        'overbought': 75,
        'oversold': 35,
        'reason': '公用事业类，波动相对较小'
    },
    
    # 周期性行业 - 波动较大，可以用标准阈值
    '煤炭开采': {
        'overbought': 70,
        'oversold': 30,
        'reason': '周期性强，波动大，使用标准阈值'
    },
    '有色金属': {
        'overbought': 70,
        'oversold': 30,
        'reason': '周期性强，价格波动大'
    },
    '钢铁': {
        'overbought': 70,
        'oversold': 30,
        'reason': '周期性行业，波动较大'
    },
    '化工': {
        'overbought': 70,
        'oversold': 30,
        'reason': '周期性行业，价格波动较大'
    },
    
    # 消费类 - 相对稳定
    '食品制造': {
        'overbought': 75,
        'oversold': 35,
        'reason': '消费类行业，相对稳定，适当放宽阈值'
    },
    '饮料制造': {
        'overbought': 75,
        'oversold': 35,
        'reason': '消费类行业，相对稳定'
    },
    
    # 医药类 - 波动中等
    '医药制造': {
        'overbought': 72,
        'oversold': 32,
        'reason': '医药行业波动中等，略微放宽阈值'
    },
    '生物制品': {
        'overbought': 72,
        'oversold': 32,
        'reason': '医药相关，波动中等'
    },
    
    # 科技类 - 波动较大
    '计算机应用': {
        'overbought': 70,
        'oversold': 30,
        'reason': '科技类波动大，使用标准阈值'
    },
    '通信设备': {
        'overbought': 70,
        'oversold': 30,
        'reason': '科技类波动大'
    },
    
    # 金融类 - 相对稳定
    '银行': {
        'overbought': 75,
        'oversold': 35,
        'reason': '金融类相对稳定，适当放宽阈值'
    },
    '保险': {
        'overbought': 75,
        'oversold': 35,
        'reason': '金融类相对稳定'
    },
    
    # 房地产类 - 波动较大
    '房地产开发': {
        'overbought': 70,
        'oversold': 30,
        'reason': '房地产波动大，使用标准阈值'
    },
    
    # 交通运输类 - 中等波动
    '航空运输': {
        'overbought': 72,
        'oversold': 32,
        'reason': '交通运输波动中等'
    },
    '港口水运': {
        'overbought': 72,
        'oversold': 32,
        'reason': '交通运输波动中等'
    }
}

# 默认阈值（当行业未在上述配置中时使用）
DEFAULT_RSI_THRESHOLDS = {
    'overbought': 70,
    'oversold': 30,
    'reason': '默认标准阈值'
}

def get_rsi_thresholds(industry):
    """
    根据行业获取RSI阈值
    
    Args:
        industry: 申万二级行业名称
        
    Returns:
        dict: 包含超买超卖阈值的字典
    """
    return INDUSTRY_RSI_THRESHOLDS.get(industry, DEFAULT_RSI_THRESHOLDS)

def get_industry_from_stock_code(stock_code):
    """
    根据股票代码获取行业信息
    这里需要根据实际的行业数据库或API来实现
    
    Args:
        stock_code: 股票代码
        
    Returns:
        str: 申万二级行业名称
    """
    # 示例映射，实际应该从数据库或API获取
    STOCK_INDUSTRY_MAPPING = {
        '600900': '电力',        # 长江电力
        '601088': '煤炭开采',    # 中国神华
        '000807': '有色金属',    # 云铝股份
        '002460': '有色金属',    # 赣锋锂业
        '002262': '医药制造',    # 恩华药业
        '002330': '食品制造',    # 得利斯
    }
    
    return STOCK_INDUSTRY_MAPPING.get(stock_code, None)

def analyze_rsi_threshold_impact():
    """
    分析不同RSI阈值对信号的影响
    """
    print("📊 不同行业RSI阈值设置分析:")
    print("=" * 60)
    
    for industry, thresholds in INDUSTRY_RSI_THRESHOLDS.items():
        print(f"\n🏭 {industry}:")
        print(f"  超买阈值: {thresholds['overbought']}")
        print(f"  超卖阈值: {thresholds['oversold']}")
        print(f"  设置理由: {thresholds['reason']}")
    
    print(f"\n🔧 默认阈值:")
    print(f"  超买阈值: {DEFAULT_RSI_THRESHOLDS['overbought']}")
    print(f"  超卖阈值: {DEFAULT_RSI_THRESHOLDS['oversold']}")
    print(f"  适用范围: {DEFAULT_RSI_THRESHOLDS['reason']}")

if __name__ == "__main__":
    # 测试长江电力的阈值
    industry = get_industry_from_stock_code('600900')
    if industry:
        thresholds = get_rsi_thresholds(industry)
        print(f"长江电力(600900)所属行业: {industry}")
        print(f"RSI阈值设置: {thresholds}")
        print(f"\n如果RSI=33.51，在新阈值下:")
        print(f"是否超卖: {33.51 <= thresholds['oversold']}")
    
    # 显示所有行业阈值
    analyze_rsi_threshold_impact()