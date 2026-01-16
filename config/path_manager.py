"""
路径管理器

职责：
1. 管理系统所有目录和文件路径
2. 自动创建必要的目录
3. 提供路径访问的统一接口
4. 处理路径的跨平台兼容性

不负责：
- 文件内容的读写
- 业务逻辑
"""

import logging
from pathlib import Path
from typing import Optional

logger = logging.getLogger(__name__)


class PathManager:
    """路径管理器"""
    
    _instance = None
    
    def __new__(cls):
        """单例模式"""
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._initialized = False
        return cls._instance
    
    def __init__(self):
        """初始化路径管理器"""
        if self._initialized:
            return
        
        self._project_root = self._find_project_root()
        self._paths = {}
        self._setup_paths()
        self._initialized = True
        
        logger.info("PathManager 初始化完成")
    
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
    
    def _setup_paths(self) -> None:
        """设置所有路径"""
        root = self._project_root
        
        # 配置目录
        self._paths['config_dir'] = root / 'config'
        self._paths['input_dir'] = root / 'Input'
        
        # 数据目录
        self._paths['data_cache_dir'] = root / 'data_cache'
        self._paths['data_dir'] = root / 'data'
        
        # 输出目录
        self._paths['output_dir'] = root / 'output'
        self._paths['reports_dir'] = root / 'reports'
        self._paths['logs_dir'] = root / 'logs'
        
        # 配置文件
        self._paths['backtest_settings'] = self._paths['input_dir'] / 'Backtest_settings.csv'
        self._paths['portfolio_config'] = self._paths['input_dir'] / 'portfolio_config.csv'
        self._paths['rsi_threshold'] = self._paths['input_dir'] / 'sw2_rsi_threshold.csv'
        self._paths['report_template'] = self._paths['config_dir'] / 'backtest_report_template.html'
        
        # 其他配置文件（兼容旧路径）
        self._paths['sw_rsi_threshold_dir'] = root / 'sw_rsi_thresholds'
        self._paths['sw_rsi_threshold_file'] = self._paths['sw_rsi_threshold_dir'] / 'sw2_rsi_threshold.csv'
    
    def ensure_directories(self) -> None:
        """确保所有必要的目录存在"""
        directories = [
            'data_cache_dir',
            'output_dir',
            'reports_dir',
            'logs_dir'
        ]
        
        for dir_key in directories:
            dir_path = self._paths.get(dir_key)
            if dir_path:
                dir_path.mkdir(parents=True, exist_ok=True)
                logger.debug(f"确保目录存在: {dir_path}")
    
    # ==================== 目录路径访问 ====================
    
    def get_project_root(self) -> Path:
        """获取项目根目录"""
        return self._project_root
    
    def get_config_dir(self) -> Path:
        """获取配置目录"""
        return self._paths['config_dir']
    
    def get_input_dir(self) -> Path:
        """获取输入目录"""
        return self._paths['input_dir']
    
    def get_data_cache_dir(self) -> Path:
        """获取数据缓存目录"""
        return self._paths['data_cache_dir']
    
    def get_output_dir(self) -> Path:
        """获取输出目录"""
        return self._paths['output_dir']
    
    def get_reports_dir(self) -> Path:
        """获取报告目录"""
        return self._paths['reports_dir']
    
    def get_logs_dir(self) -> Path:
        """获取日志目录"""
        return self._paths['logs_dir']
    
    # ==================== 配置文件路径访问 ====================
    
    def get_backtest_settings_path(self) -> Path:
        """获取回测配置文件路径"""
        return self._paths['backtest_settings']
    
    def get_portfolio_config_path(self) -> Path:
        """获取股票池配置文件路径"""
        return self._paths['portfolio_config']
    
    def get_rsi_threshold_path(self) -> Path:
        """获取RSI阈值配置文件路径"""
        # 优先使用 Input/ 目录下的文件
        if self._paths['rsi_threshold'].exists():
            return self._paths['rsi_threshold']
        # 兼容旧路径
        elif self._paths['sw_rsi_threshold_file'].exists():
            return self._paths['sw_rsi_threshold_file']
        else:
            return self._paths['rsi_threshold']
    
    def get_report_template_path(self) -> Path:
        """获取报告模板文件路径"""
        return self._paths['report_template']
    
    # ==================== 数据缓存路径 ====================
    
    def get_stock_cache_path(self, stock_code: str, freq: str = 'weekly') -> Path:
        """
        获取股票数据缓存文件路径
        
        Args:
            stock_code: 股票代码
            freq: 数据频率
        
        Returns:
            缓存文件路径
        """
        cache_dir = self.get_data_cache_dir()
        return cache_dir / f"{stock_code}_{freq}.pkl"
    
    def get_dividend_cache_path(self, stock_code: str) -> Path:
        """
        获取分红数据缓存文件路径
        
        Args:
            stock_code: 股票代码
        
        Returns:
            缓存文件路径
        """
        cache_dir = self.get_data_cache_dir()
        return cache_dir / f"{stock_code}_dividend.pkl"
    
    # ==================== 报告文件路径 ====================
    
    def get_report_path(self, report_type: str, timestamp: Optional[str] = None) -> Path:
        """
        获取报告文件路径
        
        Args:
            report_type: 报告类型，'html' 或 'csv'
            timestamp: 时间戳，如果为None则使用当前时间
        
        Returns:
            报告文件路径
        """
        from datetime import datetime
        
        if timestamp is None:
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        
        reports_dir = self.get_reports_dir()
        
        if report_type == 'html':
            return reports_dir / f"integrated_backtest_report_{timestamp}.html"
        elif report_type == 'csv':
            return reports_dir / f"detailed_transactions_{timestamp}.csv"
        else:
            return reports_dir / f"report_{timestamp}.{report_type}"
    
    # ==================== 日志文件路径 ====================
    
    def get_log_path(self, log_name: str = 'rotation_strategy') -> Path:
        """
        获取日志文件路径
        
        Args:
            log_name: 日志文件名（不含扩展名）
        
        Returns:
            日志文件路径
        """
        logs_dir = self.get_logs_dir()
        return logs_dir / f"{log_name}.log"
    
    # ==================== 工具方法 ====================
    
    def path_exists(self, key: str) -> bool:
        """
        检查路径是否存在
        
        Args:
            key: 路径键名
        
        Returns:
            路径是否存在
        """
        path = self._paths.get(key)
        if path:
            return path.exists()
        return False
    
    def get_path(self, key: str) -> Optional[Path]:
        """
        获取指定键的路径
        
        Args:
            key: 路径键名
        
        Returns:
            路径对象，如果不存在则返回None
        """
        return self._paths.get(key)
    
    def print_paths(self) -> None:
        """打印所有路径（用于调试）"""
        print("=" * 50)
        print("系统路径:")
        print(f"项目根目录: {self._project_root}")
        print("\n目录:")
        for key, path in self._paths.items():
            if key.endswith('_dir'):
                exists = "✓" if path.exists() else "✗"
                print(f"  {exists} {key}: {path}")
        print("\n文件:")
        for key, path in self._paths.items():
            if not key.endswith('_dir'):
                exists = "✓" if path.exists() else "✗"
                print(f"  {exists} {key}: {path}")
        print("=" * 50)


# 全局路径管理器实例
_path_manager = None


def get_path_manager() -> PathManager:
    """
    获取全局路径管理器实例
    
    Returns:
        PathManager实例
    """
    global _path_manager
    if _path_manager is None:
        _path_manager = PathManager()
    return _path_manager
