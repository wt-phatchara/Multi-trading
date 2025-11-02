"""Backtesting environment for the crypto futures AI agent."""
from __future__ import annotations

from dataclasses import dataclass
from typing import Tuple

from ..config import BacktestConfig


@dataclass(slots=True)
class EnvironmentState:
    """Represents the account state of the agent at each timestep."""

    balance: float
    position: float
    entry_price: float | None
    equity: float


class FuturesBacktestEnvironment:
    """Simple mark-to-market environment for perpetual futures contracts."""

    ACTIONS = ("short", "flat", "long")

    def __init__(self, config: BacktestConfig) -> None:
        self.config = config
        self.reset()

    def reset(
        self,
        *,
        initial_price: float | None = None,
        stop_loss: float = 0.0,
        take_profit: float = 1.0,
    ) -> EnvironmentState:
        self.balance = self.config.initial_balance
        self.position = 0.0
        self.entry_price: float | None = None
        self.equity = self.balance
        self._last_price: float | None = initial_price
        self._stop_loss = max(0.0, stop_loss)
        self._take_profit = max(self._stop_loss, take_profit)
        self._next_position_size = self.config.max_position
        return EnvironmentState(self.balance, self.position, self.entry_price, self.equity)

    def set_dynamic_position_size(self, size: float) -> None:
        """Set the absolute position size to be used for the next entry."""

        if size <= 0:
            self._next_position_size = 0.0
            return
        self._next_position_size = min(size, self.config.max_position)

    def step(self, action: int, price: float) -> Tuple[EnvironmentState, float]:
        """Advance the environment using the closing price of the next candle."""

        if not 0 <= action < len(self.ACTIONS):
            raise ValueError(f"action index {action} out of range")
        if price <= 0:
            raise ValueError("price must be greater than zero")

        if self._last_price is None:
            self._last_price = price
        previous_equity = self.equity

        self._update_position(action, price)
        self._apply_risk_controls(price)
        self._mark_to_market(price)
        self._last_price = price

        reward = (self.equity - previous_equity) / self.config.initial_balance
        state = EnvironmentState(self.balance, self.position, self.entry_price, self.equity)
        return state, reward

    def _update_position(self, action: int, price: float) -> None:
        current_action = self.ACTIONS[action]

        if current_action == "flat":
            self._close_position(price)
            return

        if current_action == "long":
            desired_position = self._next_position_size
        else:
            desired_position = -self._next_position_size
        if self.position == desired_position:
            return

        if self.position != 0:
            self._close_position(price)

        self._open_position(desired_position, price)

    def _open_position(self, size: float, price: float) -> None:
        if size == 0:
            return

        fee = abs(size) * self.config.contract_size * price * self.config.transaction_fee
        self.balance -= fee
        slip = self.config.slippage if size > 0 else -self.config.slippage
        self.position = size
        self.entry_price = price * (1 + slip)

    def _close_position(self, price: float) -> None:
        if self.position == 0:
            return
        realized_pnl = self.position * self.config.contract_size * (price - self.entry_price)
        fee = abs(self.position) * self.config.contract_size * price * self.config.transaction_fee
        self.balance += realized_pnl - fee
        self.position = 0.0
        self.entry_price = None

    def _apply_risk_controls(self, price: float) -> None:
        if self.position == 0 or self.entry_price is None:
            return
        direction = 1.0 if self.position > 0 else -1.0
        performance = direction * (price - self.entry_price) / self.entry_price
        should_close = False
        if self._stop_loss > 0 and performance <= -self._stop_loss:
            should_close = True
        if self._take_profit > 0 and performance >= self._take_profit:
            should_close = True
        if should_close:
            self._close_position(price)

    def _mark_to_market(self, price: float) -> None:
        unrealized = 0.0
        if self.position != 0 and self.entry_price is not None:
            unrealized = self.position * self.config.contract_size * (price - self.entry_price)
        self.equity = max(0.0, self.balance + unrealized)


__all__ = ["FuturesBacktestEnvironment", "EnvironmentState"]
