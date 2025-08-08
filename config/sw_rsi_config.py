"""
申万二级行业RSI阈值计算配置文件
"""

# RSI计算参数
RSI_PERIOD = 14  # RSI计算周期
LOOKBACK_WEEKS = 104  # 回看周数（2年）

# 波动率分层参数
VOLATILITY_Q1 = 25  # 低波动分位点
VOLATILITY_Q3 = 75  # 高波动分位点

# 分层对应的极端分位数设置
LAYER_PERCENTILES = {
    '高波动': {'extreme_low': 5, 'extreme_high': 95},
    '中波动': {'extreme_low': 8, 'extreme_high': 92},
    '低波动': {'extreme_low': 10, 'extreme_high': 90}
}

# 普通超买超卖分位数（所有分层通用）
NORMAL_OVERSOLD = 15
NORMAL_OVERBOUGHT = 85

# 数据质量控制
MIN_DATA_WEEKS = 50  # 最少需要的周数据
MIN_RSI_POINTS = 20  # 最少需要的RSI数据点

# 输出设置
OUTPUT_DIR = "output"
DEFAULT_FILENAME = "sw2_rsi_thresholds.csv"

# 日志设置
LOG_LEVEL = "INFO"
LOG_FORMAT = '%(asctime)s - %(levelname)s - %(message)s'

# AkShare相关设置
AKSHARE_TIMEOUT = 30  # 超时时间（秒）
RETRY_TIMES = 3  # 重试次数
RETRY_DELAY = 2  # 重试间隔（秒）