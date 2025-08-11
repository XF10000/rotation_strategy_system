# 申万二级行业RSI阈值计算系统使用说明

## 概述

本系统实现了基于申万二级行业波动率分层的动态RSI阈值计算功能，为量化交易策略提供个性化的超买超卖判断标准。

## 核心功能

### 1. 数据获取
- 自动获取申万二级行业指数的周线数据
- 支持多种akshare API，具备容错机制
- 计算14周RSI指标

### 2. 波动率分层
根据各行业RSI的标准差进行分层：
- **高波动行业**：σ ≥ 75%分位数，使用5%/95%极端阈值
- **中波动行业**：25%分位数 ≤ σ < 75%分位数，使用8%/92%极端阈值  
- **低波动行业**：σ < 25%分位数，使用10%/90%极端阈值

### 3. 阈值计算
为每个行业计算四类阈值：
- **普通超卖**：15%分位数（所有行业统一）
- **普通超买**：85%分位数（所有行业统一）
- **极端超卖**：根据波动率分层确定
- **极端超买**：根据波动率分层确定

## 文件结构

```
indicators/
├── sw_industry_rsi_thresholds.py  # 主功能模块
config/
├── sw_rsi_config.py              # 配置文件
docs/
├── 申万二级行业 RSI 阈值确定方法.md    # 技术文档
├── 申万二级行业RSI阈值使用说明.md     # 本文档
demo_sw_rsi_thresholds.py         # 演示脚本
test_sw_rsi_thresholds.py         # 测试脚本
```

## 使用方法

### 1. 基本使用

```python
from indicators.sw_industry_rsi_thresholds import SWIndustryRSIThresholds

# 创建计算器实例
calculator = SWIndustryRSIThresholds()

# 运行计算并保存结果
result_df = calculator.run()

# 查看结果
print(result_df.head())
```

### 2. 自定义参数

```python
# 自定义输出目录
calculator = SWIndustryRSIThresholds(output_dir="custom_output")

# 修改计算参数
calculator.rsi_period = 14        # RSI周期
calculator.lookback_weeks = 104   # 回看周数
calculator.retry_times = 3        # 重试次数
```

### 3. 读取CSV结果

```python
import pandas as pd

# 读取最新的阈值文件
df = pd.read_csv('output/sw2_rsi_thresholds_20250808_195327.csv', 
                 index_col=0, encoding='utf-8-sig')

# 获取特定行业的阈值
code = '801010'  # 农业
thresholds = df.loc[code]

print(f"行业: {thresholds['行业名称']}")
print(f"普通超卖阈值: {thresholds['普通超卖']:.1f}")
print(f"普通超买阈值: {thresholds['普通超买']:.1f}")
print(f"极端超卖阈值: {thresholds['极端超卖']:.1f}")
print(f"极端超买阈值: {thresholds['极端超买']:.1f}")
```

## 输出文件格式

CSV文件包含以下列：

| 列名 | 说明 | 示例 |
|------|------|------|
| 行业代码 | 申万二级行业代码 | 801010 |
| 行业名称 | 行业中文名称 | 农业 |
| layer | 波动率分层 | 低波动/中波动/高波动 |
| volatility | RSI标准差 | 10.18 |
| current_rsi | 当前RSI值 | 33.4 |
| 普通超卖 | 15%分位阈值 | 33.2 |
| 普通超买 | 85%分位阈值 | 53.5 |
| 极端超卖 | 分层极端阈值 | 32.3 |
| 极端超买 | 分层极端阈值 | 57.0 |
| data_points | 数据点数量 | 104 |
| 更新时间 | 计算时间戳 | 2025-08-08 19:53:27 |

> 数值精度：由 `sw_rsi_thresholds/config.py` 的 `OUTPUT_CONFIG["float_precision"]` 控制，默认两位小数。

### 新增：RSI 极端信号说明

- 定义：当 RSI ≥ 行业“极端超买”阈值，或 RSI ≤ 行业“极端超卖”阈值时，记为 True。
- 应用：在详细CSV与回测报告中用于标记强制信号，不依赖背离条件。

## 在回测系统中的应用

### 1. 策略集成示例

```python
import pandas as pd

class RSIStrategy:
    def __init__(self, threshold_file):
        self.thresholds = pd.read_csv(threshold_file, index_col=0, encoding='utf-8-sig')
    
    def get_signal(self, industry_code, current_rsi):
        """
        根据动态阈值生成交易信号
        """
        if industry_code not in self.thresholds.index:
            return 0  # 无信号
        
        row = self.thresholds.loc[industry_code]
        
        # 使用普通阈值
        if current_rsi <= row['普通超卖']:
            return 1  # 买入信号
        elif current_rsi >= row['普通超买']:
            return -1  # 卖出信号
        
        # 使用极端阈值（更强信号）
        if current_rsi <= row['极端超卖']:
            return 2  # 强买入信号
        elif current_rsi >= row['极端超买']:
            return -2  # 强卖出信号
        
        return 0  # 无信号
```

### 2. 定期更新机制

```python
import schedule
import time

def update_thresholds():
    """定期更新阈值"""
    calculator = SWIndustryRSIThresholds()
    calculator.run()
    print("阈值更新完成")

# 每月第一个周一更新
schedule.every().monday.at("09:00").do(update_thresholds)

while True:
    schedule.run_pending()
    time.sleep(3600)  # 每小时检查一次
```

## 演示和测试

### 1. 运行演示
```bash
python3 demo_sw_rsi_thresholds.py
```
使用模拟数据展示完整功能流程。

### 2. 运行测试
```bash
python3 test_sw_rsi_thresholds.py
```
测试各个功能模块的正确性。

## 注意事项

1. **数据依赖**：依赖akshare库获取数据，需要稳定的网络连接
2. **更新频率**：建议每月更新一次阈值数据
3. **数据质量**：系统会自动过滤数据不足的行业
4. **容错机制**：内置重试机制和备用数据源
5. **编码格式**：CSV文件使用UTF-8-BOM编码，确保中文正常显示

## 技术参数

- **RSI周期**：14周
- **历史窗口**：104周（约2年）
- **最小数据要求**：50周价格数据，20个RSI数据点
- **波动率分层**：25%/75%分位数
- **普通阈值**：15%/85%分位数
- **极端阈值**：根据分层动态调整

### 极端阈值系数（新增）

- 目的：对“极端超卖/极端超买”分位阈值进行按波动层（高/中/低）的系数微调。
- 作用范围：仅影响极端阈值，普通15%/85%阈值不受影响。
- 配置位置：`sw_rsi_thresholds/config.py` 的 `EXTREME_THRESHOLD_COEFFICIENTS`，键名为“超卖系数”和“超买系数”。
- 公式：`调整后极端阈值 = 原分位数RSI × 系数`。

示例：
```python
EXTREME_THRESHOLD_COEFFICIENTS = {
  "高波动": {"超卖系数": 0.95, "超买系数": 1.05},
  "中波动": {"超卖系数": 0.95, "超买系数": 1.05},
  "低波动": {"超卖系数": 0.95, "超买系数": 1.05},
}
```

### CSV小数位精度（新增）

- 配置：`OUTPUT_CONFIG["float_precision"] = 2`
- 影响：导出CSV中阈值、RSI与波动率等数值的显示精度。

## 扩展功能

系统设计具有良好的扩展性，可以：

1. **调整参数**：修改RSI周期、历史窗口长度等
2. **增加指标**：集成其他技术指标的动态阈值
3. **自定义分层**：修改波动率分层逻辑
4. **多时间框架**：支持日线、月线等其他周期
5. **实时更新**：集成实时数据源

## 联系支持

如有问题或建议，请查看：
- 技术文档：`docs/申万二级行业 RSI 阈值确定方法.md`
- 代码注释：`indicators/sw_industry_rsi_thresholds.py`
- 演示代码：`demo_sw_rsi_thresholds.py`