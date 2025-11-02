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
        self._stop_loss_ratio = max(0.0, stop_loss)
        self._take_profit_ratio = max(self._stop_loss_ratio, take_profit)
        self._stop_price: float | None = None
        self._break_even_trigger = 0.0
        self._trailing_step = 0.0
        self._trailing_anchor: float | None = None
        self._next_position_size = self.config.max_position
        return EnvironmentState(self.balance, self.position, self.entry_price, self.equity)

    def set_dynamic_position_size(self, size: float) -> None:
        """Set the absolute position size to be used for the next entry."""

        if size <= 0:
            self._next_position_size = 0.0
            return
        self._next_position_size = min(size, self.config.max_position)

    def configure_risk_controls(self, *, break_even_trigger: float, trailing_step: float) -> None:
        """Set dynamic risk parameters applied while a position is open."""

        self._break_even_trigger = max(0.0, break_even_trigger)
        self._trailing_step = max(0.0, trailing_step)

    def current_protective_stop(self) -> float | None:
        """Return the absolute stop level currently protecting the position."""

        return self._stop_price

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
        if self._stop_loss_ratio > 0:
            if self.position > 0:
                self._stop_price = self.entry_price * (1 - self._stop_loss_ratio)
            else:
                self._stop_price = self.entry_price * (1 + self._stop_loss_ratio)
        else:
            self._stop_price = None
        self._trailing_anchor = self.entry_price

    def _close_position(self, price: float) -> None:
        if self.position == 0:
            return
        realized_pnl = self.position * self.config.contract_size * (price - self.entry_price)
        fee = abs(self.position) * self.config.contract_size * price * self.config.transaction_fee
        self.balance += realized_pnl - fee
        self.position = 0.0
        self.entry_price = None
        self._stop_price = None
        self._trailing_anchor = None

    def _apply_risk_controls(self, price: float) -> None:
        if self.position == 0 or self.entry_price is None:
            return
        direction = 1.0 if self.position > 0 else -1.0
        performance = direction * (price - self.entry_price) / self.entry_price

        # Promote the stop to break-even when the trade has moved sufficiently in profit
        if (
            self._break_even_trigger > 0
            and performance >= self._break_even_trigger
            and self._stop_price is not None
        ):
            if direction > 0:
                self._stop_price = max(self._stop_price, self.entry_price)
            else:
                self._stop_price = min(self._stop_price, self.entry_price)

        # Trail the stop with favourable structure-based moves
        if self._trailing_step > 0 and self._stop_price is not None:
            if direction > 0:
                self._trailing_anchor = max(self._trailing_anchor or price, price)
                trail_price = (self._trailing_anchor or price) * (1 - self._trailing_step)
                self._stop_price = max(self._stop_price, trail_price)
            else:
                self._trailing_anchor = min(self._trailing_anchor or price, price)
                trail_price = (self._trailing_anchor or price) * (1 + self._trailing_step)
                self._stop_price = min(self._stop_price, trail_price)

        should_close = False
        if self._stop_price is not None:
            if direction > 0 and price <= self._stop_price:
                should_close = True
            elif direction < 0 and price >= self._stop_price:
                should_close = True

        if self._take_profit_ratio > 0:
            target_price = (
                self.entry_price * (1 + self._take_profit_ratio)
                if direction > 0
                else self.entry_price * (1 - self._take_profit_ratio)
            )
            if (direction > 0 and price >= target_price) or (
                direction < 0 and price <= target_price
            ):
                should_close = True

        if should_close:
            self._close_position(price)

    def _mark_to_market(self, price: float) -> None:
        unrealized = 0.0
        if self.position != 0 and self.entry_price is not None:
            unrealized = self.position * self.config.contract_size * (price - self.entry_price)
        self.equity = max(0.0, self.balance + unrealized)


__all__ = ["FuturesBacktestEnvironment", "EnvironmentState"]
