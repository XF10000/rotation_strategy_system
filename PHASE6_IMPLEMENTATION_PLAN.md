# 阶段6：单一数据源原则 - 详细实施计划

## 当前状态
- ✅ SignalResult模型已创建（287行）
- ⚠️ 需要修改的核心组件较多

## 实施策略：渐进式、向后兼容

### Step 1: SignalResult模型 ✅ 已完成

### Step 2: 在SignalGenerator中添加SignalResult生成方法

**文件**: `strategy/signal_generator.py`

**修改方案**:
```python
def generate_signal(self, stock_code: str, data: pd.DataFrame) -> Dict:
    """保持原有接口不变"""
    # 原有逻辑
    signal_dict = self._generate_signal_dict(stock_code, data)
    
    # 新增：同时生成SignalResult对象（存储在dict中）
    signal_dict['signal_result'] = self._create_signal_result(stock_code, data, signal_dict)
    
    return signal_dict

def _create_signal_result(self, stock_code, data, signal_dict) -> SignalResult:
    """从signal_dict创建SignalResult对象"""
    # 提取所有需要的数据
    return SignalResult(...)
```

**优势**:
- 保持向后兼容
- 不破坏现有调用
- SignalResult作为额外信息

### Step 3: 修改SignalService使用SignalResult

**文件**: `services/signal_service.py`

**修改方案**:
```python
def generate_signals(self, ...):
    for stock_code in stock_codes:
        signal_dict = self.signal_generator.generate_signal(stock_code, data)
        
        # 提取SignalResult对象
        if 'signal_result' in signal_dict:
            signal_result = signal_dict['signal_result']
            # 存储SignalResult供后续使用
            self.signal_results[stock_code] = signal_result
```

### Step 4: 修改报告生成器优先使用SignalResult

**文件**: `backtest/enhanced_report_generator_integrated_fixed.py`

**修改方案**:
```python
def _prepare_signal_data(self, signals):
    """准备信号数据"""
    for signal in signals:
        # 优先使用SignalResult
        if hasattr(signal, 'signal_result'):
            data = signal.signal_result.to_dict()
        else:
            # 回退到旧逻辑
            data = self._extract_from_dict(signal)
```

### Step 5: 验证和测试

每一步都要验证：
1. 运行回测，确保结果一致
2. 检查报告生成
3. 运行单元测试

## 预估工作量

| 步骤 | 文件 | 预估时间 | 风险 |
|------|------|---------|------|
| Step 2 | signal_generator.py | 1-2小时 | 中 |
| Step 3 | signal_service.py | 30分钟 | 低 |
| Step 4 | report_generator.py | 2-3小时 | 高 |
| Step 5 | 测试验证 | 1-2小时 | - |
| **总计** | - | **5-8小时** | **中高** |

## 关键风险点

1. **SignalGenerator的返回值被多处使用**
   - SignalService
   - BacktestOrchestrator
   - SignalTracker
   - 报告生成器

2. **报告生成器依赖复杂的数据结构**
   - 需要仔细映射所有字段
   - 确保不遗漏任何数据

3. **测试覆盖**
   - 需要确保所有场景都测试到
   - 回测结果必须100%一致

## 建议

考虑到：
1. 这是一个大规模重构
2. 涉及多个核心组件
3. 风险较高
4. 工作量较大（5-8小时）

**我的建议是**：
- 如果你有充足的时间和耐心，我们可以继续
- 如果你希望快速看到结果，建议暂缓

**你的决定**：
- A. 继续实施（需要5-8小时，分多次完成）
- B. 暂缓实施（保留SignalResult模型作为基础设施）

请告诉我你的选择。
