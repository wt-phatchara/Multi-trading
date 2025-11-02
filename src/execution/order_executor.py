"""Order execution and position management for crypto futures."""
import ccxt
import asyncio
from typing import Dict, List, Optional
from datetime import datetime
from ..utils.logger import setup_logger

logger = setup_logger(__name__)


class OrderExecutor:
    """Handles order execution and position management."""

    def __init__(self, exchange: ccxt.Exchange, trading_mode: str = 'paper'):
        """
        Initialize order executor.

        Args:
            exchange: CCXT exchange instance
            trading_mode: 'paper' or 'live'
        """
        self.exchange = exchange
        self.trading_mode = trading_mode
        self.open_positions: List[Dict] = []
        self.order_history: List[Dict] = []

        logger.info(f"Initialized Order Executor - Mode: {trading_mode}")

    async def place_market_order(
        self,
        symbol: str,
        side: str,
        amount: float,
        leverage: int = 1,
        stop_loss: Optional[float] = None,
        take_profit: Optional[float] = None
    ) -> Optional[Dict]:
        """
        Place a market order.

        Args:
            symbol: Trading pair symbol
            side: 'buy' or 'sell'
            amount: Order amount
            leverage: Leverage multiplier
            stop_loss: Stop loss price
            take_profit: Take profit price

        Returns:
            Order result or None if failed
        """
        try:
            # Set leverage
            if hasattr(self.exchange, 'set_leverage'):
                await asyncio.to_thread(
                    self.exchange.set_leverage,
                    leverage,
                    symbol
                )
                logger.info(f"Set leverage to {leverage}x for {symbol}")

            # Paper trading simulation
            if self.trading_mode == 'paper':
                logger.info(
                    f"[PAPER TRADE] Market {side.upper()}: {amount} {symbol} "
                    f"at {leverage}x leverage"
                )
                # Simulate order
                ticker = await asyncio.to_thread(self.exchange.fetch_ticker, symbol)
                order = {
                    'id': f"paper_{datetime.now().timestamp()}",
                    'symbol': symbol,
                    'type': 'market',
                    'side': side,
                    'amount': amount,
                    'price': ticker['last'],
                    'cost': amount * ticker['last'],
                    'timestamp': datetime.now().timestamp(),
                    'status': 'closed',
                    'leverage': leverage,
                    'stop_loss': stop_loss,
                    'take_profit': take_profit
                }
            else:
                # Live trading
                order = await asyncio.to_thread(
                    self.exchange.create_market_order,
                    symbol,
                    side,
                    amount
                )
                logger.info(f"[LIVE] Market order placed: {order['id']}")

                # Place stop loss and take profit orders if specified
                if stop_loss:
                    await self.place_stop_loss(symbol, side, amount, stop_loss)

                if take_profit:
                    await self.place_take_profit(symbol, side, amount, take_profit)

            # Track order
            self.order_history.append(order)

            # Add to open positions
            position = {
                'symbol': symbol,
                'side': 'long' if side == 'buy' else 'short',
                'entry_price': order['price'],
                'quantity': amount,
                'leverage': leverage,
                'entry_time': datetime.now(),
                'stop_loss': stop_loss,
                'take_profit': take_profit,
                'order_id': order['id']
            }
            self.open_positions.append(position)

            logger.info(
                f"Position opened: {side.upper()} {amount} {symbol} "
                f"at {order['price']:.4f}"
            )

            return order

        except Exception as e:
            logger.error(f"Error placing market order: {e}")
            return None

    async def place_stop_loss(
        self,
        symbol: str,
        side: str,
        amount: float,
        stop_price: float
    ) -> Optional[Dict]:
        """Place a stop loss order."""
        try:
            # Determine order side for stop loss (opposite of entry)
            stop_side = 'sell' if side == 'buy' else 'buy'

            if self.trading_mode == 'paper':
                logger.info(
                    f"[PAPER TRADE] Stop Loss: {stop_side.upper()} {amount} {symbol} "
                    f"at {stop_price:.4f}"
                )
                return None

            # Live stop loss order
            params = {'stopPrice': stop_price}
            order = await asyncio.to_thread(
                self.exchange.create_order,
                symbol,
                'stop_market',
                stop_side,
                amount,
                None,
                params
            )

            logger.info(f"Stop loss order placed at {stop_price:.4f}")
            return order

        except Exception as e:
            logger.error(f"Error placing stop loss: {e}")
            return None

    async def place_take_profit(
        self,
        symbol: str,
        side: str,
        amount: float,
        take_profit_price: float
    ) -> Optional[Dict]:
        """Place a take profit order."""
        try:
            # Determine order side for take profit (opposite of entry)
            tp_side = 'sell' if side == 'buy' else 'buy'

            if self.trading_mode == 'paper':
                logger.info(
                    f"[PAPER TRADE] Take Profit: {tp_side.upper()} {amount} {symbol} "
                    f"at {take_profit_price:.4f}"
                )
                return None

            # Live take profit order
            params = {'stopPrice': take_profit_price}
            order = await asyncio.to_thread(
                self.exchange.create_order,
                symbol,
                'take_profit_market',
                tp_side,
                amount,
                None,
                params
            )

            logger.info(f"Take profit order placed at {take_profit_price:.4f}")
            return order

        except Exception as e:
            logger.error(f"Error placing take profit: {e}")
            return None

    async def close_position(self, position: Dict, reason: str = '') -> bool:
        """
        Close an open position.

        Args:
            position: Position dictionary
            reason: Reason for closing

        Returns:
            True if successful, False otherwise
        """
        try:
            symbol = position['symbol']
            quantity = position['quantity']
            side = 'sell' if position['side'] == 'long' else 'buy'

            # Close position
            if self.trading_mode == 'paper':
                ticker = await asyncio.to_thread(self.exchange.fetch_ticker, symbol)
                exit_price = ticker['last']
                logger.info(
                    f"[PAPER TRADE] Closing position: {side.upper()} {quantity} {symbol} "
                    f"at {exit_price:.4f} - Reason: {reason}"
                )
            else:
                order = await asyncio.to_thread(
                    self.exchange.create_market_order,
                    symbol,
                    side,
                    quantity
                )
                exit_price = order['price']
                logger.info(f"[LIVE] Position closed: {order['id']} - Reason: {reason}")

            # Calculate P&L
            entry_price = position['entry_price']
            if position['side'] == 'long':
                pnl = (exit_price - entry_price) * quantity
            else:
                pnl = (entry_price - exit_price) * quantity

            logger.info(f"Position P&L: ${pnl:.2f}")

            # Remove from open positions
            self.open_positions = [p for p in self.open_positions if p != position]

            return True

        except Exception as e:
            logger.error(f"Error closing position: {e}")
            return False

    async def close_all_positions(self, reason: str = 'Manual close') -> int:
        """
        Close all open positions.

        Args:
            reason: Reason for closing

        Returns:
            Number of positions closed
        """
        closed_count = 0
        positions_to_close = self.open_positions.copy()

        for position in positions_to_close:
            if await self.close_position(position, reason):
                closed_count += 1

        logger.info(f"Closed {closed_count} positions - Reason: {reason}")
        return closed_count

    def get_open_positions(self) -> List[Dict]:
        """Get list of open positions."""
        return self.open_positions.copy()

    def get_position_by_symbol(self, symbol: str) -> Optional[Dict]:
        """Get position for specific symbol."""
        for position in self.open_positions:
            if position['symbol'] == symbol:
                return position
        return None

    async def update_positions(self) -> None:
        """Update position information from exchange."""
        try:
            if self.trading_mode == 'live' and hasattr(self.exchange, 'fetch_positions'):
                live_positions = await asyncio.to_thread(self.exchange.fetch_positions)

                # Update open positions with live data
                for live_pos in live_positions:
                    symbol = live_pos['symbol']
                    contracts = float(live_pos.get('contracts', 0))

                    if contracts != 0:
                        # Find matching position
                        for pos in self.open_positions:
                            if pos['symbol'] == symbol:
                                pos['current_price'] = live_pos.get('markPrice', 0)
                                pos['unrealized_pnl'] = live_pos.get('unrealizedPnl', 0)
                                break

                logger.debug("Positions updated from exchange")

        except Exception as e:
            logger.error(f"Error updating positions: {e}")

    def get_order_history(self, limit: int = 10) -> List[Dict]:
        """Get recent order history."""
        return self.order_history[-limit:] if self.order_history else []
