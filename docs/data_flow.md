# 中线轮动策略系统 - 数据流说明文档

## 📋 文档概述

**文档版本：** v1.0  
**创建日期：** 2026-01-16  
**目标读者：** 开发工程师、系统维护人员  
**阅读时间：** 约10-15分钟

本文档详细说明系统中数据的流向、转换过程和关键节点。

---

## 🌊 数据流总览

### 端到端数据流

```
外部数据源 (Akshare)
    ↓
数据获取 (DataFetcher)
    ↓
数据缓存 (DataStorage)
    ↓
数据处理 (DataProcessor)
    ↓
技术指标计算 (Indicators)
    ↓
信号生成 (SignalGenerator)
    ↓
交易执行 (BacktestEngine)
    ↓
持仓管理 (PortfolioManager)
    ↓
性能分析 (PerformanceAnalyzer)
    ↓
报告生成 (ReportGenerator)
    ↓
输出文件 (HTML/CSV)
```

---

## 📥 数据获取流程

### 1. 股票数据获取

**入口：** `BacktestEngine.prepare_data()`  
**执行者：** `AkshareDataFetcher`

```
用户请求
  ↓
BacktestEngine.prepare_data()
  ├── 读取股票池配置 (portfolio_config.csv)
  ├── 扩展历史数据窗口 (向前20周)
  └── 对每只股票：
      ↓
      _get_cached_or_fetch_data()
      ├── 检查缓存
      │   ├── 缓存存在且有效 → 返回缓存数据
      │   └── 缓存不存在/过期 → 继续
      ├── 调用 DataFetcher.get_stock_data()
      │   ├── 参数验证
      │   ├── 日期格式转换
      │   ├── 频率控制 (间隔3秒)
      │   ├── 调用 Akshare API
      │   │   └── ak.stock_zh_a_hist()
      │   ├── 重试机制 (最多5次)
      │   └── 数据标准化
      └── 保存到缓存
          ↓
      返回标准格式数据
```

**数据格式转换：**

```python
# Akshare原始格式（中文列名）
{
    '日期': '2024-01-05',
    '开盘': 10.5,
    '收盘': 11.2,
    '最高': 11.5,
    '最低': 10.3,
    '成交量': 1000000
}

# ↓ 标准化后（英文列名）

DataFrame:
    index: date (datetime)
    columns: open, high, low, close, volume
```

### 2. 分红配股数据获取

**执行者：** `AkshareDataFetcher.get_dividend_data()`

```
请求分红数据
  ↓
检查缓存
  ├── 缓存覆盖日期范围 → 返回缓存
  └── 需要获取新数据
      ↓
      调用 Akshare API
      ├── ak.stock_dividend_cninfo()
      └── 获取分红配股详情
      ↓
      日期对齐到周线
      ├── 找到分红日期对应的周五
      └── 映射到周线数据
      ↓
      保存到缓存
      ↓
      返回分红数据
```

---

## 🔄 数据处理流程

### 1. 技术指标计算

**入口：** `BacktestEngine.prepare_data()`  
**执行者：** `DataProcessor`

```
原始股票数据 (日线)
  ↓
DataProcessor.process()
  ├── 数据验证
  │   ├── 检查必要列存在
  │   ├── 检查数据类型
  │   └── 检查数据范围
  ├── 周期转换
  │   └── resample_to_weekly()
  │       ├── 按周五重采样
  │       ├── OHLC聚合
  │       └── 成交量求和
  ├── 技术指标计算
  │   ├── RSI (14周期)
  │   │   └── talib.RSI()
  │   ├── MACD (12,26,9)
  │   │   └── talib.MACD()
  │   ├── EMA (20周期)
  │   │   └── talib.EMA()
  │   ├── 布林带 (20,2)
  │   │   └── talib.BBANDS()
  │   └── 成交量均线 (4周期)
  │       └── rolling().mean()
  └── 数据清洗
      ├── 处理NaN值
      ├── 删除无效周
      └── 数据完整性检查
      ↓
处理后的周线数据 (含技术指标)
```

**数据结构演变：**

```python
# 输入：日线数据
DataFrame: [date, open, high, low, close, volume]
记录数：~250条/年

# ↓ 周期转换

# 输出：周线数据 + 技术指标
DataFrame: [
    date, open, high, low, close, volume,
    rsi,                    # RSI指标
    macd, macd_signal, macd_histogram,  # MACD指标
    ema_20,                 # EMA指标
    bb_upper, bb_middle, bb_lower,  # 布林带
    volume_ma_4             # 成交量均线
]
记录数：~52条/年
```

### 2. 数据缓存机制

**执行者：** `DataStorage`

```
数据请求
  ↓
检查缓存文件
  ├── 文件存在
  │   ├── 验证数据完整性
  │   │   ├── 检查必要列
  │   │   ├── 检查数据类型
  │   │   └── 检查时间范围
  │   ├── 完整性通过 → 返回缓存
  │   └── 完整性失败 → 删除缓存，重新获取
  └── 文件不存在
      ↓
      从数据源获取
      ↓
      保存到缓存
      ├── 文件格式：pickle
      ├── 命名规则：{stock_code}_{freq}.pkl
      └── 位置：data_cache/
      ↓
      返回数据
```

**缓存策略：**
- **缓存键：** 股票代码 + 数据频率
- **缓存格式：** pickle (pandas DataFrame)
- **缓存位置：** `data_cache/` 目录
- **缓存验证：** 每次使用前验证完整性
- **缓存更新：** 增量更新，只获取缺失时间段

---

## 🎯 信号生成流程

### 完整信号生成链路

```
处理后的股票数据
  ↓
SignalGenerator.generate_signal()
  ↓
1. 获取当前日期的数据
  ├── 当前价格
  ├── 技术指标值
  └── 历史数据窗口
  ↓
2. 价值比过滤器判断 (硬性前提)
  ├── 获取DCF估值
  ├── 计算价值比 = 当前价格 / DCF估值
  ├── 卖出判断：价值比 > 80%
  └── 买入判断：价值比 < 70%
  ↓
3. 计算4维度评分
  ├── 维度1：超买超卖
  │   ├── 获取行业RSI阈值
  │   ├── 检查极端阈值
  │   │   ├── RSI ≥ 极端超买 → 强制卖出
  │   │   └── RSI ≤ 极端超卖 → 强制买入
  │   ├── 检查普通阈值
  │   │   ├── RSI > 超买阈值
  │   │   └── RSI < 超卖阈值
  │   └── 检查背离信号
  │       ├── detect_rsi_divergence()
  │       └── 顶背离/底背离
  ├── 维度2：动能确认
  │   ├── MACD柱体缩短判断
  │   │   ├── 连续2根缩短
  │   │   └── 红柱缩短/绿柱缩短
  │   ├── MACD金叉死叉
  │   │   ├── DIF上穿DEA → 金叉
  │   │   └── DIF下穿DEA → 死叉
  │   └── MACD柱体颜色
  │       ├── 已为红色
  │       └── 已为绿色
  └── 维度3：极端价格量能
      ├── 布林带位置
      │   ├── 收盘价 ≥ 布林上轨
      │   └── 收盘价 ≤ 布林下轨
      └── 成交量放大
          ├── 卖出：成交量 ≥ 4周均量 × 1.3
          └── 买入：成交量 ≥ 4周均量 × 0.8
  ↓
4. 综合判断
  ├── 价值比过滤器必须满足
  └── 其余3维至少2维满足
  ↓
5. 生成信号
  ├── 信号类型：buy / sell / hold
  ├── 信号评分：各维度得分
  └── 触发原因：详细说明
  ↓
输出：SignalResult对象
```

### 信号数据结构

```python
SignalResult = {
    'stock_code': '601225',
    'date': '2024-01-05',
    'signal_type': 'buy',  # buy / sell / hold
    
    # 4维度评分
    'trend_score': 1.0,      # 价值比过滤器
    'rsi_score': 1.0,        # 超买超卖
    'macd_score': 1.0,       # 动能确认
    'volume_score': 0.0,     # 极端价格量能
    'total_score': 3.0,      # 总分
    
    # 技术指标详情
    'close_price': 10.5,
    'rsi_value': 28.5,
    'rsi_threshold_oversold': 30.0,
    'macd_histogram': -0.15,
    'bb_lower': 10.2,
    'volume_ratio': 0.85,
    
    # 触发原因
    'trigger_reasons': [
        '价值比过滤器：价格低于DCF估值70%',
        'RSI超卖：RSI=28.5 < 30.0',
        'MACD绿柱缩短：连续2根缩短'
    ]
}
```

---

## 💼 交易执行流程

### 交易决策链路

```
信号生成完成
  ↓
BacktestEngine._execute_trades()
  ↓
1. 遍历所有信号
  ├── 买入信号
  │   ├── 检查现金是否充足
  │   ├── 计算买入数量
  │   │   └── DynamicPositionManager.calculate_position_size()
  │   ├── 计算交易成本
  │   │   ├── 手续费：成交额 × 0.0003
  │   │   ├── 滑点：成交额 × 0.001
  │   │   └── 总成本 = 成交额 + 手续费 + 滑点
  │   ├── 执行买入
  │   │   └── PortfolioManager.buy()
  │   └── 记录交易
  │       └── transaction_history.append()
  └── 卖出信号
      ├── 检查持仓是否存在
      ├── 计算卖出数量（全部卖出）
      ├── 计算交易成本
      │   ├── 手续费：成交额 × 0.0003
      │   ├── 印花税：成交额 × 0.001
      │   ├── 滑点：成交额 × 0.001
      │   └── 总成本 = 手续费 + 印花税 + 滑点
      ├── 执行卖出
      │   └── PortfolioManager.sell()
      └── 记录交易
          └── transaction_history.append()
  ↓
2. 更新持仓状态
  ├── 更新持仓股数
  ├── 更新现金余额
  └── 记录持仓历史
  ↓
3. 计算投资组合价值
  ├── 持仓市值 = Σ(股数 × 当前价格)
  ├── 总资产 = 持仓市值 + 现金
  └── 记录到 portfolio_history
```

### 交易记录数据结构

```python
Transaction = {
    'date': '2024-01-05',
    'stock_code': '601225',
    'stock_name': '淮北矿业',
    'action': 'buy',  # buy / sell
    'price': 10.5,
    'shares': 1000,
    'amount': 10500,
    'commission': 3.15,
    'tax': 0,  # 仅卖出时有
    'slippage': 10.5,
    'total_cost': 10513.65,
    
    # 信号详情
    'signal_type': 'buy',
    'rsi_value': 28.5,
    'macd_histogram': -0.15,
    'trigger_reasons': [...]
}
```

---

## 📊 性能分析流程

### 性能指标计算链路

```
回测完成
  ↓
PerformanceAnalyzer.generate_performance_report()
  ↓
1. 基础指标计算
  ├── 总收益率
  │   └── (期末总资产 - 期初总资产) / 期初总资产
  ├── 年化收益率
  │   └── (1 + 总收益率) ^ (365 / 回测天数) - 1
  ├── 最大回撤
  │   ├── 计算每日回撤
  │   │   └── (当前净值 - 历史最高净值) / 历史最高净值
  │   └── 取最大值
  └── 夏普比率
      └── (年化收益率 - 无风险利率) / 收益率标准差
  ↓
2. 交易统计
  ├── 总交易次数
  ├── 买入次数 / 卖出次数
  ├── 盈利交易 / 亏损交易
  ├── 胜率
  │   └── 盈利交易数 / 总交易数
  └── 平均持仓天数
  ↓
3. 基准对比
  ├── 计算基准收益率
  │   └── 买入持有策略收益
  ├── 超额收益
  │   └── 策略收益 - 基准收益
  └── 年化超额收益
  ↓
4. 信号分析
  ├── 各维度触发频率
  ├── 信号准确率
  └── 未执行信号统计
  ↓
输出：PerformanceReport对象
```

---

## 📄 报告生成流程

### HTML报告生成链路

```
性能分析完成
  ↓
IntegratedReportGenerator.generate_report()
  ↓
1. 准备报告数据
  ├── 基础指标
  ├── 交易记录
  ├── 持仓历史
  ├── 信号详情
  └── K线数据
  ↓
2. 准备K线图数据
  └── _prepare_kline_data()
      ├── 对每只股票：
      │   ├── 提取OHLC数据
      │   ├── 提取技术指标
      │   │   ├── RSI数据
      │   │   ├── MACD数据
      │   │   └── 布林带数据
      │   ├── 标注交易点
      │   │   ├── 买入点（红色三角）
      │   │   └── 卖出点（绿色三角）
      │   └── 标注未执行信号
      │       ├── 未执行买入（红色空心圆）
      │       └── 未执行卖出（绿色空心圆）
      └── 转换为ECharts格式
  ↓
3. 加载HTML模板
  └── config/backtest_report_template.html
  ↓
4. 数据替换
  ├── 替换基础指标
  │   └── {{total_return}}, {{max_drawdown}}, etc.
  ├── 替换交易记录表格
  │   └── _replace_transaction_details_safe()
  ├── 替换K线数据
  │   └── _replace_kline_data_safe()
  └── 替换信号统计
      └── _replace_signal_statistics_safe()
  ↓
5. 生成HTML文件
  └── reports/integrated_backtest_report_{timestamp}.html
  ↓
输出：HTML报告文件路径
```

### CSV报告生成链路

```
交易记录数据
  ↓
DetailedCSVExporter.export()
  ↓
1. 构建详细记录
  ├── 对每笔交易：
  │   ├── 基本信息
  │   │   ├── 日期、股票、动作
  │   │   └── 价格、数量、金额
  │   ├── 技术指标
  │   │   ├── RSI值、阈值
  │   │   ├── MACD值
  │   │   ├── 布林带值
  │   │   └── 成交量比率
  │   ├── 4维度评分
  │   │   ├── 价值比评分
  │   │   ├── RSI评分
  │   │   ├── MACD评分
  │   │   └── 量能评分
  │   └── 触发原因
  │       └── 详细说明文本
  └── 格式化为DataFrame
  ↓
2. 导出CSV
  └── reports/detailed_transactions_{timestamp}.csv
  ↓
输出：CSV文件路径
```

---

## 🔄 数据转换关键节点

### 节点1：日线 → 周线

**位置：** `DataProcessor.resample_to_weekly()`

```python
# 输入：日线数据
daily_data = DataFrame[
    date: 2024-01-01, 2024-01-02, ..., 2024-01-05
    open: 10.0, 10.2, ..., 10.5
    close: 10.1, 10.3, ..., 10.8
]

# 转换规则
weekly_data = daily_data.resample('W-FRI').agg({
    'open': 'first',    # 周一开盘价
    'high': 'max',      # 周内最高价
    'low': 'min',       # 周内最低价
    'close': 'last',    # 周五收盘价
    'volume': 'sum'     # 周内成交量总和
})

# 输出：周线数据
weekly_data = DataFrame[
    date: 2024-01-05 (周五)
    open: 10.0
    high: 10.9
    low: 9.8
    close: 10.8
    volume: 5000000
]
```

### 节点2：原始数据 → 技术指标

**位置：** `DataProcessor.calculate_indicators()`

```python
# 输入：周线OHLC数据
data = DataFrame[date, open, high, low, close, volume]

# 计算技术指标
data['rsi'] = talib.RSI(data['close'], timeperiod=14)
data['macd'], data['macd_signal'], data['macd_histogram'] = \
    talib.MACD(data['close'], fastperiod=12, slowperiod=26, signalperiod=9)
data['ema_20'] = talib.EMA(data['close'], timeperiod=20)
data['bb_upper'], data['bb_middle'], data['bb_lower'] = \
    talib.BBANDS(data['close'], timeperiod=20, nbdevup=2, nbdevdn=2)
data['volume_ma_4'] = data['volume'].rolling(window=4).mean()

# 输出：含技术指标的数据
data = DataFrame[
    date, open, high, low, close, volume,
    rsi, macd, macd_signal, macd_histogram,
    ema_20, bb_upper, bb_middle, bb_lower, volume_ma_4
]
```

### 节点3：技术指标 → 信号评分

**位置：** `SignalGenerator._calculate_4d_scores()`

```python
# 输入：技术指标数据
indicators = {
    'rsi': 28.5,
    'macd_histogram': -0.15,
    'close': 10.5,
    'bb_lower': 10.2,
    'volume': 1200000,
    'volume_ma_4': 1000000
}

# 评分逻辑
scores = {
    'trend_score': 1.0 if price < dcf * 0.7 else 0.0,
    'rsi_score': 1.0 if rsi < 30 and has_divergence else 0.0,
    'macd_score': 1.0 if macd_shrinking or golden_cross else 0.0,
    'volume_score': 1.0 if close <= bb_lower and volume_high else 0.0
}

# 输出：4维度评分
scores = {
    'trend_score': 1.0,
    'rsi_score': 1.0,
    'macd_score': 1.0,
    'volume_score': 0.0,
    'total_score': 3.0
}
```

---

## 📈 数据量级估算

### 典型回测场景

**配置：**
- 股票数量：3只
- 回测周期：4年（2021-2025）
- 数据频率：周线

**数据量：**

| 阶段 | 数据类型 | 单股记录数 | 总记录数 | 内存占用 |
|------|---------|-----------|---------|---------|
| 日线数据 | OHLCV | ~1000条 | ~3000条 | ~500KB |
| 周线数据 | OHLCV | ~200条 | ~600条 | ~100KB |
| 技术指标 | 9个指标 | ~200条 | ~600条 | ~150KB |
| 交易记录 | Transaction | ~30笔 | ~30笔 | ~10KB |
| 持仓历史 | Portfolio | ~200条 | ~200条 | ~50KB |
| **总计** | - | - | ~4430条 | **~810KB** |

**缓存文件：**
- 每只股票：~200KB (pickle格式)
- 3只股票总计：~600KB

---

## 🔍 数据质量保障

### 数据验证检查点

**检查点1：数据获取后**
```python
# DataFetcher._standardize_data_format()
- 检查必要列存在：date, open, high, low, close, volume
- 检查数据类型：数值列为float
- 检查数据范围：价格>0, 成交量≥0
- 检查时间序列：日期连续性
```

**检查点2：技术指标计算后**
```python
# DataProcessor.calculate_indicators()
- 检查NaN值数量：前期指标NaN正常
- 检查指标范围：RSI在0-100，MACD合理范围
- 检查数据完整性：有效数据行数≥最小要求
```

**检查点3：信号生成前**
```python
# SignalGenerator.generate_signal()
- 检查数据长度：≥60条记录
- 检查当前数据：当前日期数据存在
- 检查指标有效性：关键指标非NaN
```

**检查点4：缓存使用前**
```python
# CacheValidator.validate_cache()
- 检查文件完整性：可正常读取
- 检查数据结构：列名和类型正确
- 检查数据时效性：时间范围覆盖需求
```

---

## 📝 数据流调试技巧

### 关键日志点

```python
# 1. 数据获取
logger.info(f"获取股票 {code} 数据，共 {len(data)} 条记录")

# 2. 技术指标计算
logger.debug(f"RSI有效值: {rsi_valid_count}, NaN值: {rsi_nan_count}")

# 3. 信号生成
logger.info(f"生成信号: {signal_type}, 评分: {total_score}")

# 4. 交易执行
logger.info(f"执行交易: {action} {shares}股 @{price}")

# 5. 性能计算
logger.info(f"总收益率: {total_return:.2%}, 最大回撤: {max_drawdown:.2%}")
```

### 数据断点调试

```python
# 在关键节点打印数据样本
print(f"数据形状: {data.shape}")
print(f"数据列: {data.columns.tolist()}")
print(f"数据样本:\n{data.head()}")
print(f"数据统计:\n{data.describe()}")
```

---

## 🔗 相关文档

- **架构设计：** `architecture.md`
- **快速上手：** `quick_start_for_developers.md`
- **配置说明：** `configuration_guide.md`
- **优化计划：** `comprehensive_optimization_plan.md`

---

**文档版本历史：**
- v1.0 (2026-01-16) - 初始版本，阶段0数据流文档创建
