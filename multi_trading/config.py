"""Configuration objects for the crypto futures AI agent."""
from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Sequence


@dataclass(slots=True)
class DataConfig:
    """Configuration for loading historical market data."""

    data_path: Path
    symbol: str = "BTCUSDT"
    timeframe: str = "1h"
    features: Sequence[str] = field(
        default_factory=lambda: ["close", "volume", "funding_rate"]
    )


@dataclass(slots=True)
class StrategyConfig:
    """Configuration for the trading strategy and learning process."""

    lookback: int = 24
    learning_rate: float = 0.1
    discount_factor: float = 0.9
    exploration_rate: float = 0.2
    min_exploration_rate: float = 0.02
    exploration_decay: float = 0.995
    stop_loss: float = 0.02
    take_profit: float = 0.03
    transaction_fee: float = 0.0004


@dataclass(slots=True)
class BacktestConfig:
    """Configuration for backtesting the agent."""

    initial_balance: float = 10_000.0
    contract_size: float = 0.001  # e.g. BTC contract size on perpetual futures
    max_position: float = 0.01
    slippage: float = 0.0002
    transaction_fee: float = 0.0004
    seed: int | None = 7


__all__ = ["DataConfig", "StrategyConfig", "BacktestConfig"]
