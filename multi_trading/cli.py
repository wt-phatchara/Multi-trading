"""Command line entry point for training and evaluating the crypto futures agent."""
from __future__ import annotations

import argparse
import logging
from pathlib import Path

from .config import BacktestConfig, DataConfig, StrategyConfig
from .data.data_provider import HistoricalDataProvider, generate_synthetic_data
from .strategies.futures_agent import CryptoFuturesAIAgent


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("data", type=Path, help="Path to the CSV file containing historical futures data")
    parser.add_argument("--generate", action="store_true", help="Generate a synthetic dataset if the file does not exist")
    parser.add_argument("--episodes", type=int, default=3, help="Number of training episodes to run")
    parser.add_argument("--seed", type=int, default=7, help="Random seed for synthetic data generation")
    parser.add_argument("--eval-episodes", type=int, default=1, help="Number of evaluation episodes to average")
    parser.add_argument(
        "--log-level",
        default="INFO",
        choices=["CRITICAL", "ERROR", "WARNING", "INFO", "DEBUG"],
        help="Logging verbosity",
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()

    logging.basicConfig(
        level=getattr(logging, args.log_level.upper()),
        format="%(asctime)s %(levelname)s %(name)s - %(message)s",
    )

    if args.generate and not args.data.exists():
        logging.info("Generating synthetic dataset at %s", args.data)
        generate_synthetic_data(args.data, rows=2000, seed=args.seed)

    if not args.data.exists():
        logging.error("Data file %s does not exist. Use --generate to create synthetic data.", args.data)
        raise SystemExit(1)

    data_provider = HistoricalDataProvider(args.data)
    candles = list(data_provider.load())

    strategy_config = StrategyConfig()

    if len(candles) < strategy_config.lookback + 2:
        logging.error("Dataset contains insufficient rows for the configured lookback window")
        raise SystemExit(1)

    data_config = DataConfig(data_path=args.data)
    logging.info(
        "Loaded %s candles for %s on %s timeframe",
        len(candles),
        data_config.symbol,
        data_config.timeframe,
    )
    backtest_config = BacktestConfig(seed=args.seed)

    agent = CryptoFuturesAIAgent(strategy_config, backtest_config)

    for episode in range(args.episodes):
        result = agent.run_episode(candles, training=True)
        logging.info(
            "Episode %s: reward=%.4f, steps=%s, equity=%.2f",
            episode + 1,
            result.total_reward,
            result.steps,
            result.equity,
        )

    eval_rewards = []
    for idx in range(args.eval_episodes):
        eval_result = agent.run_episode(candles, training=False)
        eval_rewards.append(eval_result.total_reward)
        logging.info(
            "Evaluation %s/%s: reward=%.4f, steps=%s, equity=%.2f",
            idx + 1,
            args.eval_episodes,
            eval_result.total_reward,
            eval_result.steps,
            eval_result.equity,
        )

    if eval_rewards:
        avg_reward = sum(eval_rewards) / len(eval_rewards)
        logging.info("Average evaluation reward: %.4f", avg_reward)


if __name__ == "__main__":
    main()
