"""Risk management system for crypto futures trading."""
from typing import Dict, Optional, List
from datetime import datetime, timedelta
from ..utils.logger import setup_logger

logger = setup_logger(__name__)


class RiskManager:
    """Manages trading risks and position sizing."""

    def __init__(
        self,
        max_position_size: float,
        max_daily_loss_percent: float,
        stop_loss_percent: float,
        take_profit_percent: float,
        position_size_percent: float = 2.0
    ):
        """
        Initialize risk manager.

        Args:
            max_position_size: Maximum position size in USDT
            max_daily_loss_percent: Maximum daily loss percentage
            stop_loss_percent: Stop loss percentage
            take_profit_percent: Take profit percentage
            position_size_percent: Position size as percentage of portfolio
        """
        self.max_position_size = max_position_size
        self.max_daily_loss_percent = max_daily_loss_percent
        self.stop_loss_percent = stop_loss_percent
        self.take_profit_percent = take_profit_percent
        self.position_size_percent = position_size_percent

        # Track daily performance
        self.daily_pnl: Dict[str, float] = {}
        self.current_date = datetime.now().date()
        self.trades_today = 0

        logger.info(
            f"Initialized Risk Manager - Max Loss: {max_daily_loss_percent}%, "
            f"SL: {stop_loss_percent}%, TP: {take_profit_percent}%"
        )

    def calculate_position_size(
        self,
        balance: float,
        entry_price: float,
        leverage: int,
        signal_confidence: float
    ) -> float:
        """
        Calculate position size based on risk parameters.

        Args:
            balance: Account balance in USDT
            entry_price: Entry price
            leverage: Leverage multiplier
            signal_confidence: Signal confidence (0-1)

        Returns:
            Position size in contracts
        """
        # Base position size as percentage of balance
        base_size = balance * (self.position_size_percent / 100)

        # Adjust by signal confidence
        adjusted_size = base_size * signal_confidence

        # Apply leverage
        position_value = adjusted_size * leverage

        # Cap at max position size
        position_value = min(position_value, self.max_position_size)

        # Convert to contracts
        contracts = position_value / entry_price

        logger.debug(
            f"Position size calculated: {contracts:.4f} contracts "
            f"(${position_value:.2f}) at leverage {leverage}x"
        )

        return contracts

    def calculate_stop_loss(self, entry_price: float, side: str) -> float:
        """
        Calculate stop loss price.

        Args:
            entry_price: Entry price
            side: 'long' or 'short'

        Returns:
            Stop loss price
        """
        if side.lower() == 'long':
            stop_loss = entry_price * (1 - self.stop_loss_percent / 100)
        else:
            stop_loss = entry_price * (1 + self.stop_loss_percent / 100)

        logger.debug(f"Stop loss calculated: {stop_loss:.4f} for {side} at {entry_price:.4f}")
        return stop_loss

    def calculate_take_profit(self, entry_price: float, side: str) -> float:
        """
        Calculate take profit price.

        Args:
            entry_price: Entry price
            side: 'long' or 'short'

        Returns:
            Take profit price
        """
        if side.lower() == 'long':
            take_profit = entry_price * (1 + self.take_profit_percent / 100)
        else:
            take_profit = entry_price * (1 - self.take_profit_percent / 100)

        logger.debug(f"Take profit calculated: {take_profit:.4f} for {side} at {entry_price:.4f}")
        return take_profit

    def check_daily_loss_limit(self, current_pnl: float, balance: float) -> bool:
        """
        Check if daily loss limit has been reached.

        Args:
            current_pnl: Current P&L for the day
            balance: Account balance

        Returns:
            True if trading should continue, False if limit reached
        """
        # Reset if new day
        today = datetime.now().date()
        if today != self.current_date:
            self.current_date = today
            self.daily_pnl = {}
            self.trades_today = 0
            logger.info("New trading day - reset daily limits")

        # Calculate daily loss percentage
        loss_percent = abs(current_pnl / balance * 100) if balance > 0 else 0

        if current_pnl < 0 and loss_percent >= self.max_daily_loss_percent:
            logger.warning(
                f"Daily loss limit reached: {loss_percent:.2f}% "
                f"(limit: {self.max_daily_loss_percent}%)"
            )
            return False

        return True

    def validate_trade(
        self,
        signal: Dict,
        balance: float,
        current_positions: List[Dict],
        current_pnl: float
    ) -> Dict:
        """
        Validate if trade should be executed based on risk parameters.

        Args:
            signal: Trading signal
            balance: Account balance
            current_positions: List of current open positions
            current_pnl: Current daily P&L

        Returns:
            Validation result dictionary
        """
        # Check daily loss limit
        if not self.check_daily_loss_limit(current_pnl, balance):
            return {
                'allowed': False,
                'reason': 'Daily loss limit reached'
            }

        # Check signal confidence
        if signal['confidence'] < 0.5:
            return {
                'allowed': False,
                'reason': f"Low confidence: {signal['confidence']:.2f}"
            }

        # Check signal type
        if signal['signal'] == 'HOLD':
            return {
                'allowed': False,
                'reason': 'Signal is HOLD'
            }

        # Check balance
        if balance <= 0:
            return {
                'allowed': False,
                'reason': 'Insufficient balance'
            }

        # Check max open positions (limit to 3 concurrent positions)
        if len(current_positions) >= 3:
            return {
                'allowed': False,
                'reason': 'Maximum open positions reached (3)'
            }

        # All checks passed
        return {
            'allowed': True,
            'reason': 'All risk checks passed'
        }

    def calculate_position_pnl(
        self,
        entry_price: float,
        current_price: float,
        quantity: float,
        side: str
    ) -> float:
        """
        Calculate P&L for a position.

        Args:
            entry_price: Entry price
            current_price: Current market price
            quantity: Position size
            side: 'long' or 'short'

        Returns:
            P&L value
        """
        if side.lower() == 'long':
            pnl = (current_price - entry_price) * quantity
        else:
            pnl = (entry_price - current_price) * quantity

        return pnl

    def should_close_position(
        self,
        position: Dict,
        current_price: float
    ) -> Dict:
        """
        Check if position should be closed based on stop loss or take profit.

        Args:
            position: Position information
            current_price: Current market price

        Returns:
            Dictionary with decision and reason
        """
        entry_price = position['entry_price']
        side = position['side']
        stop_loss = position.get('stop_loss')
        take_profit = position.get('take_profit')

        # Check stop loss
        if stop_loss:
            if side.lower() == 'long' and current_price <= stop_loss:
                return {
                    'should_close': True,
                    'reason': f'Stop loss hit at {current_price:.4f}'
                }
            elif side.lower() == 'short' and current_price >= stop_loss:
                return {
                    'should_close': True,
                    'reason': f'Stop loss hit at {current_price:.4f}'
                }

        # Check take profit
        if take_profit:
            if side.lower() == 'long' and current_price >= take_profit:
                return {
                    'should_close': True,
                    'reason': f'Take profit hit at {current_price:.4f}'
                }
            elif side.lower() == 'short' and current_price <= take_profit:
                return {
                    'should_close': True,
                    'reason': f'Take profit hit at {current_price:.4f}'
                }

        return {
            'should_close': False,
            'reason': 'Position within risk parameters'
        }

    def update_daily_pnl(self, pnl: float) -> None:
        """Update daily P&L tracking."""
        today = datetime.now().date().isoformat()
        if today not in self.daily_pnl:
            self.daily_pnl[today] = 0.0

        self.daily_pnl[today] += pnl
        logger.info(f"Daily P&L updated: ${self.daily_pnl[today]:.2f}")

    def get_risk_metrics(self) -> Dict:
        """Get current risk metrics."""
        today = datetime.now().date().isoformat()
        return {
            'daily_pnl': self.daily_pnl.get(today, 0.0),
            'trades_today': self.trades_today,
            'max_daily_loss_percent': self.max_daily_loss_percent,
            'stop_loss_percent': self.stop_loss_percent,
            'take_profit_percent': self.take_profit_percent
        }
