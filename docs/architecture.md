# 中线轮动策略系统 - 架构设计文档

## 文档概述

**文档版本：** v1.2  
**创建日期：** 2026-01-16  
**更新日期：** 2026-01-16（阶段5：数据源插件化）  
**目标读者：** 开发工程师、系统维护人员  
**阅读时间：** 约15-20分钟

本文档旨在帮助工程师快速理解系统的整体架构、核心模块及其关系。

---

## 🎯 系统概述

### 系统定位
中线轮动策略系统是一个**量化交易回测系统**，基于4维信号分析实现股票轮动策略的回测和分析。

### 核心功能
1. **数据获取与处理** - 从Akshare等数据源获取股票历史数据
2. **技术指标计算** - 计算RSI、MACD、EMA、布林带等技术指标
3. **信号生成** - 基于4维度评分系统生成买卖信号
4. **回测执行** - 模拟交易执行，管理投资组合
5. **性能分析** - 计算收益率、最大回撤、夏普比率等指标
6. **报告生成** - 生成HTML和CSV格式的详细报告

### 技术栈
- **语言：** Python 3.8+
- **数据处理：** pandas, numpy
- **技术指标：** TA-Lib
- **数据源：** akshare
- **可视化：** ECharts (HTML报告)
- **配置：** CSV文件驱动

---

## 🏗️ 系统架构

### 架构演进

#### V2.0 架构（当前推荐）- 服务层模式 

**设计理念**: 单一职责原则，服务化拆分

```
┌─────────────────────────────────────────────────────────────┐
│                    BacktestOrchestrator                      │
│                      (协调器 - 330行)                        │
│  职责: 协调各服务，控制回测流程，不包含业务逻辑              │
└─────────────────────────────────────────────────────────────┘
                              │
        ┌─────────────────────┼─────────────────────┐
        │                     │                     │
        ▼                     ▼                     ▼
┌──────────────┐      ┌──────────────┐     ┌──────────────┐
│ DataService  │      │SignalService │     │ PortfolioSvc │
│              │      │              │     │              │
│ 数据获取     │      │ 信号生成     │     │ 持仓管理     │
│ 数据管道✨   │      │ 4维度分析    │     │ 交易执行     │
│ 缓存管理     │      │              │     │              │
│ 技术指标     │      │ 信号追踪     │     │ 资金管理     │
└──────────────┘      └──────────────┘     └──────────────┘
        │                     │                     │
        └─────────────────────┼─────────────────────┘
                              ▼
                      ┌──────────────┐
                      │ReportService │
                      │              │
                      │ HTML报告     │
                      │ CSV导出      │
                      │ 性能分析     │
                      └──────────────┘
```

**优势**:
- 职责清晰，易于维护
- 代码复用性高
- 易于测试（单元测试覆盖率>60%）
- 易于扩展新功能
- 100%向后兼容

#### V1.0 架构（已废弃）- 单体模式 

**BacktestEngine** (2378行) - 上帝对象

```
┌─────────────────────────────────────────┐
│          BacktestEngine                 │
│  ┌─────────────────────────────────┐   │
│  │ 数据获取 + 缓存 + 处理          │   │
│  │ 信号生成 + 追踪                 │   │
│  │ 持仓管理 + 交易执行             │   │
│  │ 报告生成 + 性能分析             │   │
│  │ ... 所有功能都在一个类中        │   │
│  └─────────────────────────────────┘   │
└─────────────────────────────────────────┘
```

**问题**:
- 职责过多，难以维护
- 代码耦合度高
- 测试困难
- 扩展性差

**状态**: 已标记为 DEPRECATED，保留用于向后兼容

---

## 🏗️ 系统架构

### 整体架构图

```
┌─────────────────────────────────────────────────────────────┐
│                         用户层                               │
│  ┌──────────┐  ┌──────────┐  ┌──────────┐                  │
│  │ main.py  │  │  配置文件 │  │  报告查看 │                  │
│  └────┬─────┘  └────┬─────┘  └────┬─────┘                  │
└───────┼─────────────┼─────────────┼────────────────────────┘
        │             │             │
┌───────▼─────────────▼─────────────▼────────────────────────┐
│                      应用层 (Application)                    │
│  ┌──────────────────────────────────────────────────────┐  │
│  │          BacktestEngine (回测引擎)                    │  │
│  │  - 协调各模块完成回测                                 │  │
│  │  - 管理回测流程                                       │  │
│  │  - 生成回测结果                                       │  │
│  └──────────────────────────────────────────────────────┘  │
└──────────────────────────────────────────────────────────────┘
        │
┌───────▼──────────────────────────────────────────────────────┐
│                    业务逻辑层 (Business Logic)                │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐      │
│  │ SignalGenerator│ │PortfolioMgr │  │ ReportGen    │      │
│  │ (信号生成)     │  │ (持仓管理)   │  │ (报告生成)    │      │
│  └──────────────┘  └──────────────┘  └──────────────┘      │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐      │
│  │RotationStrat │  │PositionMgr   │  │ PerfAnalyzer │      │
│  │ (轮动策略)     │  │ (仓位管理)   │  │ (性能分析)    │      │
│  └──────────────┘  └──────────────┘  └──────────────┘      │
└──────────────────────────────────────────────────────────────┘
        │
┌───────▼──────────────────────────────────────────────────────┐
│                      数据层 (Data Layer)                      │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐      │
│  │ DataFetcher  │  │ DataProcessor│  │ DataStorage  │      │
│  │ (数据获取)    │  │ (数据处理)    │  │ (数据缓存)    │      │
│  └──────────────┘  └──────────────┘  └──────────────┘      │
└──────────────────────────────────────────────────────────────┘
        │
┌───────▼──────────────────────────────────────────────────────┐
│                    基础设施层 (Infrastructure)                │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐      │
│  │ Indicators   │  │ Config       │  │ Utils        │      │
│  │ (技术指标)    │  │ (配置管理)    │  │ (工具函数)    │      │
│  └──────────────┘  └──────────────┘  └──────────────┘      │
└──────────────────────────────────────────────────────────────┘
        │
┌───────▼──────────────────────────────────────────────────────┐
│                    外部依赖 (External)                        │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐      │
│  │ Akshare API  │  │ File System  │  │ TA-Lib       │      │
│  └──────────────┘  └──────────────┘  └──────────────┘      │
└──────────────────────────────────────────────────────────────┘
```

### 分层说明

#### 1. 用户层
- **main.py** - 程序入口，初始化系统并启动回测
- **配置文件** - CSV格式的股票池和回测参数配置
- **报告查看** - 生成的HTML/CSV报告

#### 2. 应用层
- **BacktestEngine** - 回测引擎核心，协调所有模块
  - ⚠️ 当前问题：职责过重（2400行），计划重构为服务化架构

#### 3. 业务逻辑层
- **SignalGenerator** - 4维信号生成器（核心策略逻辑）
- **PortfolioManager** - 投资组合管理
- **RotationStrategy** - 轮动策略实现
- **PositionManager** - 仓位管理
- **PerformanceAnalyzer** - 性能分析
- **ReportGenerator** - 报告生成

#### 4. 数据层
- **DataFetcher** - 数据获取（支持Akshare）
- **DataProcessor** - 数据处理和技术指标计算
- **DataStorage** - 数据缓存管理

#### 5. 基础设施层
- **Indicators** - 技术指标库（RSI、MACD、EMA等）
- **Config** - 配置管理
- **Utils** - 工具函数

#### 6. 外部依赖
- **Akshare API** - 股票数据源
- **File System** - 文件存储
- **TA-Lib** - 技术分析库

---

## 📦 核心模块详解

### 1. 回测引擎 (BacktestEngine)

**文件位置：** `backtest/backtest_engine.py`  
**代码规模：** ~2400行（待重构）

**核心职责：**
```python
class BacktestEngine:
    """
    回测引擎 - 系统核心协调器
    
    当前职责（过多，待重构）：
    1. 数据获取和缓存管理
    2. 信号生成协调
    3. 交易执行
    4. 投资组合管理
    5. 报告生成
    """
```

**主要方法：**
- `run_backtest()` - 执行完整回测流程
- `prepare_data()` - 准备回测数据
- `_calculate_signals()` - 计算交易信号
- `_execute_trades()` - 执行交易
- `generate_reports()` - 生成报告

**依赖关系：**
```
BacktestEngine
├── DataFetcher (数据获取)
├── DataProcessor (数据处理)
├── SignalGenerator (信号生成)
├── PortfolioManager (持仓管理)
├── ReportGenerator (报告生成)
└── PerformanceAnalyzer (性能分析)
```

**⚠️ 待优化：**
- 职责过重，违反单一职责原则
- 计划重构为服务化架构（见优化计划阶段2）

---

### 2. 信号生成器 (SignalGenerator)

**文件位置：** `strategy/signal_generator.py`  
**代码规模：** ~1264行

**核心职责：**
```python
class SignalGenerator:
    """
    4维信号生成器 - 策略核心
    
    实现4维度评分系统：
    1. 价值比过滤器（硬性前提）
    2. 超买超卖（RSI + 背离）
    3. 动能确认（MACD）
    4. 极端价格量能（布林带 + 成交量）
    
    触发逻辑：
    - 硬性前提必须满足
    - 其余3维至少满足2维
    """
```

**信号生成流程：**
```
输入：股票数据 + 配置参数
  ↓
1. 计算技术指标
  ↓
2. 价值比过滤器判断 (硬性前提)
  ↓
3. 计算4维度评分
   - RSI超买超卖评分
   - MACD动能评分
   - 极端价格量能评分
  ↓
4. 综合判断（3维至少2维满足）
  ↓
输出：买入/卖出/持有信号
```

**关键特性：**
- 支持行业特定的RSI阈值
- 支持极端RSI阈值（强制信号）
- 背离检测（顶背离/底背离）
- 详细的信号触发原因记录

---

### 3. 数据获取器 (DataFetcher)

**文件位置：** `data/data_fetcher.py`  
**代码规模：** ~1303行

**核心职责：**
```python
class AkshareDataFetcher(DataFetcher):
    """
    Akshare数据获取器
    
    功能：
    1. 从Akshare获取股票历史数据
    2. 数据格式标准化
    3. 重试机制（最多5次）
    4. 频率控制（避免触发反爬虫）
    5. 分红配股数据获取
    """
```

**数据获取流程：**
```
请求股票数据
  ↓
频率控制（间隔3秒）
  ↓
调用Akshare API
  ↓
重试机制（失败时）
  ↓
数据标准化
  ↓
返回标准格式数据
```

**数据标准格式：**
```python
DataFrame:
  索引: date (datetime)
  列: open, high, low, close, volume
```

**⚠️ 待优化：**
- 数据源硬编码为Akshare
- 计划实现插件化数据源架构（见优化计划阶段5）

---

### 4. 数据处理器 (DataProcessor)

**文件位置：** `data/data_processor.py`  
**代码规模：** ~800行

**核心职责：**
```python
class DataProcessor:
    """
    数据处理器
    
    功能：
    1. 数据验证
    2. 技术指标计算
    3. 周期转换（日线→周线）
    4. 数据清洗
    """
```

**技术指标计算：**
- **RSI** - 相对强弱指标（14周期）
- **MACD** - 指数平滑异同移动平均线
- **EMA** - 指数移动平均线（20周期）
- **布林带** - 价格波动通道
- **成交量指标** - 量能分析

**数据转换：**
```
日线数据
  ↓
resample_to_weekly()
  ↓
周线数据（周五收盘）
```

---

### 5. 投资组合管理器 (PortfolioManager)

**文件位置：** `backtest/portfolio_manager.py`  
**代码规模：** ~600行

**核心职责：**
```python
class PortfolioManager:
    """
    投资组合管理器
    
    功能：
    1. 持仓管理
    2. 现金管理
    3. 交易成本计算
    4. 持仓历史记录
    """
```

**持仓数据结构：**
```python
{
    'stock_code': {
        'shares': 1000,        # 持仓股数
        'avg_cost': 10.5,      # 平均成本
        'current_price': 12.0  # 当前价格
    }
}
```

**交易成本：**
- 手续费：万3
- 印花税：千1（仅卖出）
- 滑点：千1

---

### 6. 报告生成器 (ReportGenerator)

**文件位置：** `backtest/enhanced_report_generator_integrated_fixed.py`  
**代码规模：** ~2000行

**核心职责：**
```python
class IntegratedReportGenerator:
    """
    集成报告生成器
    
    功能：
    1. HTML报告生成
    2. 交互式K线图表
    3. 4维信号详情展示
    4. 性能指标可视化
    """
```

**报告内容：**
- 基础回测指标（收益率、最大回撤等）
- 策略vs基准对比
- 详细交易记录（含技术指标）
- 4维信号分析
- 交互式K线图（ECharts）
- 技术指标子图（RSI、MACD、布林带）

**⚠️ 待优化：**
- 存在重复计算问题
- 计划实现单一数据源原则（见优化计划阶段6）

---

## 🔄 核心流程

### 回测主流程

```
1. 系统初始化
   ├── 加载配置文件
   ├── 创建输出目录
   └── 初始化日志系统
   
2. 数据准备
   ├── 加载股票池配置
   ├── 获取历史数据（缓存优先）
   ├── 计算技术指标
   └── 数据验证
   
3. 回测执行
   ├── 遍历每个交易日
   │   ├── 生成交易信号
   │   ├── 执行交易
   │   ├── 更新持仓
   │   └── 记录状态
   └── 循环结束
   
4. 结果分析
   ├── 计算性能指标
   ├── 生成交易统计
   └── 信号分析
   
5. 报告生成
   ├── 生成HTML报告
   ├── 生成CSV报告
   └── 输出日志摘要
```

### 信号生成流程

```
输入：股票数据 + 当前日期
  ↓
1. 获取当前行情数据
  ↓
2. 价值比过滤器判断
   ├── 获取DCF估值
   ├── 计算价值比
   └── 判断是否满足条件
  ↓
3. 计算4维度评分
   ├── RSI超买超卖评分
   │   ├── 检查极端阈值
   │   ├── 检查普通阈值
   │   └── 检查背离信号
   ├── MACD动能评分
   │   ├── 柱体缩短判断
   │   ├── 金叉死叉判断
   │   └── 柱体颜色判断
   └── 极端价格量能评分
       ├── 布林带位置
       └── 成交量放大
  ↓
4. 综合判断
   ├── 价值比过滤器必须满足
   └── 其余3维至少2维满足
  ↓
输出：信号类型 + 详细原因
```

### 数据缓存流程

```
请求数据
  ↓
检查缓存
  ├── 缓存存在且有效
  │   └── 返回缓存数据
  └── 缓存不存在或过期
      ↓
      从数据源获取
      ↓
      保存到缓存
      ↓
      返回数据
```

---

## 📊 数据流向

详见 `data_flow.md` 文档。

---

## 🔧 配置管理

### 统一配置管理器 (ConfigManager)

**新增于阶段1优化**

系统现在使用统一的配置管理器，提供单一配置访问入口：

```python
from config.config_manager import get_config_manager

config_manager = get_config_manager()
config_manager.load_config('csv')

# 获取配置
backtest_config = config_manager.get_backtest_config()
portfolio = config_manager.get_portfolio_config()
dcf_values = config_manager.get_dcf_values()
```

**主要功能：**
- 统一加载CSV配置文件
- 自动类型转换和验证
- 支持中英文列名
- 单例模式，全局唯一实例

### 路径管理器 (PathManager)

**新增于阶段1优化**

统一管理所有目录和文件路径：

```python
from config.path_manager import get_path_manager

path_manager = get_path_manager()
path_manager.ensure_directories()

# 获取路径
reports_dir = path_manager.get_reports_dir()
log_path = path_manager.get_log_path()
```

**主要功能：**
- 自动查找项目根目录
- 管理所有系统路径
- 自动创建必要目录
- 跨平台路径兼容

详见 `configuration_guide.md` 文档。

---

## 📁 目录结构

```
Rotation_Strategy_3_1/
├── main.py                 # 程序入口
├── requirements.txt        # 依赖包列表
├── README.md              # 项目说明
│
├── Input/                 # 配置文件目录
│   ├── portfolio_config.csv      # 股票池配置
│   ├── Backtest_settings.csv     # 回测参数
│   └── sw2_rsi_threshold.csv     # RSI阈值配置
│
├── backtest/              # 回测引擎模块
│   ├── backtest_engine.py        # 回测引擎（核心）
│   ├── portfolio_manager.py      # 投资组合管理
│   ├── performance_analyzer.py   # 性能分析
│   ├── enhanced_report_generator_integrated_fixed.py  # 报告生成
│   ├── detailed_csv_exporter.py  # CSV导出
│   └── signal_tracker.py         # 信号跟踪
│
├── strategy/              # 策略模块
│   ├── signal_generator.py       # 信号生成器（核心）
│   ├── rotation_strategy.py      # 轮动策略
│   ├── position_manager.py       # 仓位管理
│   └── dynamic_position_manager.py  # 动态仓位
│
├── data/                  # 数据层模块
│   ├── data_fetcher.py           # 数据获取
│   ├── data_processor.py         # 数据处理
│   ├── data_storage.py           # 数据缓存
│   └── cache_validator.py        # 缓存验证
│
├── indicators/            # 技术指标模块
│   ├── trend.py                  # 趋势指标（EMA）
│   ├── momentum.py               # 动量指标（RSI、MACD）
│   ├── volatility.py             # 波动率指标（布林带）
│   ├── divergence.py             # 背离检测
│   └── price_value_ratio.py      # 价值比计算
│
├── config/                # 配置管理模块
│   ├── settings.py               # 基础配置
│   ├── csv_config_loader.py      # CSV配置加载
│   ├── industry_rsi_thresholds.py  # RSI阈值配置
│   └── backtest_report_template.html  # 报告模板
│
├── utils/                 # 工具模块
│   ├── industry_classifier.py    # 行业分类
│   ├── industry_mapper.py        # 行业映射
│   └── rsi_threshold_updater.py  # RSI阈值更新
│
├── data_cache/            # 数据缓存目录
├── logs/                  # 日志目录
├── output/                # 输出目录
├── reports/               # 报告目录
└── docs/                  # 文档目录
    ├── architecture.md           # 架构设计文档（本文档）
    ├── data_flow.md              # 数据流说明
    ├── quick_start_for_developers.md  # 快速上手指南
    └── configuration_guide.md    # 配置指南
```

---

## 🔗 模块依赖关系

### 依赖层级（从上到下）

```
Level 1: main.py
         ↓
Level 2: BacktestEngine
         ↓
Level 3: SignalGenerator, PortfolioManager, ReportGenerator
         ↓
Level 4: DataFetcher, DataProcessor, RotationStrategy
         ↓
Level 5: Indicators, Config, Utils
         ↓
Level 6: External (Akshare, TA-Lib, pandas)
```

### 关键依赖关系

```
BacktestEngine
├── depends on → DataFetcher
├── depends on → DataProcessor
├── depends on → SignalGenerator
├── depends on → PortfolioManager
└── depends on → ReportGenerator

SignalGenerator
├── depends on → Indicators (RSI, MACD, EMA, etc.)
├── depends on → Config (RSI thresholds)
└── depends on → Utils (industry classifier)

DataFetcher
├── depends on → Akshare API
└── depends on → DataStorage

DataProcessor
├── depends on → TA-Lib
└── depends on → Indicators
```

---

## ⚠️ 已知问题和待优化项

### 高优先级问题

1. **BacktestEngine职责过重**
   - 当前：2400行，职责混乱
   - 计划：重构为服务化架构（阶段2）

2. **配置管理分散**
   - 当前：13个配置文件，功能重叠
   - 计划：统一配置管理（阶段1）

3. **Import混乱**
   - 当前：依赖关系不清晰
   - 计划：清理和规范化（阶段3）

### 中优先级问题

4. **数据源硬编码**
   - 当前：只支持Akshare
   - 计划：插件化数据源（阶段5）

5. **重复计算**
   - 当前：信号和报告重复计算指标
   - 计划：单一数据源原则（阶段6）

6. **缺少单元测试**
   - 当前：测试覆盖率<5%
   - 计划：持续增加测试（阶段7）

详见 `comprehensive_optimization_plan.md`

---

## 📚 相关文档

- **数据流说明：** `data_flow.md`
- **快速上手指南：** `quick_start_for_developers.md`
- **配置说明：** `configuration_guide.md`
- **模块职责：** `module_responsibilities.md`
- **优化计划：** `comprehensive_optimization_plan.md`
- **系统设计：** `系统设计文档.md`（策略详细说明）

---

## 🔄 文档维护

**更新频率：** 每次重大架构变更时更新  
**维护者：** 项目团队  
**反馈渠道：** 项目Issue或团队讨论

---

## 🔌 数据源插件系统 (阶段5新增)

### 插件架构

**位置**: `data/` 模块

**设计模式**: 模板方法模式 + 策略模式 + 适配器模式

```
DataSourceManager (管理器)
    ↓
[AksharePlugin, TusharePlugin, ...] (多个插件)
    ↓
自动降级 + 健康检查
    ↓
统一的数据输出
```

### 核心组件

**1. DataSourcePlugin (抽象基类)**
```python
class DataSourcePlugin(ABC):
    @abstractmethod
    def fetch_raw_data(self, code, start_date, end_date, period):
        """获取原始数据（子类实现）"""
        pass
    
    def get_stock_data(self, code, start_date, end_date, period):
        """模板方法：验证 → 重试 → 标准化"""
        pass
```

**2. DataSourceManager (管理器)**
- 管理多个数据源插件
- 按优先级自动降级
- 健康检查和监控
- 手动切换数据源

**3. 已实现的插件**
- `AksharePlugin` - 免费，无需API密钥
- `TusharePlugin` - 需要Token，备用数据源

**4. PluginDataFetcherAdapter (适配器)**
- 适配新插件系统到现有DataFetcher接口
- 保持100%向后兼容

### 使用示例

```python
# 基础使用（自动降级）
from data.data_fetcher_adapter import PluginDataFetcherAdapter

fetcher = PluginDataFetcherAdapter()
data = fetcher.get_stock_data("000001", "2024-01-01", "2024-12-31")

# 高级使用（多数据源）
from data.data_source_manager import DataSourceManager
from data.data_source_plugin import AksharePlugin, TusharePlugin

manager = DataSourceManager()
manager.register_plugin(AksharePlugin(config))
manager.register_plugin(TusharePlugin(config))

# 自动降级：Akshare失败 → 自动切换Tushare
data = manager.get_stock_data("000001", "2024-01-01", "2024-12-31")
```

### 添加新数据源

只需3步：
```python
# 1. 实现插件类
class WindPlugin(DataSourcePlugin):
    def fetch_raw_data(self, code, start_date, end_date, period):
        return wind_data
    
    def test_connection(self):
        return True
    
    def get_source_name(self):
        return "Wind"

# 2. 注册插件
manager.register_plugin(WindPlugin(config))

# 3. 自动生效，无需修改其他代码
```

### 优势

1. **可扩展** - 添加新数据源只需实现插件接口
2. **可靠** - 主数据源失败自动切换备用
3. **可维护** - 职责清晰，易于测试
4. **兼容** - 通过适配器保持向后兼容

---

**文档版本历史：**
- v1.1 (2026-01-16) - 阶段1完成，添加ConfigManager和PathManager说明
- v1.0 (2026-01-16) - 初始版本，阶段0架构文档创建
- v1.2 (2026-01-16) - 阶段5更新：添加数据源插件系统说明

**最后更新：** 2026-01-16) - 阶段5更新：添加数据源插件系统说明
