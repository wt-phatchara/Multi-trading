from pathlib import Path

from multi_trading.backtest.environment import FuturesBacktestEnvironment
from multi_trading.config import BacktestConfig, StrategyConfig
from multi_trading.data.data_provider import HistoricalDataProvider, generate_synthetic_data
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
