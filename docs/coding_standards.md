# 代码规范文档

## 📋 文档概述

**版本**: v1.0  
**创建日期**: 2026-01-16  
**适用范围**: 中线轮动策略系统所有Python代码

本文档定义了项目的代码规范，确保代码的一致性、可读性和可维护性。

---

## 📦 Import规范

### 导入顺序

所有Python文件的import必须按以下顺序组织，各组之间用空行分隔：

```python
# 1. 标准库 (Python内置模块)
import os
import sys
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple, Any

# 2. 第三方库 (通过pip安装的包)
import pandas as pd
import numpy as np
import logging
import talib

# 3. 项目内部模块 - 按层级导入
# 3.1 配置层
from config.config_manager import ConfigManager
from config.path_manager import PathManager

# 3.2 服务层
from services.data_service import DataService
from services.signal_service import SignalService
from services.portfolio_service import PortfolioService
from services.report_service import ReportService

# 3.3 业务逻辑层
from strategy.signal_generator import SignalGenerator
from backtest.portfolio_manager import PortfolioManager

# 3.4 数据层
from data.data_fetcher import DataFetcher
from data.data_processor import DataProcessor

# 3.5 工具层
from utils.logger import setup_logger
```

### 导入规则

#### ✅ 推荐做法

1. **使用显式导入**
   ```python
   # ✅ 好
   from config.config_manager import ConfigManager
   from typing import Dict, List, Optional
   
   # ✅ 好 - 标准库可以整体导入
   import os
   import sys
   ```

2. **相对导入仅用于包内**
   ```python
   # ✅ 好 - 在services包内
   from .data_service import DataService
   from .signal_service import SignalService
   ```

3. **类型提示导入**
   ```python
   # ✅ 好
   from typing import Dict, List, Optional, TYPE_CHECKING
   
   if TYPE_CHECKING:
       from services.data_service import DataService
   ```

#### ❌ 禁止做法

1. **禁止使用通配符导入**
   ```python
   # ❌ 错误
   from module import *
   
   # ✅ 正确
   from module import function1, function2, Class1
   ```

2. **禁止导入未使用的模块**
   ```python
   # ❌ 错误 - numpy未使用
   import numpy as np
   import pandas as pd
   
   df = pd.DataFrame()  # 只用了pandas
   ```

3. **禁止循环导入**
   ```python
   # ❌ 错误
   # module_a.py
   from module_b import ClassB
   
   # module_b.py
   from module_a import ClassA  # 循环依赖！
   ```

4. **禁止混乱的导入顺序**
   ```python
   # ❌ 错误 - 顺序混乱
   from services.data_service import DataService
   import pandas as pd
   import os
   from config.config_manager import ConfigManager
   import numpy as np
   ```

### 导入别名规范

#### 标准别名

```python
# 数据处理
import pandas as pd
import numpy as np

# 日期时间
from datetime import datetime as dt
from datetime import timedelta as td

# 日志
import logging
logger = logging.getLogger(__name__)

# 类型提示
from typing import Dict, List, Optional, Tuple, Any
```

#### 避免的别名

```python
# ❌ 避免 - 不清晰的别名
import pandas as p
import numpy as n
from services.data_service import DataService as DS

# ✅ 推荐 - 清晰的别名或完整名称
import pandas as pd
import numpy as np
from services.data_service import DataService
```

---

## 🏗️ 模块依赖层级

### 依赖方向规则

**原则**: 依赖只能向下，不能向上或横向

```
┌─────────────────────────────────────┐
│  Level 1: 应用入口                   │
│  main.py, run_backtest.py          │
└─────────────────────────────────────┘
              ↓ 依赖
┌─────────────────────────────────────┐
│  Level 2: 服务层                     │
│  services/                          │
└─────────────────────────────────────┘
              ↓ 依赖
┌─────────────────────────────────────┐
│  Level 3: 业务逻辑层                 │
│  strategy/, backtest/               │
└─────────────────────────────────────┘
              ↓ 依赖
┌─────────────────────────────────────┐
│  Level 4: 数据层                     │
│  data/, indicators/                 │
└─────────────────────────────────────┘
              ↓ 依赖
┌─────────────────────────────────────┐
│  Level 5: 基础设施层                 │
│  config/, utils/                    │
└─────────────────────────────────────┘
```

### 允许的依赖

- ✅ Level 1 → Level 2, 3, 4, 5
- ✅ Level 2 → Level 3, 4, 5
- ✅ Level 3 → Level 4, 5
- ✅ Level 4 → Level 5
- ✅ Level 5 → 无依赖（仅依赖标准库和第三方库）

### 禁止的依赖

- ❌ 向上依赖（如Level 5 → Level 4）
- ❌ 同级横向依赖（如strategy → backtest）
- ❌ 循环依赖

---

## 📝 命名规范

### 文件和模块命名

```python
# ✅ 好 - 小写+下划线
data_service.py
signal_generator.py
portfolio_manager.py

# ❌ 避免 - 驼峰命名
DataService.py
SignalGenerator.py
```

### 类命名

```python
# ✅ 好 - 大驼峰（PascalCase）
class DataService:
    pass

class SignalGenerator:
    pass

class BacktestOrchestrator:
    pass
```

### 函数和变量命名

```python
# ✅ 好 - 小写+下划线
def calculate_signals(data: pd.DataFrame) -> Dict:
    stock_code = "601088"
    total_return = 0.0
    return {}

# ❌ 避免 - 驼峰命名
def calculateSignals(data):
    stockCode = "601088"
    totalReturn = 0.0
```

### 常量命名

```python
# ✅ 好 - 全大写+下划线
MAX_POSITION_SIZE = 0.2
DEFAULT_CASH_RATIO = 0.1
RSI_PERIOD = 14

# ❌ 避免
maxPositionSize = 0.2
default_cash_ratio = 0.1
```

---

## 📖 文档字符串规范

### 模块文档

```python
"""
模块简短描述

详细描述模块的功能、用途和主要类/函数。
"""
```

### 类文档

```python
class DataService:
    """
    数据服务类
    
    负责所有数据获取、缓存和处理功能。
    
    Attributes:
        config: 配置管理器实例
        data_fetcher: 数据获取器
        data_processor: 数据处理器
    
    Example:
        >>> service = DataService(config)
        >>> service.initialize()
        >>> data = service.get_stock_data('601088', '2024-01-01', '2024-12-31')
    """
```

### 函数文档

```python
def calculate_signals(
    stock_data: Dict[str, pd.DataFrame],
    date: str
) -> Dict[str, SignalResult]:
    """
    生成交易信号
    
    Args:
        stock_data: 股票数据字典，键为股票代码，值为DataFrame
        date: 当前日期，格式'YYYY-MM-DD'
    
    Returns:
        信号结果字典，键为股票代码，值为SignalResult对象
    
    Raises:
        ValueError: 如果日期格式不正确
        KeyError: 如果股票数据缺失必要字段
    
    Example:
        >>> signals = calculate_signals(stock_data, '2024-01-15')
        >>> print(signals['601088'].signal_type)
        'BUY'
    """
```

---

## 🔧 代码质量工具

### 推荐工具

1. **autoflake** - 清理未使用的import
   ```bash
   pip install autoflake
   autoflake --in-place --remove-all-unused-imports -r .
   ```

2. **isort** - 自动排序import
   ```bash
   pip install isort
   isort . --profile black
   ```

3. **black** - 代码格式化
   ```bash
   pip install black
   black . --line-length 100
   ```

4. **flake8** - 代码检查
   ```bash
   pip install flake8
   flake8 . --max-line-length 100
   ```

5. **pydeps** - 依赖关系可视化
   ```bash
   pip install pydeps
   pydeps . --max-bacon 2 -o dependency_graph.svg
   ```

### 配置文件

**pyproject.toml**:
```toml
[tool.black]
line-length = 100
target-version = ['py38']

[tool.isort]
profile = "black"
line_length = 100
```

---

## ✅ 代码审查清单

### Import检查
- [ ] 按标准顺序组织（标准库→第三方→项目内部）
- [ ] 无未使用的import
- [ ] 无通配符导入
- [ ] 无循环依赖

### 命名检查
- [ ] 类名使用大驼峰
- [ ] 函数/变量使用小写+下划线
- [ ] 常量使用全大写+下划线
- [ ] 命名清晰表达意图

### 文档检查
- [ ] 所有公开类有文档字符串
- [ ] 所有公开函数有文档字符串
- [ ] 文档包含参数、返回值、异常说明
- [ ] 复杂逻辑有注释说明

### 依赖检查
- [ ] 依赖方向正确（只向下）
- [ ] 无循环依赖
- [ ] 无不必要的依赖

---

## 📚 参考资源

- [PEP 8 -- Style Guide for Python Code](https://www.python.org/dev/peps/pep-0008/)
- [Google Python Style Guide](https://google.github.io/styleguide/pyguide.html)
- [Clean Code in Python](https://github.com/zedr/clean-code-python)

---

**文档版本**: v1.0  
**最后更新**: 2026-01-16  
**维护者**: 项目团队
