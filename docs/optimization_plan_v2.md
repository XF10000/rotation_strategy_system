# 中线轮动策略系统 — 优化计划 v2

> **基于 2026-05-12 代码审查编写的可执行优化计划**
> 旧版计划参考：`docs/comprehensive_optimization_plan.md`（v1.1，2026-01-17，标注完成度 93%，但实际大量条目未落地）

---

## 审查发现：旧计划与实际代码的差距

旧计划声称已完成（阶段 2、阶段 7 标注 100%），但实际代码中存在以下未解决的问题：

| 问题 | 旧计划状态 | 实际情况 |
|------|-----------|---------|
| BacktestEngine 废弃 | 阶段 2 完成 | `backtest_engine.py` 2378 行仍存在，`analyze_stock_signals.py` 仍引用 |
| PathManager | 阶段 1 完成 | 文件存在但实际代码几乎全部硬编码路径 |
| csv_config_loader 重复函数 | 未提及 | `load_backtest_settings` 和 `create_csv_config` 各重复定义一次 |
| 配置文件冗余（13 个） | 阶段 1 完成 | 13+ 个配置文件仍在 |
| 日志过载 | 未提及 | orchestrator 中 85 个 logger 调用 / 1092 行 |
| 异常处理不一致 | 未提及 | 多处使用魔法默认值静默失败 |
| Input 目录冗余文件 | 未提及 | 存在 `.bak`、`copy.csv`、`_only.csv` 等垃圾文件 |

**结论：旧计划过于宏大（13-18 周），且大量未执行到位。新计划应更务实、可逐步执行。**

---

## 优化计划（按执行顺序）

### Step 1: 修复 csv_config_loader 的重复函数定义

**现状**：`config/csv_config_loader.py` 中 `load_backtest_settings` 和 `create_csv_config` 各定义了两次，中间的版本覆盖了前面的，产生死代码。

**操作**：删除第 99-253 行的重复定义（`load_backtest_settings` 和 `create_csv_config` 各保留一份）。

**验证**：运行 `python -m pytest tests/ -v` 确认全部通过。

---

### Step 2: 清理 Input 目录垃圾文件

**现状**：
```
Input/
├── Backtest_settings.csv.bak            ← .bak 备份文件
├── portfolio_config copy.csv            ← 副本
└── portfolio_config_002460_only.csv     ← 单股票测试配置
```

**操作**：删除以上 3 个文件，将 `.bak` 加入 `.gitignore`。

---

### Step 3: 用 PathManager 替代硬编码路径

**现状**：`config/path_manager.py` 已实现（单例模式），但实际代码中大量使用 `'Input/xxx.csv'`、`'data_cache/'`、`'reports/'` 等硬编码路径。

**操作**：扫描所有 `.py` 文件，将硬编码路径替换为 `PathManager` 调用。

**涉及文件**（经验证）：
- `config/csv_config_loader.py` — `Input/portfolio_config.csv`, `Input/Backtest_settings.csv`
- `main.py` — `logs`, `data_cache`, `reports`
- `services/report_service.py` — `reports/`
- `services/backtest_orchestrator.py` — `reports/`
- `backtest/signal_tracker.py` — `reports/`
- `backtest/detailed_csv_exporter.py` — `reports/`
- `backtest/enhanced_report_generator_integrated_fixed.py` — `reports/`
- `backtest/performance_analyzer.py` — `reports/`

---

### Step 4: 删除 BacktestEngine 遗留代码

**现状**：`backtest/backtest_engine.py`（2378 行）标记为 `DEPRECATED`，但：
- `backtest/__init__.py` 仍然 re-export 它
- `analyze_stock_signals.py` 直接导入并使用它

**操作**：
1. 确认 `analyze_stock_signals.py` 是否仍在使用
2. 如果不再使用 → 删除整个文件
3. 如果仍需使用 → 改写成调用 `BacktestOrchestrator`
4. 删除 `backtest/backtest_engine.py`
5. 从 `backtest/__init__.py` 移除 re-export

---

### Step 5: 处理 analyze_stock_signals.py

**现状**：30KB 的独立脚本，完全复用 `BacktestEngine`。

**操作**：和 Step 4 联动决定 — 删除或改写。

---

### Step 6: 日志分级瘦身

**现状**：`services/backtest_orchestrator.py` 中 85 个 logger 调用（约 8 个/100 行），包含了大量调试级别的 INFO 日志。

**原则**：
- 每轮回测只输出一条摘要日志（INFO）
- 股票级别细节走 DEBUG
- 异常路径保留完整上下文

---

### Step 7: 异常处理统一

**现状**：多处使用魔法默认值静默失败，例如基准计算失败返回 `(45.0, 12.0, -18.0)`。

**原则**：
- 数据获取失败 → 重试 → 报错终止
- 单只股票信号失败 → 跳过该股票
- 删除所有 `return 默认值` 的模式

---

### Step 8: 配置集中化

**现状**：配置分散在 `config/settings.py`、`Input/Backtest_settings.csv`、`config/csv_config_loader.py` 内的 `DEFAULT_STRATEGY_PARAMS`。

**操作**：
1. 明确以 CSV 为唯一配置入口
2. 删除 `settings.py` 中与 CSV 重复的 `STRATEGY_PARAMS` / `BACKTEST_CONFIG`
3. `settings.py` 只保留 `LOGGING_CONFIG` 和 `OUTPUT_CONFIG`
4. 用 `dataclass` 或 `TypedDict` 定义配置模型替代 `Dict[str, Any]`

---

### Step 9: 清理 pipeline 死代码

**现状**：`pipelines/data_pipeline.py` 实现了责任链模式框架，但需要确认是否有实际调用方。如果没有使用则删除。

---

## 执行建议

| 顺序 | 步骤 | 预估时间 | 风险 | 备注 |
|------|------|---------|------|------|
| 1 | 修复 csv_config_loader 重复函数 | 15min | 低 | 最紧急的 bug |
| 2 | 清理 Input 目录垃圾 | 10min | 低 | 纯删除 |
| 3 | PathManager 替换硬编码路径 | 2h | 中 | 改完要跑回归测试 |
| 4 | 删除 BacktestEngine | 1h | 中 | 需确认 analyze_stock_signals 用途 |
| 5 | 处理 analyze_stock_signals.py | 30min | 低 | 和步骤 4 联动 |
| 6 | 日志分级 | 1h | 低 | 不影响功能 |
| 7 | 异常处理统一 | 2h | 中 | 要谨慎，不能掩盖真实错误 |
| 8 | 配置集中化 | 1h | 中 | 要确保回归测试通过 |
| 9 | 清理 pipeline 死代码 | 15min | 低 | 确认无用后删除 |

**第一步建议从 Step 1 开始**，因为那是最明显的 bug。确认没问题后继续后续步骤。

---

*文档版本：v2.0*
*创建日期：2026-05-12*
