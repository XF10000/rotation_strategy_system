"""
回测配置文件
定义各种回测场景的配置参数
"""

from datetime import datetime, timedelta

# 默认交易成本配置
DEFAULT_COST_CONFIG = {
    'buy_commission_rate': 0.0002,    # 买入手续费率 0.02%
    'sell_commission_rate': 0.0002,   # 卖出手续费率 0.02%
    'min_commission': 5.0,            # 最低手续费 5元
    'stamp_tax_rate': 0.001,          # 印花税率 0.1%（仅卖出）
    'slippage_rate': 0.001,           # 滑点率 0.1%
    'transfer_fee_rate': 0.00002,     # 过户费率 0.002%（沪市）
}

# 默认策略参数
DEFAULT_STRATEGY_PARAMS = {
    'ema_period': 20,
    'rsi_period': 14,
    'rsi_overbought': 70,
    'rsi_oversold': 30,
    'macd_fast': 12,
    'macd_slow': 26,
    'macd_signal': 9,
    'bb_period': 20,
    'bb_std': 2,
    'volume_ma_period': 4,
    'volume_sell_ratio': 1.3,
    'volume_buy_ratio': 0.8,
    'use_industry_optimization': True,
    'rotation_percentage': 0.10,
    
    # V1.1新增：价值比过滤器阈值
    'value_ratio_sell_threshold': 80.0,  # 卖出阈值：价值比 > 80%
    'value_ratio_buy_threshold': 70.0    # 买入阈值：价值比 < 70%
}

# 预定义的回测配置
BACKTEST_CONFIGS = {
    # 标准配置 - 使用当前股票池的5只股票
    'standard': {
        'name': '标准配置',
        'description': '使用当前股票池的标准回测配置',
        'total_capital': 1000000,
        'initial_holdings': {
            "601088": 0.20,  # 中国神华 20%
            "600900": 0.10,  # 长江电力 10%
            "600985": 0.10,  # 淮北矿业 10%
            "002738": 0.10,  # 中矿资源 10%
            "002916": 0.10,  # 深南电路 10%
            "600079": 0.10,  # 人福医药 10%
            "cash": 0.3     # 现金 30%
        },
        'start_date': '2021-01-08',
        'end_date': '2025-07-25',
        'strategy_params': DEFAULT_STRATEGY_PARAMS.copy(),
        'cost_config': DEFAULT_COST_CONFIG.copy()
    },
    
    # 保守配置 - 更多现金，更小轮动比例
    'conservative': {
        'name': '保守配置',
        'description': '更多现金持仓，较小的轮动比例',
        'total_capital': 1000000,
        'initial_holdings': {
            "601088": 0.15,  # 中国神华 15%
            "000807": 0.10,  # 云铝股份 10%
            "002460": 0.15,  # 赣锋锂业 15%
            "002262": 0.10,  # 恩华药业 10%
            "002330": 0.10,  # 得利斯 10%
            "cash": 0.40     # 现金 40%
        },
        'start_date': '2022-01-01',
        'end_date': '2024-12-31',
        'strategy_params': {
            **DEFAULT_STRATEGY_PARAMS,
            'rotation_percentage': 0.05,  # 5%轮动
            'rsi_overbought': 75,         # 更保守的RSI阈值
            'rsi_oversold': 25
        },
        'cost_config': DEFAULT_COST_CONFIG.copy()
    },
    
    # 激进配置 - 更大轮动比例，更敏感的信号
    'aggressive': {
        'name': '激进配置',
        'description': '更大的轮动比例，更敏感的交易信号',
        'total_capital': 1000000,
        'initial_holdings': {
            "601088": 0.25,  # 中国神华 25%
            "000807": 0.20,  # 云铝股份 20%
            "002460": 0.30,  # 赣锋锂业 30%
            "002262": 0.15,  # 恩华药业 15%
            "002330": 0.10,  # 得利斯 10%
            "cash": 0.0      # 现金 0%
        },
        'start_date': '2022-01-01',
        'end_date': '2024-12-31',
        'strategy_params': {
            **DEFAULT_STRATEGY_PARAMS,
            'rotation_percentage': 0.15,  # 15%轮动
            'rsi_overbought': 65,         # 更敏感的RSI阈值
            'rsi_oversold': 35
        },
        'cost_config': DEFAULT_COST_CONFIG.copy()
    },
    
    # 短期测试配置 - 用于快速测试
    'short_test': {
        'name': '短期测试配置',
        'description': '用于快速测试的短期配置',
        'total_capital': 500000,
        'initial_holdings': {
            "601088": 0.40,  # 中国神华 40%
            "000807": 0.30,  # 云铝股份 30%
            "002460": 0.30,  # 赣锋锂业 30%
            "cash": 0.0      # 现金 0%
        },
        'start_date': '2024-01-01',
        'end_date': '2024-06-30',
        'strategy_params': DEFAULT_STRATEGY_PARAMS.copy(),
        'cost_config': DEFAULT_COST_CONFIG.copy()
    },
    
    # 无行业优化配置 - 对比测试用
    'no_industry_optimization': {
        'name': '无行业优化配置',
        'description': '关闭行业优化功能的对比测试',
        'total_capital': 1000000,
        'initial_holdings': {
            "601088": 0.20,  # 中国神华 20%
            "000807": 0.20,  # 云铝股份 20%
            "002460": 0.20,  # 赣锋锂业 20%
            "002262": 0.20,  # 恩华药业 20%
            "002330": 0.20,  # 得利斯 20%
            "cash": 0.0      # 现金 0%
        },
        'start_date': '2022-01-01',
        'end_date': '2024-12-31',
        'strategy_params': {
            **DEFAULT_STRATEGY_PARAMS,
            'use_industry_optimization': False  # 关闭行业优化
        },
        'cost_config': DEFAULT_COST_CONFIG.copy()
    }
}

def get_config(config_name: str) -> dict:
    """
    获取指定的回测配置
    
    Args:
        config_name: 配置名称，如果是'csv'则从CSV文件加载
        
    Returns:
        配置字典
    """
    # 如果请求CSV配置，则从CSV文件加载
    if config_name == 'csv':
        try:
            from config.csv_config_loader import create_csv_config
            return create_csv_config()
        except Exception as e:
            raise ValueError(f"CSV配置加载失败: {str(e)}")
    
    # 否则使用预定义配置
    if config_name not in BACKTEST_CONFIGS:
        raise ValueError(f"未找到配置: {config_name}，可用配置: {list(BACKTEST_CONFIGS.keys()) + ['csv']}")
    
    return BACKTEST_CONFIGS[config_name].copy()

def list_configs() -> dict:
    """
    列出所有可用的配置
    
    Returns:
        配置列表字典 {配置名: 描述}
    """
    return {name: config['description'] for name, config in BACKTEST_CONFIGS.items()}

def create_custom_config(name: str, total_capital: float, initial_holdings: dict,
                        start_date: str, end_date: str, 
                        strategy_params: dict = None,
                        cost_config: dict = None) -> dict:
    """
    创建自定义配置
    
    Args:
        name: 配置名称
        total_capital: 总资金
        initial_holdings: 初始持仓
        start_date: 开始日期
        end_date: 结束日期
        strategy_params: 策略参数（可选）
        cost_config: 成本配置（可选）
        
    Returns:
        自定义配置字典
    """
    config = {
        'name': name,
        'description': f'自定义配置: {name}',
        'total_capital': total_capital,
        'initial_holdings': initial_holdings,
        'start_date': start_date,
        'end_date': end_date,
        'strategy_params': strategy_params or DEFAULT_STRATEGY_PARAMS.copy(),
        'cost_config': cost_config or DEFAULT_COST_CONFIG.copy()
    }
    
    return config

if __name__ == "__main__":
    # 测试配置
    print("可用的回测配置:")
    configs = list_configs()
    for name, desc in configs.items():
        print(f"  {name}: {desc}")
    
    print("\n标准配置详情:")
    standard_config = get_config('standard')
    print(f"  总资金: {standard_config['total_capital']:,}")
    print(f"  回测期间: {standard_config['start_date']} 至 {standard_config['end_date']}")
    print(f"  初始持仓: {standard_config['initial_holdings']}")
    print(f"  轮动比例: {standard_config['strategy_params']['rotation_percentage']:.1%}")