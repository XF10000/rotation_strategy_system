
申万二级行业 RSI 阈值确定方法  
面向开发人员的完整说明文档  
版本：V1.0 | 日期：2024-08-08

────────────────  
1 目的  
为每个申万二级行业动态确定以下四类阈值，用于后续策略中的买卖信号判断。  

2 所需数据  
• 申万二级行业指数周线（akshare 代码 801***）  
• 字段：收盘价 close  
• 周期：最近 104 周（≈2 年）  
• 复权方式：不复权  

3 计算步骤（逐行可落地）  
3.1 获取数据并计算 RSI  
```python
import akshare as ak
import pandas_ta as ta
import numpy as np

code = '801161'                    # 示例：电力
df = ak.index_zh_a_hist(symbol=code, period='weekly', start_date='20220101', adjust='')
df['date'] = pd.to_datetime(df['日期'])
df.set_index('date', inplace=True)
df['rsi14'] = ta.rsi(df['收盘'], length=14)
```

3.2 截取最近 104 周  
```python
R = df['rsi14'].dropna().tail(104)
```

3.3 计算行业波动率 σ  
```python
sigma = R.std()
```

3.4 行业波动率分层  
将 **所有** 申万二级行业的 σ 收集到列表 `sigma_list`，然后计算：  
```python
q1 = np.percentile(sigma_list, 25)   # 25% 分位
q3 = np.percentile(sigma_list, 75)   # 75% 分位
```
按 σ 大小给行业贴标签：  
| 标签 | 判断条件 | 中文描述 |
|---|---|---|
| 高波动 | σ ≥ q3 | 高波动行业 |
| 中波动 | q1 ≤ σ < q3 | 中等波动行业 |
| 低波动 | σ < q1 | 低波动行业 |

3.5 根据分层取 RSI 分位阈值  
在 `R` 上调用 `np.percentile`，得到四类阈值：  

| 档位 | 普通超卖 | 普通超买 | 极端超卖 | 极端超买 |
|---|---|---|---|---|
| **高波动** | 15% 分位 | 85% 分位 | 5% 分位 | 95% 分位 |
| **中波动** | 15% 分位 | 85% 分位 | 8% 分位 | 92% 分位 |
| **低波动** | 15% 分位 | 85% 分位 | 10% 分位 | 90% 分位 |

3.6 代码示例（一次性生成阈值表）  
```python
def make_threshold_table(all_weekly_dict, sigma_list):
    q1 = np.percentile(sigma_list, 25)
    q3 = np.percentile(sigma_list, 75)

    table = {}
    for code, df in all_weekly_dict.items():
        R = df['rsi14'].dropna().tail(104)
        sigma = R.std()

        if sigma >= q3:
            layer = '高波动'
            pct_low, pct_high = 5, 95
        elif sigma < q1:
            layer = '低波动'
            pct_low, pct_high = 10, 90
        else:
            layer = '中波动'
            pct_low, pct_high = 8, 92

        table[code] = {
            'layer'      : layer,
            '普通超卖'   : float(np.percentile(R, 15)),
            '普通超买'   : float(np.percentile(R, 85)),
            '极端超卖'   : float(np.percentile(R, pct_low)),
            '极端超买'   : float(np.percentile(R, pct_high))
        }
    return pd.DataFrame.from_dict(table, orient='index')

# 使用
threshold_df = make_threshold_table(all_weekly_dict, sigma_list)
threshold_df.to_csv('sw2_rsi_threshold.csv', encoding='utf-8-sig')
```

4 更新频率  
• 每月最后一个交易日重新执行 3.1–3.6，生成新的 `sw2_rsi_threshold.csv`。  
• 策略启动时读入该表即可，无需实时计算。

5 使用示例  
```python
import pandas as pd
th = pd.read_csv('sw2_rsi_threshold.csv', index_col=0, encoding='utf-8-sig')
code = '801161'           # 电力
low  = th.loc[code, '普通超卖']
high = th.loc[code, '普通超买']
ext_low  = th.loc[code, '极端超卖']
ext_high = th.loc[code, '极端超买']
```

6 小结一句话  
“先把行业波动率 σ 按 25%/75% 分位切成低/中/高三档，再按档位取对应 RSI 分位阈值；每月重算一次。”


7 扩展：极端阈值系数与CSV精度  

7.1 极端阈值系数（设计与实现）  
- 目的：在按分层计算得到的“极端超卖/极端超买”分位数阈值基础上，提供可配置的细微调节。  
- 作用范围：仅对“极端阈值”生效；普通阈值（15%/85%）不受影响。  
- 公式：调整后极端阈值 = 原分位数RSI × 系数。  
- 配置位置：`sw_rsi_thresholds/config.py` 的 `EXTREME_THRESHOLD_COEFFICIENTS`，键名为“超卖系数”与“超买系数”，按波动层（高/中/低）分别配置。  

示例：  
```python
EXTREME_THRESHOLD_COEFFICIENTS = {
  "高波动": {"超卖系数": 0.95, "超买系数": 1.05},
  "中波动": {"超卖系数": 0.95, "超买系数": 1.05},
  "低波动": {"超卖系数": 0.95, "超买系数": 1.05},
}
```

7.2 与计算流程的衔接  
- 在完成 3.5 的分位数阈值获取后，对“极端超卖/极端超买”分别乘以所属波动层对应的系数，再写入结果表与导出CSV。  
- 实施位置：`sw_rsi_thresholds/sw_industry_rsi_thresholds.py` 的行业阈值计算逻辑中。  

7.3 CSV小数位精度  
- 目的：统一CSV导出数值格式，便于报告比对与审阅。  
- 配置位置：`sw_rsi_thresholds/config.py` 的 `OUTPUT_CONFIG["float_precision"]`，默认 `2`。  
- 应用范围：阈值、波动率、RSI等数值导出时采用对应的小数位精度。  

7.4 报告/回测集成要点  
- 详细导出与报告已包含“RSI 极端信号”字段，用于标记是否越过极端阈值（≥极端超买 或 ≤极端超卖）。  
- 回测与报告读取 `sw2_rsi_threshold.csv` 中的行业个性化极端阈值（系数已应用）。  

