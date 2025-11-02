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
    ema_ratio: float
    rsi: float
    atr_pct: float

    def as_tuple(self) -> tuple[float, ...]:
        return (
            self.close_return,
            self.volume_zscore,
            self.funding_rate,
            self.trend_strength,
            self.ema_ratio,
            self.rsi,
            self.atr_pct,
        )


@dataclass(slots=True)
class FeatureObservation:
    """Feature vector augmented with the market metadata for a timestep."""

    feature: FeatureVector
    price: float
    timestamp: datetime


class FeatureEngineer:
    """Transforms a stream of candles into agent-ready feature vectors."""

    def __init__(
        self,
        lookback: int = 24,
        *,
        ema_fast: int = 12,
        ema_slow: int = 26,
        rsi_period: int = 14,
        atr_period: int = 14,
    ) -> None:
        if lookback <= 1:
            raise ValueError("lookback must be greater than 1")
        if ema_fast <= 0 or ema_slow <= 0:
            raise ValueError("EMA periods must be positive")
        if rsi_period <= 1:
            raise ValueError("RSI period must be greater than 1")
        if atr_period <= 0:
            raise ValueError("ATR period must be positive")
        self.lookback = lookback
        self.ema_fast = ema_fast
        self.ema_slow = ema_slow
        self.rsi_period = rsi_period
        self.atr_period = atr_period
        self._close_window: Deque[float] = deque(maxlen=lookback)
        self._volume_window: Deque[float] = deque(maxlen=lookback)
        self._ema_fast_value: float | None = None
        self._ema_slow_value: float | None = None
        self._rsi_avg_gain: float | None = None
        self._rsi_avg_loss: float | None = None
        self._atr_value: float | None = None
        self._previous_close: float | None = None

    def reset(self) -> None:
        """Clear any buffered state from previous runs."""

        self._close_window.clear()
        self._volume_window.clear()
        self._ema_fast_value = None
        self._ema_slow_value = None
        self._rsi_avg_gain = None
        self._rsi_avg_loss = None
        self._atr_value = None
        self._previous_close = None

    def transform(self, candles: Iterable[Candle]) -> Iterator[FeatureObservation]:
        """Yield feature observations for each candle once enough history exists."""

        for candle in candles:
            self._close_window.append(candle.close)
            self._volume_window.append(candle.volume)
            self._update_indicators(candle)
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
            ema_ratio = self._compute_ema_ratio(candle)
            rsi = self._compute_rsi()
            atr_pct = self._compute_atr_pct(candle)

            yield FeatureObservation(
                feature=FeatureVector(
                    close_return=close_return,
                    volume_zscore=volume_z,
                    funding_rate=candle.funding_rate,
                    trend_strength=trend_strength,
                    ema_ratio=ema_ratio,
                    rsi=rsi,
                    atr_pct=atr_pct,
                ),
                price=candle.close,
                timestamp=candle.timestamp,
            )

    def _update_indicators(self, candle: Candle) -> None:
        close = candle.close
        if self._ema_fast_value is None:
            self._ema_fast_value = close
        else:
            alpha_fast = 2 / (self.ema_fast + 1)
            self._ema_fast_value = close * alpha_fast + self._ema_fast_value * (1 - alpha_fast)

        if self._ema_slow_value is None:
            self._ema_slow_value = close
        else:
            alpha_slow = 2 / (self.ema_slow + 1)
            self._ema_slow_value = close * alpha_slow + self._ema_slow_value * (1 - alpha_slow)

        if self._previous_close is not None:
            change = close - self._previous_close
            gain = max(change, 0.0)
            loss = max(-change, 0.0)
            if self._rsi_avg_gain is None or self._rsi_avg_loss is None:
                self._rsi_avg_gain = gain
                self._rsi_avg_loss = loss
            else:
                self._rsi_avg_gain = (
                    (self._rsi_avg_gain * (self.rsi_period - 1) + gain) / self.rsi_period
                )
                self._rsi_avg_loss = (
                    (self._rsi_avg_loss * (self.rsi_period - 1) + loss) / self.rsi_period
                )

            true_range = max(
                candle.high - candle.low,
                abs(candle.high - self._previous_close),
                abs(candle.low - self._previous_close),
            )
            if self._atr_value is None:
                self._atr_value = true_range
            else:
                self._atr_value = (
                    (self._atr_value * (self.atr_period - 1) + true_range) / self.atr_period
                )

        self._previous_close = close

    def _compute_ema_ratio(self, candle: Candle) -> float:
        if self._ema_fast_value is None or self._ema_slow_value is None:
            return 0.0
        if candle.close == 0:
            return 0.0
        return (self._ema_fast_value - self._ema_slow_value) / candle.close

    def _compute_rsi(self) -> float:
        if self._rsi_avg_gain is None or self._rsi_avg_loss is None:
            return 0.0
        if self._rsi_avg_loss == 0:
            return 1.0
        rs = self._rsi_avg_gain / self._rsi_avg_loss
        rsi = 100 - 100 / (1 + rs)
        return (rsi - 50) / 50  # scale to [-1, 1]

    def _compute_atr_pct(self, candle: Candle) -> float:
        if self._atr_value is None or candle.close == 0:
            return 0.0
        return max(self._atr_value / candle.close, 0.0)


__all__ = ["FeatureVector", "FeatureObservation", "FeatureEngineer"]
