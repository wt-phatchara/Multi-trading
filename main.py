"""Main entry point for the Crypto Futures Trading Agent."""
import asyncio
import sys
from src.agent.trading_agent import CryptoFuturesTradingAgent
from src.utils.config import Config
from src.utils.logger import setup_logger

logger = setup_logger(__name__)


def print_banner():
    """Print application banner."""
    banner = """
    ╔═══════════════════════════════════════════════════════════╗
    ║                                                           ║
    ║       CRYPTO FUTURES TRADING AGENT (AI-POWERED)          ║
    ║                                                           ║
    ║  Automated trading system for cryptocurrency futures     ║
    ║  with AI-enhanced decision making and risk management    ║
    ║                                                           ║
    ╚═══════════════════════════════════════════════════════════╝
    """
    print(banner)


async def main():
    """Main application entry point."""
    print_banner()

    # Load configuration
    try:
        config = Config()
        config.validate()
        logger.info("Configuration loaded successfully")
    except Exception as e:
        logger.error(f"Configuration error: {e}")
        sys.exit(1)

    # Display configuration
    logger.info(f"Exchange: {config.EXCHANGE_NAME} (testnet={config.EXCHANGE_TESTNET})")
    logger.info(f"Trading Mode: {config.TRADING_MODE}")
    logger.info(f"Symbol: {config.DEFAULT_SYMBOL}")
    logger.info(f"Timeframe: {config.TIMEFRAME}")
    logger.info(f"Leverage: {config.LEVERAGE}x")
    logger.info(f"Strategy: {config.STRATEGY}")
    logger.info(f"AI Predictions: {'Enabled' if config.USE_AI_PREDICTIONS else 'Disabled'}")

    # Create and start trading agent
    try:
        agent = CryptoFuturesTradingAgent(config)

        # Run the agent (5-minute intervals by default)
        # Adjust interval based on your timeframe
        interval_map = {
            '1m': 60,
            '5m': 300,
            '15m': 900,
            '1h': 3600,
            '4h': 14400
        }
        interval = interval_map.get(config.TIMEFRAME, 300)

        await agent.start(interval=interval)

    except KeyboardInterrupt:
        logger.info("Received shutdown signal")
    except Exception as e:
        logger.error(f"Fatal error: {e}", exc_info=True)
        sys.exit(1)


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logger.info("Application terminated by user")
        sys.exit(0)
