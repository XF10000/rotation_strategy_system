"""
鹿鼎公策略 - 动态仓位管理器
估值定仓位上限 + 分批建仓 + 步进止盈
"""
import logging
from dataclasses import dataclass
from typing import Dict, Optional, Tuple

from .ludinggong_signal import DEFAULT_PARAMS, ZoneResult

logger = logging.getLogger(__name__)


@dataclass
class TradeDecision:
    """单笔交易决策"""
    action: str          # 'BUY' | 'SELL' | 'HOLD'
    shares: int = 0
    estimated_amount: float = 0.0
    reason: str = ''


class LudinggongPositionManager:
    """鹿鼎公仓位管理器"""

    def __init__(self, total_capital: float,
                 max_single_stock_ratio: float = 0.20,
                 params: Optional[Dict] = None):
        self.total_capital = total_capital
        self.max_single_stock_ratio = max_single_stock_ratio
        self.params = {**DEFAULT_PARAMS, **(params or {})}

        # 单只股票分配资金上限 = 总资金 × 20%
        self.per_stock_cap = total_capital * max_single_stock_ratio

    def update_total_capital(self, total_capital: float):
        """更新总资产锚定点（市值增长后调用）"""
        self.total_capital = total_capital
        self.per_stock_cap = total_capital * self.max_single_stock_ratio

    def get_valuation_zone(self, value_ratio: float) -> Tuple[str, float, str]:
        """估值区间判定 → (名称, 仓位上限占分配上限比例, 操作权限)"""
        if value_ratio < 0.70:
            return '极度低估', 1.0, 'buy_only'
        elif value_ratio < 0.80:
            return '低估', 0.80, 'buy_sell'
        elif value_ratio < 1.10:
            return '合理', 0.60, 'sell_only'
        elif value_ratio < 1.30:
            return '合理偏高', 0.30, 'sell_only'
        else:
            return '高估', 0.10, 'sell_only'

    def get_max_position_value(self, zone_max_ratio: float) -> float:
        """
        当前估值区间允许的最大持仓市值
        = 单票分配上限 × 估值区间仓位上限
        """
        return self.per_stock_cap * zone_max_ratio

    def calculate_buy_decision(self, stock_code: str, price: float,
                                zone_result: ZoneResult,
                                current_shares: int,
                                available_cash: float) -> TradeDecision:
        """
        计算买入决策

        鹿鼎公买入逻辑：
        - 止跌区：买入 分配上限 × zone_max_ratio × buy_pct（试探性建仓）
        - 蓄力区：买入到 zone_max_ratio 上限（加仓到满）
        - 受单票分配上限和可用现金约束
        """
        if zone_result.signal != 'BUY':
            return TradeDecision(action='HOLD', reason='非买入信号')

        max_position_value = self.get_max_position_value(zone_result.zone_max_ratio)
        current_position_value = current_shares * price

        # 已达上限
        if current_position_value >= max_position_value:
            return TradeDecision(
                action='HOLD',
                reason=f'已达估值区间上限(max={max_position_value:,.0f})',
            )

        if zone_result.zone == 'zone2_accumulate':
            # 蓄力区：补仓到估值区间上限
            target_value = max_position_value
        else:
            # 止跌区：按信号比例买入
            target_value = max_position_value * zone_result.buy_pct
            # 如果已有持仓，在现有基础上加
            if current_shares > 0:
                target_value = min(
                    current_position_value + target_value,
                    max_position_value
                )

        # 剩余可买空间
        remaining_capacity = max_position_value - current_position_value
        buy_value = min(target_value - current_position_value, remaining_capacity)

        if buy_value <= 0:
            return TradeDecision(action='HOLD', reason='无可买空间')

        # 现金约束
        buy_value = min(buy_value, available_cash)

        shares = int(buy_value / price)
        shares = (shares // 100) * 100  # 100股整数倍

        if shares < 100:
            return TradeDecision(
                action='HOLD',
                reason=f'最小交易单位不足(计算{shares}股)',
            )

        estimated_amount = shares * price
        if estimated_amount > available_cash:
            return TradeDecision(
                action='HOLD',
                reason=f'现金不足(需{estimated_amount:,.0f},可用{available_cash:,.0f})',
            )

        zone_label = '蓄力区加仓' if zone_result.zone == 'zone2_accumulate' else '止跌区买入'
        return TradeDecision(
            action='BUY',
            shares=shares,
            estimated_amount=estimated_amount,
            reason=f'{zone_label}: {zone_result.reason}',
        )

    def calculate_sell_decision(self, stock_code: str, price: float,
                                 zone_result: ZoneResult,
                                 current_shares: int) -> TradeDecision:
        """
        计算卖出决策

        鹿鼎公卖出逻辑：
        - pre_sell: 卖出当前持仓 × 1/3
        - first_sell: 卖出当前持仓 × 1/3
        - second_sell: 卖出剩余持仓 × 1/2
        """
        if zone_result.signal != 'SELL':
            return TradeDecision(action='HOLD', reason='非卖出信号')

        if current_shares <= 0:
            return TradeDecision(action='HOLD', reason='无持仓')

        if zone_result.sell_step == 'clear_all':
            # 高估清仓：全部卖出，不取整到100股
            shares_to_sell = current_shares
        else:
            shares_to_sell = int(current_shares * zone_result.sell_pct)
            shares_to_sell = (shares_to_sell // 100) * 100

            if shares_to_sell < 100:
                if current_shares >= 100:
                    shares_to_sell = 100
                else:
                    return TradeDecision(action='HOLD', reason='持仓不足100股')

            shares_to_sell = min(shares_to_sell, current_shares)

        step_label = {
            'pre_sell': '预减仓1/3',
            'first_sell': '首次止盈1/3',
            'second_sell': '加卖剩余1/2',
            'clear_all': '高估清仓',
        }.get(zone_result.sell_step, zone_result.sell_step or '')

        return TradeDecision(
            action='SELL',
            shares=shares_to_sell,
            estimated_amount=shares_to_sell * price,
            reason=f'{step_label}: {zone_result.reason}',
        )

    def enforce_permission(self, decision: TradeDecision,
                           zone_result: ZoneResult) -> TradeDecision:
        """
        估值权限过滤：强制覆盖不允許的操作
        - buy_only 区间禁止卖出
        - sell_only 区间禁止买入
        """
        if decision.action == 'SELL' and zone_result.permission == 'buy_only':
            if zone_result.sell_step == 'pre_sell':
                # 极度低估下允许预减仓（RSI极端超买）
                return decision
            return TradeDecision(
                action='HOLD',
                reason=f'极度低估禁止卖出(原信号: {decision.reason})',
            )
        if decision.action == 'BUY' and zone_result.permission == 'sell_only':
            return TradeDecision(
                action='HOLD',
                reason=f'{zone_result.valuation_zone}区间禁止买入(原信号: {decision.reason})',
            )
        return decision
