# 云铝股份(000807)数据流跟踪总结

## 🎯 跟踪目标
验证回测系统初始化时云铝股份的持股数量与HTML报告中显示的数据是否来自同一数据源。

## 📊 数据流跟踪结果

### 1. 配置文件来源
**文件**: `Input/portfolio_config.csv`
```csv
000807,云铝股份,0.1,有色金属,25
```
- **权重**: 0.1 (10%)
- **行业**: 有色金属
- **DCF估值**: 25元/股

### 2. 资金分配计算
**总资金**: 15,000,000元
**云铝股份目标资金**: 15,000,000 × 0.1 = 1,500,000元

### 3. 初始价格获取
**数据源**: akshare接口
**回测开始日期**: 2021-01-08
**云铝股份初始价格**: 6.69元

### 4. 持股数量计算
**计算逻辑** (在`PortfolioManager.initialize_portfolio()`中):
```python
# 目标资金: 1,500,000元
# 初始价格: 6.69元
raw_shares = 1,500,000 / 6.69 = 224,215.25股
shares_rounded_to_100 = int(224,215.25 / 100) * 100 = 224,200股
actual_cost = 224,200 × 6.69 = 1,499,898元
```

**最终结果**: 224,200股

### 5. 数据存储路径

#### 5.1 BacktestEngine中的存储
```python
# 在initialize_portfolio()方法中
self.portfolio_manager.initialize_portfolio(initial_prices)
# 日志输出: "初始持仓 000807: 224200股, 成本: 1,499,898.00"
```

#### 5.2 Portfolio History记录
```python
# 在run_backtest()方法中，每个交易日记录
self.portfolio_history.append({
    'date': current_date,
    'positions': self.portfolio_manager.positions.copy()  # 包含000807: 224200
})
```

#### 5.3 HTML报告数据获取
```python
# 在_prepare_integrated_results()方法中
portfolio_history = backtest_results['portfolio_history']
initial_record = portfolio_history.iloc[0]  # 第一条记录
initial_positions = initial_record.get('positions', {})  # 包含000807: 224200
```

### 6. HTML报告中的显示

**验证结果** (从`integrated_backtest_report_20250805_105051.html`):
```html
第592行: <td><strong>(000807)</strong></td>
第593行: <td>224200</td>
第1184行: <h4>云铝股份(000807)</h4>
```

## ✅ 数据一致性验证

### 回测初始化时的持股数量
- **来源**: `PortfolioManager.initialize_portfolio()`
- **计算**: 1,500,000 ÷ 6.69 = 224,215.25 → 向下取整 = 224,200股
- **日志**: "初始持仓 000807: 224200股, 成本: 1,499,898.00"

### HTML报告中的持股数量
- **来源**: `portfolio_history[0]['positions']['000807']`
- **显示**: 224200股
- **位置**: HTML报告第593行

## 🔍 数据来源确认

**结论**: ✅ **两者是同一数据源**

### 数据流路径
```
CSV配置文件 → 权重解析 → 资金分配 → akshare获取价格 → 股数计算 → PortfolioManager存储 → portfolio_history记录 → HTML报告显示
```

### 关键验证点
1. ✅ 配置文件中云铝股份权重为0.1
2. ✅ 总资金15,000,000元，目标分配1,500,000元
3. ✅ 初始价格6.69元来自akshare真实数据
4. ✅ 计算得出224,200股（向下取整到100股）
5. ✅ HTML报告显示224,200股
6. ✅ 数据完全一致，来源相同

## 📝 技术细节

### 股数计算规则
- **原始计算**: 目标资金 ÷ 股价
- **取整规则**: `int(raw_shares / 100) * 100` (向下取整到100股的整数倍)
- **实际成本**: 取整后股数 × 股价

### 数据传递链路
1. **CSV配置** → `load_portfolio_config()`
2. **权重配置** → `BacktestEngine.__init__()`
3. **价格获取** → `prepare_data()` → akshare接口
4. **股数计算** → `PortfolioManager.initialize_portfolio()`
5. **数据记录** → `portfolio_history`
6. **报告生成** → `_prepare_integrated_results()`
7. **HTML显示** → `enhanced_report_generator`

## 🎉 总结

通过完整的数据流跟踪，确认了：
- 回测系统初始化时计算的云铝股份持股数量为224,200股
- HTML报告中显示的云铝股份持股数量也是224,200股
- **两者来自完全相同的数据源和计算过程**
- 数据传递链路完整，无冗余或不一致的情况

这验证了系统的数据一致性和可靠性。