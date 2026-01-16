"""
统一配置管理器

职责：
1. 提供系统所有配置的单一访问入口
2. 加载和验证配置文件
3. 管理配置优先级
4. 提供配置默认值

不负责：
- 配置文件的格式转换
- 业务逻辑
"""

import logging
from pathlib import Path
from typing import Any, Dict

import pandas as pd

logger = logging.getLogger(__name__)


class ConfigManager:
    """统一配置管理器"""
    
    _instance = None
    
    def __new__(cls):
        """单例模式"""
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._initialized = False
        return cls._instance
    
    def __init__(self):
        """初始化配置管理器"""
        if self._initialized:
            return
            
        self._config = {}
        self._project_root = self._find_project_root()
        self._initialized = True
        
        logger.info("ConfigManager 初始化完成")
    
    def _find_project_root(self) -> Path:
        """查找项目根目录"""
        current = Path(__file__).resolve()
        
        # 向上查找，直到找到包含 main.py 的目录
        while current.parent != current:
            if (current / 'main.py').exists():
                return current
            current = current.parent
        
        # 如果没找到，使用当前文件的父目录的父目录
        return Path(__file__).resolve().parent.parent
    
    def load_config(self, config_type: str = 'csv') -> None:
        """
        加载配置
        
        Args:
            config_type: 配置类型，'csv' 或 'default'
        """
        if config_type == 'csv':
            self._load_csv_config()
        else:
            self._load_default_config()
        
        logger.info(f"配置加载完成，类型: {config_type}")
    
    def _load_csv_config(self) -> None:
        """加载CSV配置"""
        input_dir = self._project_root / 'Input'
        
        # 1. 加载回测参数配置
        backtest_settings_path = input_dir / 'Backtest_settings.csv'
        if backtest_settings_path.exists():
            self._load_backtest_settings(backtest_settings_path)
        else:
            logger.warning(f"回测配置文件不存在: {backtest_settings_path}")
        
        # 2. 加载股票池配置
        portfolio_config_path = input_dir / 'portfolio_config.csv'
        if portfolio_config_path.exists():
            self._load_portfolio_config(portfolio_config_path)
        else:
            logger.warning(f"股票池配置文件不存在: {portfolio_config_path}")
        
        # 3. 加载RSI阈值配置
        rsi_threshold_path = input_dir / 'sw2_rsi_threshold.csv'
        if rsi_threshold_path.exists():
            self._load_rsi_thresholds(rsi_threshold_path)
        else:
            logger.warning(f"RSI阈值配置文件不存在: {rsi_threshold_path}")
    
    def _load_backtest_settings(self, file_path: Path) -> None:
        """加载回测参数配置"""
        df = pd.read_csv(file_path, encoding='utf-8', comment='#')
        
        # 检测列名格式（支持中英文）
        if 'Parameter' in df.columns and 'Value' in df.columns:
            param_col, value_col = 'Parameter', 'Value'
        elif '参数名称' in df.columns and '参数值' in df.columns:
            param_col, value_col = '参数名称', '参数值'
        else:
            logger.error(f"无法识别配置文件格式: {df.columns.tolist()}")
            return
        
        # 转换为字典
        settings = {}
        for _, row in df.iterrows():
            param_name = str(row[param_col]).strip()
            param_value = row[value_col]
            
            # 跳过空行和注释
            if not param_name or param_name.startswith('#'):
                continue
            
            # 类型转换
            if param_name in ['start_date', 'end_date', '回测开始日期', '回测结束日期']:
                settings[param_name] = str(param_value)
            elif param_name in ['total_capital', '总资本', 'min_data_length', 'historical_data_weeks']:
                try:
                    settings[param_name] = int(param_value)
                except (ValueError, TypeError):
                    settings[param_name] = param_value
            elif 'ratio' in param_name.lower() or 'threshold' in param_name.lower() or \
                 param_name in ['价值比卖出阈值', '价值比买入阈值', '最小仓位比例', '最大仓位比例',
                              '手续费率', '印花税率', '滑点率']:
                try:
                    settings[param_name] = float(param_value)
                except (ValueError, TypeError):
                    settings[param_name] = param_value
            else:
                settings[param_name] = param_value
        
        self._config['backtest'] = settings
        logger.info(f"回测配置加载完成: {len(settings)} 个参数")
    
    def _load_portfolio_config(self, file_path: Path) -> None:
        """加载股票池配置"""
        df = pd.read_csv(file_path, encoding='utf-8')
        
        # 检测列名格式（支持中英文）
        code_col = 'Stock_number' if 'Stock_number' in df.columns else '股票代码'
        name_col = 'Stock_name' if 'Stock_name' in df.columns else '股票名称'
        weight_col = 'Initial_weight' if 'Initial_weight' in df.columns else '初始权重'
        dcf_col = 'DCF_value_per_share' if 'DCF_value_per_share' in df.columns else 'DCF估值'
        industry_col = 'Industry' if 'Industry' in df.columns else '行业分类'
        
        # 存储为DataFrame，方便后续使用
        self._config['portfolio'] = df
        
        # 提取DCF估值映射
        dcf_values = {}
        if dcf_col in df.columns:
            for _, row in df.iterrows():
                stock_code = str(row[code_col])
                dcf_value = float(row[dcf_col])
                dcf_values[stock_code] = dcf_value
        
        self._config['dcf_values'] = dcf_values
        
        # 提取行业映射（如果有申万二级行业代码列）
        industry_map = {}
        industry_code_col = None
        if '申万二级行业代码' in df.columns:
            industry_code_col = '申万二级行业代码'
        elif 'SW_Industry_Code' in df.columns:
            industry_code_col = 'SW_Industry_Code'
        
        if industry_code_col:
            for _, row in df.iterrows():
                stock_code = str(row[code_col])
                industry_code = str(row[industry_code_col])
                industry_map[stock_code] = industry_code
        
        self._config['industry_map'] = industry_map
        
        logger.info(f"股票池配置加载完成: {len(df)} 只股票")
    
    def _load_rsi_thresholds(self, file_path: Path) -> None:
        """加载RSI阈值配置"""
        df = pd.read_csv(file_path, encoding='utf-8')
        
        # 转换为字典，以行业代码为键
        thresholds = {}
        for _, row in df.iterrows():
            industry_code = str(row['申万二级行业代码'])
            thresholds[industry_code] = {
                'industry_name': row['申万二级行业名称'],
                'overbought': float(row['RSI超买阈值']),
                'oversold': float(row['RSI超卖阈值']),
                'extreme_overbought': float(row['RSI极端超买阈值']),
                'extreme_oversold': float(row['RSI极端超卖阈值'])
            }
        
        self._config['rsi_thresholds'] = thresholds
        logger.info(f"RSI阈值配置加载完成: {len(thresholds)} 个行业")
    
    def _load_default_config(self) -> None:
        """加载默认配置"""
        self._config = {
            'backtest': {
                '回测开始日期': '2021-01-08',
                '回测结束日期': '2025-01-03',
                '总资本': 10000000,
                '价值比卖出阈值': 0.8,
                '价值比买入阈值': 0.7,
                '动态仓位启用': True,
                '最小仓位比例': 0.05,
                '最大仓位比例': 0.15,
                '手续费率': 0.0003,
                '印花税率': 0.001,
                '滑点率': 0.001
            },
            'strategy': {
                'timeframe': 'weekly',
                'ema_period': 20,
                'rsi_period': 14,
                'macd_fast': 12,
                'macd_slow': 26,
                'macd_signal': 9,
                'bb_period': 20,
                'bb_std': 2.0,
                'lookback_period': 13
            },
            'data_source': {
                'primary': 'akshare',
                'backup': None,
                'cache_enabled': True,
                'cache_days': 7
            }
        }
        logger.info("默认配置加载完成")
    
    # ==================== 配置访问接口 ====================
    
    def get(self, key: str, default: Any = None) -> Any:
        """
        获取配置值
        
        Args:
            key: 配置键，支持点号分隔的路径，如 'backtest.回测开始日期'
            default: 默认值
        
        Returns:
            配置值
        """
        keys = key.split('.')
        value = self._config
        
        for k in keys:
            if isinstance(value, dict):
                value = value.get(k)
            else:
                return default
            
            if value is None:
                return default
        
        return value
    
    def get_backtest_config(self) -> Dict[str, Any]:
        """获取回测配置"""
        return self._config.get('backtest', {})
    
    def get_portfolio_config(self) -> pd.DataFrame:
        """获取股票池配置"""
        return self._config.get('portfolio', pd.DataFrame())
    
    def get_dcf_values(self) -> Dict[str, float]:
        """获取DCF估值映射"""
        return self._config.get('dcf_values', {})
    
    def get_industry_map(self) -> Dict[str, str]:
        """获取股票行业映射"""
        return self._config.get('industry_map', {})
    
    def get_rsi_thresholds(self) -> Dict[str, Dict[str, float]]:
        """获取RSI阈值配置"""
        return self._config.get('rsi_thresholds', {})
    
    def get_rsi_threshold_for_industry(self, industry_code: str) -> Dict[str, float]:
        """
        获取指定行业的RSI阈值
        
        Args:
            industry_code: 申万二级行业代码
        
        Returns:
            RSI阈值字典，如果行业不存在则返回默认值
        """
        thresholds = self.get_rsi_thresholds()
        
        if industry_code in thresholds:
            return thresholds[industry_code]
        else:
            # 返回默认阈值
            logger.warning(f"行业代码 {industry_code} 未找到RSI阈值，使用默认值")
            return {
                'industry_name': '未知行业',
                'overbought': 70.0,
                'oversold': 30.0,
                'extreme_overbought': 80.0,
                'extreme_oversold': 20.0
            }
    
    def get_strategy_config(self) -> Dict[str, Any]:
        """获取策略配置"""
        return self._config.get('strategy', {})
    
    def get_data_source_config(self) -> Dict[str, Any]:
        """获取数据源配置"""
        return self._config.get('data_source', {})
    
    # ==================== 配置验证 ====================
    
    def validate(self) -> bool:
        """
        验证配置完整性和有效性
        
        Returns:
            验证是否通过
        """
        try:
            # 验证回测配置
            backtest_config = self.get_backtest_config()
            
            # 支持中英文参数名
            has_start_date = 'start_date' in backtest_config or '回测开始日期' in backtest_config
            has_end_date = 'end_date' in backtest_config or '回测结束日期' in backtest_config
            has_capital = 'total_capital' in backtest_config or '总资本' in backtest_config
            
            assert has_start_date, "缺少回测开始日期"
            assert has_end_date, "缺少回测结束日期"
            assert has_capital, "缺少总资本"
            
            # 验证总资本
            capital = backtest_config.get('total_capital', backtest_config.get('总资本', 0))
            assert capital > 0, "总资本必须大于0"
            
            # 验证股票池配置
            portfolio = self.get_portfolio_config()
            if not portfolio.empty:
                # 支持中英文列名
                has_code = 'Stock_number' in portfolio.columns or '股票代码' in portfolio.columns
                has_weight = 'Initial_weight' in portfolio.columns or '初始权重' in portfolio.columns
                
                assert has_code, "股票池配置缺少股票代码列"
                assert has_weight, "股票池配置缺少初始权重列"
                
                # 验证权重总和
                weight_col = 'Initial_weight' if 'Initial_weight' in portfolio.columns else '初始权重'
                total_weight = portfolio[weight_col].sum()
                assert abs(total_weight - 1.0) < 0.01, f"权重总和应为1.0，当前为{total_weight}"
            
            logger.info("配置验证通过")
            return True
            
        except AssertionError as e:
            logger.error(f"配置验证失败: {e}")
            return False
        except Exception as e:
            logger.error(f"配置验证出错: {e}")
            return False
    
    # ==================== 工具方法 ====================
    
    def get_project_root(self) -> Path:
        """获取项目根目录"""
        return self._project_root
    
    def print_config(self) -> None:
        """打印当前配置（用于调试）"""
        import json

        # 转换DataFrame为字典以便打印
        config_copy = self._config.copy()
        if 'portfolio' in config_copy and isinstance(config_copy['portfolio'], pd.DataFrame):
            config_copy['portfolio'] = f"<DataFrame: {len(config_copy['portfolio'])} rows>"
        
        print("=" * 50)
        print("当前配置:")
        print(json.dumps(config_copy, indent=2, ensure_ascii=False, default=str))
        print("=" * 50)


# 全局配置管理器实例
_config_manager = None


def get_config_manager() -> ConfigManager:
    """
    获取全局配置管理器实例
    
    Returns:
        ConfigManager实例
    """
    global _config_manager
    if _config_manager is None:
        _config_manager = ConfigManager()
    return _config_manager
