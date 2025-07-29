"""
行业RSI阈值配置加载器
从CSV文件中加载各行业的RSI阈值配置
"""

import pandas as pd
import os
import logging
from typing import Dict, Any, Optional

logger = logging.getLogger(__name__)

class IndustryRSILoader:
    """行业RSI阈值配置加载器"""
    
    def __init__(self, csv_path: str = 'Input/industry_rsi_thresholds.csv'):
        """
        初始化加载器
        
        Args:
            csv_path: CSV配置文件路径
        """
        self.csv_path = csv_path
        self.industry_config = {}
        self.default_config = {
            'rsi_oversold': 30,
            'rsi_overbought': 70,
            'divergence_required': True,
            'rsi_extreme_oversold': 27,
            'rsi_extreme_overbought': 74,
            'risk_level': '标准型'
        }
        self._load_config()
    
    def _load_config(self):
        """从CSV文件加载配置"""
        try:
            if not os.path.exists(self.csv_path):
                logger.warning(f"RSI阈值配置文件不存在: {self.csv_path}，使用默认配置")
                return
            
            # 读取CSV文件
            df = pd.read_csv(self.csv_path, encoding='utf-8')
            logger.info(f"成功读取RSI阈值配置文件: {self.csv_path}")
            
            # 转换为配置字典
            for _, row in df.iterrows():
                industry_name = str(row['行业名称']).strip()
                
                # 处理背离要求
                divergence_text = str(row['是否要求背离']).strip()
                if divergence_text == '是':
                    divergence_required = True
                elif divergence_text == '否':
                    divergence_required = False
                elif divergence_text == '部分':
                    divergence_required = 'partial'  # 部分要求，可以在具体逻辑中处理
                else:
                    divergence_required = True  # 默认要求
                
                config = {
                    'rsi_oversold': int(row['RSI超卖阈值']),
                    'rsi_overbought': int(row['RSI超买阈值']),
                    'divergence_required': divergence_required,
                    'rsi_extreme_oversold': int(row['极端超卖阈值']),
                    'rsi_extreme_overbought': int(row['极端超买阈值']),
                    'risk_level': str(row['风险等级']).strip(),
                    'note': str(row['备注']).strip()
                }
                
                self.industry_config[industry_name] = config
                logger.debug(f"加载行业配置: {industry_name} = {config}")
            
            logger.info(f"成功加载 {len(self.industry_config)} 个行业的RSI配置")
            
        except Exception as e:
            logger.error(f"加载RSI阈值配置失败: {str(e)}")
            logger.warning("将使用默认RSI配置")
    
    def get_industry_config(self, industry_name: str) -> Dict[str, Any]:
        """
        获取指定行业的RSI配置
        
        Args:
            industry_name: 行业名称
            
        Returns:
            Dict: 行业RSI配置
        """
        # 直接匹配
        if industry_name in self.industry_config:
            return self.industry_config[industry_name].copy()
        
        # 模糊匹配（包含关系）
        for config_industry, config in self.industry_config.items():
            if industry_name in config_industry or config_industry in industry_name:
                logger.debug(f"模糊匹配行业: {industry_name} -> {config_industry}")
                return config.copy()
        
        # 使用默认配置
        if '默认' in self.industry_config:
            logger.debug(f"使用默认配置: {industry_name}")
            return self.industry_config['默认'].copy()
        
        # 最后的兜底配置
        logger.warning(f"未找到行业 {industry_name} 的配置，使用系统默认值")
        return self.default_config.copy()
    
    def get_rsi_thresholds(self, industry_name: str) -> Dict[str, int]:
        """
        获取指定行业的RSI阈值
        
        Args:
            industry_name: 行业名称
            
        Returns:
            Dict: RSI阈值配置 {'oversold': int, 'overbought': int}
        """
        config = self.get_industry_config(industry_name)
        return {
            'oversold': config['rsi_oversold'],
            'overbought': config['rsi_overbought'],
            'extreme_oversold': config['rsi_extreme_oversold'],
            'extreme_overbought': config['rsi_extreme_overbought']
        }
    
    def is_divergence_required(self, industry_name: str) -> bool:
        """
        检查指定行业是否要求RSI背离
        
        Args:
            industry_name: 行业名称
            
        Returns:
            bool: 是否要求背离
        """
        config = self.get_industry_config(industry_name)
        divergence_req = config['divergence_required']
        
        if divergence_req == 'partial':
            # 部分要求的逻辑可以根据具体需求定制
            # 这里简化为True
            return True
        
        return bool(divergence_req)
    
    def get_risk_level(self, industry_name: str) -> str:
        """
        获取指定行业的风险等级
        
        Args:
            industry_name: 行业名称
            
        Returns:
            str: 风险等级
        """
        config = self.get_industry_config(industry_name)
        return config.get('risk_level', '标准型')
    
    def list_all_industries(self) -> Dict[str, Dict]:
        """
        列出所有已配置的行业
        
        Returns:
            Dict: 所有行业配置
        """
        return self.industry_config.copy()
    
    def reload_config(self):
        """重新加载配置文件"""
        self.industry_config.clear()
        self._load_config()
        logger.info("RSI阈值配置已重新加载")
    
    def validate_config(self) -> bool:
        """
        验证配置的有效性
        
        Returns:
            bool: 配置是否有效
        """
        try:
            if not self.industry_config:
                logger.warning("没有加载到任何行业配置")
                return False
            
            # 检查必要的默认配置
            if '默认' not in self.industry_config:
                logger.warning("缺少默认行业配置")
            
            # 检查配置完整性
            for industry, config in self.industry_config.items():
                required_keys = ['rsi_oversold', 'rsi_overbought', 'divergence_required']
                for key in required_keys:
                    if key not in config:
                        logger.error(f"行业 {industry} 缺少必要配置: {key}")
                        return False
                
                # 检查阈值合理性
                if config['rsi_oversold'] >= config['rsi_overbought']:
                    logger.error(f"行业 {industry} RSI阈值配置不合理: 超卖({config['rsi_oversold']}) >= 超买({config['rsi_overbought']})")
                    return False
            
            logger.info("RSI阈值配置验证通过")
            return True
            
        except Exception as e:
            logger.error(f"RSI阈值配置验证失败: {str(e)}")
            return False

# 全局实例
_rsi_loader = None

def get_rsi_loader() -> IndustryRSILoader:
    """获取全局RSI加载器实例"""
    global _rsi_loader
    if _rsi_loader is None:
        _rsi_loader = IndustryRSILoader()
    return _rsi_loader

def get_industry_rsi_config(industry_name: str) -> Dict[str, Any]:
    """便捷函数：获取行业RSI配置"""
    return get_rsi_loader().get_industry_config(industry_name)

def get_industry_rsi_thresholds(industry_name: str) -> Dict[str, int]:
    """便捷函数：获取行业RSI阈值"""
    return get_rsi_loader().get_rsi_thresholds(industry_name)

if __name__ == "__main__":
    # 测试代码
    import logging
    logging.basicConfig(level=logging.INFO)
    
    print("🔧 行业RSI阈值加载器测试")
    print("=" * 50)
    
    try:
        # 创建加载器
        loader = IndustryRSILoader()
        
        # 验证配置
        if loader.validate_config():
            print("✅ 配置验证通过")
            
            # 测试几个行业
            test_industries = ['煤炭', '电力', '有色金属', '银行', '不存在的行业']
            
            print(f"\n📊 行业RSI配置测试:")
            for industry in test_industries:
                config = loader.get_industry_config(industry)
                thresholds = loader.get_rsi_thresholds(industry)
                divergence = loader.is_divergence_required(industry)
                risk_level = loader.get_risk_level(industry)
                
                print(f"\n🏭 {industry}:")
                print(f"  RSI阈值: {thresholds['oversold']}/{thresholds['overbought']}")
                print(f"  极端阈值: {thresholds['extreme_oversold']}/{thresholds['extreme_overbought']}")
                print(f"  要求背离: {divergence}")
                print(f"  风险等级: {risk_level}")
            
            print(f"\n📋 总共配置了 {len(loader.list_all_industries())} 个行业")
            print("✅ 行业RSI阈值加载器测试完成")
        else:
            print("❌ 配置验证失败")
            
    except Exception as e:
        print(f"❌ 测试失败: {e}")
        import traceback
        traceback.print_exc()