
让我分析需要修改的代码和文档，制定详细的修改计划。

基于我的分析，以下是需要修改的代码和文档的详细计划：

## 📋 MACD动能确认逻辑修改计划

### 🔧 **核心代码修改**

#### 1. **SignalGenerator - 主要逻辑实现** (高优先级)
- **文件**: [/strategy/signal_generator.py](cci:7://file:///Users/xiefan/VibeCoding/Rotation_Strategy_3_1/strategy/signal_generator.py:0:0-0:0)
- **修改内容**: 
  - 实现严谨的MACD柱体缩短检测逻辑
  - 添加历史柱体状态检查（前2根柱体）
  - 修改买入/卖出条件判断

#### 2. **技术指标计算** (高优先级)
- **文件**: `/indicators/momentum.py`
- **修改内容**: 
  - 可能需要增强MACD计算，返回更多历史数据
  - 添加柱体缩短趋势检测函数

### 📊 **分析工具更新**

#### 3. **股票信号分析工具** (中优先级)
- **文件**: [/analyze_stock_signals.py](cci:7://file:///Users/xiefan/VibeCoding/Rotation_Strategy_3_1/analyze_stock_signals.py:0:0-0:0)
- **修改内容**: 
  - 更新动能确认详情显示逻辑
  - 修改MACD信号描述文本

#### 4. **HTML报告生成器** (中优先级)
- **文件**: [/backtest/enhanced_report_generator_integrated_fixed.py](cci:7://file:///Users/xiefan/VibeCoding/Rotation_Strategy_3_1/backtest/enhanced_report_generator_integrated_fixed.py:0:0-0:0)
- **修改内容**: 
  - 更新动能确认规则说明文档
  - 修改4维度详情生成逻辑

### 📝 **文档更新**

#### 5. **项目README** (低优先级)
- **文件**: [/README.md](cci:7://file:///Users/xiefan/VibeCoding/Rotation_Strategy_3_1/README.md:0:0-0:0)
- **修改内容**: 更新动能确认信号的描述

#### 6. **技术文档** (低优先级)
- **文件**: `/docs/` 目录下相关文档
- **修改内容**: 更新MACD规则的技术说明

### 🧪 **验证测试**

#### 7. **回测对比验证** (高优先级)
- 运行修改前后的回测对比
- 分析信号触发频率变化
- 验证策略性能影响

#### 8. **信号分析测试** (高优先级)
- 使用[analyze_stock_signals.py](cci:7://file:///Users/xiefan/VibeCoding/Rotation_Strategy_3_1/analyze_stock_signals.py:0:0-0:0)测试具体案例
- 确保新逻辑正确识别动能转换点

## 🎯 **实施顺序建议**

1. **第一阶段**: 修改核心逻辑 (SignalGenerator + momentum指标)
2. **第二阶段**: 更新分析工具显示
3. **第三阶段**: 更新文档和说明
4. **第四阶段**: 全面验证测试

这个计划确保了从核心逻辑到用户界面的完整一致性，你觉得这个计划合理吗？