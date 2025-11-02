"""Tests for trading strategies."""
import pytest
import pandas as pd
import numpy as np
from src.strategies.momentum_strategy import MomentumStrategy
from src.strategies.advanced_strategy import AdvancedStrategy
from src.strategies.price_action import PriceActionPatterns
from src.strategies.support_resistance import SupportResistance


@pytest.fixture
def sample_ohlcv():
    """Generate sample OHLCV data."""
    dates = pd.date_range(start='2024-01-01', periods=100, freq='1H')
    np.random.seed(42)

    return pd.DataFrame({
        'open': 40000 + np.random.randn(100).cumsum() * 50,
        'high': 40000 + np.random.randn(100).cumsum() * 50 + 25,
        'low': 40000 + np.random.randn(100).cumsum() * 50 - 25,
        'close': 40000 + np.random.randn(100).cumsum() * 50,
        'volume': np.random.randint(100, 1000, 100)
    }, index=dates)


class TestMomentumStrategy:
    """Test momentum strategy."""

    def test_initialization(self):
        """Test strategy initialization."""
        strategy = MomentumStrategy()
        assert strategy.name == "Momentum Strategy"

    def test_signal_generation(self, sample_ohlcv):
        """Test signal generation."""
        strategy = MomentumStrategy()
        signal = strategy.generate_signal(sample_ohlcv)

        assert 'signal' in signal
        assert signal['signal'] in ['BUY', 'SELL', 'HOLD']
        assert 'confidence' in signal
        assert 0 <= signal['confidence'] <= 1
        assert 'reason' in signal

    def test_indicator_calculation(self, sample_ohlcv):
        """Test indicator calculation."""
        strategy = MomentumStrategy()
        df = strategy.calculate_indicators(sample_ohlcv)

        assert 'rsi' in df.columns
        assert 'macd' in df.columns
        assert 'ema_9' in df.columns


class TestAdvancedStrategy:
    """Test advanced strategy."""

    def test_initialization(self):
        """Test strategy initialization."""
        strategy = AdvancedStrategy()
        assert strategy.name == "Advanced Multi-Method Strategy"

    def test_signal_generation(self, sample_ohlcv):
        """Test signal generation."""
        strategy = AdvancedStrategy()
        signal = strategy.generate_signal(sample_ohlcv)

        assert 'signal' in signal
        assert 'confidence' in signal
        assert 'breakdown' in signal
        assert 'scores' in signal


class TestPriceAction:
    """Test price action patterns."""

    def test_bullish_engulfing(self, sample_ohlcv):
        """Test bullish engulfing detection."""
        result = PriceActionPatterns.is_bullish_engulfing(sample_ohlcv)
        assert isinstance(result, bool)

    def test_trend_detection(self, sample_ohlcv):
        """Test trend detection."""
        trend = PriceActionPatterns.detect_trend(sample_ohlcv)
        assert trend in ['UPTREND', 'DOWNTREND', 'SIDEWAYS']


class TestSupportResistance:
    """Test support/resistance detection."""

    def test_pivot_point_detection(self, sample_ohlcv):
        """Test pivot point detection."""
        support, resistance = SupportResistance.find_pivot_points(sample_ohlcv)

        assert isinstance(support, list)
        assert isinstance(resistance, list)

    def test_zone_analysis(self, sample_ohlcv):
        """Test zone analysis."""
        current_price = sample_ohlcv['close'].iloc[-1]
        analysis = SupportResistance.analyze_zones(sample_ohlcv, current_price)

        assert 'support_zones' in analysis
        assert 'resistance_zones' in analysis
        assert 'volume_zones' in analysis
