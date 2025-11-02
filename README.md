# Multi-trading

An educational project demonstrating how to build a lightweight yet robust AI
agent for crypto perpetual futures trading. The repository contains utilities
for loading market data, engineering features, training a small Q-learning
agent, and backtesting the learned strategy with deterministic, testable
components.

## Features

- Synthetic data generator for rapid experimentation without exchange APIs.
- Feature engineering pipeline using momentum, volume, funding rate, EMA
  structure, RSI extremes, and ATR-based volatility context.
- Tabular Q-learning agent with epsilon-greedy exploration, deterministic
  seeding, adaptive volatility-aware position sizing, and configurable risk
  constraints.
- Backtesting environment for perpetual futures with dynamic position sizing,
  transaction costs, slippage, and automatic stop-loss/take-profit enforcement.
- Command line interface to train and evaluate the agent on a dataset.

## Quickstart

1. Create a Python virtual environment and install dependencies (only the
   standard library is required, but you may wish to add pandas/numpy for your
   experiments).
2. Generate synthetic data and run training with deterministic seeding:

   ```bash
   python -m multi_trading.cli /tmp/btc_futures.csv --generate --episodes 5 --eval-episodes 3
   ```

3. Inspect the structured logging output to understand how the agent is
   performing and confirm that both training and evaluation flows succeed.

### Testing and Quality Gates

The project ships with unit tests that validate the full pipeline. Execute the
suite from the repository root:

```bash
python -m pytest
```

The tests generate deterministic synthetic data and exercise agent training,
evaluation, and the backtesting environment so regressions are detected early.

## Project Structure

```
multi_trading/
├── backtest/           # Simplified futures backtesting environment
├── data/               # Data provider and synthetic generator
├── strategies/         # Feature engineering and Q-learning agent
└── cli.py              # Command line entry point
```

This codebase is intentionally compact and heavily documented so that it can be
extended with more advanced models, risk management, and exchange integrations.
