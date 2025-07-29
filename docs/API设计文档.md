# API设计文档 - 中线轮动策略系统

## 1. 数据模块 API (data/)

### 1.1 数据获取器 (data_fetcher.py)

```python
class DataFetcher:
    """数据获取器基类"""
    
    def get_stock_data(self, code: str, start_date: str, end_date: str = None, 
                      period: str = 'weekly') -> pd.DataFrame:
        """
        获取股票历史数据
        
        Args:
            code: 股票代码 (如 '601088')
            start_date: 开始日期 ('YYYY-MM-DD')
            end_date: 结束日期 ('YYYY-MM-DD', None表示当前日期)
            period: 数据周期 ('daily', 'weekly', 'monthly')
            
        Returns:
            pd.DataFrame: 标准化的股票数据
            
        Raises:
            DataFetchError: 数据获取失败
        """
        pass
    
    def get_multiple_stocks_data(self, codes: List[str], start_date: str, 
                               end_date: str = None, period: str = 'weekly') -> Dict[str, pd.DataFrame]:
        """
        批量获取多只股票数据
        
        Args:
            codes: 股票代码列表
            start_date: 开始日期
            end_date: 结束日期
            period: 数据周期
            
        Returns:
            Dict[str, pd.DataFrame]: 股票代码到数据的映射
        """
        pass

class AkshareDataFetcher(DataFetcher):
    """Akshare数据获取器实现"""
    pass
```

### 1.2 数据处理器 (data_processor.py)

```python
class DataProcessor:
    """数据预处理器"""
    
    def validate_data(self, df: pd.DataFrame) -> Tuple[bool, List[str]]:
        """
        验证数据完整性
        
        Args:
            df: 原始数据
            
        Returns:
            Tuple[bool, List[str]]: (是否有效, 问题列表)
        """
        pass
    
    def clean_data(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        清洗数据（处理缺失值、异常值等）
        
        Args:
            df: 原始数据
            
        Returns:
            pd.DataFrame: 清洗后的数据
        """
        pass
    
    def resample_to_weekly(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        将日线数据重采样为周线数据
        
        Args:
            df: 日线数据
            
        Returns:
            pd.DataFrame: 周线数据
        """
        pass
```

### 1.3 智能数据存储器 (data_storage.py)

```python
class DataStorage:
    """智能数据存储管理器 - 支持增量缓存和智能数据获取"""
    
    def save_data(self, data: pd.DataFrame, code: str, period: str) -> bool:
        """
        保存数据到缓存
        
        Args:
            data: 股票数据
            code: 股票代码
            period: 数据周期
            
        Returns:
            bool: 是否保存成功
        """
        pass
    
    def load_data(self, code: str, period: str) -> Optional[pd.DataFrame]:
        """
        从缓存加载数据
        
        Args:
            code: 股票代码
            period: 数据周期
            
        Returns:
            Optional[pd.DataFrame]: 缓存的数据或None
        """
        pass
    
    def get_cache_date_range(self, code: str, period: str) -> Optional[Tuple[str, str]]:
        """
        获取缓存数据的日期范围
        
        Args:
            code: 股票代码
            period: 数据周期
            
        Returns:
            Optional[Tuple[str, str]]: (开始日期, 结束日期) 或 None
        """
        pass
    
    def get_missing_date_ranges(self, code: str, period: str, 
                              required_start: str, required_end: str) -> List[Tuple[str, str]]:
        """
        获取缺失的日期范围列表
        
        Args:
            code: 股票代码
            period: 数据周期
            required_start: 需要的开始日期
            required_end: 需要的结束日期
            
        Returns:
            List[Tuple[str, str]]: 缺失的日期范围列表
        """
        pass
    
    def merge_incremental_data(self, existing_data: pd.DataFrame, 
                             new_data: pd.DataFrame) -> pd.DataFrame:
        """
        合并增量数据到现有数据中
        
        Args:
            existing_data: 现有缓存数据
            new_data: 新获取的增量数据
            
        Returns:
            pd.DataFrame: 合并后的完整数据
        """
        pass
    
    def is_data_fresh(self, code: str, period: str, max_age_days: int = 1) -> bool:
        """
        检查缓存数据是否新鲜
        
        Args:
            code: 股票代码
            period: 数据周期
            max_age_days: 最大缓存天数
            
        Returns:
            bool: 数据是否新鲜
        """
        pass
```

### 1.4 缓存管理器 (cache_manager.py)

```python
class CacheManager:
    """缓存管理器 - 统一管理数据缓存策略"""
    
    def __init__(self, cache_dir: str = "data_cache"):
        """
        初始化缓存管理器
        
        Args:
            cache_dir: 缓存目录路径
        """
        pass
    
    def get_cache_stats(self) -> Dict[str, Any]:
        """
        获取缓存统计信息
        
        Returns:
            Dict[str, Any]: 缓存统计信息
        """
        pass
    
    def clear_cache(self, code: str = None, period: str = None) -> bool:
        """
        清理缓存
        
        Args:
            code: 股票代码（None表示全部）
            period: 数据周期（None表示全部）
            
        Returns:
            bool: 是否清理成功
        """
        pass
    
    def optimize_cache(self) -> Dict[str, int]:
        """
        优化缓存（删除过期数据等）
        
        Returns:
            Dict[str, int]: 优化统计信息
        """
        pass
```

## 2. 技术指标模块 API (indicators/)

### 2.1 趋势指标 (trend.py)

```python
def calculate_ema(data: pd.Series, period: int) -> pd.Series:
    """
    计算指数移动平均线
    
    Args:
        data: 价格序列
        period: 周期
        
    Returns:
        pd.Series: EMA值
    """
    pass

def is_ema_trending_up(ema: pd.Series, lookback: int = 2) -> bool:
    """
    判断EMA是否向上趋势
    
    Args:
        ema: EMA序列
        lookback: 回看周期数
        
    Returns:
        bool: 是否向上趋势
    """
    pass
```

### 2.2 动量指标 (momentum.py)

```python
def calculate_rsi(data: pd.Series, period: int = 14) -> pd.Series:
    """
    计算相对强弱指标
    
    Args:
        data: 价格序列
        period: 计算周期
        
    Returns:
        pd.Series: RSI值
    """
    pass

def calculate_macd(data: pd.Series, fast: int = 12, slow: int = 26, 
                  signal: int = 9) -> Dict[str, pd.Series]:
    """
    计算MACD指标
    
    Args:
        data: 价格序列
        fast: 快线周期
        slow: 慢线周期
        signal: 信号线周期
        
    Returns:
        Dict[str, pd.Series]: {'dif': DIF线, 'dea': DEA线, 'hist': 柱状图}
    """
    pass
```

### 2.3 波动率指标 (volatility.py)

```python
def calculate_bollinger_bands(data: pd.Series, period: int = 20, 
                            std_dev: float = 2.0) -> Dict[str, pd.Series]:
    """
    计算布林带
    
    Args:
        data: 价格序列
        period: 计算周期
        std_dev: 标准差倍数
        
    Returns:
        Dict[str, pd.Series]: {'upper': 上轨, 'middle': 中轨, 'lower': 下轨}
    """
    pass
```

### 2.4 背离检测 (divergence.py)

```python
def detect_rsi_divergence(price: pd.Series, rsi: pd.Series, 
                         lookback: int = 13) -> Dict[str, bool]:
    """
    检测RSI背离
    
    Args:
        price: 价格序列
        rsi: RSI序列
        lookback: 回溯周期
        
    Returns:
        Dict[str, bool]: {'top_divergence': 顶背离, 'bottom_divergence': 底背离}
    """
    pass
```

## 3. 策略模块 API (strategy/)

### 3.1 信号生成器 (signal_generator.py)

```python
class SignalGenerator:
    """信号生成器 - 集成行业信息缓存优化"""
    
    def __init__(self, config: dict):
        """
        初始化信号生成器
        
        Args:
            config: 策略参数配置
        """
        # 初始化行业信息缓存
        self._industry_cache = {}
        self._industry_rules_cache = {}
        pass
    
    def _get_stock_industry_cached(self, stock_code: str) -> str:
        """
        获取股票行业信息（带缓存）
        
        Args:
            stock_code: 股票代码
            
        Returns:
            str: 行业名称
        """
        pass
    
    def _get_industry_rules_cached(self, industry: str) -> Dict:
        """
        获取行业规则（带缓存）
        
        Args:
            industry: 行业名称
            
        Returns:
            Dict: 行业规则
        """
        pass
    
    def get_cache_stats(self) -> Dict[str, int]:
        """
        获取行业缓存统计信息
        
        Returns:
            Dict[str, int]: {
                'industry_cache_size': 行业信息缓存数量,
                'industry_rules_cache_size': 行业规则缓存数量
            }
        """
        pass
    
    def generate_signals(self, data: pd.DataFrame) -> Dict[str, Any]:
        """
        生成买卖信号
        
        Args:
            data: 包含所有技术指标的数据
            
        Returns:
            Dict[str, Any]: {
                'sell_score': int,      # 卖出评分 (0-3)
                'buy_score': int,       # 买入评分 (0-3)
                'sell_signal': bool,    # 卖出信号
                'buy_signal': bool,     # 买入信号
                'conditions': dict      # 各条件详情
            }
        """
        pass
    
    def calculate_all_indicators(self, data: pd.DataFrame) -> pd.DataFrame:
        """
        计算所有技术指标
        
        Args:
            data: 原始价格数据
            
        Returns:
            pd.DataFrame: 包含所有指标的数据
        """
        pass
```

### 3.2 轮动引擎 (rotation_engine.py)

```python
class RotationEngine:
    """轮动引擎"""
    
    def __init__(self, stock_pool: dict, config: dict):
        """
        初始化轮动引擎
        
        Args:
            stock_pool: 股票池配置
            config: 策略配置
        """
        pass
    
    def analyze_rotation_opportunities(self, date: str) -> Dict[str, Any]:
        """
        分析轮动机会
        
        Args:
            date: 分析日期
            
        Returns:
            Dict[str, Any]: {
                'sell_candidates': List[str],    # 卖出候选
                'buy_candidates': List[str],     # 买入候选
                'rotation_pairs': List[tuple],   # 轮动对 (卖出股票, 买入股票)
                'cash_operations': dict          # 现金操作
            }
        """
        pass
    
    def generate_trading_instructions(self, analysis_result: dict) -> List[Dict[str, Any]]:
        """
        生成交易指令
        
        Args:
            analysis_result: 分析结果
            
        Returns:
            List[Dict[str, Any]]: 交易指令列表
        """
        pass
```

## 4. 回测模块 API (backtest/)

### 4.1 回测引擎 (backtest_engine.py)

```python
class BacktestEngine:
    """回测引擎"""
    
    def __init__(self, config: dict):
        """
        初始化回测引擎
        
        Args:
            config: 回测配置
        """
        pass
    
    def run_backtest(self, start_date: str, end_date: str) -> Dict[str, Any]:
        """
        运行回测
        
        Args:
            start_date: 回测开始日期
            end_date: 回测结束日期
            
        Returns:
            Dict[str, Any]: 回测结果
        """
        pass
    
    def simulate_trading(self, signals: Dict[str, Any], date: str) -> Dict[str, Any]:
        """
        模拟交易执行
        
        Args:
            signals: 交易信号
            date: 交易日期
            
        Returns:
            Dict[str, Any]: 交易执行结果
        """
        pass
    
    def _extract_detailed_indicators(self, stock_code: str, current_date: datetime, 
                                   signal_result: Dict = None) -> Dict:
        """
        从信号生成器结果中提取详细的技术指标数据
        
        Args:
            stock_code: 股票代码
            current_date: 当前日期
            signal_result: 信号生成结果
            
        Returns:
            Dict: 技术指标字典
        """
        pass
    
    def _extract_signal_details(self, signal_result: Dict, trade_type: str) -> Dict:
        """
        提取信号详情和各维度状态
        
        Args:
            signal_result: 信号生成结果
            trade_type: 交易类型 ('BUY' | 'SELL')
            
        Returns:
            Dict: 信号详情字典
        """
        pass
```

### 4.2 绩效分析 (performance.py)

```python
class PerformanceAnalyzer:
    """绩效分析器"""
    
    def calculate_returns(self, portfolio_values: pd.Series) -> Dict[str, float]:
        """
        计算收益率指标
        
        Args:
            portfolio_values: 组合价值序列
            
        Returns:
            Dict[str, float]: 收益率指标
        """
        pass
    
    def calculate_risk_metrics(self, returns: pd.Series) -> Dict[str, float]:
        """
        计算风险指标
        
        Args:
            returns: 收益率序列
            
        Returns:
            Dict[str, float]: 风险指标
        """
        pass
    
    def generate_performance_report(self, backtest_result: dict) -> Dict[str, Any]:
        """
        生成绩效报告
        
        Args:
            backtest_result: 回测结果
            
        Returns:
            Dict[str, Any]: 完整绩效报告
        """
        pass
```

## 5. CSV配置管理模块 API (config/)

### 5.1 CSV配置加载器 (csv_config_loader.py)

```python
def load_portfolio_config(csv_path: str = 'Input/portfolio_config.csv') -> Dict[str, float]:
    """
    从CSV文件加载投资组合配置
    
    Args:
        csv_path: CSV文件路径
        
    Returns:
        Dict[str, float]: 初始持仓配置 {股票代码: 权重}
        
    Raises:
        FileNotFoundError: 配置文件不存在
        ValueError: 权重总和不等于1.0
        UnicodeDecodeError: 文件编码错误
    """
    pass

def load_backtest_settings(csv_path: str = 'Input/Becktest_settings.csv') -> Dict[str, Any]:
    """
    从CSV文件加载回测设置
    
    Args:
        csv_path: CSV文件路径
        
    Returns:
        Dict[str, Any]: 回测设置参数
        
    Raises:
        FileNotFoundError: 设置文件不存在
        ValueError: 缺少必要参数
        DateFormatError: 日期格式错误
    """
    pass

def create_csv_config() -> Dict[str, Any]:
    """
    创建基于CSV文件的完整回测配置
    
    Returns:
        Dict[str, Any]: 完整的回测配置
        
    Raises:
        ConfigurationError: 配置创建失败
    """
    pass

def validate_csv_config() -> bool:
    """
    验证CSV配置文件的有效性
    
    Returns:
        bool: 配置是否有效
        
    Raises:
        ValidationError: 验证失败
    """
    pass
```

### 5.2 行业RSI配置加载器 (industry_rsi_loader.py)

```python
def load_industry_rsi_thresholds(csv_path: str = 'Input/industry_rsi_thresholds.csv') -> Dict[str, Dict]:
    """
    从CSV文件加载行业RSI阈值配置
    
    Args:
        csv_path: CSV文件路径
        
    Returns:
        Dict[str, Dict]: 行业RSI配置 {行业名称: {阈值配置}}
        
    Raises:
        FileNotFoundError: 配置文件不存在
        ValueError: 阈值配置无效
    """
    pass

def get_industry_rsi_config(industry: str) -> Dict[str, Any]:
    """
    获取特定行业的RSI配置
    
    Args:
        industry: 行业名称
        
    Returns:
        Dict[str, Any]: 行业RSI配置
        
    Raises:
        IndustryNotFoundError: 行业未找到
    """
    pass
```

### 5.3 配置验证器 (config_validator.py)

```python
class ConfigValidator:
    """配置验证器"""
    
    def validate_portfolio_config(self, config_data: pd.DataFrame) -> Tuple[bool, List[str]]:
        """
        验证投资组合配置
        
        Args:
            config_data: 配置数据
            
        Returns:
            Tuple[bool, List[str]]: (是否有效, 错误列表)
        """
        pass
    
    def validate_backtest_settings(self, settings_data: pd.DataFrame) -> Tuple[bool, List[str]]:
        """
        验证回测设置
        
        Args:
            settings_data: 设置数据
            
        Returns:
            Tuple[bool, List[str]]: (是否有效, 错误列表)
        """
        pass
    
    def validate_weight_sum(self, weights: Dict[str, float], tolerance: float = 0.01) -> bool:
        """
        验证权重总和
        
        Args:
            weights: 权重字典
            tolerance: 容差
            
        Returns:
            bool: 权重总和是否有效
        """
        pass
    
    def validate_date_format(self, date_str: str) -> bool:
        """
        验证日期格式
        
        Args:
            date_str: 日期字符串
            
        Returns:
            bool: 日期格式是否有效
        """
        pass
```

## 6. 报告生成模块 API (backtest/)

### 5.1 增强版报告生成器 (enhanced_report_generator.py)

```python
class EnhancedReportGenerator:
    """增强版报告生成器"""
    
    def __init__(self, output_dir: str = "reports"):
        """
        初始化报告生成器
        
        Args:
            output_dir: 输出目录
        """
        pass
    
    def generate_complete_report(self, backtest_results: Dict, 
                               strategy_params: Dict) -> Dict[str, str]:
        """
        生成完整报告套件
        
        Args:
            backtest_results: 回测结果
            strategy_params: 策略参数
            
        Returns:
            Dict[str, str]: 文件类型到路径的映射
            {
                'html_report': str,           # HTML报告路径
                'detailed_csv': str,          # 详细交易记录CSV路径
                'basic_csv': str,             # 基础交易记录CSV路径
                'signal_analysis': str,       # 信号分析报告路径
                'portfolio_summary': str,     # 投资组合摘要路径
                'performance_metrics': str    # 绩效指标路径
            }
        """
        pass
    
    def generate_enhanced_html_report(self, backtest_results: Dict,
                                    strategy_params: Dict,
                                    weekly_data_dict: Dict = None) -> str:
        """
        生成增强版HTML报告
        
        Args:
            backtest_results: 回测结果
            strategy_params: 策略参数
            weekly_data_dict: 周线数据字典
            
        Returns:
            str: HTML报告文件路径
        """
        pass
    
    def export_detailed_trading_records_csv(self, transaction_history: pd.DataFrame) -> str:
        """
        导出详细交易记录CSV文件
        
        Args:
            transaction_history: 交易历史数据
            
        Returns:
            str: CSV文件路径
        """
        pass
    
    def export_basic_trading_records_csv(self, transaction_history: pd.DataFrame) -> str:
        """
        导出基础交易记录CSV文件
        
        Args:
            transaction_history: 交易历史数据
            
        Returns:
            str: CSV文件路径
        """
        pass
    
    def generate_signal_analysis_report(self, backtest_results: Dict) -> str:
        """
        生成信号分析报告
        
        Args:
            backtest_results: 回测结果
            
        Returns:
            str: 信号分析报告文件路径
        """
        pass
```

### 5.2 详细交易记录数据结构

```python
# 详细交易记录CSV字段定义
DETAILED_TRADING_RECORD_FIELDS = {
    # 基础交易信息
    '日期': str,                    # 交易日期 (YYYY-MM-DD)
    '交易类型': str,                # BUY/SELL
    '股票代码': str,                # 6位股票代码
    '股票数量': int,                # 交易股数
    '交易价格': float,              # 成交价格
    '交易金额': float,              # 交易总金额
    '手续费': float,                # 交易手续费
    
    # 技术指标数据
    '收盘价': float,                # 当日收盘价
    'EMA20': float,                # 20周指数移动平均
    'EMA60': float,                # 60周指数移动平均
    'RSI14': float,                # 14周相对强弱指数
    'MACD_DIF': float,             # MACD快线
    'MACD_DEA': float,             # MACD慢线
    'MACD_HIST': float,            # MACD柱状图
    '布林上轨': float,              # 布林带上轨
    '布林中轨': float,              # 布林带中轨
    '布林下轨': float,              # 布林带下轨
    '成交量': int,                  # 当日成交量
    '量能倍数': float,              # 成交量相对均值倍数
    '布林带位置': str,              # 价格在布林带中的位置
    
    # 4维信号分析
    '趋势过滤器': str,              # 满足/不满足
    '超买超卖信号': str,            # 满足/不满足
    '动能确认': str,                # 满足/不满足
    '极端价格量能': str,            # 满足/不满足
    '满足维度数': str,              # X/4格式
    '信号强度评分': int,            # 0-3分
    '触发原因': str                 # 交易触发的具体原因
}
```

### 5.3 投资组合管理器扩展 API

```python
class PortfolioManager:
    """投资组合管理器"""
    
    def execute_buy(self, stock_code: str, shares: int, price: float,
                   transaction_cost: float, date: datetime, reason: str = "",
                   technical_indicators: dict = None, signal_details: dict = None) -> bool:
        """
        执行买入交易（带技术指标记录）
        
        Args:
            stock_code: 股票代码
            shares: 买入股数
            price: 买入价格
            transaction_cost: 交易成本
            date: 交易日期
            reason: 交易原因
            technical_indicators: 技术指标数值
            signal_details: 信号判断详情
            
        Returns:
            bool: 是否执行成功
        """
        pass
    
    def execute_sell(self, stock_code: str, shares: int, price: float,
                    transaction_cost: float, date: datetime, reason: str = "",
                    technical_indicators: dict = None, signal_details: dict = None) -> bool:
        """
        执行卖出交易（带技术指标记录）
        
        Args:
            stock_code: 股票代码
            shares: 卖出股数
            price: 卖出价格
            transaction_cost: 交易成本
            date: 交易日期
            reason: 交易原因
            technical_indicators: 技术指标数值
            signal_details: 信号判断详情
            
        Returns:
            bool: 是否执行成功
        """
        pass
    
    def execute_rotation_with_indicators(self, sell_stock: str, buy_stock: str, 
                                       rotation_percentage: float, current_prices: Dict[str, float],
                                       transaction_costs: Dict[str, float], date: datetime,
                                       sell_indicators: Dict, sell_signal_details: Dict,
                                       buy_indicators: Dict, buy_signal_details: Dict) -> Tuple[bool, str]:
        """
        执行轮动交易（带技术指标记录）
        
        Args:
            sell_stock: 卖出股票代码
            buy_stock: 买入股票代码
            rotation_percentage: 轮动比例
            current_prices: 当前价格字典
            transaction_costs: 交易成本字典
            date: 交易日期
            sell_indicators: 卖出股票技术指标
            sell_signal_details: 卖出信号详情
            buy_indicators: 买入股票技术指标
            buy_signal_details: 买入信号详情
            
        Returns:
            Tuple[bool, str]: (是否成功, 执行消息)
        """
        pass
```

## 6. 异常处理

### 6.1 自定义异常类

```python
class RotationStrategyError(Exception):
    """策略系统基础异常"""
    pass

class DataFetchError(RotationStrategyError):
    """数据获取异常"""
    pass

class IndicatorCalculationError(RotationStrategyError):
    """指标计算异常"""
    pass

class SignalGenerationError(RotationStrategyError):
    """信号生成异常"""
    pass

class BacktestError(RotationStrategyError):
    """回测异常"""
    pass

class ReportGenerationError(RotationStrategyError):
    """报告生成异常"""
    pass
```

## 7. 通用工具函数

### 7.1 日期处理

```python
def get_trading_dates(start_date: str, end_date: str, frequency: str = 'W') -> List[str]:
    """获取交易日期列表"""
    pass

def is_trading_day(date: str) -> bool:
    """判断是否为交易日"""
    pass
```

### 7.2 数据验证

```python
def validate_stock_code(code: str) -> bool:
    """验证股票代码格式"""
    pass

def validate_date_format(date: str) -> bool:
    """验证日期格式"""
    pass

def validate_trading_record(record: Dict) -> Tuple[bool, List[str]]:
    """验证交易记录完整性"""
    pass
```

### 7.3 文件处理

```python
def ensure_utf8_encoding(file_path: str) -> bool:
    """确保文件使用UTF-8编码"""
    pass

def generate_timestamp_filename(base_name: str, extension: str) -> str:
    """生成带时间戳的文件名"""
    pass
```

## 8. 新增功能说明

### 8.1 详细交易记录导出

系统现在支持导出包含完整技术指标的详细交易记录CSV文件，包含：

1. **完整的交易信息**：日期、类型、代码、数量、价格、金额、手续费
2. **技术指标快照**：交易时刻的所有技术指标数值
3. **4维信号分析**：趋势过滤器、超买超卖、动能确认、极端价格量能
4. **信号强度评分**：0-3分的量化评分
5. **触发原因说明**：详细的交易触发原因

### 8.2 中文字段支持

- 所有CSV文件都使用UTF-8编码
- 支持中文字段名，便于中文用户阅读
- 提供中英文字段映射功能

### 8.3 报告生成增强

- 支持生成多种格式的报告文件
- 自动生成带时间戳的文件名
- 提供完整的报告套件（HTML + 多个CSV文件）

---

**API设计原则**：
- 所有函数都应包含详细的文档字符串
- 参数类型使用类型提示
- 异常情况应明确定义和处理
- 返回值格式应保持一致性
- 支持中文字段和UTF-8编码（新增）
- 提供详细的技术指标记录功能（新增）