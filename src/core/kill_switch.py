"""Production kill switch and safety mechanisms."""
from typing import Dict, Any, Optional, Callable
from datetime import datetime, timedelta
from enum import Enum
from ..utils.logger import setup_logger

logger = setup_logger(__name__)


class KillSwitchReason(Enum):
    """Reasons for triggering kill switch."""
    MAX_DRAWDOWN = "max_drawdown_exceeded"
    MAX_DAILY_LOSS = "max_daily_loss_exceeded"
    RAPID_LOSSES = "rapid_consecutive_losses"
    EXCHANGE_ERROR = "critical_exchange_error"
    MANUAL_TRIGGER = "manual_trigger"
    HEALTH_CHECK_FAILED = "health_check_failed"
    POSITION_RECONCILIATION_FAILED = "position_reconciliation_failed"


class KillSwitch:
    """
    Production kill switch for emergency shutdown.

    Monitors multiple safety conditions and can halt trading immediately.
    """

    def __init__(
        self,
        max_drawdown_percent: float = 10.0,
        max_daily_loss_percent: float = 5.0,
        max_consecutive_losses: int = 5,
        enable_auto_recovery: bool = False,
        recovery_delay_minutes: int = 60
    ):
        """
        Initialize kill switch.

        Args:
            max_drawdown_percent: Maximum drawdown before shutdown
            max_daily_loss_percent: Maximum daily loss before shutdown
            max_consecutive_losses: Max consecutive losses before shutdown
            enable_auto_recovery: Whether to auto-recover after delay
            recovery_delay_minutes: Minutes to wait before auto-recovery
        """
        self.max_drawdown_percent = max_drawdown_percent
        self.max_daily_loss_percent = max_daily_loss_percent
        self.max_consecutive_losses = max_consecutive_losses
        self.enable_auto_recovery = enable_auto_recovery
        self.recovery_delay = timedelta(minutes=recovery_delay_minutes)

        self.is_triggered = False
        self.trigger_reason: Optional[KillSwitchReason] = None
        self.trigger_time: Optional[datetime] = None
        self.trigger_data: Dict[str, Any] = {}

        self.consecutive_losses = 0
        self.peak_equity = 0.0
        self.daily_start_equity = 0.0
        self.current_equity = 0.0

        self.callbacks: Dict[KillSwitchReason, list] = {reason: [] for reason in KillSwitchReason}

        logger.info(
            f"Kill Switch initialized - Max DD: {max_drawdown_percent}%, "
            f"Max Daily Loss: {max_daily_loss_percent}%, "
            f"Max Consecutive Losses: {max_consecutive_losses}"
        )

    def register_callback(self, reason: KillSwitchReason, callback: Callable) -> None:
        """
        Register callback for specific trigger reason.

        Args:
            reason: Trigger reason
            callback: Async function to call when triggered
        """
        self.callbacks[reason].append(callback)

    async def check_conditions(
        self,
        current_equity: float,
        initial_equity: float,
        daily_pnl: float
    ) -> bool:
        """
        Check all kill switch conditions.

        Args:
            current_equity: Current account equity
            initial_equity: Initial equity for the trading session
            daily_pnl: Today's P&L

        Returns:
            True if safe to continue, False if kill switch triggered
        """
        self.current_equity = current_equity

        # Track peak equity for drawdown calculation
        if current_equity > self.peak_equity:
            self.peak_equity = current_equity

        # Check maximum drawdown
        if self.peak_equity > 0:
            drawdown_percent = ((self.peak_equity - current_equity) / self.peak_equity) * 100

            if drawdown_percent >= self.max_drawdown_percent:
                await self.trigger(
                    KillSwitchReason.MAX_DRAWDOWN,
                    {
                        'drawdown_percent': drawdown_percent,
                        'peak_equity': self.peak_equity,
                        'current_equity': current_equity
                    }
                )
                return False

        # Check maximum daily loss
        if initial_equity > 0:
            daily_loss_percent = (daily_pnl / initial_equity) * 100

            if daily_pnl < 0 and abs(daily_loss_percent) >= self.max_daily_loss_percent:
                await self.trigger(
                    KillSwitchReason.MAX_DAILY_LOSS,
                    {
                        'daily_loss_percent': abs(daily_loss_percent),
                        'daily_pnl': daily_pnl,
                        'initial_equity': initial_equity
                    }
                )
                return False

        return not self.is_triggered

    def record_trade_result(self, pnl: float) -> None:
        """
        Record trade result and check consecutive losses.

        Args:
            pnl: Trade P&L
        """
        if pnl < 0:
            self.consecutive_losses += 1

            if self.consecutive_losses >= self.max_consecutive_losses:
                # Use sync trigger for rapid response
                self._trigger_sync(
                    KillSwitchReason.RAPID_LOSSES,
                    {
                        'consecutive_losses': self.consecutive_losses,
                        'last_loss': pnl
                    }
                )
        else:
            self.consecutive_losses = 0

    async def trigger(
        self,
        reason: KillSwitchReason,
        data: Dict[str, Any] = None
    ) -> None:
        """
        Trigger kill switch.

        Args:
            reason: Reason for trigger
            data: Additional trigger data
        """
        if self.is_triggered:
            logger.warning(f"Kill switch already triggered: {self.trigger_reason.value}")
            return

        self.is_triggered = True
        self.trigger_reason = reason
        self.trigger_time = datetime.utcnow()
        self.trigger_data = data or {}

        logger.critical(
            f"🚨 KILL SWITCH TRIGGERED 🚨 "
            f"Reason: {reason.value}, "
            f"Data: {data}"
        )

        # Execute callbacks
        for callback in self.callbacks[reason]:
            try:
                await callback(reason, data)
            except Exception as e:
                logger.error(f"Kill switch callback error: {e}")

        # Execute global callbacks
        for callback in self.callbacks.get(KillSwitchReason.MANUAL_TRIGGER, []):
            try:
                await callback(reason, data)
            except Exception as e:
                logger.error(f"Kill switch global callback error: {e}")

    def _trigger_sync(self, reason: KillSwitchReason, data: Dict[str, Any] = None) -> None:
        """Synchronous trigger for urgent cases."""
        self.is_triggered = True
        self.trigger_reason = reason
        self.trigger_time = datetime.utcnow()
        self.trigger_data = data or {}

        logger.critical(
            f"🚨 KILL SWITCH TRIGGERED (SYNC) 🚨 "
            f"Reason: {reason.value}, "
            f"Data: {data}"
        )

    def manual_trigger(self, reason: str = "Manual intervention") -> None:
        """
        Manually trigger kill switch.

        Args:
            reason: Human-readable reason
        """
        self._trigger_sync(
            KillSwitchReason.MANUAL_TRIGGER,
            {'reason': reason}
        )

    def can_auto_recover(self) -> bool:
        """
        Check if auto-recovery is allowed.

        Returns:
            True if can auto-recover
        """
        if not self.enable_auto_recovery or not self.is_triggered:
            return False

        if not self.trigger_time:
            return False

        elapsed = datetime.utcnow() - self.trigger_time
        return elapsed >= self.recovery_delay

    def reset(self, manual_override: bool = False) -> bool:
        """
        Reset kill switch.

        Args:
            manual_override: Force reset even if not allowed

        Returns:
            True if reset successful
        """
        if not manual_override and not self.can_auto_recover():
            logger.warning("Kill switch reset not allowed at this time")
            return False

        logger.warning("Kill switch reset - resuming operations")

        self.is_triggered = False
        self.trigger_reason = None
        self.trigger_time = None
        self.trigger_data = {}
        self.consecutive_losses = 0

        return True

    def get_status(self) -> Dict[str, Any]:
        """Get current kill switch status."""
        return {
            'is_triggered': self.is_triggered,
            'trigger_reason': self.trigger_reason.value if self.trigger_reason else None,
            'trigger_time': self.trigger_time.isoformat() if self.trigger_time else None,
            'trigger_data': self.trigger_data,
            'consecutive_losses': self.consecutive_losses,
            'peak_equity': self.peak_equity,
            'current_equity': self.current_equity,
            'can_auto_recover': self.can_auto_recover()
        }


class PositionReconciliation:
    """Reconcile positions between local state and exchange."""

    def __init__(self, tolerance_percent: float = 1.0):
        """
        Initialize position reconciliation.

        Args:
            tolerance_percent: Acceptable difference percentage
        """
        self.tolerance_percent = tolerance_percent
        logger.info(f"Position reconciliation initialized (tolerance: {tolerance_percent}%)")

    async def reconcile(
        self,
        local_positions: list,
        exchange_positions: list
    ) -> Dict[str, Any]:
        """
        Reconcile local positions with exchange.

        Args:
            local_positions: Local position records
            exchange_positions: Positions from exchange

        Returns:
            Reconciliation result
        """
        discrepancies = []
        warnings = []

        # Create position maps
        local_map = {p['symbol']: p for p in local_positions}
        exchange_map = {p['symbol']: p for p in exchange_positions}

        # Check for missing positions
        local_symbols = set(local_map.keys())
        exchange_symbols = set(exchange_map.keys())

        missing_on_exchange = local_symbols - exchange_symbols
        missing_locally = exchange_symbols - local_symbols

        if missing_on_exchange:
            warnings.append(f"Positions in local state but not on exchange: {missing_on_exchange}")

        if missing_locally:
            warnings.append(f"Positions on exchange but not in local state: {missing_locally}")

        # Check position sizes
        for symbol in local_symbols & exchange_symbols:
            local_pos = local_map[symbol]
            exchange_pos = exchange_map[symbol]

            local_qty = abs(local_pos.get('quantity', 0))
            exchange_qty = abs(float(exchange_pos.get('contracts', 0)))

            if local_qty == 0 and exchange_qty == 0:
                continue

            diff_percent = abs(local_qty - exchange_qty) / max(local_qty, exchange_qty) * 100

            if diff_percent > self.tolerance_percent:
                discrepancies.append({
                    'symbol': symbol,
                    'local_quantity': local_qty,
                    'exchange_quantity': exchange_qty,
                    'difference_percent': diff_percent
                })

        is_healthy = len(discrepancies) == 0

        if not is_healthy:
            logger.error(
                f"Position reconciliation failed - Discrepancies: {len(discrepancies)}, "
                f"Warnings: {len(warnings)}"
            )

        return {
            'is_healthy': is_healthy,
            'discrepancies': discrepancies,
            'warnings': warnings,
            'local_count': len(local_positions),
            'exchange_count': len(exchange_positions)
        }
