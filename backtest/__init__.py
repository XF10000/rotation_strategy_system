"""
回测系统模块
实现完整的策略回测功能，包括投资组合管理、交易执行、绩效分析等
"""

from .backtest_engine import BacktestEngine
from .performance_analyzer import PerformanceAnalyzer
from .portfolio_manager import PortfolioManager
from .transaction_cost import TransactionCostCalculator

# from .report_generator import ReportGenerator  # 已移至obsolete文件夹

__all__ = [
    'BacktestEngine',
    'PortfolioManager', 
    'TransactionCostCalculator',
    'PerformanceAnalyzer',
    'ReportGenerator'
]