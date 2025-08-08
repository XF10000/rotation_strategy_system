# 申万二级行业RSI阈值计算模块

## 概述

本模块用于计算申万二级行业的RSI（相对强弱指数）动态阈值，支持量化交易策略中的超买超卖信号判断。

## 核心功能

- **数据获取**：使用AkShare API获取申万二级行业指数历史数据
- **RSI计算**：基于104周历史数据计算14周期RSI
- **波动率分层**：根据RSI标准差进行高/中/低波动率分层
- **动态阈值**：为不同波动率分层设置不同的极端分位数阈值
- **结果输出**：生成CSV格式的阈值文件

## 文件结构

```
sw_rsi_thresholds/
├── __init__.py                           # 模块初始化
├── README.md                            # 说明文档
├── sw_industry_rsi_thresholds.py        # 核心计算模块
├── run_sw_2021_rsi_calculation.py       # 命令行工具
├── demo_sw_2021_rsi_thresholds.py       # 演示脚本
├── demo_sw_rsi_thresholds.py            # 旧版演示脚本
├── run_sw_rsi_calculation.py            # 旧版命令行工具
└── 申万二级行业RSI阈值使用说明.md        # 详细使用说明
```

## 快速开始

### 1. 运行完整计算

```bash
python run_sw_2021_rsi_calculation.py
```

### 2. 演示模式（使用模拟数据）

```bash
python demo_sw_2021_rsi_thresholds.py
```

### 3. 编程调用

```python
from sw_rsi_thresholds import SWIndustryRSIThresholds

# 创建计算器
calculator = SWIndustryRSIThresholds(output_dir="output")

# 运行计算
result_df = calculator.run()

# 查看结果
print(result_df.head())
```

## 输出格式

生成的CSV文件包含以下列：

- `行业代码`: 申万行业代码
- `行业名称`: 行业名称
- `layer`: 波动率分层（高波动/中波动/低波动）
- `volatility`: RSI波动率（标准差）
- `current_rsi`: 当前RSI值
- `普通超卖/超买`: 15%/85%分位数阈值
- `极端超卖/超买`: 根据波动率分层的极端阈值
- `data_points`: 数据点数量
- `更新时间`: 计算时间

## 波动率分层规则

- **高波动**（≥75%分位数）：极端阈值 5%/95%
- **中波动**（25%-75%分位数）：极端阈值 8%/92%
- **低波动**（<25%分位数）：极端阈值 10%/90%

## 技术参数

- **历史数据窗口**：104周（约2年）
- **RSI周期**：14周
- **数据频率**：周线
- **数据源**：AkShare API

## 依赖要求

- pandas
- numpy
- akshare
- talib (可选，用于RSI计算优化)

## 注意事项

1. 需要稳定的网络连接以获取AkShare数据
2. 首次运行可能需要2-3分钟完成所有行业计算
3. 建议定期更新阈值以适应市场变化
4. 输出文件自动保存到output目录

## 版本历史

- v1.0.0: 初始版本，支持AkShare API集成和动态阈值计算