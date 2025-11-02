from pathlib import Path

from multi_trading.backtest.environment import FuturesBacktestEnvironment
from multi_trading.config import BacktestConfig, StrategyConfig
from multi_trading.data.data_provider import HistoricalDataProvider, generate_synthetic_data
from multi_trading.strategies.features import FeatureEngineer
from multi_trading.strategies.futures_agent import CryptoFuturesAIAgent


def test_agent_runs_episode(tmp_path: Path) -> None:
    data_path = tmp_path / "synthetic.csv"
    generate_synthetic_data(data_path, rows=300, seed=5)

    provider = HistoricalDataProvider(data_path)
    candles = list(provider.load())

    agent = CryptoFuturesAIAgent(StrategyConfig(lookback=12), BacktestConfig())
    result = agent.run_episode(candles, training=True)

    assert result.steps > 0
    assert result.equity > 0


def test_agent_evaluation(tmp_path: Path) -> None:
    data_path = tmp_path / "synthetic.csv"
    generate_synthetic_data(data_path, rows=300, seed=2)

    provider = HistoricalDataProvider(data_path)
    candles = list(provider.load())

    agent = CryptoFuturesAIAgent(StrategyConfig(lookback=10), BacktestConfig())
    agent.run_episode(candles, training=True)
    eval_result = agent.run_episode(candles, training=False)

    assert eval_result.steps > 0
    assert eval_result.equity > 0


def test_environment_applies_risk_controls() -> None:
    config = BacktestConfig(initial_balance=10_000.0, contract_size=1.0, max_position=1.0)
    env = FuturesBacktestEnvironment(config)
    env.reset(initial_price=100.0, stop_loss=0.01, take_profit=0.05)

    # Open a long position
    state, _ = env.step(2, 100.0)
    assert state.position == config.max_position

    # Price drops beyond stop loss -> position should close
    state, reward = env.step(2, 97.0)
    assert state.position == 0
    assert reward <= 0
    assert state.balance < config.initial_balance


def test_environment_dynamic_sizing() -> None:
    config = BacktestConfig(initial_balance=10_000.0, contract_size=1.0, max_position=1.0)
    env = FuturesBacktestEnvironment(config)
    env.reset(initial_price=100.0)

    env.set_dynamic_position_size(0.25)
    state, _ = env.step(2, 101.0)
    assert state.position == 0.25

    # Update to a different size and ensure it is honoured on a new entry
    env.step(1, 101.0)
    env.set_dynamic_position_size(0.5)
    state, _ = env.step(0, 100.0)
    assert state.position == -0.5


def test_feature_engineer_outputs_additional_indicators(tmp_path: Path) -> None:
    data_path = tmp_path / "synthetic.csv"
    generate_synthetic_data(data_path, rows=200, seed=11)
    provider = HistoricalDataProvider(data_path)
    engineer = FeatureEngineer(lookback=20, ema_fast=5, ema_slow=10, rsi_period=8, atr_period=10)

    observations = list(engineer.transform(provider.load()))
    assert observations, "Expected engineered features"
    last_feature = observations[-1].feature
    assert -1.1 < last_feature.rsi < 1.1
    assert last_feature.atr_pct >= 0
    assert -1.0 < last_feature.ema_ratio < 1.0
