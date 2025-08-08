"""
信号生成器
严格按照设计文档实现4维度评分系统的信号生成逻辑
"""

import pandas as pd
import numpy as np
from typing import Dict, List, Tuple, Optional
import logging
from datetime import datetime

import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from indicators.trend import calculate_ema, detect_ema_trend
from indicators.momentum import calculate_rsi, calculate_macd
from indicators.volatility import calculate_bollinger_bands
from indicators.divergence import detect_rsi_divergence, detect_macd_divergence
from strategy.exceptions import SignalGenerationError, InsufficientDataError
from config.industry_rsi_thresholds import get_rsi_thresholds, get_industry_from_stock_code
from config.industry_signal_rules import get_industry_signal_rules, should_require_divergence
from config.comprehensive_industry_rules import get_comprehensive_industry_rules
from config.industry_rsi_loader import get_industry_rsi_thresholds, get_rsi_loader
from config.enhanced_industry_rsi_loader import get_enhanced_rsi_loader
from config.stock_industry_mapping import get_stock_industry
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
    
    def __init__(self, config: Dict, dcf_values: Dict[str, float] = None):
        """
        初始化信号生成器
        
        Args:
            config: 配置参数
            dcf_values: DCF估值数据字典 {股票代码: DCF估值}
        """
        self.config = config
        self.logger = logging.getLogger("strategy.SignalGenerator")
        
        # 存储DCF估值数据
        self.dcf_values = dcf_values or {}
        
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
            'min_data_length': 60,      # 最小数据长度
            # V1.1新增：价值比过滤器阈值
            'value_ratio_sell_threshold': 80.0,  # 卖出阈值：价值比 > 80%
            'value_ratio_buy_threshold': 70.0,   # 买入阈值：价值比 < 70%
        }
        
        # 合并配置
        self.params = {**self.default_params, **config}
        
        # 添加行业信息缓存
        self._industry_cache = {}
        self._industry_rules_cache = {}
        
        self.logger.info("信号生成器初始化完成")
        self.logger.info("行业信息缓存已启用，将显著提升回测性能")
        
        # 记录DCF数据状态
        if self.dcf_values:
            self.logger.info(f"已加载 {len(self.dcf_values)} 只股票的DCF估值数据")
            self.logger.info("将使用价值比过滤器 (V1.1策略)")
        else:
            self.logger.warning("未提供DCF估值数据，将回退到EMA趋势过滤器")
    
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
            # 数据验证
            if data is None or data.empty:
                raise InsufficientDataError(f"股票 {stock_code} 数据为空")
            
            if len(data) < self.params['min_data_length']:
                raise InsufficientDataError(
                    f"股票 {stock_code} 数据不足，需要至少 {self.params['min_data_length']} 条记录"
                )
            
            # 计算技术指标
            indicators = self._calculate_indicators(data)
            
            # 4维度评分 - 传入股票代码以支持行业特定阈值
            scores = self._calculate_4d_scores(data, indicators, stock_code)
            
            # 生成最终信号
            signal_result = self._generate_final_signal(stock_code, scores, indicators)
            
            # 将重新计算的技术指标添加到结果中
            extracted_indicators = self._extract_current_indicators(data, indicators)
            self.logger.debug(f"提取的技术指标: {extracted_indicators}")
            signal_result['technical_indicators'] = extracted_indicators
            
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
            
            # 1. 趋势指标 - 使用TA-Lib
            indicators['ema'] = calculate_ema(close_prices, self.params['ema_period'])
            
            # 2. 动量指标 - 使用TA-Lib
            indicators['rsi'] = calculate_rsi(close_prices, self.params['rsi_period'])
            
            macd_result = calculate_macd(
                close_prices, 
                self.params['macd_fast'],
                self.params['macd_slow'],
                self.params['macd_signal']
            )
            indicators['macd'] = {
                'DIF': macd_result['dif'],
                'DEA': macd_result['dea'], 
                'HIST': macd_result['hist']
            }
            
            # 3. 波动率指标 - 使用TA-Lib
            indicators['bb'] = calculate_bollinger_bands(
                close_prices, 
                self.params['bb_period'],
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
                    df = pd.read_csv('Input/portfolio_config.csv', encoding='utf-8-sig')
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
                # 使用价值比过滤器 (V1.1策略)
                price_value_ratio = (current_price / dcf_value) * 100
                
                self.logger.debug(f"价值比过滤器: 收盘价={current_price:.2f}, DCF估值={dcf_value:.2f}, 价值比={price_value_ratio:.1f}%")
                
                # 支持卖出信号：收盘价 > DCF每股估值的80% (价值比 > 80%)
                if price_value_ratio > 80.0:
                    scores['trend_filter_high'] = True
                    self.logger.debug(f"价值比过滤器支持卖出: {price_value_ratio:.1f}% > 80%")
                
                # 支持买入信号：收盘价 < DCF每股估值的70% (价值比 < 70%)
                if price_value_ratio < 70.0:
                    scores['trend_filter_low'] = True
                    self.logger.debug(f"价值比过滤器支持买入: {price_value_ratio:.1f}% < 70%")
            
            # 2. 超买/超卖 - 支持行业特定阈值
            rsi_current = indicators['rsi'].iloc[-1]
            
            
            # 获取行业特定的RSI阈值 - 使用增强版加载器
            rsi_overbought = self.params['rsi_overbought']  # 默认阈值
            rsi_oversold = self.params['rsi_oversold']      # 默认阈值
            
            if stock_code:
                try:
                    # 使用缓存的行业信息获取方法
                    industry = self._get_stock_industry_cached(stock_code)
                    
                    # 优先使用增强版RSI阈值加载器（动态计算的阈值）
                    if industry:
                        try:
                            enhanced_loader = get_enhanced_rsi_loader()
                            rsi_thresholds = enhanced_loader.get_rsi_thresholds(industry, use_extreme=False)
                            rsi_overbought = rsi_thresholds['overbought']
                            rsi_oversold = rsi_thresholds['oversold']
                            self.logger.debug(f"股票 {stock_code} 行业 {industry} 动态RSI阈值: 超买={rsi_overbought:.2f}, 超卖={rsi_oversold:.2f}")
                        except Exception as enhanced_e:
                            self.logger.warning(f"从增强版加载器获取行业 {industry} RSI阈值失败: {enhanced_e}，回退到原有配置")
                            # 回退到原有的CSV配置
                            try:
                                rsi_loader = get_rsi_loader()
                                rsi_thresholds = rsi_loader.get_rsi_thresholds(industry)
                                rsi_overbought = rsi_thresholds['overbought']
                                rsi_oversold = rsi_thresholds['oversold']
                                self.logger.debug(f"股票 {stock_code} 行业 {industry} 静态RSI阈值: 超买={rsi_overbought}, 超卖={rsi_oversold}")
                            except Exception as csv_e:
                                self.logger.warning(f"从静态配置加载行业 {industry} RSI阈值也失败: {csv_e}，使用默认阈值")
                except Exception as e:
                    self.logger.warning(f"获取股票 {stock_code} 行业RSI阈值失败: {e}，使用默认阈值")
            
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
            
            # 阶段高点：14周RSI > 行业特定超买阈值 且 (出现顶背离 或 不要求背离)
            rsi_high_condition = (not pd.isna(rsi_current) and rsi_current >= rsi_overbought and 
                                (rsi_divergence['top_divergence'] or not need_divergence_sell))
            if rsi_high_condition:
                scores['overbought_oversold_high'] = True
            
            # 阶段低点：14周RSI <= 行业特定超卖阈值 且 (出现底背离 或 不要求背离)
            rsi_low_condition = (not pd.isna(rsi_current) and rsi_current <= rsi_oversold and 
                               (rsi_divergence['bottom_divergence'] or not need_divergence_buy))
            if rsi_low_condition:
                scores['overbought_oversold_low'] = True
                
            # 记录RSI分析详情
            self.logger.debug(f"RSI分析: 当前值={rsi_current:.2f}, 超买阈值={rsi_overbought}, 超卖阈值={rsi_oversold}")
            self.logger.debug(f"RSI背离: 顶背离={rsi_divergence['top_divergence']}, 底背离={rsi_divergence['bottom_divergence']}")
            self.logger.debug(f"RSI条件: 高点={rsi_high_condition}, 低点={rsi_low_condition}")
            
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
                
                # 阶段高点（卖出）：MACD红色柱体连续2根缩短 或 MACD柱体已为绿色 或 DIF死叉DEA
                sell_conditions = [red_hist_shrinking, macd_is_green, dif_cross_down]
                if any(sell_conditions):
                    scores['momentum_high'] = True
                
                # 阶段低点（买入）：MACD绿色柱体连续2根缩短 或 MACD柱体已为红色 或 DIF金叉DEA
                buy_conditions = [green_hist_shrinking, macd_is_red, dif_cross_up]
                if any(buy_conditions):
                    scores['momentum_low'] = True
                
                # 调试日志
                self.logger.debug(f"动能确认 - 卖出条件: 红色缩短={red_hist_shrinking}, 已转绿色={macd_is_green}, DIF死叉={dif_cross_down}")
                self.logger.debug(f"动能确认 - 买入条件: 绿色缩短={green_hist_shrinking}, 已转红色={macd_is_red}, DIF金叉={dif_cross_up}")
            
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
            
            # 阶段高点：收盘价 ≥ 布林上轨 且 本周量 ≥ 4周均量 × 1.3
            if (not pd.isna(bb_upper) and not pd.isna(volume_ma) and
                current_price >= bb_upper and 
                current_volume >= volume_ma * self.params['volume_sell_ratio']):
                scores['extreme_price_volume_high'] = True
            
            # 阶段低点：收盘价 ≤ 布林下轨 且 本周量 ≥ 4周均量 × 0.8
            if (not pd.isna(bb_lower) and not pd.isna(volume_ma) and
                current_price <= bb_lower and 
                current_volume >= volume_ma * self.params['volume_buy_ratio']):
                scores['extreme_price_volume_low'] = True
            
            return scores
            
        except Exception as e:
            raise SignalGenerationError(f"4维度评分计算失败: {str(e)}") from e
    
    def _generate_final_signal(self, stock_code: str, scores: Dict, indicators: Dict, rsi_thresholds: Dict = None) -> Dict:
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
                return {
                    'signal': 'HOLD',
                    'confidence': 0.0,
                    'reason': '趋势过滤器不支持任何交易信号',
                    'scores': scores,
                    'details': self._get_signal_details(indicators),
                    'rsi_thresholds': rsi_thresholds
                }
            
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
                    confidence_score = 1 + high_signal_count  # 1-4分
                    return {
                        'signal': 'SELL',
                        'confidence': confidence_score,
                        'reason': f'卖出信号：价值比过滤器+{high_signal_count}个卖出维度',
                        'scores': scores,
                        'details': self._get_signal_details(indicators),
                        'action': '卖出10%'
                    }
            
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
                    confidence_score = 1 + low_signal_count  # 1-4分
                    return {
                        'signal': 'BUY',
                        'confidence': confidence_score,
                        'reason': f'买入信号：价值比过滤器+{low_signal_count}个买入维度',
                        'scores': scores,
                        'details': self._get_signal_details(indicators),
                        'action': '买入10%'
                    }
            
            # 信号不足，持有
            high_count = sum(1 for signal in [scores['overbought_oversold_high'], 
                                            scores['momentum_high'], 
                                            scores['extreme_price_volume_high']] if signal)
            low_count = sum(1 for signal in [scores['overbought_oversold_low'], 
                                           scores['momentum_low'], 
                                           scores['extreme_price_volume_low']] if signal)
            
            return {
                'signal': 'HOLD',
                'confidence': 0.0,
                'reason': f'信号不足(卖出:{high_count},买入:{low_count})',
                'scores': scores,
                'details': self._get_signal_details(indicators)
            }
            
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
            
            # 提取各项技术指标 - 使用数据处理器的字段名
            ema_20w = smart_get_from_data('ema_20', indicators.get('ema'), current_close)
            ema_60w = smart_get_from_data('ema_50', indicators.get('ema'), current_close)  # 使用ema_50作为60周替代
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

if __name__ == "__main__":
    # 测试代码
    import sys
    import os
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