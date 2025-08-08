"""
申万二级行业RSI阈值计算模块

该模块提供申万二级行业RSI阈值的计算功能，支持：
- 基于AkShare API获取申万行业数据
- 计算14周期RSI指标
- 根据波动率分层设置动态阈值
- 输出CSV格式的阈值文件供回测使用

主要文件：
- sw_industry_rsi_thresholds.py: 核心计算模块
- run_sw_2021_rsi_calculation.py: 命令行工具
- demo_sw_2021_rsi_thresholds.py: 演示脚本
"""

from .sw_industry_rsi_thresholds import SWIndustryRSIThresholds

__version__ = "1.0.0"
__author__ = "CodeBuddy"
__all__ = ["SWIndustryRSIThresholds"]