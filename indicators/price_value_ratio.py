"""
价值比 (Price-to-Value Ratio, PVR) 计算模块

该模块用于计算股票当前价格相对于DCF估值的比例，
帮助判断股票的估值水平和安全边际。

价值比 = (当前股价 / DCF估值) × 100%
- 100% = 股价等于内在价值（完全合理定价）
- < 100% = 股价被低估（如70% = 低估30%）
- > 100% = 股价被高估（如120% = 高估20%）
"""

import logging
from typing import Any, Dict, Optional

import numpy as np
import pandas as pd

logger = logging.getLogger(__name__)


def calculate_pvr(current_price: float, dcf_value: float) -> Optional[float]:
    """
    计算单个股票的价值比 (Price-to-Value Ratio, PVR)
    
    Args:
        current_price (float): 当前股价
        dcf_value (float): DCF估值
    
    Returns:
        Optional[float]: 价值比百分比 (如 76.5 表示76.5%)，无效输入时返回None
    
    Examples:
        >>> calculate_pvr(15.20, 20.00)
        76.0
        >>> calculate_pvr(24.00, 20.00)
        120.0
    """
    try:
        # 输入验证
        if not isinstance(current_price, (int, float)) or not isinstance(dcf_value, (int, float)):
            logger.warning(f"输入类型错误: current_price={type(current_price)}, dcf_value={type(dcf_value)}")
            return None
        
        if current_price <= 0:
            logger.warning(f"当前股价无效: {current_price}")
            return None
            
        if dcf_value <= 0:
            logger.warning(f"DCF估值无效: {dcf_value}")
            return None
        
        # 计算价值比
        pvr = (current_price / dcf_value) * 100
        
        return round(pvr, 2)
        
    except Exception as e:
        logger.error(f"计算价值比时出错: {str(e)}")
        return None


def calculate_pvr_series(price_series: pd.Series, dcf_value: float) -> pd.Series:
    """
    计算价格序列的价值比
    
    Args:
        price_series (pd.Series): 价格序列（如历史收盘价）
        dcf_value (float): DCF估值
    
    Returns:
        pd.Series: 价值比序列
    
    Examples:
        >>> prices = pd.Series([15.0, 16.0, 17.0])
        >>> calculate_pvr_series(prices, 20.0)
        0    75.0
        1    80.0
        2    85.0
        dtype: float64
    """
    try:
        if dcf_value <= 0:
            logger.warning(f"DCF估值无效: {dcf_value}")
            return pd.Series([None] * len(price_series), index=price_series.index)
        
        # 过滤无效价格
        valid_prices = price_series[price_series > 0]
        
        if len(valid_prices) == 0:
            logger.warning("没有有效的价格数据")
            return pd.Series([None] * len(price_series), index=price_series.index)
        
        # 计算价值比序列
        pvr_series = (price_series / dcf_value * 100).round(2)
        
        # 将无效价格对应的价值比设为NaN
        pvr_series[price_series <= 0] = np.nan
        
        return pvr_series
        
    except Exception as e:
        logger.error(f"计算价值比序列时出错: {str(e)}")
        return pd.Series([None] * len(price_series), index=price_series.index)


def get_pvr_status(pvr: float, safety_margin_threshold: float = 70.0) -> Dict[str, Any]:
    """
    根据价值比判断估值状态
    
    Args:
        pvr (float): 价值比百分比
        safety_margin_threshold (float): 安全边际阈值，默认70%
    
    Returns:
        Dict[str, Any]: 包含估值状态信息的字典
        
    Examples:
        >>> get_pvr_status(76.0)
        {
            'pvr': 76.0,
            'status': '低估',
            'undervalued_pct': 24.0,
            'within_safety_margin': False,
            'description': '当前价格低估24.0%，但未达到安全边际要求'
        }
    """
    try:
        if pvr is None or not isinstance(pvr, (int, float)):
            return {
                'pvr': pvr,
                'status': '无效',
                'undervalued_pct': None,
                'within_safety_margin': False,
                'description': '价值比数据无效'
            }
        
        # 判断估值状态
        if pvr < 100:
            status = '低估'
            undervalued_pct = 100 - pvr
            within_safety_margin = pvr <= safety_margin_threshold
            
            if within_safety_margin:
                description = f'当前价格低估{undervalued_pct:.1f}%，符合安全边际要求'
            else:
                description = f'当前价格低估{undervalued_pct:.1f}%，但未达到安全边际要求'
                
        elif pvr == 100:
            status = '合理'
            undervalued_pct = 0
            within_safety_margin = False
            description = '当前价格等于内在价值，估值合理'
            
        else:  # pvr > 100
            status = '高估'
            overvalued_pct = pvr - 100
            undervalued_pct = -overvalued_pct  # 负数表示高估
            within_safety_margin = False
            description = f'当前价格高估{overvalued_pct:.1f}%，存在估值风险'
        
        return {
            'pvr': pvr,
            'status': status,
            'undervalued_pct': undervalued_pct,
            'within_safety_margin': within_safety_margin,
            'description': description
        }
        
    except Exception as e:
        logger.error(f"分析价值比状态时出错: {str(e)}")
        return {
            'pvr': pvr,
            'status': '错误',
            'undervalued_pct': None,
            'within_safety_margin': False,
            'description': f'分析出错: {str(e)}'
        }


def calculate_portfolio_pvr_summary(portfolio_data: Dict[str, Dict[str, float]]) -> Dict[str, Any]:
    """
    计算投资组合的价值比汇总信息
    
    Args:
        portfolio_data (Dict): 投资组合数据
        格式: {
            '股票代码': {
                'current_price': 当前价格,
                'dcf_value': DCF估值,
                'weight': 权重 (可选)
            }
        }
    
    Returns:
        Dict[str, Any]: 投资组合价值比汇总
    
    Examples:
        >>> portfolio = {
        ...     '600036': {'current_price': 15.2, 'dcf_value': 20.0, 'weight': 0.3},
        ...     '000858': {'current_price': 180.0, 'dcf_value': 200.0, 'weight': 0.7}
        ... }
        >>> calculate_portfolio_pvr_summary(portfolio)
    """
    try:
        if not portfolio_data:
            return {'error': '投资组合数据为空'}
        
        pvr_list = []
        weighted_pvr_sum = 0
        total_weight = 0
        stock_details = {}
        
        for stock_code, data in portfolio_data.items():
            current_price = data.get('current_price')
            dcf_value = data.get('dcf_value')
            weight = data.get('weight', 1.0)  # 默认等权重
            
            pvr = calculate_pvr(current_price, dcf_value)
            
            if pvr is not None:
                pvr_list.append(pvr)
                weighted_pvr_sum += pvr * weight
                total_weight += weight
                
                stock_details[stock_code] = {
                    'pvr': pvr,
                    'status': get_pvr_status(pvr),
                    'weight': weight
                }
        
        if not pvr_list:
            return {'error': '没有有效的价值比数据'}
        
        # 计算汇总统计
        summary = {
            'stock_count': len(pvr_list),
            'average_pvr': round(np.mean(pvr_list), 2),
            'weighted_average_pvr': round(weighted_pvr_sum / total_weight, 2) if total_weight > 0 else None,
            'min_pvr': round(min(pvr_list), 2),
            'max_pvr': round(max(pvr_list), 2),
            'median_pvr': round(np.median(pvr_list), 2),
            'undervalued_count': len([p for p in pvr_list if p < 100]),
            'overvalued_count': len([p for p in pvr_list if p > 100]),
            'fairly_valued_count': len([p for p in pvr_list if p == 100]),
            'within_safety_margin_count': len([p for p in pvr_list if p <= 70]),
            'stock_details': stock_details
        }
        
        return summary
        
    except Exception as e:
        logger.error(f"计算投资组合价值比汇总时出错: {str(e)}")
        return {'error': f'计算出错: {str(e)}'}


# 便捷函数别名
def pvr(current_price: float, dcf_value: float) -> Optional[float]:
    """calculate_pvr的简化别名"""
    return calculate_pvr(current_price, dcf_value)


if __name__ == "__main__":
    # 测试代码
    print("=== 价值比计算模块测试 ===")
    
    # 测试单个计算
    print("\n1. 单个价值比计算:")
    test_cases = [
        (15.20, 20.00),  # 低估
        (20.00, 20.00),  # 合理
        (24.00, 20.00),  # 高估
        (0, 20.00),      # 无效价格
        (15.20, 0),      # 无效估值
    ]
    
    for price, value in test_cases:
        result = calculate_pvr(price, value)
        print(f"价格: {price}, 估值: {value} -> 价值比: {result}%")
    
    # 测试状态分析
    print("\n2. 估值状态分析:")
    for pvr_value in [65.0, 76.0, 100.0, 120.0]:
        status = get_pvr_status(pvr_value)
        print(f"价值比: {pvr_value}% -> {status['description']}")
    
    # 测试序列计算
    print("\n3. 价格序列计算:")
    prices = pd.Series([15.0, 16.0, 17.0, 18.0, 19.0])
    dcf_val = 20.0
    pvr_series = calculate_pvr_series(prices, dcf_val)
    print(f"价格序列: {prices.tolist()}")
    print(f"价值比序列: {pvr_series.tolist()}")
    
    print("\n=== 测试完成 ===")