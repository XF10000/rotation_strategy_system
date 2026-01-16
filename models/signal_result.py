"""
信号结果模型

包含信号生成的所有详细信息，作为信号生成和报告生成之间的数据契约。
确保单一数据源原则，避免重复计算。
"""

from dataclasses import dataclass, field
from datetime import datetime
from typing import Dict, List, Optional


@dataclass
class SignalResult:
    """
    信号结果 - 包含所有计算细节
    
    作为信号生成和报告生成之间的数据契约，确保单一数据源原则。
    所有技术指标、阈值、评分等信息都在信号生成时计算一次，
    报告生成时直接使用，避免重复计算和不一致。
    
    Attributes:
        stock_code: 股票代码
        stock_name: 股票名称
        date: 信号日期
        signal_type: 信号类型 ('buy' / 'sell' / 'hold')
        close_price: 收盘价
        open_price: 开盘价
        high_price: 最高价
        low_price: 最低价
        volume: 成交量
        trend_score: 趋势维度评分
        rsi_score: RSI维度评分
        macd_score: MACD维度评分
        volume_score: 成交量维度评分
        total_score: 总评分
        ... (其他技术指标详情)
    """
    
    # 基本信息
    stock_code: str
    stock_name: str
    date: datetime
    signal_type: str  # 'buy' / 'sell' / 'hold'
    
    # 价格信息
    close_price: float
    open_price: float
    high_price: float
    low_price: float
    volume: float
    
    # 4维度评分
    trend_score: float = 0.0
    rsi_score: float = 0.0
    macd_score: float = 0.0
    volume_score: float = 0.0
    total_score: float = 0.0
    
    # 趋势过滤器详情
    ema_20: float = 0.0
    ema_trend: str = 'flat'  # 'up' / 'down' / 'flat'
    ema_slope: float = 0.0
    
    # RSI详情
    rsi_value: float = 0.0
    rsi_threshold_overbought: float = 70.0
    rsi_threshold_oversold: float = 30.0
    rsi_extreme_overbought: float = 80.0
    rsi_extreme_oversold: float = 20.0
    rsi_divergence: Optional[str] = None  # 'bullish' / 'bearish' / None
    
    # MACD详情
    macd_value: float = 0.0
    macd_signal: float = 0.0
    macd_histogram: float = 0.0
    macd_histogram_prev: float = 0.0
    macd_cross: Optional[str] = None  # 'golden' / 'death' / None
    
    # 布林带详情
    bb_upper: float = 0.0
    bb_middle: float = 0.0
    bb_lower: float = 0.0
    bb_position: float = 0.0  # 价格在布林带中的位置 (0-1)
    
    # 成交量详情
    volume_ma_4: float = 0.0
    volume_ratio: float = 0.0
    
    # 价值比详情（如果有DCF数据）
    dcf_value: Optional[float] = None
    price_value_ratio: Optional[float] = None
    
    # 行业信息
    industry: Optional[str] = None
    
    # 触发原因
    trigger_reasons: List[str] = field(default_factory=list)
    
    def to_dict(self) -> Dict:
        """
        转换为字典供报告使用
        
        Returns:
            Dict: 包含所有字段的字典
        """
        return {
            # 基本信息
            'stock_code': self.stock_code,
            'stock_name': self.stock_name,
            'date': self.date.strftime('%Y-%m-%d') if isinstance(self.date, datetime) else str(self.date),
            'signal_type': self.signal_type,
            
            # 价格信息
            'close_price': self.close_price,
            'open_price': self.open_price,
            'high_price': self.high_price,
            'low_price': self.low_price,
            'volume': self.volume,
            
            # 评分
            'trend_score': self.trend_score,
            'rsi_score': self.rsi_score,
            'macd_score': self.macd_score,
            'volume_score': self.volume_score,
            'total_score': self.total_score,
            
            # 趋势
            'ema_20': self.ema_20,
            'ema_trend': self.ema_trend,
            'ema_slope': self.ema_slope,
            
            # RSI
            'rsi_value': self.rsi_value,
            'rsi_threshold_overbought': self.rsi_threshold_overbought,
            'rsi_threshold_oversold': self.rsi_threshold_oversold,
            'rsi_extreme_overbought': self.rsi_extreme_overbought,
            'rsi_extreme_oversold': self.rsi_extreme_oversold,
            'rsi_divergence': self.rsi_divergence,
            
            # MACD
            'macd_value': self.macd_value,
            'macd_signal': self.macd_signal,
            'macd_histogram': self.macd_histogram,
            'macd_histogram_prev': self.macd_histogram_prev,
            'macd_cross': self.macd_cross,
            
            # 布林带
            'bb_upper': self.bb_upper,
            'bb_middle': self.bb_middle,
            'bb_lower': self.bb_lower,
            'bb_position': self.bb_position,
            
            # 成交量
            'volume_ma_4': self.volume_ma_4,
            'volume_ratio': self.volume_ratio,
            
            # 价值比
            'dcf_value': self.dcf_value,
            'price_value_ratio': self.price_value_ratio,
            
            # 行业
            'industry': self.industry,
            
            # 触发原因
            'trigger_reasons': self.trigger_reasons,
        }
    
    def get_signal_summary(self) -> str:
        """
        获取信号摘要
        
        Returns:
            str: 信号摘要字符串
        """
        return f"{self.signal_type.upper()} - {self.stock_name}({self.stock_code}) - {self.date}"
    
    def meets_criteria(self) -> bool:
        """
        判断是否满足信号条件
        
        4维信号系统：趋势过滤器（硬性条件）+ 其他3维至少2个
        
        Returns:
            bool: 是否满足信号条件
        """
        # 趋势过滤器必须通过
        if self.trend_score <= 0:
            return False
        
        # 其他3维至少2个
        other_scores = self.rsi_score + self.macd_score + self.volume_score
        return other_scores >= 2
    
    def get_dimension_details(self) -> Dict[str, str]:
        """
        获取各维度详细信息
        
        Returns:
            Dict[str, str]: 各维度的详细说明
        """
        details = {}
        
        # 趋势维度
        if self.trend_score > 0:
            details['trend'] = f"EMA20趋势{self.ema_trend}，斜率{self.ema_slope:.4f}"
        else:
            details['trend'] = "趋势不符合"
        
        # RSI维度
        if self.rsi_score > 0:
            rsi_desc = f"RSI={self.rsi_value:.2f}"
            if self.rsi_divergence:
                rsi_desc += f"，{self.rsi_divergence}背离"
            details['rsi'] = rsi_desc
        else:
            details['rsi'] = f"RSI={self.rsi_value:.2f}（未触发）"
        
        # MACD维度
        if self.macd_score > 0:
            macd_desc = f"MACD柱状图={self.macd_histogram:.4f}"
            if self.macd_cross:
                macd_desc += f"，{self.macd_cross}交叉"
            details['macd'] = macd_desc
        else:
            details['macd'] = f"MACD柱状图={self.macd_histogram:.4f}（未触发）"
        
        # 成交量维度
        if self.volume_score > 0:
            details['volume'] = f"成交量比={self.volume_ratio:.2f}，布林带位置={self.bb_position:.2f}"
        else:
            details['volume'] = f"成交量比={self.volume_ratio:.2f}（未触发）"
        
        return details
    
    def __str__(self) -> str:
        """字符串表示"""
        return self.get_signal_summary()
    
    def __repr__(self) -> str:
        """调试表示"""
        return (
            f"SignalResult(stock_code='{self.stock_code}', "
            f"date='{self.date}', signal_type='{self.signal_type}', "
            f"total_score={self.total_score})"
        )
