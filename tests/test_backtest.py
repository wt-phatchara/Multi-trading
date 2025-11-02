"""Tests for backtesting engine."""
import pytest
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
from src.backtesting.backtest_engine import BacktestEngine, BacktestMetrics
from src.strategies.momentum_strategy import MomentumStrategy


@pytest.fixture
def sample_data():
    """Generate sample OHLCV data."""
    dates = pd.date_range(start='2024-01-01', end='2024-03-01', freq='1H')
    np.random.seed(42)

    data = pd.DataFrame({
        'open': 40000 + np.random.randn(len(dates)).cumsum() * 100,
        'high': 40000 + np.random.randn(len(dates)).cumsum() * 100 + 50,
        'low': 40000 + np.random.randn(len(dates)).cumsum() * 100 - 50,
        'close': 40000 + np.random.randn(len(dates)).cumsum() * 100,
        'volume': np.random.randint(100, 1000, len(dates))
    }, index=dates)

    # Ensure high >= low
    data['high'] = data[['open', 'close', 'high']].max(axis=1)
    data['low'] = data[['open', 'close', 'low']].min(axis=1)

    return data


@pytest.fixture
def backtest_engine():
    """Create backtest engine instance."""
    return BacktestEngine(
        initial_capital=10000,
        fee_rate=0.0004,
        slippage=0.0005
    )


def test_backtest_initialization(backtest_engine):
    """Test backtest engine initialization."""
    assert backtest_engine.initial_capital == 10000
    assert backtest_engine.current_capital == 10000
    assert len(backtest_engine.trades) == 0


def test_position_size_calculation(backtest_engine):
    """Test position size calculation."""
    size = backtest_engine.calculate_position_size(
        price=40000,
        leverage=1,
        risk_percent=2.0,
        stop_loss_percent=2.0
    )

    assert size > 0
    # Risk 2% of 10000 = 200
    # With 2% SL, position should be ~200/0.02 = 10000
    # At price 40000, should be ~0.25 BTC
    assert 0.2 < size < 0.3


def test_slippage_application(backtest_engine):
    """Test slippage application."""
    price = 40000

    buy_price = backtest_engine.apply_slippage(price, 'buy')
    assert buy_price > price  # Buy price increased by slippage

    sell_price = backtest_engine.apply_slippage(price, 'sell')
    assert sell_price < price  # Sell price decreased by slippage


def test_fee_calculation(backtest_engine):
    """Test fee calculation."""
    fee = backtest_engine.calculate_fees(quantity=0.1, price=40000)

    # Fee = 0.1 * 40000 * 0.0004 = 1.6
    assert abs(fee - 1.6) < 0.01


def test_backtest_run(backtest_engine, sample_data):
    """Test complete backtest run."""
    strategy = MomentumStrategy()

    config = {
        'symbol': 'BTC/USDT',
        'leverage': 1,
        'position_size_percent': 2.0,
        'stop_loss_percent': 2.0,
        'take_profit_percent': 4.0,
        'max_positions': 1,
        'min_confidence': 0.6
    }

    metrics = backtest_engine.run_backtest(sample_data, strategy, config)

    assert isinstance(metrics, BacktestMetrics)
    assert metrics.total_trades >= 0
    assert len(backtest_engine.equity_history) > 0


def test_backtest_metrics_calculation(backtest_engine, sample_data):
    """Test metrics calculation."""
    strategy = MomentumStrategy()

    config = {
        'symbol': 'BTC/USDT',
        'leverage': 1,
        'position_size_percent': 1.0,
        'stop_loss_percent': 2.0,
        'take_profit_percent': 4.0,
        'max_positions': 1,
        'min_confidence': 0.5
    }

    metrics = backtest_engine.run_backtest(sample_data, strategy, config)

    if metrics.total_trades > 0:
        assert metrics.winning_trades + metrics.losing_trades == metrics.total_trades
        assert 0 <= metrics.win_rate <= 1
        assert metrics.total_pnl == metrics.net_pnl  # Since net = total - fees already calculated


def test_report_generation(backtest_engine, sample_data):
    """Test report generation."""
    strategy = MomentumStrategy()

    config = {
        'symbol': 'BTC/USDT',
        'leverage': 1,
        'position_size_percent': 2.0,
        'stop_loss_percent': 2.0,
        'take_profit_percent': 4.0,
        'max_positions': 1,
        'min_confidence': 0.6
    }

    metrics = backtest_engine.run_backtest(sample_data, strategy, config)
    report = backtest_engine.generate_report(metrics)

    assert isinstance(report, str)
    assert 'BACKTEST REPORT' in report
    assert 'Initial Capital' in report
