"""Feature engineering helpers for the futures trading agent."""
from __future__ import annotations

from collections import deque
from dataclasses import dataclass
from datetime import datetime
from typing import Deque, Iterable, Iterator

import math

from ..data.data_provider import Candle


@dataclass(slots=True)
class FeatureVector:
    """Numeric representation of a candle used by the agent."""

    close_return: float
    volume_zscore: float
    funding_rate: float
    trend_strength: float

    def as_tuple(self) -> tuple[float, float, float, float]:
        return (self.close_return, self.volume_zscore, self.funding_rate, self.trend_strength)


@dataclass(slots=True)
class FeatureObservation:
    """Feature vector augmented with the market metadata for a timestep."""

    feature: FeatureVector
    price: float
    timestamp: datetime


class FeatureEngineer:
    """Transforms a stream of candles into agent-ready feature vectors."""

    def __init__(self, lookback: int = 24) -> None:
        if lookback <= 1:
            raise ValueError("lookback must be greater than 1")
        self.lookback = lookback
        self._close_window: Deque[float] = deque(maxlen=lookback)
        self._volume_window: Deque[float] = deque(maxlen=lookback)

    def reset(self) -> None:
        """Clear any buffered state from previous runs."""

        self._close_window.clear()
        self._volume_window.clear()

    def transform(self, candles: Iterable[Candle]) -> Iterator[FeatureObservation]:
        """Yield feature observations for each candle once enough history exists."""

        for candle in candles:
            self._close_window.append(candle.close)
            self._volume_window.append(candle.volume)
            if len(self._close_window) < self.lookback:
                continue

            closes = tuple(self._close_window)
            close_return = (closes[-1] - closes[0]) / closes[0]
            mean_volume = sum(self._volume_window) / self.lookback
            variance = sum((v - mean_volume) ** 2 for v in self._volume_window) / self.lookback
            std_volume = math.sqrt(variance) if variance > 0 else 1.0
            volume_z = (self._volume_window[-1] - mean_volume) / std_volume
            trend_strength = sum(
                1 if later > earlier else -1 for earlier, later in zip(closes[:-1], closes[1:])
            ) / (self.lookback - 1)

            yield FeatureObservation(
                feature=FeatureVector(
                    close_return=close_return,
                    volume_zscore=volume_z,
                    funding_rate=candle.funding_rate,
                    trend_strength=trend_strength,
                ),
                price=candle.close,
                timestamp=candle.timestamp,
            )


__all__ = ["FeatureVector", "FeatureObservation", "FeatureEngineer"]
