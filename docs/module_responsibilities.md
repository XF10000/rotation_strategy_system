# 中线轮动策略系统 - 模块职责说明

## 📋 文档概述

**文档版本：** v1.0  
**创建日期：** 2026-01-16  
**目标读者：** 开发工程师、系统维护人员  
**阅读时间：** 约10-15分钟

本文档详细说明每个模块的职责边界、对外接口和依赖关系。

---

## 🎯 模块职责总览

| 模块 | 职责 | 重要性 | 状态 |
|------|------|--------|------|
| main.py | 程序入口，系统初始化 | ⭐⭐⭐⭐⭐ | ✅ 正常 |
| **services/** | **服务层（推荐）** | ⭐⭐⭐⭐⭐ | ✅ **已完成** |
| backtest/ | 回测引擎和相关功能 | ⭐⭐⭐⭐⭐ | ⚠️ Deprecated |
| strategy/ | 策略逻辑和信号生成 | ⭐⭐⭐⭐⭐ | ✅ 正常 |
| data/ | 数据获取、处理、缓存 | ⭐⭐⭐⭐ | ✅ 正常 |
| indicators/ | 技术指标计算 | ⭐⭐⭐⭐ | ✅ 正常 |
| config/ | 配置管理 | ⭐⭐⭐ | ✅ 已统一 |
| utils/ | 工具函数 | ⭐⭐⭐ | ✅ 正常 |

---

## 📦 核心模块详解

### 1. 服务层 (services/) ✨ 推荐使用

#### 1.1 BacktestOrchestrator (services/backtest_orchestrator.py)

**职责：**
- 协调各服务完成回测
- 管理服务初始化顺序
- 控制回测主循环
- 协调服务间数据流
- 收集和整理回测结果

**对外接口：**
```python
class BacktestOrchestrator(BaseService):
    def __init__(self, config: Dict[str, Any]) -> None:
        """初始化回测协调器"""
        pass
    
    def initialize(self) -> bool:
        """初始化所有服务"""
        pass
    
    def run_backtest(self) -> bool:
        """运行回测"""
        pass
    
    def get_results(self) -> Dict:
        """获取回测结果"""
        pass
```

**依赖：**
- `services.data_service` - 数据服务
- `services.signal_service` - 信号服务
- `services.portfolio_service` - 投资组合服务
- `services.report_service` - 报告服务

**优势：**
- ✅ 职责清晰（~330行 vs BacktestEngine 2400行）
- ✅ 易于测试
- ✅ 易于扩展
- ✅ 100%功能一致性

**代码规模：** 328行

---

#### 1.2 DataService (services/data_service.py)

**职责：**
- 数据获取协调
- DCF估值加载
- RSI阈值加载
- 股票-行业映射加载
- 数据缓存管理

**对外接口：**
```python
class DataService(BaseService):
    def initialize(self) -> bool:
        """初始化数据服务"""
        pass
    
    def get_stock_data(self, stock_code: str, 
                      start_date: str, 
                      end_date: str) -> Dict:
        """获取股票数据"""
        pass
```

**代码规模：** ~200行

---

#### 1.3 SignalService (services/signal_service.py)

**职责：**
- 信号生成协调
- SignalGenerator管理
- 信号详情收集

**对外接口：**
```python
class SignalService(BaseService):
    def initialize(self) -> bool:
        """初始化信号服务"""
        pass
    
    def generate_signals(self, stock_data: Dict, 
                        current_date: pd.Timestamp) -> Dict[str, str]:
        """生成交易信号"""
        pass
```

**代码规模：** ~150行

---

#### 1.4 PortfolioService (services/portfolio_service.py)

**职责：**
- 持仓管理协调
- 交易执行
- 动态仓位管理
- 交易成本计算

**对外接口：**
```python
class PortfolioService(BaseService):
    def initialize(self, stock_data: Dict, 
                   start_date: pd.Timestamp,
                   dcf_values: Dict) -> bool:
        """初始化投资组合服务"""
        pass
    
    def execute_trades(self, signals: Dict[str, str], 
                      current_date: pd.Timestamp,
                      stock_data: Dict) -> List[str]:
        """执行交易"""
        pass
```

**代码规模：** ~250行

---

#### 1.5 ReportService (services/report_service.py)

**职责：**
- 报告生成协调
- CSV报告生成
- HTML报告生成

**对外接口：**
```python
class ReportService(BaseService):
    def generate_reports(self, backtest_results: Dict,
                        config: Dict) -> Dict[str, str]:
        """生成所有报告"""
        pass
```

**代码规模：** ~100行

---

### 2. 程序入口 (main.py)

**职责：**
- 系统初始化
- 日志系统配置
- 目录创建
- 配置加载
- 回测流程启动
- 结果输出

**对外接口：**
```python
def main() -> None:
    """主程序入口"""
    pass
```

**依赖：**
- `config.settings` - 系统配置
- `config.csv_config_loader` - CSV配置加载
- `backtest.backtest_engine` - 回测引擎
- `backtest.performance_analyzer` - 性能分析

**不负责：**
- ❌ 数据获取
- ❌ 信号生成
- ❌ 交易执行
- ❌ 报告生成细节

**代码规模：** 145行

---

### 3. 回测引擎模块 (backtest/) ⚠️ Deprecated

#### 3.1 BacktestEngine (backtest_engine.py) - 已废弃

**⚠️ 状态：已废弃，请使用 services/BacktestOrchestrator**

**职责：**
- 协调回测流程（单体架构）
- 数据准备
- 信号计算协调
- 交易执行协调
- 持仓状态管理
- 报告生成协调

**对外接口：**
```python
class BacktestEngine:
    def __init__(self, config: Dict[str, Any]) -> None:
        """初始化回测引擎
        
        ⚠️ DEPRECATED: 请使用 BacktestOrchestrator
        """
        warnings.warn("BacktestEngine已废弃，请使用BacktestOrchestrator", 
                     DeprecationWarning)
        pass
    
    def run_backtest(self) -> bool:
        """运行回测"""
        pass
    
    def get_backtest_results(self) -> Dict:
        """获取回测结果"""
        pass
    
    def generate_reports(self) -> Dict[str, str]:
        """生成报告"""
        pass
```

**依赖：**
- `data.data_fetcher` - 数据获取
- `data.data_processor` - 数据处理
- `strategy.signal_generator` - 信号生成
- `backtest.portfolio_manager` - 持仓管理
- `backtest.enhanced_report_generator_integrated_fixed` - 报告生成

**问题：**
- ❌ 职责过重（2400行）
- ❌ 难以维护
- ❌ 难以测试
- ✅ 已被 BacktestOrchestrator 替代

**迁移指南：**
```python
# 旧方式（不推荐）
from backtest.backtest_engine import BacktestEngine
engine = BacktestEngine(config)
engine.run_backtest()

# 新方式（推荐）
from services.backtest_orchestrator import BacktestOrchestrator
orchestrator = BacktestOrchestrator(config)
orchestrator.initialize()
orchestrator.run_backtest()
```

**代码规模：** 2412行

---

#### 2.2 PortfolioManager (portfolio_manager.py)

**职责：**
- 持仓管理
- 现金管理
- 买入操作
- 卖出操作
- 持仓查询
- 持仓历史记录

**对外接口：**
```python
class PortfolioManager:
    def __init__(self, initial_capital: float) -> None:
        """初始化投资组合管理器"""
        pass
    
    def buy(self, stock_code: str, shares: int, price: float, 
            date: str, cost: float) -> bool:
        """买入股票"""
        pass
    
    def sell(self, stock_code: str, shares: int, price: float, 
             date: str, cost: float) -> bool:
        """卖出股票"""
        pass
    
    def get_position(self, stock_code: str) -> Dict:
        """获取持仓信息"""
        pass
    
    def get_total_value(self, current_prices: Dict[str, float]) -> float:
        """获取总资产"""
        pass
```

**依赖：**
- 无外部依赖（纯数据管理）

**不负责：**
- ❌ 交易决策
- ❌ 价格获取
- ❌ 交易成本计算（由TransactionCostCalculator负责）

**代码规模：** 600行

---

#### 2.3 PerformanceAnalyzer (performance_analyzer.py)

**职责：**
- 性能指标计算
- 收益率分析
- 风险指标计算
- 交易统计
- 基准对比

**对外接口：**
```python
class PerformanceAnalyzer:
    def generate_performance_report(self, 
                                   portfolio_history: pd.DataFrame,
                                   transaction_history: List[Dict]) -> Dict:
        """生成性能报告"""
        pass
    
    def print_performance_summary(self, report: Dict) -> None:
        """打印性能摘要"""
        pass
```

**依赖：**
- `pandas`, `numpy` - 数据处理

**不负责：**
- ❌ 数据获取
- ❌ 报告格式化
- ❌ 报告输出

**代码规模：** 400行

---

#### 2.4 ReportGenerator (enhanced_report_generator_integrated_fixed.py)

**职责：**
- HTML报告生成
- K线图数据准备
- 交易点标注
- 技术指标图表
- 模板渲染

**对外接口：**
```python
class IntegratedReportGenerator:
    def generate_report(self, 
                       backtest_results: Dict,
                       config: Dict) -> str:
        """生成HTML报告"""
        pass
```

**依赖：**
- `config.backtest_report_template.html` - HTML模板
- `backtest_results` - 回测结果数据

**不负责：**
- ❌ 数据计算（应使用已计算的结果）
- ❌ 信号生成
- ❌ 性能分析

**⚠️ 当前问题：**
- 存在重复计算
- 计划实施单一数据源原则

**代码规模：** 2000行

---

### 3. 策略模块 (strategy/)

#### 3.1 SignalGenerator (signal_generator.py)

**职责：**
- 4维信号生成
- 价值比过滤器判断
- RSI超买超卖判断
- MACD动能判断
- 极端价格量能判断
- 信号详情记录

**对外接口：**
```python
class SignalGenerator:
    def __init__(self, config: Dict, 
                 dcf_values: Dict[str, float] = None,
                 rsi_thresholds: Dict = None,
                 stock_industry_map: Dict = None) -> None:
        """初始化信号生成器"""
        pass
    
    def generate_signal(self, data: pd.DataFrame, 
                       date: str) -> str:
        """生成交易信号"""
        pass
    
    def get_signal_details(self) -> Dict:
        """获取信号详情"""
        pass
```

**依赖：**
- `indicators.*` - 技术指标计算
- `config.industry_rsi_thresholds` - RSI阈值配置
- DCF估值数据

**不负责：**
- ❌ 数据获取
- ❌ 交易执行
- ❌ 持仓管理

**代码规模：** 1264行

---

#### 3.2 DynamicPositionManager (dynamic_position_manager.py)

**职责：**
- 动态仓位计算
- 根据信号强度调整仓位
- 仓位限制控制

**对外接口：**
```python
class DynamicPositionManager:
    def calculate_position_size(self, 
                               signal_strength: float,
                               available_capital: float,
                               stock_price: float) -> int:
        """计算买入数量"""
        pass
```

**依赖：**
- 配置参数（最小/最大仓位）

**不负责：**
- ❌ 信号生成
- ❌ 实际交易执行

**代码规模：** 300行

---

### 4. 数据模块 (data/)

#### 4.1 DataFetcher (data_fetcher.py)

**职责：**
- 从外部数据源获取股票数据
- 数据格式标准化
- 重试机制
- 频率控制
- 分红配股数据获取

**对外接口：**
```python
class DataFetcher(ABC):
    @abstractmethod
    def get_stock_data(self, code: str, 
                      start_date: str, 
                      end_date: str,
                      period: str = 'weekly') -> pd.DataFrame:
        """获取股票数据"""
        pass

class AkshareDataFetcher(DataFetcher):
    """Akshare数据获取器实现"""
    pass
```

**依赖：**
- `akshare` - 数据源API

**不负责：**
- ❌ 数据缓存（由DataStorage负责）
- ❌ 技术指标计算（由DataProcessor负责）
- ❌ 数据分析

**⚠️ 待优化：**
- 计划实施插件化数据源架构

**代码规模：** 1303行

---

#### 4.2 DataProcessor (data_processor.py)

**职责：**
- 数据验证
- 周期转换（日线→周线）
- 技术指标计算
- 数据清洗
- 缺失值处理

**对外接口：**
```python
class DataProcessor:
    def process(self, data: pd.DataFrame) -> pd.DataFrame:
        """处理数据"""
        pass
    
    def resample_to_weekly(self, data: pd.DataFrame) -> pd.DataFrame:
        """转换为周线数据"""
        pass
    
    def calculate_indicators(self, data: pd.DataFrame) -> pd.DataFrame:
        """计算技术指标"""
        pass
```

**依赖：**
- `indicators.*` - 技术指标函数
- `talib` - 技术分析库

**不负责：**
- ❌ 数据获取
- ❌ 数据缓存
- ❌ 信号生成

**代码规模：** 800行

---

#### 4.3 DataStorage (data_storage.py)

**职责：**
- 数据缓存管理
- 缓存读取
- 缓存写入
- 缓存验证
- 缓存更新

**对外接口：**
```python
class DataStorage:
    def save_data(self, stock_code: str, 
                  data: pd.DataFrame,
                  freq: str) -> None:
        """保存数据到缓存"""
        pass
    
    def load_data(self, stock_code: str, 
                  freq: str) -> Optional[pd.DataFrame]:
        """从缓存加载数据"""
        pass
    
    def is_cache_valid(self, stock_code: str, 
                      freq: str,
                      start_date: str,
                      end_date: str) -> bool:
        """检查缓存是否有效"""
        pass
```

**依赖：**
- 文件系统

**不负责：**
- ❌ 数据获取
- ❌ 数据处理
- ❌ 缓存策略决策（由调用者决定）

**代码规模：** 500行

---

### 5. 技术指标模块 (indicators/)

#### 5.1 Trend (trend.py)

**职责：**
- EMA计算
- 趋势方向判断
- 趋势强度分析

**对外接口：**
```python
def calculate_ema(data: pd.DataFrame, 
                  period: int = 20) -> pd.Series:
    """计算EMA"""
    pass

def detect_ema_trend(data: pd.DataFrame, 
                     period: int = 20,
                     lookback: int = 8) -> str:
    """检测EMA趋势"""
    pass
```

**依赖：**
- `talib.EMA`

**不负责：**
- ❌ 数据获取
- ❌ 信号生成

**代码规模：** 200行

---

#### 5.2 Momentum (momentum.py)

**职责：**
- RSI计算
- MACD计算
- 动量指标分析

**对外接口：**
```python
def calculate_rsi(data: pd.DataFrame, 
                  period: int = 14) -> pd.Series:
    """计算RSI"""
    pass

def calculate_macd(data: pd.DataFrame,
                   fastperiod: int = 12,
                   slowperiod: int = 26,
                   signalperiod: int = 9) -> Tuple[pd.Series, pd.Series, pd.Series]:
    """计算MACD"""
    pass
```

**依赖：**
- `talib.RSI`, `talib.MACD`

**不负责：**
- ❌ 数据获取
- ❌ 信号判断

**代码规模：** 250行

---

#### 5.3 Volatility (volatility.py)

**职责：**
- 布林带计算
- 波动率分析

**对外接口：**
```python
def calculate_bollinger_bands(data: pd.DataFrame,
                              period: int = 20,
                              std: float = 2.0) -> Tuple[pd.Series, pd.Series, pd.Series]:
    """计算布林带"""
    pass
```

**依赖：**
- `talib.BBANDS`

**不负责：**
- ❌ 数据获取
- ❌ 信号判断

**代码规模：** 150行

---

#### 5.4 Divergence (divergence.py)

**职责：**
- RSI背离检测
- MACD背离检测
- 顶背离/底背离判断

**对外接口：**
```python
def detect_rsi_divergence(data: pd.DataFrame,
                         lookback: int = 13) -> Optional[str]:
    """检测RSI背离"""
    pass

def detect_macd_divergence(data: pd.DataFrame,
                          lookback: int = 13) -> Optional[str]:
    """检测MACD背离"""
    pass
```

**依赖：**
- `pandas`, `numpy`

**不负责：**
- ❌ 指标计算（使用已计算的指标）
- ❌ 信号生成

**代码规模：** 400行

---

### 6. 配置模块 (config/)

#### 6.1 Settings (settings.py)

**职责：**
- 系统默认配置
- 数据源配置
- 策略参数配置
- 日志配置
- 输出配置

**对外接口：**
```python
DATA_SOURCE = {...}
STRATEGY_PARAMS = {...}
LOGGING_CONFIG = {...}
OUTPUT_CONFIG = {...}
```

**依赖：**
- 无

**不负责：**
- ❌ 配置加载逻辑
- ❌ 配置验证

**⚠️ 待优化：**
- 计划统一配置管理

**代码规模：** 60行

---

#### 6.2 CSVConfigLoader (csv_config_loader.py)

**职责：**
- 加载CSV配置文件
- 配置解析
- 配置验证
- 配置对象构建

**对外接口：**
```python
def create_csv_config() -> Dict[str, Any]:
    """创建CSV配置"""
    pass

def load_portfolio_config() -> pd.DataFrame:
    """加载股票池配置"""
    pass
```

**依赖：**
- `pandas` - CSV读取

**不负责：**
- ❌ 配置存储
- ❌ 配置修改

**代码规模：** 400行

---

### 7. 工具模块 (utils/)

#### 7.1 IndustryClassifier (industry_classifier.py)

**职责：**
- 股票行业分类
- 行业代码映射
- 行业信息查询

**对外接口：**
```python
def get_stock_industry_auto(stock_code: str) -> Dict[str, str]:
    """自动获取股票行业分类"""
    pass
```

**依赖：**
- `akshare` - 行业数据

**不负责：**
- ❌ 行业数据存储
- ❌ 行业分析

**代码规模：** 300行

---

## 🔗 模块依赖关系图

```
main.py
  ├── BacktestEngine
  │   ├── DataFetcher
  │   │   └── DataStorage
  │   ├── DataProcessor
  │   │   └── Indicators (trend, momentum, volatility)
  │   ├── SignalGenerator
  │   │   ├── Indicators
  │   │   ├── Divergence
  │   │   └── Config (RSI thresholds)
  │   ├── PortfolioManager
  │   ├── DynamicPositionManager
  │   ├── ReportGenerator
  │   └── PerformanceAnalyzer
  └── Config
      ├── Settings
      └── CSVConfigLoader
```

---

## 📝 职责边界原则

### 单一职责原则

每个模块应该只有一个改变的理由：

✅ **好的例子：**
```python
# PortfolioManager 只负责持仓管理
class PortfolioManager:
    def buy(...): pass
    def sell(...): pass
    def get_position(...): pass
```

❌ **不好的例子：**
```python
# PortfolioManager 不应该负责数据获取
class PortfolioManager:
    def buy(...): pass
    def fetch_stock_data(...): pass  # ❌ 职责越界
```

### 依赖倒置原则

高层模块不应该依赖低层模块，都应该依赖抽象：

✅ **好的例子：**
```python
# BacktestEngine 依赖抽象的 DataFetcher
class BacktestEngine:
    def __init__(self, data_fetcher: DataFetcher):
        self.data_fetcher = data_fetcher  # 抽象接口
```

❌ **不好的例子：**
```python
# BacktestEngine 直接依赖具体实现
class BacktestEngine:
    def __init__(self):
        self.data_fetcher = AkshareDataFetcher()  # ❌ 耦合具体实现
```

---

## ⚠️ 当前职责问题

### 问题1：BacktestEngine职责过重

**现状：**
- 数据获取、信号生成、交易执行、报告生成都在一个类中
- 2400行代码，难以维护

**计划：**
- 重构为服务化架构（优化计划阶段2）
- 拆分为DataService、SignalService、PortfolioService、ReportService

### 问题2：配置管理分散

**现状：**
- 13个配置文件，职责重叠
- 3套RSI阈值加载器并存

**计划：**
- 统一配置管理（优化计划阶段1）
- 创建ConfigManager统一入口

### 问题3：报告生成器重复计算

**现状：**
- ReportGenerator重新计算指标
- 违反单一数据源原则

**计划：**
- 实施单一数据源原则（优化计划阶段6）
- 使用SignalResult对象传递所有计算结果

---

## 🔧 模块开发指南

### 添加新模块

**步骤：**
1. 明确模块职责
2. 定义对外接口
3. 确定依赖关系
4. 编写模块代码
5. 添加单元测试
6. 更新本文档

**模板：**
```python
"""
模块名称 - 简短描述

职责：
1. 职责1
2. 职责2

不负责：
- 不负责的事项1
- 不负责的事项2
"""

class ModuleName:
    """模块类"""
    
    def __init__(self, dependencies):
        """初始化"""
        pass
    
    def public_method(self):
        """公开方法"""
        pass
    
    def _private_method(self):
        """私有方法"""
        pass
```

### 修改现有模块

**原则：**
1. 不改变对外接口（向后兼容）
2. 不扩展职责范围
3. 添加deprecation警告（如果废弃旧接口）
4. 更新文档

---

## 📚 相关文档

- **架构设计：** `architecture.md`
- **数据流说明：** `data_flow.md`
- **快速上手：** `quick_start_for_developers.md`
- **优化计划：** `comprehensive_optimization_plan.md`

---

**文档版本历史：**
- v1.0 (2026-01-16) - 初始版本，阶段0模块职责文档创建
- v1.1 (2026-01-16) - 阶段3更新：
  - 添加services层完整说明
  - 标记BacktestEngine为Deprecated
  - 更新config/状态为"已统一"
  - 更新data/状态为"正常"
  - 添加Import规范说明（见coding_standards.md）
  - 消除循环依赖（backtest ↔ services已解决）
