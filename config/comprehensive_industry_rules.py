"""
全面的申万二级行业信号规则配置
基于行业特性、波动性、周期性等因素制定个性化的RSI阈值和背离要求
"""

# 申万二级行业完整信号规则配置
COMPREHENSIVE_INDUSTRY_RULES = {
    
    # ==================== 公用事业 ====================
    # 特点：波动小、稳定性强、RSI很少达到极端值、背离信号少见
    '电力': {
        'rsi_thresholds': {'overbought': 75, 'oversold': 35},
        'divergence_required': False,
        'rsi_extreme_threshold': {'overbought': 78, 'oversold': 32},
        'reason': '电力行业波动小，RSI很少到达极端值，背离信号少见，适合放宽阈值且不强制背离'
    },
    '水务': {
        'rsi_thresholds': {'overbought': 75, 'oversold': 35},
        'divergence_required': False,
        'rsi_extreme_threshold': {'overbought': 78, 'oversold': 32},
        'reason': '水务公用事业，波动极小，RSI背离罕见'
    },
    '燃气': {
        'rsi_thresholds': {'overbought': 75, 'oversold': 35},
        'divergence_required': False,
        'rsi_extreme_threshold': {'overbought': 78, 'oversold': 32},
        'reason': '燃气供应稳定，价格波动小'
    },
    '环保': {
        'rsi_thresholds': {'overbought': 73, 'oversold': 33},
        'divergence_required': False,
        'rsi_extreme_threshold': {'overbought': 76, 'oversold': 30},
        'reason': '环保行业政策驱动，但整体波动不大'
    },
    
    # ==================== 金融服务 ====================
    # 特点：相对稳定、受政策影响大、波动中等
    '银行': {
        'rsi_thresholds': {'overbought': 75, 'oversold': 35},
        'divergence_required': False,
        'rsi_extreme_threshold': {'overbought': 78, 'oversold': 32},
        'reason': '银行业相对稳定，受监管严格，波动有限'
    },
    '保险': {
        'rsi_thresholds': {'overbought': 74, 'oversold': 34},
        'divergence_required': False,
        'rsi_extreme_threshold': {'overbought': 77, 'oversold': 31},
        'reason': '保险业稳定性强，长期投资属性'
    },
    '证券': {
        'rsi_thresholds': {'overbought': 72, 'oversold': 32},
        'divergence_required': True,
        'rsi_extreme_threshold': {'overbought': 75, 'oversold': 28},
        'reason': '证券业波动较大，与市场情绪关联度高，保持背离要求'
    },
    '多元金融': {
        'rsi_thresholds': {'overbought': 73, 'oversold': 33},
        'divergence_required': True,
        'rsi_extreme_threshold': {'overbought': 76, 'oversold': 30},
        'reason': '多元金融业务复杂，波动中等'
    },
    
    # ==================== 房地产 ====================
    # 特点：周期性强、政策敏感、波动大
    '房地产开发': {
        'rsi_thresholds': {'overbought': 70, 'oversold': 30},
        'divergence_required': True,
        'rsi_extreme_threshold': {'overbought': 75, 'oversold': 25},
        'reason': '房地产周期性强，政策敏感，波动大，保持严格标准'
    },
    '园区开发': {
        'rsi_thresholds': {'overbought': 71, 'oversold': 31},
        'divergence_required': True,
        'rsi_extreme_threshold': {'overbought': 74, 'oversold': 27},
        'reason': '园区开发相对稳定，但仍有周期性'
    },
    
    # ==================== 基础化工 ====================
    # 特点：周期性强、原料价格波动大、供需关系复杂
    '石油化工': {
        'rsi_thresholds': {'overbought': 70, 'oversold': 30},
        'divergence_required': True,
        'rsi_extreme_threshold': {'overbought': 75, 'oversold': 25},
        'reason': '石化行业周期性强，原油价格影响大'
    },
    '化学制品': {
        'rsi_thresholds': {'overbought': 70, 'oversold': 30},
        'divergence_required': True,
        'rsi_extreme_threshold': {'overbought': 75, 'oversold': 25},
        'reason': '化工产品价格波动大，供需变化频繁'
    },
    '化学纤维': {
        'rsi_thresholds': {'overbought': 69, 'oversold': 29},
        'divergence_required': True,
        'rsi_extreme_threshold': {'overbought': 74, 'oversold': 24},
        'reason': '化纤行业周期性明显，价格波动剧烈'
    },
    '化肥农药': {
        'rsi_thresholds': {'overbought': 71, 'oversold': 31},
        'divergence_required': True,
        'rsi_extreme_threshold': {'overbought': 75, 'oversold': 27},
        'reason': '农化产品有季节性，但相对稳定'
    },
    
    # ==================== 有色金属 ====================
    # 特点：强周期性、商品属性、价格波动极大
    '工业金属': {
        'rsi_thresholds': {'overbought': 68, 'oversold': 28},
        'divergence_required': True,
        'rsi_extreme_threshold': {'overbought': 73, 'oversold': 23},
        'reason': '工业金属强周期性，价格波动极大'
    },
    '贵金属': {
        'rsi_thresholds': {'overbought': 69, 'oversold': 29},
        'divergence_required': True,
        'rsi_extreme_threshold': {'overbought': 74, 'oversold': 24},
        'reason': '贵金属避险属性，但仍有较大波动'
    },
    '小金属': {
        'rsi_thresholds': {'overbought': 67, 'oversold': 27},
        'divergence_required': True,
        'rsi_extreme_threshold': {'overbought': 72, 'oversold': 22},
        'reason': '小金属供需集中，价格波动最为剧烈'
    },
    
    # ==================== 钢铁 ====================
    # 特点：强周期性、产能过剩、政策影响大
    '钢铁': {
        'rsi_thresholds': {'overbought': 69, 'oversold': 29},
        'divergence_required': True,
        'rsi_extreme_threshold': {'overbought': 74, 'oversold': 24},
        'reason': '钢铁行业强周期性，供需波动大'
    },
    
    # ==================== 煤炭 - 现已按公用事业标准处理 ====================
    # 特点：现已相当稳定，可视为准公用事业
    '煤炭开采': {
        'rsi_thresholds': {'overbought': 75, 'oversold': 35},
        'divergence_required': False,
        'rsi_extreme_threshold': {'overbought': 78, 'oversold': 32},
        'reason': '煤炭行业现已相当稳定，可视为准公用事业，波动性大幅降低，无需背离确认'
    },
    '焦炭加工': {
        'rsi_thresholds': {'overbought': 69, 'oversold': 29},
        'divergence_required': True,
        'rsi_extreme_threshold': {'overbought': 74, 'oversold': 24},
        'reason': '焦炭与钢铁联动，波动较大'
    },
    
    # ==================== 石油石化 ====================
    # 特点：受国际油价影响、周期性强
    '石油开采': {
        'rsi_thresholds': {'overbought': 70, 'oversold': 30},
        'divergence_required': True,
        'rsi_extreme_threshold': {'overbought': 75, 'oversold': 25},
        'reason': '石油开采受国际油价影响，波动大'
    },
    '油服工程': {
        'rsi_thresholds': {'overbought': 71, 'oversold': 31},
        'divergence_required': True,
        'rsi_extreme_threshold': {'overbought': 75, 'oversold': 27},
        'reason': '油服行业与油价关联，但波动相对缓和'
    },
    
    # ==================== 建筑建材 ====================
    # 特点：与基建地产关联、周期性明显
    '水泥制造': {
        'rsi_thresholds': {'overbought': 71, 'oversold': 31},
        'divergence_required': True,
        'rsi_extreme_threshold': {'overbought': 75, 'oversold': 27},
        'reason': '水泥行业与基建关联，有周期性'
    },
    '玻璃制造': {
        'rsi_thresholds': {'overbought': 70, 'oversold': 30},
        'divergence_required': True,
        'rsi_extreme_threshold': {'overbought': 74, 'oversold': 26},
        'reason': '玻璃行业供需波动明显'
    },
    '装修建材': {
        'rsi_thresholds': {'overbought': 72, 'oversold': 32},
        'divergence_required': True,
        'rsi_extreme_threshold': {'overbought': 75, 'oversold': 28},
        'reason': '装修建材与地产关联，但相对稳定'
    },
    '专业工程': {
        'rsi_thresholds': {'overbought': 72, 'oversold': 32},
        'divergence_required': True,
        'rsi_extreme_threshold': {'overbought': 75, 'oversold': 28},
        'reason': '专业工程项目性强，波动中等'
    },
    
    # ==================== 机械设备 ====================
    # 特点：制造业属性、技术含量不同波动各异
    '工程机械': {
        'rsi_thresholds': {'overbought': 71, 'oversold': 31},
        'divergence_required': True,
        'rsi_extreme_threshold': {'overbought': 75, 'oversold': 27},
        'reason': '工程机械与基建关联，有周期性'
    },
    '专用设备': {
        'rsi_thresholds': {'overbought': 72, 'oversold': 32},
        'divergence_required': True,
        'rsi_extreme_threshold': {'overbought': 75, 'oversold': 28},
        'reason': '专用设备技术含量高，相对稳定'
    },
    '通用机械': {
        'rsi_thresholds': {'overbought': 71, 'oversold': 31},
        'divergence_required': True,
        'rsi_extreme_threshold': {'overbought': 74, 'oversold': 27},
        'reason': '通用机械应用广泛，波动中等'
    },
    '仪器仪表': {
        'rsi_thresholds': {'overbought': 73, 'oversold': 33},
        'divergence_required': True,
        'rsi_extreme_threshold': {'overbought': 76, 'oversold': 30},
        'reason': '仪器仪表技术门槛高，相对稳定'
    },
    
    # ==================== 电力设备 ====================
    # 特点：新能源驱动、政策支持、成长性强
    '电机': {
        'rsi_thresholds': {'overbought': 72, 'oversold': 32},
        'divergence_required': True,
        'rsi_extreme_threshold': {'overbought': 75, 'oversold': 28},
        'reason': '电机行业稳定，技术成熟'
    },
    '电气自动化': {
        'rsi_thresholds': {'overbought': 73, 'oversold': 33},
        'divergence_required': True,
        'rsi_extreme_threshold': {'overbought': 76, 'oversold': 30},
        'reason': '电气自动化技术含量高'
    },
    '新能源设备': {
        'rsi_thresholds': {'overbought': 70, 'oversold': 30},
        'divergence_required': True,
        'rsi_extreme_threshold': {'overbought': 74, 'oversold': 26},
        'reason': '新能源设备成长性强，但波动较大'
    },
    
    # ==================== 国防军工 ====================
    # 特点：政策驱动、订单集中、波动较大
    '航空装备': {
        'rsi_thresholds': {'overbought': 71, 'oversold': 31},
        'divergence_required': True,
        'rsi_extreme_threshold': {'overbought': 75, 'oversold': 27},
        'reason': '航空装备技术壁垒高，但订单波动大'
    },
    '地面兵装': {
        'rsi_thresholds': {'overbought': 71, 'oversold': 31},
        'divergence_required': True,
        'rsi_extreme_threshold': {'overbought': 75, 'oversold': 27},
        'reason': '地面装备订单集中，波动明显'
    },
    '船舶制造': {
        'rsi_thresholds': {'overbought': 70, 'oversold': 30},
        'divergence_required': True,
        'rsi_extreme_threshold': {'overbought': 74, 'oversold': 26},
        'reason': '船舶制造周期长，订单波动大'
    },
    
    # ==================== 汽车 ====================
    # 特点：消费属性、技术变革、电动化转型
    '汽车整车': {
        'rsi_thresholds': {'overbought': 71, 'oversold': 31},
        'divergence_required': True,
        'rsi_extreme_threshold': {'overbought': 75, 'oversold': 27},
        'reason': '汽车整车消费属性，但转型期波动大'
    },
    '汽车零部件': {
        'rsi_thresholds': {'overbought': 72, 'oversold': 32},
        'divergence_required': True,
        'rsi_extreme_threshold': {'overbought': 75, 'oversold': 28},
        'reason': '汽车零部件相对稳定'
    },
    '汽车服务': {
        'rsi_thresholds': {'overbought': 73, 'oversold': 33},
        'divergence_required': True,
        'rsi_extreme_threshold': {'overbought': 76, 'oversold': 30},
        'reason': '汽车服务稳定性较强'
    },
    
    # ==================== 家用电器 ====================
    # 特点：消费属性、品牌集中、相对稳定
    '白色家电': {
        'rsi_thresholds': {'overbought': 74, 'oversold': 34},
        'divergence_required': False,
        'rsi_extreme_threshold': {'overbought': 77, 'oversold': 31},
        'reason': '白电行业成熟稳定，龙头集中'
    },
    '黑色家电': {
        'rsi_thresholds': {'overbought': 73, 'oversold': 33},
        'divergence_required': True,
        'rsi_extreme_threshold': {'overbought': 76, 'oversold': 30},
        'reason': '黑电技术变化快，竞争激烈'
    },
    '小家电': {
        'rsi_thresholds': {'overbought': 74, 'oversold': 34},
        'divergence_required': False,
        'rsi_extreme_threshold': {'overbought': 77, 'oversold': 31},
        'reason': '小家电创新频繁，但整体稳定'
    },
    
    # ==================== 纺织服装 ====================
    # 特点：消费属性、季节性、品牌分化
    '纺织制造': {
        'rsi_thresholds': {'overbought': 72, 'oversold': 32},
        'divergence_required': True,
        'rsi_extreme_threshold': {'overbought': 75, 'oversold': 28},
        'reason': '纺织制造有季节性，原料价格影响大'
    },
    '服装家纺': {
        'rsi_thresholds': {'overbought': 73, 'oversold': 33},
        'divergence_required': True,
        'rsi_extreme_threshold': {'overbought': 76, 'oversold': 30},
        'reason': '服装家纺品牌分化，消费属性强'
    },
    
    # ==================== 轻工制造 ====================
    # 特点：制造业属性、出口导向、成本敏感
    '造纸': {
        'rsi_thresholds': {'overbought': 71, 'oversold': 31},
        'divergence_required': True,
        'rsi_extreme_threshold': {'overbought': 75, 'oversold': 27},
        'reason': '造纸行业原料价格波动大'
    },
    '包装印刷': {
        'rsi_thresholds': {'overbought': 72, 'oversold': 32},
        'divergence_required': True,
        'rsi_extreme_threshold': {'overbought': 75, 'oversold': 28},
        'reason': '包装印刷相对稳定'
    },
    '家具制造': {
        'rsi_thresholds': {'overbought': 73, 'oversold': 33},
        'divergence_required': True,
        'rsi_extreme_threshold': {'overbought': 76, 'oversold': 30},
        'reason': '家具制造与地产关联，但相对稳定'
    },
    
    # ==================== 食品饮料 ====================
    # 特点：消费属性强、防御性强、相对稳定
    '食品制造': {
        'rsi_thresholds': {'overbought': 75, 'oversold': 35},
        'divergence_required': False,
        'rsi_extreme_threshold': {'overbought': 78, 'oversold': 32},
        'reason': '食品制造消费属性强，防御性好，波动小'
    },
    '饮料制造': {
        'rsi_thresholds': {'overbought': 75, 'oversold': 35},
        'divergence_required': False,
        'rsi_extreme_threshold': {'overbought': 78, 'oversold': 32},
        'reason': '饮料行业品牌集中，稳定性强'
    },
    '乳品': {
        'rsi_thresholds': {'overbought': 74, 'oversold': 34},
        'divergence_required': False,
        'rsi_extreme_threshold': {'overbought': 77, 'oversold': 31},
        'reason': '乳品行业必需消费，相对稳定'
    },
    '调味发酵品': {
        'rsi_thresholds': {'overbought': 75, 'oversold': 35},
        'divergence_required': False,
        'rsi_extreme_threshold': {'overbought': 78, 'oversold': 32},
        'reason': '调味品刚需属性强，价格稳定'
    },
    
    # ==================== 农林牧渔 ====================
    # 特点：周期性、季节性、政策影响
    '种植业': {
        'rsi_thresholds': {'overbought': 71, 'oversold': 31},
        'divergence_required': True,
        'rsi_extreme_threshold': {'overbought': 75, 'oversold': 27},
        'reason': '种植业有季节性和周期性'
    },
    '畜禽养殖': {
        'rsi_thresholds': {'overbought': 69, 'oversold': 29},
        'divergence_required': True,
        'rsi_extreme_threshold': {'overbought': 74, 'oversold': 24},
        'reason': '养殖业周期性强，价格波动大'
    },
    '水产养殖': {
        'rsi_thresholds': {'overbought': 70, 'oversold': 30},
        'divergence_required': True,
        'rsi_extreme_threshold': {'overbought': 74, 'oversold': 26},
        'reason': '水产养殖季节性明显'
    },
    '林业': {
        'rsi_thresholds': {'overbought': 72, 'oversold': 32},
        'divergence_required': True,
        'rsi_extreme_threshold': {'overbought': 75, 'oversold': 28},
        'reason': '林业周期长，相对稳定'
    },
    
    # ==================== 医药生物 ====================
    # 特点：创新驱动、政策敏感、分化明显
    '化学制药': {
        'rsi_thresholds': {'overbought': 72, 'oversold': 32},
        'divergence_required': True,
        'rsi_extreme_threshold': {'overbought': 75, 'oversold': 28},
        'reason': '化学制药技术门槛高，但政策影响大'
    },
    '中药': {
        'rsi_thresholds': {'overbought': 73, 'oversold': 33},
        'divergence_required': True,
        'rsi_extreme_threshold': {'overbought': 76, 'oversold': 30},
        'reason': '中药相对稳定，但政策影响明显'
    },
    '生物制品': {
        'rsi_thresholds': {'overbought': 71, 'oversold': 31},
        'divergence_required': True,
        'rsi_extreme_threshold': {'overbought': 75, 'oversold': 27},
        'reason': '生物制品创新性强，波动较大'
    },
    '医疗器械': {
        'rsi_thresholds': {'overbought': 72, 'oversold': 32},
        'divergence_required': True,
        'rsi_extreme_threshold': {'overbought': 75, 'oversold': 28},
        'reason': '医疗器械技术含量高，相对稳定'
    },
    '医疗服务': {
        'rsi_thresholds': {'overbought': 73, 'oversold': 33},
        'divergence_required': True,
        'rsi_extreme_threshold': {'overbought': 76, 'oversold': 30},
        'reason': '医疗服务稳定性强'
    },
    '医药商业': {
        'rsi_thresholds': {'overbought': 74, 'oversold': 34},
        'divergence_required': False,
        'rsi_extreme_threshold': {'overbought': 77, 'oversold': 31},
        'reason': '医药商业模式稳定，波动小'
    },
    
    # ==================== 商贸零售 ====================
    # 特点：消费属性、线上冲击、模式变化
    '百货': {
        'rsi_thresholds': {'overbought': 72, 'oversold': 32},
        'divergence_required': True,
        'rsi_extreme_threshold': {'overbought': 75, 'oversold': 28},
        'reason': '百货受电商冲击，波动较大'
    },
    '超市': {
        'rsi_thresholds': {'overbought': 73, 'oversold': 33},
        'divergence_required': True,
        'rsi_extreme_threshold': {'overbought': 76, 'oversold': 30},
        'reason': '超市刚需属性，相对稳定'
    },
    '专业零售': {
        'rsi_thresholds': {'overbought': 72, 'oversold': 32},
        'divergence_required': True,
        'rsi_extreme_threshold': {'overbought': 75, 'oversold': 28},
        'reason': '专业零售分化明显'
    },
    '贸易': {
        'rsi_thresholds': {'overbought': 71, 'oversold': 31},
        'divergence_required': True,
        'rsi_extreme_threshold': {'overbought': 74, 'oversold': 27},
        'reason': '贸易业务波动较大'
    },
    
    # ==================== 交通运输 ====================
    # 特点：周期性、油价敏感、政策影响
    '航空运输': {
        'rsi_thresholds': {'overbought': 70, 'oversold': 30},
        'divergence_required': True,
        'rsi_extreme_threshold': {'overbought': 74, 'oversold': 26},
        'reason': '航空运输周期性强，油价敏感'
    },
    '铁路运输': {
        'rsi_thresholds': {'overbought': 74, 'oversold': 34},
        'divergence_required': False,
        'rsi_extreme_threshold': {'overbought': 77, 'oversold': 31},
        'reason': '铁路运输垄断性强，相对稳定'
    },
    '公路运输': {
        'rsi_thresholds': {'overbought': 72, 'oversold': 32},
        'divergence_required': True,
        'rsi_extreme_threshold': {'overbought': 75, 'oversold': 28},
        'reason': '公路运输竞争激烈，波动中等'
    },
    '水上运输': {
        'rsi_thresholds': {'overbought': 71, 'oversold': 31},
        'divergence_required': True,
        'rsi_extreme_threshold': {'overbought': 75, 'oversold': 27},
        'reason': '水运与大宗商品关联，波动较大'
    },
    '港口': {
        'rsi_thresholds': {'overbought': 73, 'oversold': 33},
        'divergence_required': True,
        'rsi_extreme_threshold': {'overbought': 76, 'oversold': 30},
        'reason': '港口基础设施属性，相对稳定'
    },
    '物流': {
        'rsi_thresholds': {'overbought': 72, 'oversold': 32},
        'divergence_required': True,
        'rsi_extreme_threshold': {'overbought': 75, 'oversold': 28},
        'reason': '物流行业快速发展，波动中等'
    },
    
    # ==================== 休闲服务 ====================
    # 特点：消费属性、季节性、政策敏感
    '酒店': {
        'rsi_thresholds': {'overbought': 72, 'oversold': 32},
        'divergence_required': True,
        'rsi_extreme_threshold': {'overbought': 75, 'oversold': 28},
        'reason': '酒店业季节性明显，疫情影响大'
    },
    '旅游': {
        'rsi_thresholds': {'overbought': 71, 'oversold': 31},
        'divergence_required': True,
        'rsi_extreme_threshold': {'overbought': 75, 'oversold': 27},
        'reason': '旅游业波动大，政策敏感'
    },
    '餐饮': {
        'rsi_thresholds': {'overbought': 72, 'oversold': 32},
        'divergence_required': True,
        'rsi_extreme_threshold': {'overbought': 75, 'oversold': 28},
        'reason': '餐饮业竞争激烈，波动较大'
    },
    '教育': {
        'rsi_thresholds': {'overbought': 71, 'oversold': 31},
        'divergence_required': True,
        'rsi_extreme_threshold': {'overbought': 75, 'oversold': 27},
        'reason': '教育行业政策敏感，波动较大'
    }
}

def get_comprehensive_industry_rules(industry_name):
    """
    获取指定行业的完整信号规则
    
    Args:
        industry_name (str): 行业名称
        
    Returns:
        dict: 行业规则配置，如果未找到则返回None
    """
    # 行业名称映射表，处理自动识别与配置键名不一致的情况
    industry_mapping = {
        '煤炭': '煤炭开采',
        '石油': '石油开采',
        '化工': '化学制品',
        '钢铁': '钢铁',
        '有色': '工业金属',
        '电力': '电力',
        '银行': '银行',
        '保险': '保险',
        '证券': '证券',
        '房地产': '房地产开发',
        '建筑': '专业工程',
        '机械': '通用机械',
        '汽车': '汽车整车',
        '家电': '白色家电',
        '食品': '食品制造',
        '医药': '化学制药',
        '零售': '专业零售',
        '交通': '公路运输'
    }
    
    # 先尝试直接匹配
    rules = COMPREHENSIVE_INDUSTRY_RULES.get(industry_name)
    if rules:
        return rules
    
    # 如果直接匹配失败，尝试映射匹配
    mapped_industry = industry_mapping.get(industry_name)
    if mapped_industry:
        return COMPREHENSIVE_INDUSTRY_RULES.get(mapped_industry)
    
    return None

def get_all_industry_names():
    """
    获取所有已配置的行业名称列表
    
    Returns:
        list: 行业名称列表
    """
    return list(COMPREHENSIVE_INDUSTRY_RULES.keys())

def get_industry_classification():
    """
    按照RSI阈值对行业进行分类
    
    Returns:
        dict: 分类结果
    """
    classification = {
        '超保守型': [],  # RSI阈值 >= 35
        '保守型': [],    # RSI阈值 32-34
        '标准型': [],    # RSI阈值 30-31
        '激进型': []     # RSI阈值 <= 29
    }
    
    for industry, rules in COMPREHENSIVE_INDUSTRY_RULES.items():
        oversold_threshold = rules['rsi_thresholds']['oversold']
        
        if oversold_threshold >= 35:
            classification['超保守型'].append(industry)
        elif oversold_threshold >= 32:
            classification['保守型'].append(industry)
        elif oversold_threshold >= 30:
            classification['标准型'].append(industry)
        else:
            classification['激进型'].append(industry)
    
    return classification
