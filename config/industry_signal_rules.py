"""
不同行业的信号规则配置
针对不同行业特性调整信号生成规则
"""

# 行业特定信号规则配置
INDUSTRY_SIGNAL_RULES = {
    # 公用事业类 - 波动小，背离少见
    '电力': {
        'rsi_thresholds': {
            'overbought': 75,
            'oversold': 35
        },
        'divergence_required': False,  # 不强制要求背离
        'rsi_extreme_threshold': {
            'oversold': 32,  # 极端超卖阈值，无需背离
            'overbought': 78  # 极端超买阈值，无需背离
        },
        'reason': '电力行业波动小，RSI背离较少见，放宽背离要求'
    },
    '水务': {
        'rsi_thresholds': {
            'overbought': 75,
            'oversold': 35
        },
        'divergence_required': False,
        'rsi_extreme_threshold': {
            'oversold': 32,
            'overbought': 78
        },
        'reason': '公用事业类，波动小，背离少见'
    },
    '燃气': {
        'rsi_thresholds': {
            'overbought': 75,
            'oversold': 35
        },
        'divergence_required': False,
        'rsi_extreme_threshold': {
            'oversold': 32,
            'overbought': 78
        },
        'reason': '公用事业类，波动小，背离少见'
    },
    
    # 周期性行业 - 波动大，保持严格要求
    '煤炭开采': {
        'rsi_thresholds': {
            'overbought': 70,
            'oversold': 30
        },
        'divergence_required': True,  # 强制要求背离
        'rsi_extreme_threshold': {
            'oversold': 25,  # 极端超卖阈值
            'overbought': 75  # 极端超买阈值
        },
        'reason': '周期性强，波动大，保持严格的背离要求'
    },
    '有色金属': {
        'rsi_thresholds': {
            'overbought': 70,
            'oversold': 30
        },
        'divergence_required': True,
        'rsi_extreme_threshold': {
            'oversold': 25,
            'overbought': 75
        },
        'reason': '周期性强，价格波动大，保持严格要求'
    },
    
    # 消费类 - 相对稳定，适度放宽
    '食品制造': {
        'rsi_thresholds': {
            'overbought': 75,
            'oversold': 35
        },
        'divergence_required': False,
        'rsi_extreme_threshold': {
            'oversold': 30,
            'overbought': 80
        },
        'reason': '消费类相对稳定，适度放宽背离要求'
    },
    
    # 医药类 - 中等要求
    '医药制造': {
        'rsi_thresholds': {
            'overbought': 72,
            'oversold': 32
        },
        'divergence_required': True,
        'rsi_extreme_threshold': {
            'oversold': 28,
            'overbought': 76
        },
        'reason': '医药行业波动中等，保持适中要求'
    }
}

# 默认规则（当行业未在上述配置中时使用）
DEFAULT_SIGNAL_RULES = {
    'rsi_thresholds': {
        'overbought': 70,
        'oversold': 30
    },
    'divergence_required': True,
    'rsi_extreme_threshold': {
        'oversold': 25,
        'overbought': 75
    },
    'reason': '默认严格规则'
}

def get_industry_signal_rules(industry):
    """
    根据行业获取信号规则
    
    Args:
        industry: 申万二级行业名称
        
    Returns:
        dict: 包含该行业信号规则的字典
    """
    return INDUSTRY_SIGNAL_RULES.get(industry, DEFAULT_SIGNAL_RULES)

def should_require_divergence(industry, rsi_value, signal_type='buy'):
    """
    判断是否需要背离确认
    
    Args:
        industry: 行业名称
        rsi_value: 当前RSI值
        signal_type: 信号类型 ('buy' 或 'sell')
        
    Returns:
        bool: 是否需要背离确认
    """
    rules = get_industry_signal_rules(industry)
    
    # 如果该行业不强制要求背离，直接返回False
    if not rules['divergence_required']:
        return False
    
    # 检查是否达到极端阈值，极端情况下可以不要求背离
    extreme_thresholds = rules['rsi_extreme_threshold']
    
    if signal_type == 'buy':
        # 买入信号：RSI极端超卖时不要求背离
        if rsi_value <= extreme_thresholds['oversold']:
            return False
    else:  # sell
        # 卖出信号：RSI极端超买时不要求背离
        if rsi_value >= extreme_thresholds['overbought']:
            return False
    
    # 其他情况要求背离
    return True

def analyze_industry_rules():
    """分析不同行业的信号规则"""
    print("📊 不同行业信号规则分析:")
    print("=" * 80)
    
    for industry, rules in INDUSTRY_SIGNAL_RULES.items():
        print(f"\n🏭 {industry}:")
        print(f"  RSI阈值: 超买≥{rules['rsi_thresholds']['overbought']}, 超卖≤{rules['rsi_thresholds']['oversold']}")
        print(f"  背离要求: {'强制' if rules['divergence_required'] else '不强制'}")
        print(f"  极端阈值: 超买≥{rules['rsi_extreme_threshold']['overbought']}, 超卖≤{rules['rsi_extreme_threshold']['oversold']}")
        print(f"  设置理由: {rules['reason']}")
    
    print(f"\n🔧 默认规则:")
    print(f"  RSI阈值: 超买≥{DEFAULT_SIGNAL_RULES['rsi_thresholds']['overbought']}, 超卖≤{DEFAULT_SIGNAL_RULES['rsi_thresholds']['oversold']}")
    print(f"  背离要求: {'强制' if DEFAULT_SIGNAL_RULES['divergence_required'] else '不强制'}")
    print(f"  设置理由: {DEFAULT_SIGNAL_RULES['reason']}")

if __name__ == "__main__":
    # 测试长江电力的规则
    industry = '电力'
    rsi_value = 33.51
    
    rules = get_industry_signal_rules(industry)
    need_divergence = should_require_divergence(industry, rsi_value, 'buy')
    
    print(f"长江电力(电力行业)信号规则测试:")
    print(f"当前RSI: {rsi_value}")
    print(f"行业规则: {rules}")
    print(f"是否需要背离确认: {need_divergence}")
    
    # 显示所有行业规则
    analyze_industry_rules()