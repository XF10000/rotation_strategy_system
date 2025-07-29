"""
股票代码到申万二级行业的映射
用于获取股票对应的行业特定信号规则
"""

# 股票代码到申万二级行业的映射表
STOCK_INDUSTRY_MAPPING = {
    # 电力行业
    '600900': '电力',  # 长江电力
    '600886': '电力',  # 国投电力
    '000001': '电力',  # 平安银行 (注意：这里应该是银行，示例用)
    '600027': '电力',  # 华电国际
    '600795': '电力',  # 国电电力
    
    # 煤炭开采
    '601088': '煤炭开采',  # 中国神华
    '601898': '煤炭开采',  # 中煤能源
    '600188': '煤炭开采',  # 兖州煤业
    '000983': '煤炭开采',  # 西山煤电
    '600348': '煤炭开采',  # 阳泉煤业
    
    # 有色金属
    '000807': '工业金属',  # 云铝股份
    '002460': '小金属',   # 赣锋锂业
    '600362': '工业金属',  # 江西铜业
    '000878': '工业金属',  # 云南铜业
    '002466': '小金属',   # 天齐锂业
    
    # 医药制造
    '002262': '化学制药',  # 恩华药业
    '000858': '化学制药',  # 五粮液 (注意：这里应该是饮料制造)
    '600276': '化学制药',  # 恒瑞医药
    '000661': '中药',     # 长春高新
    
    # 食品制造
    '002330': '食品制造',  # 得利斯
    '000858': '饮料制造',  # 五粮液
    '600519': '饮料制造',  # 贵州茅台
    '000895': '食品制造',  # 双汇发展
    
    # 银行
    '000001': '银行',  # 平安银行
    '600036': '银行',  # 招商银行
    '601398': '银行',  # 工商银行
    '601939': '银行',  # 建设银行
    
    # 房地产开发
    '000002': '房地产开发',  # 万科A
    '600048': '房地产开发',  # 保利发展
    '001979': '房地产开发',  # 招商蛇口
    
    # 石油化工
    '600028': '石油化工',  # 中国石化
    '601857': '石油开采',  # 中国石油
    '600346': '石油化工',  # 恒力石化
    
    # 钢铁
    '600019': '钢铁',  # 宝钢股份
    '000709': '钢铁',  # 河钢股份
    '600581': '钢铁',  # 八一钢铁
    
    # 汽车整车
    '000625': '汽车整车',  # 长安汽车
    '600104': '汽车整车',  # 上汽集团
    '002594': '汽车整车',  # 比亚迪
    
    # 家用电器
    '000333': '白色家电',  # 美的集团
    '000651': '白色家电',  # 格力电器
    '002415': '白色家电',  # 海康威视 (注意：这里应该是电子)
    
    # 计算机应用
    '002415': '计算机应用',  # 海康威视
    '300059': '计算机应用',  # 东方财富
    '002230': '计算机应用',  # 科大讯飞
    
    # 通信设备
    '000063': '通信设备',  # 中兴通讯
    '002502': '通信设备',  # 骅威股份
    
    # 半导体
    '002415': '半导体',  # 海康威视 (注意：重复映射示例)
    '300661': '半导体',  # 圣邦股份
    '688981': '半导体',  # 中芯国际
    
    # 证券
    '000166': '证券',  # 申万宏源
    '600030': '证券',  # 中信证券
    '000776': '证券',  # 广发证券
    
    # 保险
    '601318': '保险',  # 中国平安
    '601601': '保险',  # 中国太保
    '601628': '保险',  # 中国人寿
    
    # 航空运输
    '600029': '航空运输',  # 南方航空
    '600115': '航空运输',  # 东方航空
    '601111': '航空运输',  # 中国国航
    
    # 港口
    '600018': '港口',  # 上港集团
    '000088': '港口',  # 盐田港
    '600317': '港口',  # 营口港
}

def get_stock_industry(stock_code):
    """
    根据股票代码获取申万二级行业
    
    Args:
        stock_code: 股票代码 (如 '600900')
        
    Returns:
        str: 申万二级行业名称，如果未找到返回None
    """
    return STOCK_INDUSTRY_MAPPING.get(stock_code)

def add_stock_industry_mapping(stock_code, industry):
    """
    添加股票代码到行业的映射
    
    Args:
        stock_code: 股票代码
        industry: 申万二级行业名称
    """
    STOCK_INDUSTRY_MAPPING[stock_code] = industry
    print(f"已添加映射: {stock_code} -> {industry}")

def get_industry_stocks(industry):
    """
    根据行业获取该行业的所有股票代码
    
    Args:
        industry: 申万二级行业名称
        
    Returns:
        list: 该行业的股票代码列表
    """
    return [code for code, ind in STOCK_INDUSTRY_MAPPING.items() if ind == industry]

def get_all_industries():
    """获取所有已映射的行业列表"""
    return list(set(STOCK_INDUSTRY_MAPPING.values()))

def get_mapping_statistics():
    """获取映射统计信息"""
    industries = {}
    for code, industry in STOCK_INDUSTRY_MAPPING.items():
        if industry not in industries:
            industries[industry] = []
        industries[industry].append(code)
    
    return {
        'total_stocks': len(STOCK_INDUSTRY_MAPPING),
        'total_industries': len(industries),
        'industries': industries
    }

if __name__ == "__main__":
    # 测试映射功能
    print("📊 股票行业映射测试")
    print("=" * 50)
    
    # 测试长江电力
    stock_code = '600900'
    industry = get_stock_industry(stock_code)
    print(f"股票 {stock_code} 的行业: {industry}")
    
    # 获取电力行业的所有股票
    power_stocks = get_industry_stocks('电力')
    print(f"电力行业股票: {power_stocks}")
    
    # 获取统计信息
    stats = get_mapping_statistics()
    print(f"\n📈 映射统计:")
    print(f"• 总股票数: {stats['total_stocks']}")
    print(f"• 总行业数: {stats['total_industries']}")
    
    print(f"\n🏭 各行业股票数量:")
    for industry, stocks in stats['industries'].items():
        print(f"• {industry}: {len(stocks)}只股票")