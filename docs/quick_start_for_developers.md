# 中线轮动策略系统 - 开发者快速上手指南

## 文档概述

**文档版本：** v1.2  
**创建日期：** 2026-01-16  
**更新日期：** 2026-01-17（阶段2完成：BacktestOrchestrator完全独立运行）  
**目标读者：** 新加入的开发工程师  
**阅读时间：** 约20-30分钟

本文档帮助新工程师快速理解系统、运行第一个回测、并开始开发工作。

---

## 🎯 30分钟快速理解系统

### 第1步：理解系统是做什么的（5分钟）

这是一个**量化交易回测系统**，用于：
1. 测试股票轮动策略的历史表现
2. 基于4维信号分析生成买卖信号
3. 模拟交易执行，计算收益率
4. 生成详细的分析报告

**核心概念：**
- **回测** - 用历史数据测试策略
- **4维信号** - 价值比 + RSI + MACD + 量能
- **轮动策略** - 在多只股票间切换持仓

### 第2步：理解代码结构（10分钟）

**从哪里开始看代码？**

```
推荐阅读顺序（V2.0 服务层架构）：

1. main.py (5分钟)
   ↓ 理解程序入口和主流程
   
2. services/backtest_orchestrator.py (10分钟)
   ↓ 理解回测协调流程（推荐）
   
3. strategy/signal_generator.py (10分钟)
   ↓ 理解核心策略逻辑
   
4. services/data_service.py (5分钟)
   ↓ 理解数据服务
   
5. 其他模块 (按需查看)

⚠️ 注意：backtest/backtest_engine.py 已废弃，请使用 services/ 层
```

**核心文件速览（V2.0架构）：**

| 文件 | 作用 | 重要性 | 代码量 | 状态 |
|------|------|--------|--------|------|
| `main.py` | 程序入口 | ⭐⭐⭐⭐⭐ | 145行 | ✅ 正常 |
| **`services/backtest_orchestrator.py`** | **回测协调器（完全独立）** | ⭐⭐⭐⭐⭐ | 1050行 | ✅ **推荐使用** |
| `services/data_service.py` | 数据服务 | ⭐⭐⭐⭐ | ~200行 | ✅ 正常 |
| `services/signal_service.py` | 信号服务 | ⭐⭐⭐⭐ | ~150行 | ✅ 正常 |
| `services/portfolio_service.py` | 投资组合服务 | ⭐⭐⭐⭐ | ~250行 | ✅ 正常 |
| `services/report_service.py` | 报告服务 | ⭐⭐⭐⭐ | ~150行 | ✅ 正常 |
| `strategy/signal_generator.py` | 信号生成（核心） | ⭐⭐⭐⭐⭐ | 1425行 | ✅ 正常 |
| ~~`backtest/backtest_engine.py`~~ | ~~回测引擎（旧）~~ | ⭐⭐⭐⭐⭐ | 2412行 | ❌ **已废弃** |
| `data/data_fetcher.py` | 数据获取 | ⭐⭐⭐⭐ | 1303行 | ✅ 正常 |
| `backtest/portfolio_manager.py` | 持仓管理 | ⭐⭐⭐ | 600行 | ✅ 正常 |

### 第3步：运行第一个回测（15分钟）

见下文"运行第一个回测"章节。

---

## 🚀 环境准备

### 系统要求

- **Python版本：** 3.8+
- **操作系统：** macOS / Linux / Windows
- **内存：** 建议4GB+
- **磁盘：** 建议1GB+（用于数据缓存）

### 安装依赖

```bash
# 1. 克隆或进入项目目录
cd /path/to/Rotation_Strategy_3_1

# 2. 创建虚拟环境（推荐）
python3 -m venv venv
source venv/bin/activate  # macOS/Linux
# venv\Scripts\activate  # Windows

# 3. 安装依赖
pip install -r requirements.txt

# 4. 验证安装
python3 -c "import akshare; import talib; print('依赖安装成功')"
```

**核心依赖：**
- `pandas` - 数据处理
- `numpy` - 数值计算
- `akshare` - 数据源
- `TA-Lib` - 技术指标（需要单独安装C库）

**TA-Lib安装（如遇问题）：**

```bash
# macOS
brew install ta-lib
pip install TA-Lib

# Linux
sudo apt-get install ta-lib
pip install TA-Lib

# Windows
# 下载预编译包：https://www.lfd.uci.edu/~gohlke/pythonlibs/#ta-lib
pip install TA_Lib-0.4.XX-cpXX-cpXX-win_amd64.whl
```

---

## 🎮 运行第一个回测

### 快速运行（使用默认配置）

```bash
# 在项目根目录执行
python3 main.py
```

**预期输出：**
```
2026-01-16 11:30:00 - INFO - ==================================================
2026-01-16 11:30:00 - INFO - 中线轮动策略系统启动
2026-01-16 11:30:00 - INFO - 启动时间: 2026-01-16 11:30:00
2026-01-16 11:30:00 - INFO - ==================================================
2026-01-16 11:30:00 - INFO - 使用CSV配置文件进行回测...
2026-01-16 11:30:00 - INFO - 配置详情: 中线轮动策略 - 基于4维信号分析
2026-01-16 11:30:00 - INFO - 回测期间: 2021-01-08 至 2025-01-03
2026-01-16 11:30:00 - INFO - 总资金: 14,999,341 元
...
2026-01-16 11:35:00 - INFO - 回测运行完成，开始生成报告...
2026-01-16 11:35:30 - INFO - 报告生成完成:
2026-01-16 11:35:30 - INFO -   HTML报告: reports/integrated_backtest_report_20260116_113530.html
2026-01-16 11:35:30 - INFO -   详细CSV报告: reports/detailed_transactions_20260116_113530.csv
```

**运行时间：** 约3-5分钟（首次运行需要下载数据）

### 查看报告

```bash
# 打开HTML报告（macOS）
open reports/integrated_backtest_report_*.html

# 或在浏览器中打开
# 文件位于：reports/目录下
```

**报告内容：**
- 基础回测指标（收益率、最大回撤等）
- 策略vs基准对比
- 详细交易记录
- 交互式K线图
- 4维信号分析

---

## 📝 修改配置运行回测

### 配置文件说明

系统使用CSV文件配置，主要有两个配置文件：

**1. 股票池配置：** `Input/portfolio_config.csv`

```csv
股票代码,股票名称,初始权重,行业分类,DCF估值
601088,中国神华,0.33,煤炭开采,25.5
601225,淮北矿业,0.33,煤炭开采,18.2
600985,淮矿控股,0.34,煤炭开采,15.8
```

**2. 回测参数：** `Input/Backtest_settings.csv`

```csv
参数名称,参数值
回测开始日期,2021-01-08
回测结束日期,2025-01-03
总资本,14999341
价值比卖出阈值,0.8
价值比买入阈值,0.7
```

### 修改股票池

**场景：想测试其他股票**

```bash
# 1. 编辑 Input/portfolio_config.csv
# 2. 修改股票代码、名称、权重
# 3. 保存文件
# 4. 运行回测

python3 main.py
```

**示例：测试银行股**

```csv
股票代码,股票名称,初始权重,行业分类,DCF估值
601398,工商银行,0.33,银行,6.5
601939,建设银行,0.33,银行,7.2
601288,农业银行,0.34,银行,4.8
```

### 修改回测时间段

**场景：测试最近1年表现**

```bash
# 1. 编辑 Input/Backtest_settings.csv
# 2. 修改回测开始日期和结束日期
回测开始日期,2024-01-01
回测结束日期,2025-01-16

# 3. 运行回测
python3 main.py
```

---

## 🔍 理解核心代码

### 主程序流程 (main.py)

```python
def main():
    """主程序入口"""
    
    # 1. 系统初始化
    logger = setup_logging()
    os.makedirs('output', exist_ok=True)
    os.makedirs('data_cache', exist_ok=True)
    
    # 2. 加载配置
    config = create_csv_config()
    
    # 3. 创建回测协调器（V2.0推荐）
    from services.backtest_orchestrator import BacktestOrchestrator
    orchestrator = BacktestOrchestrator(config)
    
    # 4. 初始化并运行回测
    orchestrator.initialize()
    success = orchestrator.run_backtest()
    
    # 5. 生成报告
    report_files = engine.generate_reports()
    
    # 6. 性能分析
    analyzer = PerformanceAnalyzer()
    performance_report = analyzer.generate_performance_report(...)
```

**关键点（V2.0架构）：**
- 配置驱动：所有参数从CSV读取
- 服务层架构：通过BacktestOrchestrator协调各服务
- 职责清晰：DataService、SignalService、PortfolioService、ReportService
- 自动化：数据获取、缓存、报告生成全自动

**⚠️ 注意**：旧的BacktestEngine已废弃，请使用BacktestOrchestrator

### 信号生成逻辑 (signal_generator.py)

```python
class SignalGenerator:
    """4维信号生成器"""
    
    def generate_signal(self, data, date):
        """生成交易信号"""
        
        # 1. 价值比过滤器（硬性前提）
        if not self._check_value_ratio(data, date):
            return 'hold'  # 不满足硬性前提，不交易
        
        # 2. 计算4维度评分
        scores = self._calculate_4d_scores(data, date)
        # scores = {
        #     'rsi_score': 1.0,
        #     'macd_score': 1.0,
        #     'volume_score': 0.0
        # }
        
        # 3. 综合判断（3维至少2维满足）
        if sum(scores.values()) >= 2:
            return 'buy' or 'sell'
        else:
            return 'hold'
```

**关键点：**
- 硬性前提：价值比过滤器必须满足
- 3选2逻辑：其余3维至少2维满足
- 详细记录：保存所有评分和触发原因

### 回测执行流程 (services/backtest_orchestrator.py)

**V2.0 服务层架构（推荐）：**

```python
class BacktestOrchestrator(BaseService):
    """回测协调器 - 协调各服务完成回测"""
    
    def initialize(self):
        """初始化所有服务"""
        self.data_service.initialize()
        self.signal_service.initialize()
        # ...
    
    def run_backtest(self):
        """执行回测"""
        
        # 1. 准备数据
        stock_data = self.prepare_data()
        
        # 2. 遍历每个交易日
        for date in trading_dates:
            # 2.1 生成信号
            signals = self._calculate_signals(stock_data, date)
            
            # 2.2 执行交易
            trades = self._execute_trades(signals, date)
            
            # 2.3 更新持仓
            self.portfolio_manager.update(trades)
            
            # 2.4 记录状态
            self._record_portfolio_state(date)
        
        # 3. 返回结果
        return True
```

**关键点：**
- 逐日回测：按时间顺序模拟交易
- 状态管理：每日更新持仓和资金
- 完整记录：保存所有交易和持仓历史

---

## 🛠️ 常见开发任务

### 任务1：添加新的技术指标

**场景：想在信号生成中使用KDJ指标**

```python
# 1. 在 indicators/ 目录下创建新文件
# indicators/kdj.py

import talib
import pandas as pd

def calculate_kdj(data: pd.DataFrame, 
                  fastk_period: int = 9,
                  slowk_period: int = 3,
                  slowd_period: int = 3) -> pd.DataFrame:
    """
    计算KDJ指标
    
    Args:
        data: 包含high, low, close的DataFrame
        fastk_period: K值周期
        slowk_period: K平滑周期
        slowd_period: D平滑周期
    
    Returns:
        包含k, d, j列的DataFrame
    """
    # 计算K和D
    k, d = talib.STOCH(
        data['high'], 
        data['low'], 
        data['close'],
        fastk_period=fastk_period,
        slowk_period=slowk_period,
        slowd_period=slowd_period
    )
    
    # 计算J
    j = 3 * k - 2 * d
    
    return pd.DataFrame({'k': k, 'd': d, 'j': j}, index=data.index)

# 2. 在 DataProcessor 中添加计算
# data/data_processor.py

def calculate_indicators(self, data):
    # 现有指标...
    
    # 添加KDJ
    from indicators.kdj import calculate_kdj
    kdj = calculate_kdj(data)
    data['kdj_k'] = kdj['k']
    data['kdj_d'] = kdj['d']
    data['kdj_j'] = kdj['j']
    
    return data

# 3. 在 SignalGenerator 中使用
# strategy/signal_generator.py

def _calculate_kdj_score(self, data, date):
    """计算KDJ评分"""
    current = data.loc[date]
    
    # 超卖：K < 20, D < 20, J < 0
    if current['kdj_k'] < 20 and current['kdj_d'] < 20 and current['kdj_j'] < 0:
        return 1.0  # 买入信号
    
    # 超买：K > 80, D > 80, J > 100
    if current['kdj_k'] > 80 and current['kdj_d'] > 80 and current['kdj_j'] > 100:
        return 1.0  # 卖出信号
    
    return 0.0
```

### 任务2：修改信号生成逻辑

**场景：想改为4维全部满足才交易**

```python
# strategy/signal_generator.py

def generate_signal(self, data, date):
    # 1. 价值比过滤器
    if not self._check_value_ratio(data, date):
        return 'hold'
    
    # 2. 计算4维度评分
    scores = self._calculate_4d_scores(data, date)
    
    # 3. 修改判断逻辑：从3选2改为全部满足
    # 原来：if sum(scores.values()) >= 2:
    # 改为：
    if sum(scores.values()) >= 3:  # 全部3维都要满足
        if self._is_buy_signal(data, date):
            return 'buy'
        elif self._is_sell_signal(data, date):
            return 'sell'
    
    return 'hold'
```

### 任务3：添加新的数据源

**场景：想使用Tushare数据源**

```python
# 1. 在 data/data_fetcher.py 中添加新类
class TushareDataFetcher(DataFetcher):
    """Tushare数据获取器"""
    
    def __init__(self, token: str):
        import tushare as ts
        self.pro = ts.pro_api(token)
    
    def get_stock_data(self, code, start_date, end_date, period='weekly'):
        """从Tushare获取数据"""
        # 转换股票代码格式
        ts_code = f"{code}.SH" if code.startswith('6') else f"{code}.SZ"
        
        # 调用Tushare API
        df = self.pro.daily(
            ts_code=ts_code,
            start_date=start_date.replace('-', ''),
            end_date=end_date.replace('-', '')
        )
        
        # 标准化数据格式
        df = self._standardize_data_format(df)
        
        return df

# 2. 在 BacktestEngine 中使用
# backtest/backtest_engine.py

def __init__(self, config):
    # 根据配置选择数据源
    data_source = config.get('data_source', 'akshare')
    
    if data_source == 'tushare':
        token = config.get('tushare_token')
        self.data_fetcher = TushareDataFetcher(token)
    else:
        self.data_fetcher = AkshareDataFetcher()
```

### 任务4：自定义报告内容

**场景：想在报告中添加自定义指标**

```python
# backtest/enhanced_report_generator_integrated_fixed.py

def generate_report(self, backtest_results):
    # 现有报告生成逻辑...
    
    # 添加自定义指标
    custom_metrics = self._calculate_custom_metrics(backtest_results)
    
    # 替换到HTML模板
    html_content = html_content.replace(
        '{{custom_metric_1}}', 
        f"{custom_metrics['metric_1']:.2f}"
    )
    
    return html_content

def _calculate_custom_metrics(self, results):
    """计算自定义指标"""
    return {
        'metric_1': self._calculate_calmar_ratio(results),
        'metric_2': self._calculate_sortino_ratio(results),
    }
```

---

## 🏗️ 系统架构（阶段2更新）

### 服务层架构

系统采用**服务层架构**，通过`BacktestOrchestrator`协调各个服务完成回测：

```
BacktestOrchestrator (协调器)
    ├── DataService (数据服务)
    ├── SignalService (信号服务)
    ├── PortfolioService (投资组合服务)
    └── ReportService (报告服务)
```

**核心服务：**

1. **DataService** - 数据获取和处理
   - 从数据源获取股票数据
   - 计算技术指标
   - 管理数据缓存

2. **SignalService** - 信号生成
   - 4维信号分析
   - 信号评分和过滤
   - 信号跟踪记录

3. **PortfolioService** - 投资组合管理
   - 持仓管理
   - 交易执行
   - 资金管理

4. **ReportService** - 报告生成
   - HTML报告
   - CSV报告
   - 信号跟踪报告

---

## 🐛 调试技巧

### 1. 查看详细日志

```python
# 修改日志级别为DEBUG
# config/settings.py

LOGGING_CONFIG = {
    'level': 'DEBUG',  # 从INFO改为DEBUG
    ...
}
```

### 2. 打印中间数据

```python
# 在关键位置添加调试输出
# strategy/signal_generator.py

def _calculate_4d_scores(self, data, date):
    scores = {...}
    
    # 添加调试输出
    print(f"[DEBUG] {date} - 评分详情: {scores}")
    print(f"[DEBUG] RSI值: {data.loc[date, 'rsi']}")
    
    return scores
```

### 3. 使用断点调试

```python
# 在需要调试的地方添加断点
import pdb; pdb.set_trace()

# 或使用IDE的断点功能（推荐）
```

### 4. 单独测试模块

```python
# 创建测试脚本
# test_signal_generator.py

from strategy.signal_generator import SignalGenerator
import pandas as pd

# 准备测试数据
test_data = pd.DataFrame({...})

# 创建信号生成器
generator = SignalGenerator(config={})

# 测试信号生成
signal = generator.generate_signal(test_data, '2024-01-05')
print(f"生成信号: {signal}")
```

---

## 📚 推荐学习路径

### 第1周：熟悉系统

- [ ] 运行默认回测，查看报告
- [ ] 阅读 `architecture.md` 理解架构
- [ ] 阅读 `data_flow.md` 理解数据流
- [ ] 修改配置，运行不同场景的回测

### 第2周：理解核心逻辑

- [ ] 深入阅读 `signal_generator.py`
- [ ] 理解4维信号系统
- [ ] 阅读 `backtest_engine.py` 理解回测流程
- [ ] 尝试修改信号参数，观察结果变化

### 第3周：开始开发

- [ ] 添加新的技术指标
- [ ] 修改信号生成逻辑
- [ ] 优化某个模块的代码
- [ ] 提交第一个Pull Request

### 第4周：深入优化

- [ ] 参与架构优化讨论
- [ ] 实施优化计划的某个阶段
- [ ] 编写单元测试
- [ ] 改进文档

---

## 🔗 重要文档链接

### 必读文档
- **架构设计：** `architecture.md` - 理解系统整体架构
- **数据流说明：** `data_flow.md` - 理解数据如何流动
- **配置指南：** `configuration_guide.md` - 理解配置系统

### 参考文档
- **模块职责：** `module_responsibilities.md` - 各模块详细职责
- **优化计划：** `comprehensive_optimization_plan.md` - 系统优化路线图
- **系统设计：** `系统设计文档.md` - 策略详细说明

---

## ❓ 常见问题

### Q1: 首次运行很慢怎么办？

**A:** 首次运行需要下载历史数据，约3-5分钟。数据会缓存到 `data_cache/` 目录，后续运行会快很多。

### Q2: 如何清除缓存重新获取数据？

**A:** 删除 `data_cache/` 目录：
```bash
rm -rf data_cache/
python3 main.py
```

### Q3: TA-Lib安装失败怎么办？

**A:** TA-Lib需要C库支持，参考上文"环境准备"章节的详细安装说明。

### Q4: 如何测试单只股票？

**A:** 修改 `Input/portfolio_config.csv`，只保留一只股票，权重设为1.0。

### Q5: 报告在哪里？

**A:** 报告生成在 `reports/` 目录下，文件名包含时间戳。

### Q6: 如何修改RSI阈值？

**A:** RSI阈值在 `Input/sw2_rsi_threshold.csv` 中配置，按行业分类。

### Q7: 代码太复杂看不懂怎么办？

**A:** 
1. 先看本文档理解整体流程
2. 从 `main.py` 开始逐步深入
3. 使用调试工具单步执行
4. 向团队成员请教

### Q8: 想贡献代码应该从哪里开始？

**A:**
1. 阅读 `comprehensive_optimization_plan.md`
2. 选择一个待优化项
3. 创建分支开始开发
4. 提交Pull Request

---

## 💬 获取帮助

### 团队沟通
- **代码问题：** 在项目Issue中提问
- **架构讨论：** 参加团队技术会议
- **紧急问题：** 联系项目负责人

### 学习资源
- **量化交易：** 《量化投资：以Python为工具》
- **技术指标：** TA-Lib官方文档
- **Python数据分析：** pandas官方文档

---

## ✅ 上手检查清单

完成以下任务，说明你已经成功上手：

- [ ] 成功运行第一个回测
- [ ] 查看并理解HTML报告
- [ ] 修改股票池配置并运行
- [ ] 修改回测时间段并运行
- [ ] 阅读完 `architecture.md`
- [ ] 阅读完 `data_flow.md`
- [ ] 理解4维信号系统
- [ ] 能够解释主程序流程
- [ ] 添加一个简单的调试输出
- [ ] 成功运行一个自定义配置的回测

---

**欢迎加入中线轮动策略系统开发团队！** 🎉

如有任何问题，随时在团队中提问。

---

**文档版本历史：**
- v1.0 (2026-01-16) - 初始版本，阶段0快速上手指南创建
