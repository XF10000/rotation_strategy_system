"""
信号生成器
严格按照设计文档实现4维度评分系统的信号生成逻辑
"""

import logging
import os
import sys
from datetime import datetime
from typing import Dict

import pandas as pd

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from config.comprehensive_industry_rules import get_comprehensive_industry_rules
from config.stock_industry_mapping import get_stock_industry
from indicators.divergence import detect_macd_divergence, detect_rsi_divergence
from indicators.momentum import calculate_macd, calculate_rsi
from indicators.trend import calculate_ema, detect_ema_trend
from indicators.volatility import calculate_bollinger_bands
from models.signal_result import SignalResult
from strategy.exceptions import InsufficientDataError, SignalGenerationError
from utils.industry_classifier import get_stock_industry_auto

logger = logging.getLogger(__name__)

class SignalGenerator:
    """
    4维度信号生成器
    严格按照设计文档实现中线轮动策略的信号生成逻辑
    
    信号规则（共4维，硬性前提 + 3选2）：
    1. 趋势过滤器（硬性）：卖出信号=20周EMA方向向下或走平，买入信号=20周EMA方向向上或走平
    2. 超买/超卖：卖出信号=14周RSI>70且出现顶背离，买入信号=14周RSI<30且出现底背离
    3. 动能确认：卖出信号=MACD红色柱体连续2根缩短或MACD柱体已为绿色或DIF死叉DEA，买入信号=MACD绿色柱体连续2根缩短或MACD柱体已为红色或DIF金叉DEA
    4. 极端价格+量能：卖出信号=收盘价≥布林上轨且本周量≥4周均量×1.3，买入信号=收盘价≤布林下轨且本周量≥4周均量×0.8
    
    EMA趋势定义（使用线性回归法）：
    - 方向向上：线性回归斜率为正且相对斜率绝对值 >= 0.003（0.3%）
    - 方向向下：线性回归斜率为负且相对斜率绝对值 >= 0.003（0.3%）
    - 走平：最近8周EMA的相对斜率绝对值 < 0.003（0.3%）
    
    触发逻辑：先满足「趋势过滤器」→ 再在其余3条里至少满足2条 → 生成信号
    """
    
    def __init__(self, config: Dict, dcf_values: Dict[str, float] = None, 
                 rsi_thresholds: Dict[str, Dict[str, float]] = None,
                 stock_industry_map: Dict[str, Dict[str, str]] = None):
        """
        初始化信号生成器
        
        Args:
            config: 配置参数
            dcf_values: DCF估值数据字典 {股票代码: DCF估值}
            rsi_thresholds: 行业RSI阈值数据字典 {行业代码: RSI阈值信息}
            stock_industry_map: 股票-行业映射字典 {股票代码: 行业信息}
        """
        self.config = config
        self.logger = logging.getLogger("strategy.SignalGenerator")
        
        # 存储DCF估值数据
        self.dcf_values = dcf_values or {}
        
        # 存储动态RSI阈值数据
        self.rsi_thresholds = rsi_thresholds or {}
        
        # 存储股票-行业映射数据
        self.stock_industry_map = stock_industry_map or {}
        
        # 默认参数
        self.default_params = {
            'ema_period': 20,           # EMA周期
            'rsi_period': 14,           # RSI周期
            'rsi_overbought': 70,       # RSI超买阈值
            'rsi_oversold': 30,         # RSI超卖阈值
            'macd_fast': 12,            # MACD快线
            'macd_slow': 26,            # MACD慢线
            'macd_signal': 9,           # MACD信号线
            'bb_period': 20,            # 布林带周期
            'bb_std': 2,                # 布林带标准差倍数
            'volume_ma_period': 4,      # 成交量均线周期
            'volume_buy_ratio': 0.8,    # 买入成交量比例
            'volume_sell_ratio': 1.3,   # 卖出成交量比例
            'min_data_length': 120,      # 最小数据长度
        }
        
        # 合并配置
        self.params = {**self.default_params, **config}
        
        # 确保价值比率阈值存在 (从配置加载，提供默认值)
        self.params.setdefault('value_ratio_sell_threshold', 0.8) # 从配置加载，默认为0.8
        self.params.setdefault('value_ratio_buy_threshold', 0.7)  # 从配置加载，默认为0.7
        
        # 添加行业信息缓存
        self._industry_cache = {}
        self._industry_rules_cache = {}
        
        self.logger.info("信号生成器初始化完成")
        self.logger.info("行业信息缓存已启用，将显著提升回测性能")
        
        # 记录数据加载状态
        if self.dcf_values:
            self.logger.info(f"📊 已加载 {len(self.dcf_values)} 只股票的DCF估值数据")
            self.logger.info("将使用价值比过滤器 (V1.1策略)")
        else:
            self.logger.warning("未提供DCF估值数据，将回退到EMA趋势过滤器")
            
        if self.rsi_thresholds:
            self.logger.info(f"📈 已加载 {len(self.rsi_thresholds)} 个行业的动态RSI阈值")
            self.logger.info("将使用行业特定的动态RSI阈值进行超买超卖判断")
        else:
            self.logger.warning("未提供动态RSI阈值数据，将使用固定阈值(70/30)")
            
        if self.stock_industry_map:
            self.logger.info(f"🏭 已加载 {len(self.stock_industry_map)} 只股票的行业映射")
        else:
            self.logger.warning("未提供股票-行业映射数据，动态RSI阈值功能将无法使用")
    
    def generate_signal(self, stock_code: str, data: pd.DataFrame) -> Dict:
        """
        生成单只股票的交易信号
        
        Args:
            stock_code: 股票代码
            data: 股票数据 (OHLCV)
            
        Returns:
            Dict: 信号结果
        """
        try:
            # 数据验证 - 使用分层标准化策略的最低稳定要求
            if data is None or data.empty:
                raise InsufficientDataError(f"股票 {stock_code} 数据为空")
            
            # 使用分层标准化策略的最低稳定要求（60条）
            # 这与技术指标计算中的minimum_stable_length保持一致
            minimum_stable_length = 60
            if len(data) < minimum_stable_length:
                raise InsufficientDataError(
                    f"股票 {stock_code} 数据不足，需要至少 {minimum_stable_length} 条记录以确保技术指标稳定计算"
                )
            
            # 计算技术指标
            indicators = self._calculate_indicators(data)
            
            # 4维度评分 - 传入股票代码以支持行业特定阈值
            scores, actual_rsi_thresholds = self._calculate_4d_scores(data, indicators, stock_code)
            
            # 获取当前价格和DCF估值
            current_price = data['close'].iloc[-1]
            dcf_value = self.dcf_values.get(stock_code) if stock_code else None
            
            # 获取行业信息
            industry = None
            if actual_rsi_thresholds and 'industry_name' in actual_rsi_thresholds:
                industry = actual_rsi_thresholds['industry_name']
            
            # 生成最终信号
            signal_result = self._generate_final_signal(
                stock_code, scores, indicators, actual_rsi_thresholds,
                dcf_value, current_price, industry
            )
            
            # 将重新计算的技术指标添加到结果中
            extracted_indicators = self._extract_current_indicators(data, indicators)
            self.logger.debug(f"提取的技术指标: {extracted_indicators}")
            signal_result['technical_indicators'] = extracted_indicators
            
            # 添加价值比信息供动态仓位管理器使用
            current_price = data['close'].iloc[-1]
            dcf_value = self.dcf_values.get(stock_code) if stock_code else None
            if dcf_value and dcf_value > 0:
                value_price_ratio = current_price / dcf_value
                signal_result['value_price_ratio'] = value_price_ratio
                signal_result['dcf_value'] = dcf_value
                signal_result['current_price'] = current_price
                self.logger.debug(f"股票 {stock_code} 价值比: {value_price_ratio:.3f} (价格{current_price:.2f}/DCF{dcf_value:.2f})")
            
            # 🆕 新增：为BUY/SELL信号收集详细信息（信号跟踪功能）
            if signal_result['signal'] in ['BUY', 'SELL']:
                detailed_signal_info = self._collect_detailed_signal_info(
                    stock_code, data, indicators, scores, signal_result, actual_rsi_thresholds
                )
                signal_result['detailed_info'] = detailed_signal_info
                self.logger.debug(f"📊 已收集 {stock_code} 的详细信号信息")
            
            # 🆕 阶段6：生成SignalResult对象（单一数据源原则）
            try:
                signal_result_obj = self._create_signal_result(
                    stock_code, data, indicators, scores, signal_result, actual_rsi_thresholds
                )
                signal_result['signal_result'] = signal_result_obj
                self.logger.debug(f"✅ 已生成 {stock_code} 的SignalResult对象")
            except Exception as e:
                self.logger.warning(f"⚠️ SignalResult对象生成失败: {e}，继续使用Dict格式")
            
            self.logger.debug(f"股票 {stock_code} 信号生成完成: {signal_result['signal']}")
            
            return signal_result
            
        except Exception as e:
            raise SignalGenerationError(f"股票 {stock_code} 信号生成失败: {str(e)}") from e
    
    def _calculate_indicators(self, data: pd.DataFrame) -> Dict:
        """计算所有需要的技术指标"""
        try:
            close_prices = data['close']
            high_prices = data['high']
            low_prices = data['low']
            volumes = data['volume']
            
            indicators = {}
            
            # 确保数据是Series且有足够长度
            if not isinstance(close_prices, pd.Series):
                close_prices = pd.Series(close_prices)
            
            # 检查TA-Lib可用性并给出警告
            talib_available = False
            try:
                import talib
                talib_available = True
            except ImportError:
                self.logger.warning("⚠️  TA-Lib未安装，将使用项目内备用计算方法")
                self.logger.warning("💡 建议安装TA-Lib以获得更准确的技术指标计算: pip install TA-Lib")
            
            # 1. 趋势指标 - 优先使用TA-Lib
            if talib_available:
                try:
                    close_values = close_prices.values
                    ema_values = talib.EMA(close_values, timeperiod=int(self.params['ema_period']))
                    indicators['ema'] = pd.Series(ema_values, index=close_prices.index)
                    self.logger.debug("✅ 使用TA-Lib计算EMA")
                except Exception as e:
                    # TA-Lib计算失败，使用项目内的calculate_ema作为备用
                    self.logger.warning(f"⚠️  TA-Lib EMA计算失败: {e}，回退到项目内计算")
                    indicators['ema'] = calculate_ema(close_prices, int(self.params['ema_period']))
            else:
                # TA-Lib不可用，使用项目内的calculate_ema作为备用
                indicators['ema'] = calculate_ema(close_prices, int(self.params['ema_period']))
            
            # 2. 动量指标 - 优先使用TA-Lib
            if talib_available:
                try:
                    close_values = close_prices.values
                    rsi_values = talib.RSI(close_values, timeperiod=int(self.params['rsi_period']))
                    indicators['rsi'] = pd.Series(rsi_values, index=close_prices.index)
                    self.logger.debug("✅ 使用TA-Lib计算RSI")
                except Exception as e:
                    # TA-Lib计算失败，使用项目内的calculate_rsi作为备用
                    self.logger.warning(f"⚠️  TA-Lib RSI计算失败: {e}，回退到项目内计算")
                    indicators['rsi'] = calculate_rsi(close_prices, int(self.params['rsi_period']))
            else:
                # TA-Lib不可用，使用项目内的calculate_rsi作为备用
                indicators['rsi'] = calculate_rsi(close_prices, int(self.params['rsi_period']))
            
            # MACD指标 - 优先使用TA-Lib
            if talib_available:
                try:
                    close_values = close_prices.values
                    macd_dif, macd_signal, macd_hist = talib.MACD(
                        close_values,
                        fastperiod=int(self.params['macd_fast']),
                        slowperiod=int(self.params['macd_slow']),
                        signalperiod=int(self.params['macd_signal'])
                    )
                    indicators['macd'] = {
                        'DIF': pd.Series(macd_dif, index=close_prices.index),
                        'DEA': pd.Series(macd_signal, index=close_prices.index),
                        'HIST': pd.Series(macd_hist, index=close_prices.index)
                    }
                    self.logger.debug("✅ 使用TA-Lib计算MACD")
                except Exception as e:
                    # TA-Lib计算失败，使用项目内的calculate_macd作为备用
                    self.logger.warning(f"⚠️  TA-Lib MACD计算失败: {e}，回退到项目内计算")
                    macd_result = calculate_macd(
                        close_prices, 
                        int(self.params['macd_fast']),
                        int(self.params['macd_slow']),
                        int(self.params['macd_signal'])
                    )
                    indicators['macd'] = {
                        'DIF': macd_result['dif'],
                        'DEA': macd_result['dea'], 
                        'HIST': macd_result['hist']
                    }
            else:
                # TA-Lib不可用，使用项目内的calculate_macd作为备用
                macd_result = calculate_macd(
                    close_prices, 
                    int(self.params['macd_fast']),
                    int(self.params['macd_slow']),
                    int(self.params['macd_signal'])
                )
                indicators['macd'] = {
                    'DIF': macd_result['dif'],
                    'DEA': macd_result['dea'], 
                    'HIST': macd_result['hist']
                }
            
            # 3. 波动率指标 - 优先使用TA-Lib
            if talib_available:
                try:
                    close_values = close_prices.values
                    upper_values, middle_values, lower_values = talib.BBANDS(
                        close_values,
                        timeperiod=int(self.params['bb_period']),
                        nbdevup=self.params['bb_std'],
                        nbdevdn=self.params['bb_std'],
                        matype=0
                    )
                    indicators['bb'] = {
                        'upper': pd.Series(upper_values, index=close_prices.index),
                        'middle': pd.Series(middle_values, index=close_prices.index),
                        'lower': pd.Series(lower_values, index=close_prices.index)
                    }
                    self.logger.debug("✅ 使用TA-Lib计算布林带")
                except Exception as e:
                    # TA-Lib计算失败，使用项目内的calculate_bollinger_bands作为备用
                    self.logger.warning(f"⚠️  TA-Lib布林带计算失败: {e}，回退到项目内计算")
                    indicators['bb'] = calculate_bollinger_bands(
                        close_prices, 
                        int(self.params['bb_period']),
                        self.params['bb_std']
                    )
            else:
                # TA-Lib不可用，使用项目内的calculate_bollinger_bands作为备用
                indicators['bb'] = calculate_bollinger_bands(
                    close_prices, 
                    int(self.params['bb_period']),
                    self.params['bb_std']
                )
            
            # 4. 成交量指标
            indicators['volume_ma'] = volumes.rolling(
                window=self.params['volume_ma_period']
            ).mean()
            
            # 5. 背离检测
            indicators['rsi_divergence'] = detect_rsi_divergence(
                close_prices, indicators['rsi']
            )
            
            indicators['macd_divergence'] = detect_macd_divergence(
                close_prices, indicators['macd']['HIST']
            )
            
            return indicators
            
        except Exception as e:
            raise SignalGenerationError(f"技术指标计算失败: {str(e)}") from e
    
    def _get_stock_industry_cached(self, stock_code: str) -> str:
        """
        获取股票行业信息（带缓存）
        
        Args:
            stock_code: 股票代码
            
        Returns:
            str: 行业名称
        """
        # 检查缓存
        if stock_code in self._industry_cache:
            return self._industry_cache[stock_code]
        
        # 缓存未命中，获取行业信息
        industry = None
        try:
            # 1. 优先使用静态映射表
            industry = get_stock_industry(stock_code)
            
            # 2. 如果静态映射表没有，尝试自动识别
            if not industry:
                industry = get_stock_industry_auto(stock_code)
                if industry:
                    self.logger.info(f"通过自动识别获取股票 {stock_code} 的行业: {industry}")
            
            # 3. 缓存结果（包括空结果）
            self._industry_cache[stock_code] = industry or ""
            
        except Exception as e:
            self.logger.warning(f"获取股票 {stock_code} 行业信息失败: {e}")
            self._industry_cache[stock_code] = ""
            industry = ""
        
        return industry or ""
    
    def _get_industry_rules_cached(self, industry: str) -> Dict:
        """
        获取行业规则（带缓存）
        
        Args:
            industry: 行业名称
            
        Returns:
            Dict: 行业规则
        """
        if not industry:
            return {}
        
        # 检查缓存
        if industry in self._industry_rules_cache:
            return self._industry_rules_cache[industry]
        
        # 缓存未命中，获取行业规则
        try:
            industry_rules = get_comprehensive_industry_rules(industry)
            self._industry_rules_cache[industry] = industry_rules or {}
            return industry_rules or {}
        except Exception as e:
            self.logger.warning(f"获取行业 {industry} 规则失败: {e}")
            self._industry_rules_cache[industry] = {}
            return {}
    
    def _calculate_4d_scores(self, data: pd.DataFrame, indicators: Dict, stock_code: str = None) -> Dict:
        """
        计算4维度评分
        严格按照设计文档实现，支持行业特定的RSI阈值
        
        Args:
            data: 股票数据
            indicators: 技术指标
            stock_code: 股票代码，用于获取行业特定阈值
        
        Returns:
            Dict: 各维度评分结果
        """
        try:
            current_price = data['close'].iloc[-1]
            current_volume = data['volume'].iloc[-1]
            
            scores = {
                'trend_filter_high': False,    # 趋势过滤器支持卖出信号
                'trend_filter_low': False,     # 趋势过滤器支持买入信号
                'overbought_oversold_high': False,  # 超买超卖支持卖出信号
                'overbought_oversold_low': False,   # 超买超卖支持买入信号
                'momentum_high': False,        # 动能确认支持卖出信号
                'momentum_low': False,         # 动能确认支持买入信号
                'extreme_price_volume_high': False,  # 极端价格+量能支持卖出信号
                'extreme_price_volume_low': False    # 极端价格+量能支持买入信号
            }
            
            # 1. 价值比过滤器 (硬性前提) - V1.1策略更新
            # 替换原有的EMA趋势过滤器为基于DCF估值的价值比过滤器
            
            # 获取DCF估值数据
            dcf_value = None
            if stock_code and hasattr(self, 'dcf_values') and self.dcf_values:
                dcf_value = self.dcf_values.get(stock_code)
            elif stock_code:
                # 如果signal_generator没有dcf_values，尝试从配置加载
                try:
                    # 从portfolio_config中提取DCF估值
                    from config.path_manager import get_path_manager
                    pm = get_path_manager()
                    df = pd.read_csv(pm.get_portfolio_config_path(), encoding='utf-8-sig')
                    for _, row in df.iterrows():
                        if str(row['Stock_number']).strip() == stock_code:
                            dcf_value = float(row['DCF_value_per_share'])
                            self.logger.debug(f"从配置文件获取 {stock_code} DCF估值: {dcf_value}")
                            break
                except Exception as e:
                    self.logger.warning(f"无法从配置文件获取股票 {stock_code} 的DCF估值: {e}")
            
            if dcf_value is None or dcf_value <= 0:
                self.logger.warning(f"股票 {stock_code} 缺少有效的DCF估值数据，价值比过滤器无法工作")
                # 如果没有DCF数据，回退到原有的EMA趋势过滤器
                ema_current = indicators['ema'].iloc[-1]
                
                # 计算EMA趋势方向 - 使用线性回归法判断
                ema_series = indicators['ema']
                ema_trend_up = False
                ema_trend_down = False
                
                try:
                    # 使用新的detect_ema_trend函数判断趋势
                    if len(ema_series) >= 8:
                        ema_trend = detect_ema_trend(ema_series, 8, 0.003)
                        ema_trend_up = (ema_trend == "向上")
                        ema_trend_down = (ema_trend == "向下")
                        
                        self.logger.debug(f"回退到EMA趋势过滤器: 趋势={ema_trend}")
                    else:
                        # 数据不足时使用简单方法
                        if len(ema_series) >= 2 and not pd.isna(ema_series.iloc[-2]):
                            ema_prev = ema_series.iloc[-2]
                            ema_trend_up = ema_current > ema_prev
                            ema_trend_down = ema_current < ema_prev
                except Exception as e:
                    self.logger.warning(f"EMA趋势判断失败: {e}")
                
                # 支持卖出信号：收盘价 > 20周EMA 且 EMA向上
                if current_price > ema_current and ema_trend_up:
                    scores['trend_filter_high'] = True
                
                # 支持买入信号：收盘价 < 20周EMA 且 EMA向下
                if current_price < ema_current and ema_trend_down:
                    scores['trend_filter_low'] = True
                    
            else:
                # 使用价值比过滤器
                price_value_ratio = current_price / dcf_value
                
                # 从配置中获取阈值
                sell_threshold = self.params['value_ratio_sell_threshold']
                buy_threshold = self.params['value_ratio_buy_threshold']
                
                self.logger.debug(f"价值比过滤器: 收盘价={current_price:.2f}, DCF估值={dcf_value:.2f}, 价值比={price_value_ratio:.2f}")
                
                # 支持卖出信号：价值比 > 卖出阈值
                if price_value_ratio > sell_threshold:
                    scores['trend_filter_high'] = True
                    self.logger.debug(f"价值比过滤器支持卖出: {price_value_ratio:.2f} > {sell_threshold}")
                
                # 支持买入信号：价值比 < 买入阈值
                if price_value_ratio < buy_threshold:
                    scores['trend_filter_low'] = True
                    self.logger.debug(f"价值比过滤器支持买入: {price_value_ratio:.2f} < {buy_threshold}")
            
            # 2. 超买/超卖 - 支持行业特定阈值
            rsi_current = indicators['rsi'].iloc[-1]
            
            
            # 获取动态RSI阈值（新系统）
            rsi_overbought = self.params['rsi_overbought']  # 默认阈值
            rsi_oversold = self.params['rsi_oversold']      # 默认阈值
            
            # 初始化极端阈值
            rsi_extreme_overbought = self.params.get('rsi_extreme_overbought', 80)  # 默认极端超买阈值
            rsi_extreme_oversold = self.params.get('rsi_extreme_oversold', 20)      # 默认极端超卖阈值
            
            # 使用新的动态RSI阈值系统
            if stock_code and self.stock_industry_map and self.rsi_thresholds:
                try:
                    # 从股票-行业映射中获取行业信息
                    if stock_code in self.stock_industry_map:
                        industry_info = self.stock_industry_map[stock_code]
                        industry_code = industry_info['industry_code']
                        industry_name = industry_info['industry_name']
                        
                        # 从RSI阈值数据中获取该行业的动态阈值
                        if industry_code in self.rsi_thresholds:
                            threshold_info = self.rsi_thresholds[industry_code]
                            rsi_overbought = threshold_info['sell_threshold']  # 使用普通超买阈值
                            rsi_oversold = threshold_info['buy_threshold']     # 使用普通超卖阈值
                            rsi_extreme_overbought = threshold_info.get('extreme_sell_threshold', 80)  # 极端超买阈值
                            rsi_extreme_oversold = threshold_info.get('extreme_buy_threshold', 20)     # 极端超卖阈值
                            
                            self.logger.debug(f"股票 {stock_code} 行业 {industry_name}({industry_code}) 动态RSI阈值: "
                                            f"超买={rsi_overbought:.2f}, 超卖={rsi_oversold:.2f}, "
                                            f"极端超买={rsi_extreme_overbought:.2f}, 极端超卖={rsi_extreme_oversold:.2f}, "
                                            f"波动率等级={threshold_info['volatility_level']}")
                        else:
                            self.logger.debug(f"股票 {stock_code} 行业 {industry_name}({industry_code}) 未找到RSI阈值，使用默认值")
                    else:
                        self.logger.debug(f"股票 {stock_code} 未找到行业映射，使用默认RSI阈值")
                        
                except Exception as e:
                    self.logger.warning(f"获取股票 {stock_code} 动态RSI阈值失败: {e}，使用默认阈值")
            else:
                if not self.stock_industry_map:
                    self.logger.debug("股票-行业映射数据未加载，使用默认RSI阈值")
                elif not self.rsi_thresholds:
                    self.logger.debug("动态RSI阈值数据未加载，使用默认RSI阈值")
            
            rsi_divergence = indicators['rsi_divergence']
            
            # 获取行业特定的信号规则
            need_divergence_buy = True
            need_divergence_sell = True
            industry = ""
            
            if stock_code:
                try:
                    # 使用缓存的行业信息获取方法
                    industry = self._get_stock_industry_cached(stock_code)
                    
                    # 使用行业规则
                    if industry:
                        industry_rules = self._get_industry_rules_cached(industry)
                        if industry_rules:
                            need_divergence_buy = industry_rules['divergence_required']
                            need_divergence_sell = industry_rules['divergence_required']
                            
                            # 检查是否达到极端阈值，极端情况下可以不要求背离
                            if need_divergence_buy and rsi_current <= industry_rules['rsi_extreme_threshold']['oversold']:
                                need_divergence_buy = False
                                self.logger.debug(f"股票 {stock_code} RSI达到极端超卖阈值，免除买入背离要求")
                            if need_divergence_sell and rsi_current >= industry_rules['rsi_extreme_threshold']['overbought']:
                                need_divergence_sell = False
                                self.logger.debug(f"股票 {stock_code} RSI达到极端超买阈值，免除卖出背离要求")
                                
                            self.logger.debug(f"股票 {stock_code} 行业 {industry} 背离要求: 买入={need_divergence_buy}, 卖出={need_divergence_sell}")
                except Exception as e:
                    self.logger.warning(f"获取股票 {stock_code} 行业信号规则失败: {e}")
            
            # RSI信号逻辑：分为普通阈值和极端阈值两种情况
            
            # 1. 极端RSI阈值：强制信号，无需考虑背离
            extreme_rsi_high_condition = (not pd.isna(rsi_current) and rsi_current >= rsi_extreme_overbought)
            extreme_rsi_low_condition = (not pd.isna(rsi_current) and rsi_current <= rsi_extreme_oversold)
            
            if extreme_rsi_high_condition:
                scores['overbought_oversold_high'] = True
                self.logger.debug(f"🔥 极端RSI超买信号: RSI={rsi_current:.2f} >= 极端阈值{rsi_extreme_overbought:.2f}，强制卖出信号")
            elif extreme_rsi_low_condition:
                scores['overbought_oversold_low'] = True
                self.logger.debug(f"🔥 极端RSI超卖信号: RSI={rsi_current:.2f} <= 极端阈值{rsi_extreme_oversold:.2f}，强制买入信号")
            else:
                # 2. 普通RSI阈值：需要考虑背离条件
                # 阶段高点：14周RSI > 行业特定超买阈值 且 (出现顶背离 或 不要求背离)
                rsi_high_condition = (not pd.isna(rsi_current) and rsi_current >= rsi_overbought and 
                                    (rsi_divergence['top_divergence'] or not need_divergence_sell))
                if rsi_high_condition:
                    scores['overbought_oversold_high'] = True
                    self.logger.debug(f"📊 普通RSI超买信号: RSI={rsi_current:.2f} >= 阈值{rsi_overbought:.2f}，背离条件满足")
                
                # 阶段低点：14周RSI <= 行业特定超卖阈值 且 (出现底背离 或 不要求背离)
                rsi_low_condition = (not pd.isna(rsi_current) and rsi_current <= rsi_oversold and 
                                   (rsi_divergence['bottom_divergence'] or not need_divergence_buy))
                if rsi_low_condition:
                    scores['overbought_oversold_low'] = True
                    self.logger.debug(f"📊 普通RSI超卖信号: RSI={rsi_current:.2f} <= 阈值{rsi_oversold:.2f}，背离条件满足")
                
            # 记录RSI分析详情
            self.logger.debug(f"RSI分析: 当前值={rsi_current:.2f}")
            self.logger.debug(f"RSI普通阈值: 超买={rsi_overbought:.2f}, 超卖={rsi_oversold:.2f}")
            self.logger.debug(f"RSI极端阈值: 极端超买={rsi_extreme_overbought:.2f}, 极端超卖={rsi_extreme_oversold:.2f}")
            self.logger.debug(f"RSI背离: 顶背离={rsi_divergence['top_divergence']}, 底背离={rsi_divergence['bottom_divergence']}")
            self.logger.debug(f"RSI信号状态: 极端超买={extreme_rsi_high_condition}, 极端超卖={extreme_rsi_low_condition}")
            
            # 3. 动能确认
            macd_data = indicators['macd']
            dif_current = macd_data['DIF'].iloc[-1]
            dea_current = macd_data['DEA'].iloc[-1]
            hist_current = macd_data['HIST'].iloc[-1]
            
            # 检查MACD柱体变化和金叉死叉
            if len(macd_data['HIST']) >= 3:
                hist_prev1 = macd_data['HIST'].iloc[-2]
                hist_prev2 = macd_data['HIST'].iloc[-3]
                
                # 红色柱体连续2根缩短（用于卖出信号）
                red_hist_shrinking = False
                if hist_current > 0 and hist_prev1 > 0 and hist_prev2 > 0:
                    red_hist_shrinking = hist_current < hist_prev1 < hist_prev2
                
                # 绿色柱体连续2根缩短（用于买入信号）
                green_hist_shrinking = False
                if hist_current < 0 and hist_prev1 < 0 and hist_prev2 < 0:
                    green_hist_shrinking = abs(hist_current) < abs(hist_prev1) < abs(hist_prev2)
                
                # MACD柱体颜色状态
                macd_is_green = hist_current < 0  # 当前为绿色柱体
                macd_is_red = hist_current > 0    # 当前为红色柱体
                
                # 金叉死叉
                if len(macd_data['DIF']) >= 2:
                    dif_prev = macd_data['DIF'].iloc[-2]
                    dea_prev = macd_data['DEA'].iloc[-2]
                    dif_cross_up = dif_current > dea_current and dif_prev <= dea_prev  # 金叉
                    dif_cross_down = dif_current < dea_current and dif_prev >= dea_prev  # 死叉
                else:
                    dif_cross_up = False
                    dif_cross_down = False
                
                # 检查前期柱体缩短 + 当前转色的严谨条件
                # 买入：前2根绿柱缩短 + 当前转红
                green_to_red_transition = False
                if (hist_prev1 < 0 and hist_prev2 < 0 and  # 前2根是绿柱
                    abs(hist_prev1) < abs(hist_prev2) and  # 前期绿柱在缩短
                    hist_current > 0):  # 当前转为红柱
                    green_to_red_transition = True
                
                # 卖出：前2根红柱缩短 + 当前转绿
                red_to_green_transition = False
                if (hist_prev1 > 0 and hist_prev2 > 0 and  # 前2根是红柱
                    hist_prev1 < hist_prev2 and  # 前期红柱在缩短
                    hist_current < 0):  # 当前转为绿柱
                    red_to_green_transition = True
                
                # 阶段高点（卖出）：MACD红色柱体连续2根缩短 或 前期红柱缩短+当前转绿 或 DIF死叉DEA
                sell_conditions = [red_hist_shrinking, red_to_green_transition, dif_cross_down]
                if any(sell_conditions):
                    scores['momentum_high'] = True
                
                # 阶段低点（买入）：MACD绿色柱体连续2根缩短 或 前期绿柱缩短+当前转红 或 DIF金叉DEA
                buy_conditions = [green_hist_shrinking, green_to_red_transition, dif_cross_up]
                if any(buy_conditions):
                    scores['momentum_low'] = True
                
                # 调试日志
                self.logger.debug(f"动能确认 - 卖出条件: 红色缩短={red_hist_shrinking}, 红转绿={red_to_green_transition}, DIF死叉={dif_cross_down}")
                self.logger.debug(f"动能确认 - 买入条件: 绿色缩短={green_hist_shrinking}, 绿转红={green_to_red_transition}, DIF金叉={dif_cross_up}")
            
            # 4. 极端价格 + 量能
            bb_upper = indicators['bb']['upper'].iloc[-1]
            bb_lower = indicators['bb']['lower'].iloc[-1]
            
            # 如果布林带计算失败，使用备用计算
            if pd.isna(bb_upper) or pd.isna(bb_lower):
                # 尝试使用TA-Lib重新计算
                try:
                    import talib
                    close_values = data['close'].values
                    upper_values, middle_values, lower_values = talib.BBANDS(
                        close_values,
                        timeperiod=self.params['bb_period'],
                        nbdevup=self.params['bb_std'],
                        nbdevdn=self.params['bb_std'],
                        matype=0
                    )
                    bb_upper = upper_values[-1]
                    bb_lower = lower_values[-1]
                    # 更新指标
                    indicators['bb'] = {
                        'upper': pd.Series(upper_values, index=data.index),
                        'middle': pd.Series(middle_values, index=data.index),
                        'lower': pd.Series(lower_values, index=data.index)
                    }
                except:
                    # TA-Lib失败，使用pandas备用方法
                    sma = data['close'].rolling(window=self.params['bb_period']).mean()
                    std = data['close'].rolling(window=self.params['bb_period']).std()
                    bb_upper = (sma + (std * self.params['bb_std'])).iloc[-1]
                    bb_lower = (sma - (std * self.params['bb_std'])).iloc[-1]
                    # 更新指标
                    indicators['bb'] = {
                        'upper': sma + (std * self.params['bb_std']),
                        'middle': sma,
                        'lower': sma - (std * self.params['bb_std'])
                    }
            
            volume_ma = indicators['volume_ma'].iloc[-1]
            
            # 调试日志：极端价格量能判断
            self.logger.info(f"🔍 极端价格量能判断 - 当前价格: {current_price:.2f}, 布林上轨: {bb_upper:.2f}")
            self.logger.info(f"🔍 极端价格量能判断 - 当前成交量: {current_volume:.0f}, 成交量均线: {volume_ma:.0f}")
            self.logger.info(f"🔍 极端价格量能判断 - 成交量阈值(×{self.params['volume_sell_ratio']}): {volume_ma * self.params['volume_sell_ratio']:.0f}")
            self.logger.info(f"🔍 极端价格量能判断 - 价格条件: {current_price >= bb_upper}, 成交量条件: {current_volume >= volume_ma * self.params['volume_sell_ratio']}")
            self.logger.info(f"🔍 极端价格量能判断 - bb_upper is NaN: {pd.isna(bb_upper)}, volume_ma is NaN: {pd.isna(volume_ma)}")
            
            # 阶段高点：收盘价 ≥ 布林上轨 且 本周量 ≥ 4周均量 × 1.3
            if (not pd.isna(bb_upper) and not pd.isna(volume_ma) and
                current_price >= bb_upper and 
                current_volume >= volume_ma * self.params['volume_sell_ratio']):
                scores['extreme_price_volume_high'] = True
                self.logger.debug(f"✅ 极端价格量能卖出信号触发！")
            
            # 阶段低点：收盘价 ≤ 布林下轨 且 本周量 ≥ 4周均量 × 0.8
            if (not pd.isna(bb_lower) and not pd.isna(volume_ma) and
                current_price <= bb_lower and 
                current_volume >= volume_ma * self.params['volume_buy_ratio']):
                scores['extreme_price_volume_low'] = True
            
            # 构建实际使用的RSI阈值信息
            actual_rsi_thresholds = {
                'buy_threshold': rsi_oversold,
                'sell_threshold': rsi_overbought,
                'extreme_buy_threshold': rsi_extreme_oversold,
                'extreme_sell_threshold': rsi_extreme_overbought,
                'oversold': rsi_oversold,  # 兼容旧格式
                'overbought': rsi_overbought,  # 兼容旧格式
                'extreme_oversold': rsi_extreme_oversold,  # 兼容旧格式
                'extreme_overbought': rsi_extreme_overbought,  # 兼容旧格式
                'divergence_required': need_divergence_buy  # 添加背离要求信息
            }
            
            # 如果使用了动态阈值，添加行业信息
            if stock_code and self.stock_industry_map and stock_code in self.stock_industry_map:
                industry_info = self.stock_industry_map[stock_code]
                actual_rsi_thresholds['industry_name'] = industry_info['industry_name']
                actual_rsi_thresholds['industry_code'] = industry_info['industry_code']
            
            return scores, actual_rsi_thresholds
            
        except Exception as e:
            raise SignalGenerationError(f"4维度评分计算失败: {str(e)}") from e
    
    def _generate_final_signal(self, stock_code: str, scores: Dict, indicators: Dict, 
                              rsi_thresholds: Dict = None, dcf_value: float = None, 
                              current_price: float = None, industry: str = None) -> Dict:
        """
        根据4维度评分生成最终信号
        
        触发逻辑：先满足「趋势过滤器」→ 再在其余3条里至少满足2条 → 生成信号
        """
        try:
            # 检查趋势过滤器（硬性前提）
            trend_filter_high = scores['trend_filter_high']  # 支持卖出信号
            trend_filter_low = scores['trend_filter_low']    # 支持买入信号
            
            # 获取RSI阈值信息用于记录
            if rsi_thresholds is None:
                rsi_thresholds = {'oversold': 30, 'overbought': 70}
            
            # 如果趋势过滤器都不满足，持有
            if not trend_filter_high and not trend_filter_low:
                result = {
                    'signal': 'HOLD',
                    'confidence': 0.0,
                    'reason': '趋势过滤器不支持任何交易信号',
                    'scores': scores,
                    'details': self._get_signal_details(indicators),
                    'rsi_thresholds': rsi_thresholds
                }
                # 添加DCF估值和行业信息
                if dcf_value and dcf_value > 0:
                    result['dcf_value'] = dcf_value
                    result['value_price_ratio'] = current_price / dcf_value
                if industry:
                    result['industry'] = industry
                return result
            
            # 检查卖出信号（卖出10%）
            if trend_filter_high:
                # 统计其余3个维度的卖出信号
                high_signals = [
                    scores['overbought_oversold_high'],
                    scores['momentum_high'],
                    scores['extreme_price_volume_high']
                ]
                
                high_signal_count = sum(1 for signal in high_signals if signal)
                
                if high_signal_count >= 2:
                    # 满足条件：趋势过滤器 + 至少2个其他卖出信号
                    # 置信度计算：趋势过滤器(1分) + 其他维度满足数量
                    result = {
                        'signal': 'SELL',
                        'confidence': 1 + high_signal_count,  # 1-4分
                        'reason': f'卖出信号：价值比过滤器+{high_signal_count}个卖出维度',
                        'scores': scores,
                        'details': self._get_signal_details(indicators),
                        'action': '卖出10%',
                        'rsi_thresholds': rsi_thresholds
                    }
                    # 添加DCF估值和行业信息
                    if dcf_value and dcf_value > 0:
                        result['dcf_value'] = dcf_value
                        result['value_price_ratio'] = current_price / dcf_value
                    if industry:
                        result['industry'] = industry
                    return result
            
            # 检查买入信号（买入10%）
            if trend_filter_low:
                # 统计其余3个维度的买入信号
                low_signals = [
                    scores['overbought_oversold_low'],
                    scores['momentum_low'],
                    scores['extreme_price_volume_low']
                ]
                
                low_signal_count = sum(1 for signal in low_signals if signal)
                
                if low_signal_count >= 2:
                    # 满足条件：趋势过滤器 + 至少2个其他买入信号
                    # 置信度计算：趋势过滤器(1分) + 其他维度满足数量
                    result = {
                        'signal': 'BUY',
                        'confidence': 1 + low_signal_count,  # 1-4分
                        'reason': f'买入信号：价值比过滤器+{low_signal_count}个买入维度',
                        'scores': scores,
                        'details': self._get_signal_details(indicators),
                        'action': '买入10%',
                        'rsi_thresholds': rsi_thresholds
                    }
                    # 添加DCF估值和行业信息
                    if dcf_value and dcf_value > 0:
                        result['dcf_value'] = dcf_value
                        result['value_price_ratio'] = current_price / dcf_value
                    if industry:
                        result['industry'] = industry
                    return result
            
            # 信号不足，持有
            high_count = sum(1 for signal in [scores['overbought_oversold_high'], 
                                            scores['momentum_high'], 
                                            scores['extreme_price_volume_high']] if signal)
            low_count = sum(1 for signal in [scores['overbought_oversold_low'], 
                                           scores['momentum_low'], 
                                           scores['extreme_price_volume_low']] if signal)
            
            result = {
                'signal': 'HOLD',
                'confidence': 0.0,
                'reason': f'信号不足(卖出:{high_count},买入:{low_count})',
                'scores': scores,
                'details': self._get_signal_details(indicators),
                'rsi_thresholds': rsi_thresholds
            }
            # 添加DCF估值和行业信息
            if dcf_value and dcf_value > 0:
                result['dcf_value'] = dcf_value
                result['value_price_ratio'] = current_price / dcf_value
            if industry:
                result['industry'] = industry
            return result
            
        except Exception as e:
            raise SignalGenerationError(f"最终信号生成失败: {str(e)}") from e
    
    def _get_signal_details(self, indicators: Dict) -> Dict:
        """获取信号详细信息"""
        try:
            return {
                'ema': float(indicators['ema'].iloc[-1]),
                'rsi': float(indicators['rsi'].iloc[-1]),
                'macd_dif': float(indicators['macd']['DIF'].iloc[-1]),
                'macd_dea': float(indicators['macd']['DEA'].iloc[-1]),
                'macd_hist': float(indicators['macd']['HIST'].iloc[-1]),
                'bb_upper': float(indicators['bb']['upper'].iloc[-1]),
                'bb_middle': float(indicators['bb']['middle'].iloc[-1]),
                'bb_lower': float(indicators['bb']['lower'].iloc[-1]),
                'volume_ma': float(indicators['volume_ma'].iloc[-1]),
                'rsi_divergence': indicators['rsi_divergence'],
                'macd_divergence': indicators['macd_divergence']
            }
        except Exception:
            return {}
    
    def _extract_current_indicators(self, data: pd.DataFrame, indicators: Dict) -> Dict:
        """提取当前时点的技术指标值，直接从数据中获取已计算的指标"""
        try:
            current_data = data.iloc[-1]
            current_close = float(current_data['close'])
            current_volume = int(current_data['volume'])
            
            self.logger.debug("🔍 开始提取技术指标 - 直接从数据获取")
            
            # 智能获取指标值：优先从数据中获取，然后从indicators获取
            def smart_get_from_data(field_name, indicator_series=None, fallback_value=None):
                try:
                    # 1. 优先从数据中获取（数据处理器已计算的指标）
                    if field_name in data.columns:
                        value = data[field_name].iloc[-1]
                        if not pd.isna(value):
                            self.logger.debug(f"   - {field_name}: 从数据获取 {value:.4f}")
                            return float(value)
                        else:
                            # 寻找最近的有效值
                            valid_values = data[field_name].dropna()
                            if len(valid_values) > 0:
                                last_valid = float(valid_values.iloc[-1])
                                self.logger.debug(f"   - {field_name}: 数据中最新值NaN，使用最近有效值 {last_valid:.4f}")
                                return last_valid
                    
                    # 2. 从indicators中获取
                    if indicator_series is not None:
                        if len(indicator_series) > 0:
                            latest_value = indicator_series.iloc[-1]
                            if not pd.isna(latest_value):
                                self.logger.debug(f"   - {field_name}: 从indicators获取 {latest_value:.4f}")
                                return float(latest_value)
                            
                            # 寻找最近的有效值
                            valid_values = indicator_series.dropna()
                            if len(valid_values) > 0:
                                last_valid = float(valid_values.iloc[-1])
                                self.logger.debug(f"   - {field_name}: indicators中最新值NaN，使用最近有效值 {last_valid:.4f}")
                                return last_valid
                    
                    # 3. 使用默认值
                    default_val = fallback_value if fallback_value is not None else current_close
                    self.logger.debug(f"   - {field_name}: 使用默认值 {default_val:.4f}")
                    return float(default_val)
                    
                except Exception as e:
                    default_val = fallback_value if fallback_value is not None else current_close
                    self.logger.warning(f"   - {field_name}: 获取失败 {e}，使用默认值 {default_val:.4f}")
                    return float(default_val)
            
            # 提取各项技术指标 - 强制重新计算最新值而非使用缓存
            ema_20w = smart_get_from_data('ema_20', indicators.get('ema'), current_close)
            ema_60w = smart_get_from_data('ema_50', indicators.get('ema'), current_close)  # 使用ema_50作为60周替代
            
            # RSI - 优先从数据中获取，然后从indicators获取
            rsi_14w = smart_get_from_data('rsi', indicators.get('rsi'), 50.0)
            
            # MACD指标
            macd_dif = smart_get_from_data('macd', indicators.get('macd', {}).get('DIF'), 0.0)
            macd_dea = smart_get_from_data('macd_signal', indicators.get('macd', {}).get('DEA'), 0.0)
            macd_hist = smart_get_from_data('macd_histogram', indicators.get('macd', {}).get('HIST'), 0.0)
            
            # 布林带指标
            bb_upper = smart_get_from_data('bb_upper', indicators.get('bb', {}).get('upper'), current_close * 1.02)
            bb_middle = smart_get_from_data('bb_middle', indicators.get('bb', {}).get('middle'), current_close)
            bb_lower = smart_get_from_data('bb_lower', indicators.get('bb', {}).get('lower'), current_close * 0.98)
            
            # 成交量指标
            volume_ma_value = smart_get_from_data('volume_ma', indicators.get('volume_ma'), current_volume)
            volume_ratio = smart_get_from_data('volume_ratio', None, 1.0)
            
            # 计算4周平均成交量（如果数据中没有）
            if 'volume_ma' not in data.columns and len(data) >= 4:
                volume_4w_avg = data['volume'].iloc[-4:].mean()
                volume_ratio = current_volume / volume_4w_avg if volume_4w_avg > 0 else 1.0
                volume_ma_value = volume_4w_avg
                self.logger.debug(f"   - 计算4周平均成交量: {volume_4w_avg:.0f}, 比率: {volume_ratio:.2f}")
            
            result = {
                'close': current_close,
                'volume': current_volume,
                'ema_20w': ema_20w,
                'ema_60w': ema_60w,
                'rsi_14w': rsi_14w,
                'macd_dif': macd_dif,
                'macd_dea': macd_dea,
                'macd_hist': macd_hist,
                'bb_upper': bb_upper,
                'bb_middle': bb_middle,
                'bb_lower': bb_lower,
                'volume_ma': volume_ma_value,
                'volume_4w_avg': volume_ma_value,  # 添加此字段以兼容HTML报告
                'volume_ratio': volume_ratio
            }
            
            # 验证结果
            nan_count = sum(1 for v in result.values() if pd.isna(v))
            if nan_count > 0:
                self.logger.warning(f"⚠️  提取结果仍有 {nan_count} 个NaN值")
                for key, value in result.items():
                    if pd.isna(value):
                        self.logger.warning(f"   - {key}: NaN")
            else:
                self.logger.debug("✅ 技术指标提取完成，无NaN值")
            
            return result
            
        except Exception as e:
            self.logger.error(f"❌ 提取技术指标失败: {e}")
            import traceback
            self.logger.error(traceback.format_exc())
            # 返回基本的默认值
            return {
                'close': current_close,
                'volume': current_volume,
                'ema_20w': current_close,
                'ema_60w': current_close,
                'rsi_14w': 50.0,
                'macd_dif': 0.0,
                'macd_dea': 0.0,
                'macd_hist': 0.0,
                'bb_upper': current_close * 1.02,
                'bb_middle': current_close,
                'bb_lower': current_close * 0.98,
                'volume_ma': current_volume,
                'volume_4w_avg': current_volume,  # 添加此字段以兼容HTML报告
                'volume_ratio': 1.0
            }
    
    def get_signal_explanation(self, signal_result: Dict) -> str:
        """获取信号解释说明"""
        try:
            signal = signal_result['signal']
            confidence = signal_result['confidence']
            reason = signal_result['reason']
            scores = signal_result['scores']
            
            explanation = f"信号: {signal} (置信度: {confidence:.2f})\n"
            explanation += f"原因: {reason}\n"
            if 'action' in signal_result:
                explanation += f"操作: {signal_result['action']}\n"
            explanation += "\n4维度评分详情:\n"
            explanation += f"1. 趋势过滤器: 支持卖出={scores['trend_filter_high']}, 支持买入={scores['trend_filter_low']}\n"
            explanation += f"2. 超买超卖: 支持卖出={scores['overbought_oversold_high']}, 支持买入={scores['overbought_oversold_low']}\n"
            explanation += f"3. 动能确认: 支持卖出={scores['momentum_high']}, 支持买入={scores['momentum_low']} (红色缩短/转绿色/死叉 | 绿色缩短/转红色/金叉)\n"
            explanation += f"4. 极端价格+量能: 支持卖出={scores['extreme_price_volume_high']}, 支持买入={scores['extreme_price_volume_low']}\n"
            
            return explanation
            
        except Exception:
            return "信号解释生成失败"
    
    def _collect_detailed_signal_info(self, stock_code: str, data: pd.DataFrame, 
                                      indicators: Dict, scores: Dict, signal_result: Dict, 
                                      actual_rsi_thresholds: Dict) -> Dict:
        """
        收集32个字段的详细信号信息（用于信号跟踪）
        
        Args:
            stock_code: 股票代码
            data: 股票数据
            indicators: 技术指标
            scores: 4维度评分
            signal_result: 信号结果
            actual_rsi_thresholds: 实际RSI阈值
            
        Returns:
            Dict: 详细信号信息
        """
        try:
            detailed_info = {}
            
            # 获取基础价格和成交量信息
            current_price = data['close'].iloc[-1]
            current_volume = data['volume'].iloc[-1] if 'volume' in data.columns else 0
            
            # 获取行业信息
            industry_info = self._get_stock_industry_info(stock_code)
            detailed_info['industry_name'] = industry_info.get('industry_name', '未知行业')
            
            # 获取RSI阈值信息
            detailed_info['industry_rsi_thresholds'] = actual_rsi_thresholds
            
            # RSI信号类型和背离状态
            rsi_value = indicators.get('rsi', pd.Series([50])).iloc[-1] if len(indicators.get('rsi', [])) > 0 else 50
            detailed_info['rsi_signal_type'] = self._determine_rsi_signal_type(rsi_value, actual_rsi_thresholds)
            detailed_info['price_divergence'] = self._check_price_divergence(data, indicators)
            
            # MACD相关信息
            macd_info = indicators.get('macd', {})
            if macd_info:
                macd_hist = macd_info.get('HIST', pd.Series([0])).iloc[-1] if len(macd_info.get('HIST', [])) > 0 else 0
                detailed_info['histogram_trend'] = self._analyze_histogram_trend(macd_info.get('HIST', pd.Series()))
                detailed_info['golden_cross_status'] = self._check_golden_cross(macd_info)
            else:
                detailed_info['histogram_trend'] = '无变化'
                detailed_info['golden_cross_status'] = '无交叉'
            
            # 布林带位置
            bb_info = indicators.get('bb', {})
            if bb_info:
                detailed_info['price_bb_position'] = self._get_bb_position(current_price, bb_info)
            else:
                detailed_info['price_bb_position'] = '区间内'
            
            # 成交量分析
            volume_ma = indicators.get('volume_ma', pd.Series([current_volume])).iloc[-1] if len(indicators.get('volume_ma', [])) > 0 else current_volume
            volume_ratio = current_volume / volume_ma if volume_ma > 0 else 1.0
            detailed_info['significant_volume'] = '是' if volume_ratio > 1.3 else '否'
            
            # 最近5周数据
            detailed_info['recent_5w_prices'] = data['close'].tail(5).tolist()
            detailed_info['recent_5w_volumes'] = data['volume'].tail(5).tolist() if 'volume' in data.columns else []
            
            # 数据质量状态
            detailed_info['data_quality'] = f"数据长度{len(data)}条"
            detailed_info['calculation_errors'] = '无'
            
            return detailed_info
            
        except Exception as e:
            self.logger.error(f"收集详细信号信息失败: {str(e)}")
            return {
                'industry_name': '未知',
                'industry_rsi_thresholds': {},
                'rsi_signal_type': '无信号',
                'price_divergence': '无背离',
                'histogram_trend': '无变化',
                'golden_cross_status': '无交叉',
                'price_bb_position': '区间内',
                'significant_volume': '否',
                'recent_5w_prices': [],
                'recent_5w_volumes': [],
                'data_quality': '正常',
                'calculation_errors': '无'
            }
    
    def _get_stock_industry_info(self, stock_code: str) -> Dict:
        """获取股票行业信息"""
        try:
            if self.stock_industry_map and stock_code in self.stock_industry_map:
                return self.stock_industry_map[stock_code]
            return {'industry_name': '未知行业', 'industry_code': 'UNKNOWN'}
        except Exception:
            return {'industry_name': '未知行业', 'industry_code': 'UNKNOWN'}
    
    def _determine_rsi_signal_type(self, rsi_value: float, rsi_thresholds: Dict) -> str:
        """判断RSI信号类型"""
        try:
            extreme_buy = rsi_thresholds.get('extreme_buy_threshold', 20)
            normal_buy = rsi_thresholds.get('buy_threshold', 30)
            normal_sell = rsi_thresholds.get('sell_threshold', 70)
            extreme_sell = rsi_thresholds.get('extreme_sell_threshold', 80)
            
            if rsi_value <= extreme_buy:
                return '极端信号'
            elif rsi_value <= normal_buy:
                return '普通信号'
            elif rsi_value >= extreme_sell:
                return '极端信号'
            elif rsi_value >= normal_sell:
                return '普通信号'
            else:
                return '无信号'
        except Exception:
            return '无信号'
    
    def _check_price_divergence(self, data: pd.DataFrame, indicators: Dict) -> str:
        """检查价格背离状态"""
        try:
            rsi_divergence = indicators.get('rsi_divergence', {})
            if isinstance(rsi_divergence, dict):
                if rsi_divergence.get('bullish_divergence', False):
                    return '出现底背离'
                elif rsi_divergence.get('bearish_divergence', False):
                    return '出现顶背离'
            return '无背离信号'
        except Exception:
            return '无背离信号'
    
    def _analyze_histogram_trend(self, macd_hist: pd.Series) -> str:
        """分析MACD柱体趋势"""
        try:
            if len(macd_hist) < 3:
                return '数据不足'
            
            recent_hist = macd_hist.tail(3).values
            if len(recent_hist) >= 2:
                if recent_hist[-1] > recent_hist[-2]:
                    return '连续放大'
                elif recent_hist[-1] < recent_hist[-2]:
                    return '连续缩短'
            return '无变化'
        except Exception:
            return '无变化'
    
    def _check_golden_cross(self, macd_info: Dict) -> str:
        """检查MACD金叉死叉状态"""
        try:
            dif = macd_info.get('DIF', pd.Series())
            dea = macd_info.get('DEA', pd.Series())
            
            if len(dif) < 2 or len(dea) < 2:
                return '数据不足'
            
            current_dif = dif.iloc[-1]
            current_dea = dea.iloc[-1]
            prev_dif = dif.iloc[-2]
            prev_dea = dea.iloc[-2]
            
            # 金叉：DIF上穿DEA
            if prev_dif <= prev_dea and current_dif > current_dea:
                return 'DIF金叉DEA'
            # 死叉：DIF下穿DEA
            elif prev_dif >= prev_dea and current_dif < current_dea:
                return 'DIF死叉DEA'
            else:
                return '无交叉'
        except Exception:
            return '无交叉'
    
    def _get_bb_position(self, current_price: float, bb_info: Dict) -> str:
        """获取布林带位置"""
        try:
            bb_upper = bb_info.get('upper', pd.Series()).iloc[-1] if len(bb_info.get('upper', [])) > 0 else current_price * 1.02
            bb_lower = bb_info.get('lower', pd.Series()).iloc[-1] if len(bb_info.get('lower', [])) > 0 else current_price * 0.98
            
            if current_price >= bb_upper:
                return '突破上轨'
            elif current_price <= bb_lower:
                return '跌破下轨'
            else:
                return '区间内'
        except Exception:
            return '区间内'
    
    def _create_signal_result(self, stock_code: str, data: pd.DataFrame, 
                             indicators: Dict, scores: Dict, 
                             signal_dict: Dict, rsi_thresholds: Dict) -> SignalResult:
        """
        从信号字典创建SignalResult对象
        
        这是阶段6的核心方法：将所有计算结果封装到SignalResult对象中，
        确保单一数据源原则，避免重复计算。
        """
        try:
            # 获取当前数据
            current_data = data.iloc[-1]
            current_date = current_data.name if hasattr(current_data.name, 'strftime') else datetime.now()
            
            # 获取股票名称
            stock_name = signal_dict.get('detailed_info', {}).get('stock_name', stock_code)
            
            # 获取行业信息
            industry_info = self._get_stock_industry_info(stock_code)
            industry = industry_info.get('industry_name', '未知行业')
            
            # 提取技术指标值
            tech_indicators = signal_dict.get('technical_indicators', {})
            details = signal_dict.get('details', {})
            
            # 获取EMA信息
            ema_value = tech_indicators.get('ema_20w', details.get('ema', 0.0))
            ema_trend = 'flat'
            ema_slope = 0.0
            
            # 获取MACD信息
            macd_value = details.get('macd_dif', 0.0)
            macd_signal_val = details.get('macd_dea', 0.0)
            macd_histogram = details.get('macd_hist', 0.0)
            macd_histogram_prev = 0.0
            
            # 判断MACD交叉
            macd_cross = None
            if macd_value > macd_signal_val and macd_histogram > 0:
                macd_cross = 'golden'
            elif macd_value < macd_signal_val and macd_histogram < 0:
                macd_cross = 'death'
            
            # 获取布林带信息
            bb_upper = tech_indicators.get('bb_upper', 0.0)
            bb_middle = tech_indicators.get('bb_middle', 0.0)
            bb_lower = tech_indicators.get('bb_lower', 0.0)
            
            # 计算布林带位置
            bb_position = 0.5
            if bb_upper > bb_lower and bb_upper > 0:
                bb_position = (current_data['close'] - bb_lower) / (bb_upper - bb_lower)
                bb_position = max(0.0, min(1.0, bb_position))
            
            # 获取成交量信息
            volume_ma_4 = tech_indicators.get('volume_ma_4w', 0.0)
            volume_ratio = 0.0
            if volume_ma_4 > 0:
                volume_ratio = current_data['volume'] / volume_ma_4
            
            # 获取RSI背离信息
            rsi_divergence = None
            if details.get('rsi_divergence'):
                div_str = str(details['rsi_divergence']).lower()
                if 'bullish' in div_str:
                    rsi_divergence = 'bullish'
                elif 'bearish' in div_str:
                    rsi_divergence = 'bearish'
            
            # 获取价值比信息
            dcf_value = signal_dict.get('dcf_value')
            price_value_ratio = signal_dict.get('value_price_ratio')
            
            # 构建触发原因列表
            trigger_reasons = []
            if signal_dict['signal'] in ['BUY', 'SELL']:
                trigger_reasons.append(signal_dict.get('reason', ''))
            
            # 创建SignalResult对象
            signal_result = SignalResult(
                stock_code=stock_code,
                stock_name=stock_name,
                date=current_date,
                signal_type=signal_dict['signal'].lower(),
                close_price=float(current_data['close']),
                open_price=float(current_data['open']),
                high_price=float(current_data['high']),
                low_price=float(current_data['low']),
                volume=float(current_data['volume']),
                trend_score=1.0 if (scores.get('trend_filter_high') or scores.get('trend_filter_low')) else 0.0,
                rsi_score=1.0 if (scores.get('overbought_oversold_high') or scores.get('overbought_oversold_low')) else 0.0,
                macd_score=1.0 if (scores.get('momentum_high') or scores.get('momentum_low')) else 0.0,
                volume_score=1.0 if (scores.get('extreme_price_volume_high') or scores.get('extreme_price_volume_low')) else 0.0,
                total_score=signal_dict.get('confidence', 0.0),
                ema_20=float(ema_value),
                ema_trend=ema_trend,
                ema_slope=float(ema_slope),
                rsi_value=float(details.get('rsi', tech_indicators.get('rsi', 0.0))),
                rsi_threshold_overbought=float(rsi_thresholds.get('overbought', 70.0)),
                rsi_threshold_oversold=float(rsi_thresholds.get('oversold', 30.0)),
                rsi_extreme_overbought=float(rsi_thresholds.get('extreme_overbought', 80.0)),
                rsi_extreme_oversold=float(rsi_thresholds.get('extreme_oversold', 20.0)),
                rsi_divergence=rsi_divergence,
                macd_value=float(macd_value),
                macd_signal=float(macd_signal_val),
                macd_histogram=float(macd_histogram),
                macd_histogram_prev=float(macd_histogram_prev),
                macd_cross=macd_cross,
                bb_upper=float(bb_upper),
                bb_middle=float(bb_middle),
                bb_lower=float(bb_lower),
                bb_position=float(bb_position),
                volume_ma_4=float(volume_ma_4),
                volume_ratio=float(volume_ratio),
                dcf_value=float(dcf_value) if dcf_value else None,
                price_value_ratio=float(price_value_ratio) if price_value_ratio else None,
                industry=industry,
                trigger_reasons=trigger_reasons
            )
            
            return signal_result
            
        except Exception as e:
            self.logger.error(f"创建SignalResult对象失败: {e}")
            raise

if __name__ == "__main__":
    # 测试代码
    import os
    import sys
    sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    
    from data.data_fetcher import AkshareDataFetcher
    from data.data_processor import DataProcessor
    
    logging.basicConfig(level=logging.INFO)
    
    # 测试配置
    config = {
        'ema_period': 20,
        'rsi_period': 14,
        'rsi_overbought': 70,
        'rsi_oversold': 30
    }
    
    # 创建信号生成器
    signal_gen = SignalGenerator(config)
    
    print("🚀 信号生成器测试")
    print("=" * 50)
    
    try:
        # 获取测试数据
        fetcher = AkshareDataFetcher()
        processor = DataProcessor()
        
        # 获取中国神华数据
        stock_code = "601088"
        end_date = "2025-01-01"
        start_date = "2023-01-01"
        
        print(f"获取 {stock_code} 数据...")
        daily_data = fetcher.get_stock_data(stock_code, start_date, end_date)
        
        if daily_data is not None and not daily_data.empty:
            # 转换为周线
            weekly_data = processor.resample_to_weekly(daily_data)
            print(f"✅ 获取到 {len(weekly_data)} 条周线数据")
            
            # 生成信号
            signal_result = signal_gen.generate_signal(stock_code, weekly_data)
            
            print("\n📊 信号生成结果:")
            print("-" * 30)
            print(signal_gen.get_signal_explanation(signal_result))
            
        else:
            print("❌ 数据获取失败")
            
    except Exception as e:
        print(f"❌ 测试失败: {e}")
        import traceback
        traceback.print_exc()