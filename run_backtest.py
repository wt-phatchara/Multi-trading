#!/usr/bin/env python3
"""Backtest runner script."""
import asyncio
import argparse
import pandas as pd
from datetime import datetime, timedelta
from src.backtesting.backtest_engine import BacktestEngine
from src.strategies.momentum_strategy import MomentumStrategy
from src.strategies.advanced_strategy import AdvancedStrategy
from src.utils.logger import setup_logger
import ccxt

logger = setup_logger(__name__)


async def fetch_historical_data(
    exchange_name: str,
    symbol: str,
    timeframe: str,
    days: int = 30
) -> pd.DataFrame:
    """
    Fetch historical data from exchange.

    Args:
        exchange_name: Exchange name (binance, bybit, etc.)
        symbol: Trading symbol
        timeframe: Candle timeframe
        days: Number of days of history

    Returns:
        DataFrame with OHLCV data
    """
    logger.info(f"Fetching {days} days of {timeframe} data for {symbol} from {exchange_name}")

    exchange_class = getattr(ccxt, exchange_name)
    exchange = exchange_class()

    since = exchange.parse8601((datetime.now() - timedelta(days=days)).isoformat())

    all_candles = []
    while True:
        candles = await asyncio.to_thread(
            exchange.fetch_ohlcv,
            symbol,
            timeframe,
            since,
            limit=1000
        )

        if not candles:
            break

        all_candles.extend(candles)
        since = candles[-1][0] + 1

        if len(candles) < 1000:
            break

    df = pd.DataFrame(
        all_candles,
        columns=['timestamp', 'open', 'high', 'low', 'close', 'volume']
    )
    df['timestamp'] = pd.to_datetime(df['timestamp'], unit='ms')
    df.set_index('timestamp', inplace=True)

    logger.info(f"Fetched {len(df)} candles")
    return df


async def main():
    """Main backtest runner."""
    parser = argparse.ArgumentParser(description='Run trading strategy backtest')
    parser.add_argument('--exchange', default='binance', help='Exchange name')
    parser.add_argument('--symbol', default='BTC/USDT', help='Trading symbol')
    parser.add_argument('--timeframe', default='5m', help='Candle timeframe')
    parser.add_argument('--days', type=int, default=30, help='Days of history')
    parser.add_argument('--capital', type=float, default=10000, help='Initial capital')
    parser.add_argument('--strategy', default='advanced', choices=['momentum', 'advanced'], help='Strategy to test')
    parser.add_argument('--leverage', type=int, default=1, help='Leverage')
    parser.add_argument('--position-size', type=float, default=2.0, help='Position size %')
    parser.add_argument('--stop-loss', type=float, default=2.0, help='Stop loss %')
    parser.add_argument('--take-profit', type=float, default=4.0, help='Take profit %')
    parser.add_argument('--min-confidence', type=float, default=0.6, help='Minimum signal confidence')

    args = parser.parse_args()

    print("="*60)
    print("CRYPTO FUTURES BACKTEST")
    print("="*60)
    print(f"Exchange: {args.exchange}")
    print(f"Symbol: {args.symbol}")
    print(f"Timeframe: {args.timeframe}")
    print(f"Period: {args.days} days")
    print(f"Initial Capital: ${args.capital:,.2f}")
    print(f"Strategy: {args.strategy}")
    print("="*60)
    print("")

    # Fetch data
    try:
        data = await fetch_historical_data(
            args.exchange,
            args.symbol,
            args.timeframe,
            args.days
        )
    except Exception as e:
        logger.error(f"Failed to fetch data: {e}")
        return

    # Select strategy
    if args.strategy == 'advanced':
        strategy = AdvancedStrategy()
    else:
        strategy = MomentumStrategy()

    logger.info(f"Using strategy: {strategy.name}")

    # Create backtest engine
    engine = BacktestEngine(
        initial_capital=args.capital,
        fee_rate=0.0004,  # Binance futures maker fee
        slippage=0.0005
    )

    # Backtest configuration
    config = {
        'symbol': args.symbol,
        'leverage': args.leverage,
        'position_size_percent': args.position_size,
        'stop_loss_percent': args.stop_loss,
        'take_profit_percent': args.take_profit,
        'max_positions': 3,
        'min_confidence': args.min_confidence
    }

    # Run backtest
    logger.info("Starting backtest...")
    metrics = engine.run_backtest(data, strategy, config)

    # Display results
    print(engine.generate_report(metrics))

    # Save detailed results
    output_file = f"backtest_results_{datetime.now().strftime('%Y%m%d_%H%M%S')}.txt"
    with open(output_file, 'w') as f:
        f.write(engine.generate_report(metrics))

        f.write("\n\nDETAILED TRADE LOG\n")
        f.write("="*60 + "\n")

        for i, trade in enumerate(engine.trades, 1):
            f.write(f"\nTrade #{i}\n")
            f.write(f"  Entry: {trade.entry_time} @ ${trade.entry_price:.2f}\n")
            f.write(f"  Exit: {trade.exit_time} @ ${trade.exit_price:.2f}\n")
            f.write(f"  Side: {trade.side.upper()}\n")
            f.write(f"  Quantity: {trade.quantity:.6f}\n")
            f.write(f"  P&L: ${trade.pnl:.2f} ({trade.pnl_percent:.2f}%)\n")
            f.write(f"  Status: {trade.status}\n")
            f.write(f"  Reason: {trade.signal_reason}\n")

    logger.info(f"Results saved to {output_file}")

    # Generate equity curve CSV
    equity_csv = f"equity_curve_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv"
    equity_df = pd.DataFrame(engine.equity_history)
    equity_df.to_csv(equity_csv, index=False)
    logger.info(f"Equity curve saved to {equity_csv}")

    print("")
    print(f"Full report saved to: {output_file}")
    print(f"Equity curve saved to: {equity_csv}")


if __name__ == '__main__':
    asyncio.run(main())
