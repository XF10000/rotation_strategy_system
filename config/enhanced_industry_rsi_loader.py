"""
增强版行业RSI阈值加载器
支持动态计算的申万二级行业RSI阈值
"""

import logging
import os
from typing import Any, Dict

import pandas as pd

logger = logging.getLogger(__name__)

class EnhancedIndustryRSILoader:
    """增强版行业RSI阈值加载器，支持动态计算的阈值"""
    
    def __init__(self, dynamic_threshold_path: str = None, fallback_path: str = None):
        """
        初始化加载器
        
        Args:
            dynamic_threshold_path: 动态计算的RSI阈值文件路径
            fallback_path: 备用的静态阈值文件路径
        """
        self.dynamic_threshold_path = dynamic_threshold_path or "sw_rsi_thresholds/output/sw2_rsi_threshold.csv"
        self.fallback_path = fallback_path or "Input/industry_rsi_thresholds.csv"
        self.thresholds_data = {}
        self.industry_mapping = {}
        self._load_thresholds()
    
    def _load_thresholds(self):
        """加载RSI阈值数据"""
        try:
            # 优先尝试加载动态计算的阈值
            if os.path.exists(self.dynamic_threshold_path):
                self._load_dynamic_thresholds()
                logger.info(f"成功加载动态RSI阈值：{self.dynamic_threshold_path}")
            else:
                logger.warning(f"动态阈值文件不存在：{self.dynamic_threshold_path}")
                self._load_fallback_thresholds()
        except Exception as e:
            logger.error(f"加载动态阈值失败：{e}")
            self._load_fallback_thresholds()
    
    def _load_dynamic_thresholds(self):
        """加载动态计算的RSI阈值"""
        df = pd.read_csv(self.dynamic_threshold_path, encoding='utf-8')
        
        for _, row in df.iterrows():
            industry_code = str(row['行业代码'])
            industry_name = row['行业名称']
            
            # 建立行业代码和名称的映射
            self.industry_mapping[industry_code] = industry_name
            self.industry_mapping[industry_name] = industry_code
            
            # 存储阈值数据
            self.thresholds_data[industry_code] = {
                'industry_name': industry_name,
                'layer': row['layer'],
                'volatility': row['volatility'],
                'current_rsi': row['current_rsi'],
                'oversold': row['普通超卖'],
                'overbought': row['普通超买'],
                'extreme_oversold': row['极端超卖'],
                'extreme_overbought': row['极端超买'],
                'data_points': row['data_points'],
                'update_time': row['更新时间']
            }
            
            # 同时支持行业名称作为键
            self.thresholds_data[industry_name] = self.thresholds_data[industry_code]
    
    def _load_fallback_thresholds(self):
        """加载备用的静态阈值"""
        try:
            df = pd.read_csv(self.fallback_path, encoding='utf-8')
            logger.info(f"使用备用静态阈值：{self.fallback_path}")
            
            for _, row in df.iterrows():
                industry = row['industry']
                self.thresholds_data[industry] = {
                    'industry_name': industry,
                    'oversold': row['rsi_oversold'],
                    'overbought': row['rsi_overbought'],
                    'extreme_oversold': row.get('rsi_extreme_oversold', row['rsi_oversold']),
                    'extreme_overbought': row.get('rsi_extreme_overbought', row['rsi_overbought'])
                }
        except Exception as e:
            logger.error(f"加载备用阈值失败：{e}")
            # 使用默认阈值
            self._load_default_thresholds()
    
    def _load_default_thresholds(self):
        """加载默认阈值"""
        logger.warning("使用默认RSI阈值")
        default_thresholds = {
            'oversold': 30,
            'overbought': 70,
            'extreme_oversold': 20,
            'extreme_overbought': 80
        }
        self.thresholds_data['default'] = default_thresholds
    
    def get_rsi_thresholds(self, industry: str, use_extreme: bool = False) -> Dict[str, float]:
        """
        获取指定行业的RSI阈值
        
        Args:
            industry: 行业名称或代码
            use_extreme: 是否使用极端阈值
            
        Returns:
            包含oversold和overbought阈值的字典
        """
        # 尝试直接匹配
        if industry in self.thresholds_data:
            data = self.thresholds_data[industry]
        # 尝试通过映射匹配
        elif industry in self.industry_mapping:
            mapped_industry = self.industry_mapping[industry]
            data = self.thresholds_data.get(mapped_industry, {})
        else:
            # 使用默认阈值
            logger.warning(f"未找到行业 {industry} 的RSI阈值，使用默认值")
            data = self.thresholds_data.get('default', {
                'oversold': 30, 'overbought': 70,
                'extreme_oversold': 20, 'extreme_overbought': 80
            })
        
        if use_extreme:
            return {
                'oversold': data.get('extreme_oversold', data.get('oversold', 30)),
                'overbought': data.get('extreme_overbought', data.get('overbought', 70))
            }
        else:
            return {
                'oversold': data.get('oversold', 30),
                'overbought': data.get('overbought', 70)
            }
    
    def get_industry_info(self, industry: str) -> Dict[str, Any]:
        """
        获取行业的完整信息
        
        Args:
            industry: 行业名称或代码
            
        Returns:
            行业的完整信息字典
        """
        if industry in self.thresholds_data:
            return self.thresholds_data[industry].copy()
        elif industry in self.industry_mapping:
            mapped_industry = self.industry_mapping[industry]
            return self.thresholds_data.get(mapped_industry, {}).copy()
        else:
            return {}
    
    def list_available_industries(self) -> list:
        """获取所有可用的行业列表"""
        industries = []
        for key, value in self.thresholds_data.items():
            if isinstance(value, dict) and 'industry_name' in value:
                industries.append({
                    'code': key if key.isdigit() else self.industry_mapping.get(key, ''),
                    'name': value['industry_name'],
                    'volatility_layer': value.get('layer', 'unknown')
                })
        return industries
    
    def get_statistics(self) -> Dict[str, Any]:
        """获取阈值数据的统计信息"""
        if not self.thresholds_data:
            return {}
        
        # 过滤出有效的行业数据
        valid_data = [v for v in self.thresholds_data.values() 
                     if isinstance(v, dict) and 'oversold' in v]
        
        if not valid_data:
            return {}
        
        oversold_values = [d['oversold'] for d in valid_data]
        overbought_values = [d['overbought'] for d in valid_data]
        
        return {
            'total_industries': len(valid_data),
            'oversold_range': (min(oversold_values), max(oversold_values)),
            'overbought_range': (min(overbought_values), max(overbought_values)),
            'avg_oversold': sum(oversold_values) / len(oversold_values),
            'avg_overbought': sum(overbought_values) / len(overbought_values)
        }


# 全局实例
_enhanced_rsi_loader = None

def get_enhanced_rsi_loader() -> EnhancedIndustryRSILoader:
    """获取增强版RSI阈值加载器的全局实例"""
    global _enhanced_rsi_loader
    if _enhanced_rsi_loader is None:
        _enhanced_rsi_loader = EnhancedIndustryRSILoader()
    return _enhanced_rsi_loader

def reload_enhanced_rsi_loader():
    """重新加载RSI阈值数据"""
    global _enhanced_rsi_loader
    _enhanced_rsi_loader = None
    return get_enhanced_rsi_loader()