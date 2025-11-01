"""Reinforcement-learning inspired agent for crypto futures trading."""
from __future__ import annotations

from collections import defaultdict
from dataclasses import dataclass
from typing import Dict, Iterable, Tuple

import random

from ..backtest.environment import FuturesBacktestEnvironment
from ..config import BacktestConfig, StrategyConfig
from ..data.data_provider import Candle
from .features import FeatureEngineer, FeatureObservation, FeatureVector


@dataclass
class EpisodeResult:
    """Summary of a single training or evaluation episode."""

    total_reward: float
    steps: int
    equity: float


class CryptoFuturesAIAgent:
    """A tiny tabular Q-learning agent for directional futures trading."""

    def __init__(
        self,
        strategy_config: StrategyConfig,
        backtest_config: BacktestConfig,
    ) -> None:
        self.strategy_config = strategy_config
        self.backtest_config = backtest_config
        self.q_table: Dict[Tuple[int, int, int, int], list[float]] = defaultdict(
            lambda: [0.0, 0.0, 0.0]
        )
        self.feature_engineer = FeatureEngineer(strategy_config.lookback)
        self.environment = FuturesBacktestEnvironment(backtest_config)
        self._rng = random.Random(backtest_config.seed)
        self._exploration_rate = strategy_config.exploration_rate

    def _discretise(self, feature: FeatureVector) -> tuple[int, int, int, int]:
        """Convert a :class:`FeatureVector` into a discrete state."""

        def bucket(value: float, edges: Tuple[float, ...]) -> int:
            for index, edge in enumerate(edges):
                if value < edge:
                    return index
            return len(edges)

        return (
            bucket(feature.close_return, (-0.02, -0.005, 0.005, 0.02)),
            bucket(feature.volume_zscore, (-1.5, -0.5, 0.5, 1.5)),
            bucket(feature.funding_rate, (-0.0005, -0.0001, 0.0001, 0.0005)),
            bucket(feature.trend_strength, (-0.4, -0.1, 0.1, 0.4)),
        )

    def select_action(self, state: tuple[int, int, int, int]) -> int:
        """Select an action following an epsilon-greedy strategy."""

        if self._rng.random() < self._exploration_rate:
            return self._rng.randint(0, 2)
        q_values = self.q_table[state]
        return max(range(len(q_values)), key=lambda a: q_values[a])

    def update_q_table(self, state: tuple[int, ...], action: int, reward: float, next_state: tuple[int, ...]) -> None:
        q_values = self.q_table[state]
        best_next = max(self.q_table[next_state])
        q_values[action] += self.strategy_config.learning_rate * (
            reward + self.strategy_config.discount_factor * best_next - q_values[action]
        )

    def run_episode(self, candles: Iterable[Candle], training: bool = True) -> EpisodeResult:
        """Run a single training or evaluation episode."""

        observations = self._prepare_observations(candles)
        if len(observations) < 2:
            raise ValueError("Not enough data to compute features. Increase history length.")

        self.feature_engineer.reset()
        self.environment.reset(
            initial_price=observations[0].price,
            stop_loss=self.strategy_config.stop_loss,
            take_profit=self.strategy_config.take_profit,
        )

        total_reward = 0.0
        steps = 0

        previous_obs = observations[0]
        for obs in observations[1:]:
            state = self._discretise(previous_obs.feature)
            next_state = self._discretise(obs.feature)
            action = self.select_action(state) if training else self._greedy_action(state)

            _, reward = self.environment.step(action, obs.price)
            reward -= self._risk_penalty()
            if training:
                self.update_q_table(state, action, reward, next_state)

            total_reward += reward
            steps += 1
            previous_obs = obs

        if training:
            self._decay_exploration()

        equity = self.environment.equity
        return EpisodeResult(total_reward=total_reward, steps=steps, equity=equity)

    def _prepare_observations(self, candles: Iterable[Candle]) -> list[FeatureObservation]:
        self.feature_engineer.reset()
        return list(self.feature_engineer.transform(candles))

    def _greedy_action(self, state: tuple[int, ...]) -> int:
        q_values = self.q_table[state]
        return max(range(len(q_values)), key=lambda a: q_values[a])

    def _risk_penalty(self) -> float:
        risk_span = self.strategy_config.stop_loss + self.strategy_config.take_profit
        balance_ratio = self.environment.equity / max(self.backtest_config.initial_balance, 1.0)
        return risk_span * self.strategy_config.transaction_fee * balance_ratio

    def _decay_exploration(self) -> None:
        self._exploration_rate = max(
            self.strategy_config.min_exploration_rate,
            self._exploration_rate * self.strategy_config.exploration_decay,
        )


__all__ = ["CryptoFuturesAIAgent", "EpisodeResult"]
