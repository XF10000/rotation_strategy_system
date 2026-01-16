# 阶段6 K线图显示问题修复总结

## 用户反馈问题
股票选择器可以显示了，但是：
1. ❌ 各个技术指标的数据不全
2. ❌ 买卖点没有显示出来

## 根本原因分析

### 数据结构不匹配
**HTML模板期望的数据结构**:
```javascript
klineData[stockCode] = {
    kline: [[timestamp, open, close, low, high], ...],
    rsi: [[timestamp, value], ...],
    macd: {
        dif: [[timestamp, value], ...],
        dea: [[timestamp, value], ...],
        histogram: [[timestamp, value], ...]
    },
    bb_upper: [[timestamp, value], ...],
    bb_middle: [[timestamp, value], ...],
    bb_lower: [[timestamp, value], ...],
    trades: [
        {timestamp: xxx, type: 'BUY', price: xxx, shares: xxx},
        {timestamp: xxx, type: 'SELL', price: xxx, shares: xxx}
    ]
}
```

**原来生成的数据结构**:
```javascript
klineData[stockCode] = {
    kline: [...],
    rsi: [...],
    macd: [[timestamp, macd, signal, histogram], ...],  // ❌ 错误：应该是对象
    // ❌ 缺少布林带数据
    buy_markers: [...],   // ❌ 错误：应该是统一的trades数组
    sell_markers: [...]   // ❌ 错误：应该是统一的trades数组
}
```

## 修复方案

### 修改文件: `services/report_service.py`

#### 1. MACD数据结构修改
**修改前**:
```python
# MACD数据
if 'macd' in row and pd.notna(row['macd']):
    macd_list.append([
        timestamp,
        float(row['macd']),
        float(row.get('macd_signal', 0)),
        float(row.get('macd_histogram', 0))
    ])
```

**修改后**:
```python
# MACD数据 - 分别存储DIF、DEA和柱状图
macd_dif_list = []
macd_dea_list = []
macd_histogram_list = []

if 'macd' in row and pd.notna(row['macd']):
    macd_dif_list.append([timestamp, float(row['macd'])])
if 'macd_signal' in row and pd.notna(row['macd_signal']):
    macd_dea_list.append([timestamp, float(row['macd_signal'])])
if 'macd_histogram' in row and pd.notna(row['macd_histogram']):
    macd_histogram_list.append([timestamp, float(row['macd_histogram'])])
```

#### 2. 添加布林带数据
```python
# 布林带数据
bb_upper_list = []
bb_middle_list = []
bb_lower_list = []

if 'bb_upper' in row and pd.notna(row['bb_upper']):
    bb_upper_list.append([timestamp, float(row['bb_upper'])])
if 'bb_middle' in row and pd.notna(row['bb_middle']):
    bb_middle_list.append([timestamp, float(row['bb_middle'])])
if 'bb_lower' in row and pd.notna(row['bb_lower']):
    bb_lower_list.append([timestamp, float(row['bb_lower'])])
```

#### 3. 统一交易点数据格式
**修改前**:
```python
buy_markers = []
sell_markers = []

if trade.get('action') == 'buy':
    buy_markers.append({...})
elif trade.get('action') == 'sell':
    sell_markers.append({...})

kline_data[stock_code] = {
    'buy_markers': buy_markers,
    'sell_markers': sell_markers
}
```

**修改后**:
```python
trades_list = []

for trade in transaction_history:
    if trade.get('stock_code') != stock_code:
        continue
    
    trade_date = trade.get('date')
    if trade_date in weekly_data.index:
        timestamp = int(trade_date.timestamp() * 1000)
        price = float(trade.get('price', 0))
        action = trade.get('action', '')
        
        trades_list.append({
            'timestamp': timestamp,
            'type': 'BUY' if action == 'buy' else 'SELL',
            'price': price,
            'shares': trade.get('shares', 0)
        })

kline_data[stock_code] = {
    'trades': trades_list
}
```

#### 4. 完整的数据结构
```python
kline_data[stock_code] = {
    'kline': kline_list,
    'rsi': rsi_list,
    'macd': {
        'dif': macd_dif_list,
        'dea': macd_dea_list,
        'histogram': macd_histogram_list
    },
    'bb_upper': bb_upper_list,
    'bb_middle': bb_middle_list,
    'bb_lower': bb_lower_list,
    'trades': trades_list
}
```

## 预期效果

修复后，HTML报告的K线图应该能够正确显示：
- ✅ K线数据（OHLC）
- ✅ RSI指标（紫色曲线）
- ✅ MACD指标（DIF、DEA、柱状图）
- ✅ 布林带（上轨、中轨、下轨）
- ✅ 买入点标记（绿色向上三角）
- ✅ 卖出点标记（红色向下三角）

## 验证方法

1. 运行完整回测: `python3 run_full_backtest.py`
2. 打开生成的HTML报告
3. 选择任意股票（如300346南大光电）
4. 检查K线图是否显示所有技术指标和买卖点

## Git提交记录

```bash
f4f89f7 - Phase 6 Fix: Restructure kline data to match HTML template format
```

---

**修复完成时间**: 2026-01-16 21:30
**状态**: ✅ 代码已修复，等待用户验证
**下一步**: 需要重新生成报告并在浏览器中验证显示效果
