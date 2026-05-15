"""
鹿鼎公策略 - 交易状态追踪器
追踪每只股票的交易回合状态（预减仓、首次止盈、交易回合活跃否）
"""
import logging
from dataclasses import dataclass, field
from datetime import datetime
from typing import Dict, Optional

logger = logging.getLogger(__name__)


@dataclass
class StockState:
    """单只股票的交易状态"""
    has_pre_sold: bool = False
    has_first_sold: bool = False
    transaction_round_active: bool = False
    round_entry_price: float = 0.0
    round_entry_date: Optional[datetime] = None
    last_sell_step: str = ""
    total_bought_this_round: int = 0
    was_oversold: bool = False  # 价格曾跌破布林下轨，且尚未因买入而重置
    vol_dried_up: bool = False  # 超跌期间出现过量能枯竭(MA5<MA20)
    was_rsi_oversold: bool = False  # 超跌期间RSI曾进入超卖区(<os)


class LudinggongStateTracker:
    """鹿鼎公交易状态追踪器"""

    def __init__(self):
        self.states: Dict[str, StockState] = {}

    def get_state(self, stock_code: str) -> StockState:
        if stock_code not in self.states:
            self.states[stock_code] = StockState()
        return self.states[stock_code]

    def has_any_sell_executed(self, stock_code: str) -> bool:
        state = self.get_state(stock_code)
        return state.has_pre_sold or state.has_first_sold

    def is_new_round_allowed(self, stock_code: str, value_ratio: float,
                             current_shares: int) -> bool:
        """
        判断是否允许开启新交易回合。
        条件：已清仓 且 价值比回落至买入区间 (< 0.80)
        """
        if current_shares > 0:
            return False
        if value_ratio >= 0.80:
            return False
        return True

    def start_new_round(self, stock_code: str, entry_price: float, entry_date):
        state = self.get_state(stock_code)
        state.transaction_round_active = True
        state.has_pre_sold = False
        state.has_first_sold = False
        state.last_sell_step = ""
        state.total_bought_this_round = 0
        state.round_entry_price = entry_price
        state.round_entry_date = entry_date
        self.reset_bottom_window(stock_code)
        logger.info(f"🆕 {stock_code} 开启新交易回合，入场价 {entry_price:.2f}")

    def record_buy(self, stock_code: str, shares: int):
        state = self.get_state(stock_code)
        state.transaction_round_active = True
        state.total_bought_this_round += shares

    def record_sell(self, stock_code: str, sell_step: str, shares_sold: int,
                    remaining_shares: int):
        state = self.get_state(stock_code)
        state.last_sell_step = sell_step
        if sell_step == 'pre_sell':
            state.has_pre_sold = True
        elif sell_step == 'first_sell':
            state.has_first_sold = True
        if remaining_shares <= 0:
            self._end_round(stock_code)

    def _end_round(self, stock_code: str):
        state = self.get_state(stock_code)
        state.transaction_round_active = False
        state.has_pre_sold = False
        state.has_first_sold = False
        self.reset_bottom_window(stock_code)
        state.last_sell_step = ""
        logger.info(f"🏁 {stock_code} 交易回合结束")

    def set_oversold(self, stock_code: str):
        """标记价格已跌破布林下轨"""
        self.get_state(stock_code).was_oversold = True

    def reset_oversold(self, stock_code: str):
        """重置超跌状态（买入后调用）"""
        self.get_state(stock_code).was_oversold = False

    def set_vol_dried_up(self, stock_code: str):
        """标记超跌期间出现过量能枯竭"""
        state = self.get_state(stock_code)
        if not state.vol_dried_up:
            state.vol_dried_up = True
            logger.debug(f"📉 {stock_code} 超跌期间量能枯竭确认(MA5<MA20)")

    def set_rsi_oversold(self, stock_code: str):
        """标记超跌期间RSI曾进入超卖区"""
        state = self.get_state(stock_code)
        if not state.was_rsi_oversold:
            state.was_rsi_oversold = True
            logger.debug(f"📉 {stock_code} 超跌期间RSI进入超卖区确认")

    def reset_bottom_window(self, stock_code: str):
        """价格回到中轨上方，关闭底部窗口，重置所有底部状态"""
        state = self.get_state(stock_code)
        state.was_oversold = False
        state.vol_dried_up = False
        state.was_rsi_oversold = False

    def get_state_summary(self, stock_code: str) -> dict:
        state = self.get_state(stock_code)
        return {
            'has_pre_sold': state.has_pre_sold,
            'has_first_sold': state.has_first_sold,
            'round_active': state.transaction_round_active,
            'entry_price': state.round_entry_price,
            'total_bought': state.total_bought_this_round,
        }
