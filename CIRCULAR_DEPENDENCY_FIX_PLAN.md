# 循环依赖修复方案

## 检测时间
2026-01-16 19:30

## 发现的循环依赖

### 1. backtest ↔ services （严重）⚠️

**循环路径**:
```
BacktestEngine (backtest/) 
  → imports SignalService (services/)
  
PortfolioService (services/)
  → imports PortfolioManager (backtest/)
  → imports TransactionCostCalculator (backtest/)
  
ReportService (services/)
  → imports DetailedCSVExporter (backtest/)
  → imports IntegratedReportGenerator (backtest/)
```

**影响**: 严重 - 违反了层级架构原则

---

## 修复方案

### 方案A：将backtest/中的工具类移到独立模块（推荐）✅

**原理**: 
- services层需要的是工具类，不是回测引擎
- 将工具类移到独立的模块，打破循环

**步骤**:
1. 创建 `core/` 目录存放核心工具类
2. 移动以下文件到 `core/`:
   - `portfolio_manager.py`
   - `transaction_cost.py`
   - `detailed_csv_exporter.py`
   - `enhanced_report_generator_integrated_fixed.py`
3. 更新所有import引用
4. 验证功能

**优点**:
- ✅ 彻底解决循环依赖
- ✅ 架构更清晰
- ✅ 符合单一职责原则

**缺点**:
- ⚠️ 需要修改多个文件的import
- ⚠️ 需要仔细测试

---

### 方案B：BacktestEngine不导入SignalService（简单）✅

**原理**:
- BacktestEngine是旧架构，已标记为deprecated
- 移除BacktestEngine对services层的依赖
- 让BacktestEngine直接使用SignalGenerator

**步骤**:
1. 修改BacktestEngine，移除 `from services.signal_service import SignalService`
2. 直接使用 `from strategy.signal_generator import SignalGenerator`
3. 验证功能

**优点**:
- ✅ 修改最小
- ✅ 快速解决
- ✅ 不影响新架构

**缺点**:
- ⚠️ BacktestEngine仍然很大
- ⚠️ 没有从根本上改善架构

---

### 方案C：services层不导入backtest/（复杂）

**原理**:
- 将backtest/中的类复制到services/
- services层完全独立

**优点**:
- ✅ services层完全独立

**缺点**:
- ❌ 代码重复
- ❌ 维护困难
- ❌ 不推荐

---

## 推荐方案：方案B（快速修复）+ 方案A（长期优化）

### 第一步：快速修复（方案B）- 立即执行
修改BacktestEngine，移除对services层的依赖

### 第二步：长期优化（方案A）- 阶段4执行
在阶段4（数据流管道化）时，重构目录结构

---

## 其他循环依赖

### 2. strategy ↔ strategy （可接受）✅
**原因**: 包内部循环
**影响**: 低
**处理**: 可接受，不需要修复

### 3. config ↔ config （可接受）✅
**原因**: 包内部循环
**影响**: 低
**处理**: 可接受，不需要修复

---

## 执行计划

### 立即执行（方案B）
1. 修改 `backtest/backtest_engine.py`
   - 移除 `from services.signal_service import SignalService`
   - 改为 `from strategy.signal_generator import SignalGenerator`
   - 修改相关代码逻辑

2. 验证功能
   - 运行完整回测
   - 运行单元测试
   - 重新检测循环依赖

3. 确认修复成功

### 后续优化（阶段4）
在阶段4执行方案A，创建core/目录并重构

---

**修复优先级**: 🔴 高  
**预计时间**: 10-15分钟  
**风险等级**: 低（BacktestEngine已deprecated）
