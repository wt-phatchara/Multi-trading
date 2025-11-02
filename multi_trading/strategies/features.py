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
    structure_bias: float
    bos_signal: float
    liquidity_sweep: float
    imbalance_ratio: float
    demand_distance: float
    supply_distance: float
    session_london: float
    session_newyork: float

    def as_tuple(self) -> tuple[float, ...]:
        return (
            self.close_return,
            self.volume_zscore,
            self.funding_rate,
            self.trend_strength,
            self.ema_ratio,
            self.rsi,
            self.atr_pct,
            self.structure_bias,
            self.bos_signal,
            self.liquidity_sweep,
            self.imbalance_ratio,
            self.demand_distance,
            self.supply_distance,
            self.session_london,
            self.session_newyork,
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
        structure_decay: float = 0.96,
        zone_base_multiplier: float = 0.6,
        zone_impulse_multiplier: float = 1.6,
        max_zones: int = 8,
    ) -> None:
        if lookback <= 1:
            raise ValueError("lookback must be greater than 1")
        if ema_fast <= 0 or ema_slow <= 0:
            raise ValueError("EMA periods must be positive")
        if rsi_period <= 1:
            raise ValueError("RSI period must be greater than 1")
        if atr_period <= 0:
            raise ValueError("ATR period must be positive")
        if not 0 < structure_decay <= 1:
            raise ValueError("structure_decay must be in (0, 1]")
        self.lookback = lookback
        self.ema_fast = ema_fast
        self.ema_slow = ema_slow
        self.rsi_period = rsi_period
        self.atr_period = atr_period
        self._structure_decay = structure_decay
        self._zone_base_multiplier = zone_base_multiplier
        self._zone_impulse_multiplier = zone_impulse_multiplier
        self._max_zones = max(1, max_zones)
        self._close_window: Deque[float] = deque(maxlen=lookback)
        self._volume_window: Deque[float] = deque(maxlen=lookback)
        self._high_window: Deque[float] = deque(maxlen=lookback + 1)
        self._low_window: Deque[float] = deque(maxlen=lookback + 1)
        self._ema_fast_value: float | None = None
        self._ema_slow_value: float | None = None
        self._rsi_avg_gain: float | None = None
        self._rsi_avg_loss: float | None = None
        self._atr_value: float | None = None
        self._previous_close: float | None = None
        self._structure_bias = 0.0
        self._recent_candles: Deque[Candle] = deque(maxlen=4)
        self._zones: list[SupplyDemandZone] = []

    def reset(self) -> None:
        """Clear any buffered state from previous runs."""

        self._close_window.clear()
        self._volume_window.clear()
        self._high_window.clear()
        self._low_window.clear()
        self._ema_fast_value = None
        self._ema_slow_value = None
        self._rsi_avg_gain = None
        self._rsi_avg_loss = None
        self._atr_value = None
        self._previous_close = None
        self._structure_bias = 0.0
        self._recent_candles.clear()
        self._zones.clear()

    def transform(self, candles: Iterable[Candle]) -> Iterator[FeatureObservation]:
        """Yield feature observations for each candle once enough history exists."""

        for candle in candles:
            self._close_window.append(candle.close)
            self._volume_window.append(candle.volume)
            self._high_window.append(candle.high)
            self._low_window.append(candle.low)
            self._recent_candles.append(candle)
            self._update_indicators(candle)
            self._update_supply_demand_zones()
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
            (
                structure_bias,
                bos_signal,
                liquidity_sweep,
                imbalance_ratio,
                demand_distance,
                supply_distance,
                session_london,
                session_newyork,
            ) = self._compute_price_action_features(candle)

            yield FeatureObservation(
                feature=FeatureVector(
                    close_return=close_return,
                    volume_zscore=volume_z,
                    funding_rate=candle.funding_rate,
                    trend_strength=trend_strength,
                    ema_ratio=ema_ratio,
                    rsi=rsi,
                    atr_pct=atr_pct,
                    structure_bias=structure_bias,
                    bos_signal=bos_signal,
                    liquidity_sweep=liquidity_sweep,
                    imbalance_ratio=imbalance_ratio,
                    demand_distance=demand_distance,
                    supply_distance=supply_distance,
                    session_london=session_london,
                    session_newyork=session_newyork,
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

    def _compute_price_action_features(self, candle: Candle) -> tuple[float, ...]:
        previous_high, previous_low = self._previous_extremes()
        bos_signal = 0.0
        liquidity_sweep = 0.0

        if previous_high is not None and previous_low is not None:
            if candle.close > previous_high:
                bos_signal = 1.0
                self._structure_bias = min(1.0, self._structure_bias + 0.3)
            elif candle.close < previous_low:
                bos_signal = -1.0
                self._structure_bias = max(-1.0, self._structure_bias - 0.3)
            else:
                self._structure_bias *= self._structure_decay

            if candle.high > previous_high and candle.close <= previous_high:
                liquidity_sweep = 1.0
            elif candle.low < previous_low and candle.close >= previous_low:
                liquidity_sweep = -1.0
        else:
            self._structure_bias *= self._structure_decay

        demand_distance, supply_distance, imbalance_ratio = self._zone_distances(candle.close)
        session_london, session_newyork = self._session_features(candle.timestamp)

        return (
            self._structure_bias,
            bos_signal,
            liquidity_sweep,
            imbalance_ratio,
            demand_distance,
            supply_distance,
            session_london,
            session_newyork,
        )

    def _previous_extremes(self) -> tuple[float | None, float | None]:
        highs = list(self._high_window)
        lows = list(self._low_window)
        if len(highs) < 2 or len(lows) < 2:
            return None, None
        return max(highs[:-1]), min(lows[:-1])

    def _session_features(self, timestamp: datetime) -> tuple[float, float]:
        hour = timestamp.hour
        london = 1.0 if 7 <= hour < 16 else 0.0
        new_york = 1.0 if 12 <= hour < 21 else 0.0
        return london, new_york

    def _update_supply_demand_zones(self) -> None:
        if len(self._recent_candles) < 2 or self._atr_value is None:
            return
        prev = self._recent_candles[-2]
        current = self._recent_candles[-1]
        atr = max(self._atr_value, 1e-6)
        base_range = prev.high - prev.low
        base_body = abs(prev.close - prev.open)
        impulse_body = abs(current.close - current.open)
        base_threshold = atr * self._zone_base_multiplier
        impulse_threshold = atr * self._zone_impulse_multiplier

        if base_range <= atr * 1.2 and base_body <= base_threshold and impulse_body >= impulse_threshold:
            if current.close > prev.high:
                imbalance = max(0.0, current.low - prev.high)
                self._zones.append(
                    SupplyDemandZone(
                        direction=1,
                        low=prev.low,
                        high=prev.high,
                        imbalance=imbalance / max(current.close, 1e-6),
                        created_at=current.timestamp,
                    )
                )
            elif current.close < prev.low:
                imbalance = max(0.0, prev.low - current.high)
                self._zones.append(
                    SupplyDemandZone(
                        direction=-1,
                        low=prev.low,
                        high=prev.high,
                        imbalance=imbalance / max(current.close, 1e-6),
                        created_at=current.timestamp,
                    )
                )

        for zone in self._zones:
            if zone.touched or zone.created_at == current.timestamp:
                continue
            if zone.direction == 1 and current.low <= zone.high and current.high >= zone.low:
                zone.touched = True
            elif zone.direction == -1 and current.high >= zone.low and current.low <= zone.high:
                zone.touched = True

        self._zones = [zone for zone in self._zones if not zone.touched]
        if len(self._zones) > self._max_zones:
            self._zones = self._zones[-self._max_zones :]

    def _zone_distances(self, price: float) -> tuple[float, float, float]:
        demand_distance = 1.0
        supply_distance = 1.0
        imbalance_ratio = 0.0
        for zone in self._zones:
            if zone.direction == 1:
                if price <= zone.high:
                    demand_distance = 0.0
                else:
                    dist = (price - zone.high) / price
                    demand_distance = min(demand_distance, max(dist, 0.0))
            else:
                if price >= zone.low:
                    supply_distance = 0.0
                else:
                    dist = (zone.low - price) / price
                    supply_distance = min(supply_distance, max(dist, 0.0))
            imbalance_ratio = max(imbalance_ratio, zone.imbalance)

        return demand_distance, supply_distance, imbalance_ratio


@dataclass(slots=True)
class SupplyDemandZone:
    direction: int
    low: float
    high: float
    imbalance: float
    created_at: datetime
    touched: bool = False


__all__ = ["FeatureVector", "FeatureObservation", "FeatureEngineer"]
