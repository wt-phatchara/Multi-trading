"""Utilities for loading and preparing crypto futures market data."""
from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta
from pathlib import Path
from typing import Iterator

import csv
import math
import random



@dataclass(slots=True)
class Candle:
    """Represents a single OHLCV candle with additional metadata."""

    timestamp: datetime
    open: float
    high: float
    low: float
    close: float
    volume: float
    funding_rate: float


class HistoricalDataProvider:
    """Loads futures market data from CSV files and yields :class:`Candle` items."""

    def __init__(self, csv_path: Path) -> None:
        self.csv_path = csv_path

    def __iter__(self) -> Iterator[Candle]:
        yield from self.load()

    def load(self) -> Iterator[Candle]:
        """Load candles from the CSV file.

        The CSV is expected to contain the columns ``timestamp``, ``open``, ``high``,
        ``low``, ``close``, ``volume`` and ``funding_rate``. The timestamp must be an
        ISO formatted string.
        """

        if not self.csv_path.exists():
            raise FileNotFoundError(
                f"Historical data file '{self.csv_path}' does not exist."
            )

        with self.csv_path.open("r", newline="") as handle:
            reader = csv.DictReader(handle)
            required = {
                "timestamp",
                "open",
                "high",
                "low",
                "close",
                "volume",
                "funding_rate",
            }
            missing = required - set(reader.fieldnames or [])
            if missing:
                raise ValueError(
                    "CSV file is missing required columns: " + ", ".join(sorted(missing))
                )

            for row in reader:
                try:
                    yield Candle(
                        timestamp=datetime.fromisoformat(row["timestamp"]),
                        open=float(row["open"]),
                        high=float(row["high"]),
                        low=float(row["low"]),
                        close=float(row["close"]),
                        volume=float(row["volume"]),
                        funding_rate=float(row["funding_rate"]),
                    )
                except Exception as exc:  # pragma: no cover - defensive branch
                    raise ValueError(f"Invalid row in CSV file: {row}") from exc


def generate_synthetic_data(
    csv_path: Path,
    *,
    rows: int = 1_000,
    seed: int | None = None,
    base_price: float = 27_000.0,
) -> None:
    """Generate a synthetic BTC futures market dataset for experimentation.

    The synthetic generator is deliberately simple but produces non-trivial price
    behaviour with varying funding rates and volumes. It is intended for use in
    unit tests or quick experiments where real data is not available.
    """

    rng = random.Random(seed)

    with csv_path.open("w", newline="") as handle:
        fieldnames = [
            "timestamp",
            "open",
            "high",
            "low",
            "close",
            "volume",
            "funding_rate",
        ]
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()

        price = base_price
        start = datetime(2021, 1, 1)
        trend_regime = 1.0
        regime_length = max(50, rows // 10)
        for index in range(rows):
            if index % regime_length == 0 and index > 0:
                # Flip between bullish and bearish bias to test regime switches
                trend_regime *= -1.0

            timestamp = start + timedelta(hours=index)
            cyclical = math.sin(index / 35) * 18
            drift = trend_regime * rng.uniform(5, 15)
            volatility = rng.uniform(25, 65)
            shock = rng.gauss(0, volatility)
            funding_bias = trend_regime * 0.0004
            funding = funding_bias + cyclical * 0.00002 + rng.gauss(0, 0.0003)

            volume_base = 120 + abs(trend_regime) * 40
            volume_vol = abs(shock) * 0.6 / max(price, 1.0)
            volume = abs(rng.gauss(volume_base + volume_vol, 35)) + 25

            open_price = price
            price = max(1.0, price + drift + cyclical + shock)
            close = price
            wicks = abs(rng.gauss(0, volatility * 0.4))
            high = max(open_price, close) + wicks
            low = min(open_price, close) - wicks

            writer.writerow(
                {
                    "timestamp": timestamp.isoformat(),
                    "open": round(open_price, 2),
                    "high": round(high, 2),
                    "low": round(low, 2),
                    "close": round(close, 2),
                    "volume": round(volume, 4),
                    "funding_rate": round(funding, 6),
                }
            )


__all__ = ["Candle", "HistoricalDataProvider", "generate_synthetic_data"]
