# 临时文件清理计划

## 清理时间
2026-01-16

## 清理目标
删除调试和诊断过程中生成的临时文件，保留有价值的文档和代码

---

## 📋 待删除文件清单

### 1. 诊断脚本（共13个）
**用途**: 调试BacktestOrchestrator一致性问题
**状态**: 问题已解决，不再需要

- [ ] `analyze_stock_signals.py` - 分析股票信号
- [ ] `analyze_transaction_diff.py` - 分析交易差异
- [ ] `compare_all_transactions.py` - 对比所有交易
- [ ] `compare_daily_signals.py` - 对比每日信号
- [ ] `compare_first_signals.py` - 对比首个信号
- [ ] `compare_initialization.py` - 对比初始化
- [ ] `compare_results.py` - 对比结果
- [ ] `compare_signal_configs.py` - 对比信号配置
- [ ] `compare_signal_generators.py` - 对比信号生成器
- [ ] `compare_transactions.py` - 对比交易记录
- [ ] `diagnose_orchestrator.py` - 诊断Orchestrator
- [ ] `diagnose_txn_source.py` - 诊断交易来源
- [ ] `final_diagnosis.py` - 最终诊断

### 2. 临时测试脚本（共4个）
**用途**: 临时测试功能
**状态**: 已有正式单元测试，不再需要

- [ ] `test_divergence.py` - 测试背离功能
- [ ] `test_missing_signals.py` - 测试缺失信号
- [ ] `test_orchestrator.py` - 测试Orchestrator
- [ ] `test_signal_generation.py` - 测试信号生成

### 3. 临时文档（共11个）
**用途**: 阶段性总结和诊断报告
**状态**: 已整合到最终报告，可删除

- [ ] `CORRECTION_PLAN.md` - 改正计划（已完成）
- [ ] `DIAGNOSIS_PLAN.md` - 诊断计划（已完成）
- [ ] `ORCHESTRATOR_FIX_REPORT.md` - 修复报告（已完成）
- [ ] `PHASE1_VERIFICATION_REPORT_FINAL.md` - 阶段1验证报告
- [ ] `PHASE2_FINAL_SUMMARY.md` - 阶段2总结
- [ ] `PHASE2_SERVICE_REFACTORING_COMPLETE.md` - 阶段2重构完成
- [ ] `SERVICE_ARCHITECTURE_COMPLETE.md` - 服务架构完成
- [ ] `SIGNALSERVICE_INTEGRATION_SUCCESS.md` - SignalService集成成功
- [ ] `TALIB_UPGRADE_SUMMARY.md` - TA-Lib升级总结
- [ ] `UNIT_TEST_COMPLETION_SUMMARY.md` - 单元测试完成总结
- [ ] `UNIT_TEST_PROGRESS.md` - 单元测试进度

### 4. 验证脚本（保留）
**用途**: 完整回测验证
**状态**: 保留，可能还会使用

- [x] `run_full_backtest.py` - **保留**

---

## 📌 保留文件清单

### 重要文档（保留）
- [x] `README.md` - 项目说明
- [x] `BACKTEST_RESULTS_SUMMARY.md` - 回测结果总结
- [x] `FINAL_VERIFICATION_REPORT.md` - 最终验证报告
- [x] `UNIT_TEST_FINAL_REPORT.md` - 单元测试最终报告

### 正式测试（保留）
- [x] `tests/test_services.py` - 正式单元测试

---

## 🗑️ 清理统计

**待删除文件总数**: 28个
- 诊断脚本: 13个
- 临时测试: 4个
- 临时文档: 11个

**保留文件**: 5个
- 重要文档: 4个
- 验证脚本: 1个

---

## ✅ 清理后的项目结构

```
Rotation_Strategy_3_1/
├── README.md                          # 项目说明
├── main.py                            # 主程序入口
├── requirements.txt                   # 依赖包
├── run_full_backtest.py              # 完整回测验证脚本
│
├── BACKTEST_RESULTS_SUMMARY.md       # 回测结果总结
├── FINAL_VERIFICATION_REPORT.md      # 最终验证报告
├── UNIT_TEST_FINAL_REPORT.md         # 单元测试报告
│
├── Input/                             # 配置文件
├── backtest/                          # 回测引擎
├── strategy/                          # 策略模块
├── data/                              # 数据层
├── indicators/                        # 技术指标
├── config/                            # 配置管理
├── services/                          # 服务层（新）
├── utils/                             # 工具模块
├── tests/                             # 单元测试
├── docs/                              # 文档目录
├── data_cache/                        # 数据缓存
├── logs/                              # 日志
├── output/                            # 输出
└── reports/                           # 报告
```

---

## 📝 执行记录

- [ ] 删除13个诊断脚本
- [ ] 删除4个临时测试脚本
- [ ] 删除11个临时文档
- [ ] 验证项目结构清晰
- [ ] 确认所有功能正常
