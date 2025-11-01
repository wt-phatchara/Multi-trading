"""Main trading agent controller for crypto futures."""
import asyncio
from typing import Dict, Optional
from datetime import datetime
from ..utils.config import Config
from ..utils.logger import setup_logger
from ..data.market_data import MarketDataHandler
from ..strategies.momentum_strategy import MomentumStrategy
from ..strategies.advanced_strategy import AdvancedStrategy
from ..agent.ai_engine import AIDecisionEngine
from ..risk.risk_manager import RiskManager
from ..execution.order_executor import OrderExecutor

logger = setup_logger(__name__)


class CryptoFuturesTradingAgent:
    """AI-powered crypto futures trading agent."""

    def __init__(self, config: Optional[Config] = None):
        """
        Initialize the trading agent.

        Args:
            config: Configuration object (uses default if not provided)
        """
        self.config = config or Config()
        self.config.validate()

        # Initialize components
        self.market_data = MarketDataHandler(
            self.config.EXCHANGE_NAME,
            self.config.EXCHANGE_API_KEY,
            self.config.EXCHANGE_API_SECRET,
            self.config.EXCHANGE_TESTNET
        )

        # Select strategy based on configuration
        if self.config.STRATEGY.lower() == 'advanced':
            self.strategy = AdvancedStrategy()
            logger.info("Using Advanced Strategy (SMC + EW + PA + S/R + Indicators)")
        else:
            self.strategy = MomentumStrategy(
                rsi_period=self.config.RSI_PERIOD,
                rsi_overbought=self.config.RSI_OVERBOUGHT,
                rsi_oversold=self.config.RSI_OVERSOLD
            )
            logger.info("Using Momentum Strategy")

        self.ai_engine = AIDecisionEngine(
            model_path=self.config.AI_MODEL_PATH if self.config.USE_AI_PREDICTIONS else None,
            confidence_threshold=self.config.CONFIDENCE_THRESHOLD
        )

        self.risk_manager = RiskManager(
            max_position_size=self.config.MAX_POSITION_SIZE,
            max_daily_loss_percent=self.config.MAX_DAILY_LOSS_PERCENT,
            stop_loss_percent=self.config.STOP_LOSS_PERCENT,
            take_profit_percent=self.config.TAKE_PROFIT_PERCENT,
            position_size_percent=self.config.POSITION_SIZE_PERCENT
        )

        self.order_executor = OrderExecutor(
            self.market_data.exchange,
            self.config.TRADING_MODE
        )

        self.is_running = False
        self.symbol = self.config.DEFAULT_SYMBOL

        logger.info(f"Trading Agent initialized - Symbol: {self.symbol}, Mode: {self.config.TRADING_MODE}")

    async def analyze_market(self) -> Dict:
        """
        Analyze current market conditions.

        Returns:
            Market analysis dictionary
        """
        try:
            # Fetch market data
            df = await self.market_data.fetch_ohlcv(
                self.symbol,
                self.config.TIMEFRAME,
                limit=100
            )

            ticker = await self.market_data.fetch_ticker(self.symbol)
            funding_rate = await self.market_data.fetch_funding_rate(self.symbol)

            # Calculate market metrics
            metrics = self.market_data.calculate_market_metrics(df)

            # Generate strategy signal
            strategy_signal = self.strategy.generate_signal(df)

            # Combine with AI if enabled
            if self.config.USE_AI_PREDICTIONS:
                final_signal = self.ai_engine.combine_with_strategy(strategy_signal, df)
            else:
                final_signal = strategy_signal

            analysis = {
                'timestamp': datetime.now(),
                'symbol': self.symbol,
                'current_price': ticker['last'],
                'metrics': metrics,
                'signal': final_signal,
                'funding_rate': funding_rate
            }

            logger.info(
                f"Market Analysis - Price: ${ticker['last']:.2f}, "
                f"Signal: {final_signal['signal']}, "
                f"Confidence: {final_signal['confidence']:.2f}"
            )

            return analysis

        except Exception as e:
            logger.error(f"Error analyzing market: {e}")
            return {}

    async def execute_trade(self, analysis: Dict) -> bool:
        """
        Execute trade based on market analysis.

        Args:
            analysis: Market analysis dictionary

        Returns:
            True if trade executed, False otherwise
        """
        try:
            signal = analysis.get('signal', {})
            current_price = analysis.get('current_price', 0)

            # Get balance
            balance = await self.market_data.fetch_balance()
            usdt_balance = float(balance.get('USDT', {}).get('free', 0))

            # Get current positions
            open_positions = self.order_executor.get_open_positions()
            current_pnl = sum(
                self.risk_manager.calculate_position_pnl(
                    p['entry_price'],
                    current_price,
                    p['quantity'],
                    p['side']
                ) for p in open_positions
            )

            # Validate trade
            validation = self.risk_manager.validate_trade(
                signal,
                usdt_balance,
                open_positions,
                current_pnl
            )

            if not validation['allowed']:
                logger.info(f"Trade not executed: {validation['reason']}")
                return False

            # Calculate position size
            position_size = self.risk_manager.calculate_position_size(
                usdt_balance,
                current_price,
                self.config.LEVERAGE,
                signal['confidence']
            )

            # Determine trade side
            side = 'buy' if signal['signal'] == 'BUY' else 'sell'

            # Calculate stop loss and take profit
            trade_side = 'long' if signal['signal'] == 'BUY' else 'short'
            stop_loss = self.risk_manager.calculate_stop_loss(current_price, trade_side)
            take_profit = self.risk_manager.calculate_take_profit(current_price, trade_side)

            # Execute order
            order = await self.order_executor.place_market_order(
                symbol=self.symbol,
                side=side,
                amount=position_size,
                leverage=self.config.LEVERAGE,
                stop_loss=stop_loss,
                take_profit=take_profit
            )

            if order:
                logger.info(
                    f"Trade executed: {signal['signal']} {position_size:.4f} {self.symbol} "
                    f"at ${current_price:.2f} - Reason: {signal['reason']}"
                )
                return True
            else:
                logger.warning("Failed to execute trade")
                return False

        except Exception as e:
            logger.error(f"Error executing trade: {e}")
            return False

    async def manage_positions(self, current_price: float) -> None:
        """
        Manage open positions (check stop loss, take profit, etc.).

        Args:
            current_price: Current market price
        """
        try:
            open_positions = self.order_executor.get_open_positions()

            for position in open_positions:
                # Check if position should be closed
                close_decision = self.risk_manager.should_close_position(
                    position,
                    current_price
                )

                if close_decision['should_close']:
                    await self.order_executor.close_position(
                        position,
                        close_decision['reason']
                    )

                    # Calculate and update P&L
                    pnl = self.risk_manager.calculate_position_pnl(
                        position['entry_price'],
                        current_price,
                        position['quantity'],
                        position['side']
                    )
                    self.risk_manager.update_daily_pnl(pnl)

        except Exception as e:
            logger.error(f"Error managing positions: {e}")

    async def run_trading_cycle(self) -> None:
        """Execute one complete trading cycle."""
        try:
            logger.info("=" * 60)
            logger.info("Starting trading cycle")

            # Analyze market
            analysis = await self.analyze_market()

            if not analysis:
                logger.warning("Skipping cycle - no market analysis")
                return

            current_price = analysis.get('current_price', 0)

            # Manage existing positions
            await self.manage_positions(current_price)

            # Check if we should open a new position
            signal = analysis.get('signal', {})
            if signal.get('signal') != 'HOLD' and signal.get('confidence', 0) > 0.6:
                await self.execute_trade(analysis)

            # Update positions from exchange
            await self.order_executor.update_positions()

            # Log status
            risk_metrics = self.risk_manager.get_risk_metrics()
            logger.info(f"Daily P&L: ${risk_metrics['daily_pnl']:.2f}")
            logger.info(f"Open positions: {len(self.order_executor.get_open_positions())}")
            logger.info("Trading cycle completed")
            logger.info("=" * 60)

        except Exception as e:
            logger.error(f"Error in trading cycle: {e}")

    async def start(self, interval: int = 300) -> None:
        """
        Start the trading agent.

        Args:
            interval: Time between trading cycles in seconds (default: 5 minutes)
        """
        self.is_running = True
        logger.info(f"Starting Crypto Futures Trading Agent - Interval: {interval}s")
        logger.info(f"Symbol: {self.symbol}, Timeframe: {self.config.TIMEFRAME}")
        logger.info(f"Mode: {self.config.TRADING_MODE}, Leverage: {self.config.LEVERAGE}x")

        try:
            while self.is_running:
                await self.run_trading_cycle()
                await asyncio.sleep(interval)

        except KeyboardInterrupt:
            logger.info("Received stop signal")
            await self.stop()
        except Exception as e:
            logger.error(f"Fatal error in agent: {e}")
            await self.stop()

    async def stop(self) -> None:
        """Stop the trading agent."""
        logger.info("Stopping trading agent...")
        self.is_running = False

        # Close all positions if needed
        # Uncomment if you want to auto-close positions on stop
        # await self.order_executor.close_all_positions("Agent stopped")

        logger.info("Trading agent stopped")

    def get_status(self) -> Dict:
        """Get current agent status."""
        return {
            'is_running': self.is_running,
            'symbol': self.symbol,
            'trading_mode': self.config.TRADING_MODE,
            'open_positions': len(self.order_executor.get_open_positions()),
            'risk_metrics': self.risk_manager.get_risk_metrics()
        }
