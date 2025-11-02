"""Tests for risk management."""
import pytest
from src.risk.risk_manager import RiskManager
from src.core.kill_switch import KillSwitch, KillSwitchReason


class TestRiskManager:
    """Test risk management."""

    def test_initialization(self):
        """Test risk manager initialization."""
        rm = RiskManager(
            max_position_size=1000,
            max_daily_loss_percent=5.0,
            stop_loss_percent=2.0,
            take_profit_percent=4.0
        )

        assert rm.max_position_size == 1000
        assert rm.max_daily_loss_percent == 5.0

    def test_position_size_calculation(self):
        """Test position size calculation."""
        rm = RiskManager(
            max_position_size=1000,
            max_daily_loss_percent=5.0,
            stop_loss_percent=2.0,
            take_profit_percent=4.0
        )

        size = rm.calculate_position_size(
            balance=10000,
            entry_price=40000,
            leverage=5,
            signal_confidence=0.8
        )

        assert size > 0

    def test_stop_loss_calculation(self):
        """Test stop loss calculation."""
        rm = RiskManager(
            max_position_size=1000,
            max_daily_loss_percent=5.0,
            stop_loss_percent=2.0,
            take_profit_percent=4.0
        )

        # Long position
        sl_long = rm.calculate_stop_loss(40000, 'long')
        assert sl_long < 40000

        # Short position
        sl_short = rm.calculate_stop_loss(40000, 'short')
        assert sl_short > 40000

    def test_daily_loss_limit(self):
        """Test daily loss limit check."""
        rm = RiskManager(
            max_position_size=1000,
            max_daily_loss_percent=5.0,
            stop_loss_percent=2.0,
            take_profit_percent=4.0
        )

        # Within limit
        assert rm.check_daily_loss_limit(-400, 10000) is True

        # Exceeds limit
        assert rm.check_daily_loss_limit(-600, 10000) is False


class TestKillSwitch:
    """Test kill switch."""

    def test_initialization(self):
        """Test kill switch initialization."""
        ks = KillSwitch(
            max_drawdown_percent=10.0,
            max_daily_loss_percent=5.0
        )

        assert ks.max_drawdown_percent == 10.0
        assert not ks.is_triggered

    @pytest.mark.asyncio
    async def test_drawdown_check(self):
        """Test drawdown checking."""
        ks = KillSwitch(max_drawdown_percent=5.0)

        # Safe condition
        result = await ks.check_conditions(
            current_equity=10000,
            initial_equity=10000,
            daily_pnl=0
        )
        assert result is True
        assert not ks.is_triggered

        # Trigger drawdown
        result = await ks.check_conditions(
            current_equity=9400,  # 6% drawdown from peak
            initial_equity=10000,
            daily_pnl=-600
        )
        assert result is False
        assert ks.is_triggered
        assert ks.trigger_reason == KillSwitchReason.MAX_DRAWDOWN

    def test_consecutive_losses(self):
        """Test consecutive loss tracking."""
        ks = KillSwitch(max_consecutive_losses=3)

        ks.record_trade_result(-100)
        assert ks.consecutive_losses == 1
        assert not ks.is_triggered

        ks.record_trade_result(-100)
        ks.record_trade_result(-100)
        assert ks.consecutive_losses == 3
        assert ks.is_triggered

        # Reset on win
        ks2 = KillSwitch(max_consecutive_losses=3)
        ks2.record_trade_result(-100)
        ks2.record_trade_result(100)
        assert ks2.consecutive_losses == 0

    def test_manual_trigger(self):
        """Test manual trigger."""
        ks = KillSwitch()

        ks.manual_trigger("Emergency stop")

        assert ks.is_triggered
        assert ks.trigger_reason == KillSwitchReason.MANUAL_TRIGGER

    def test_reset(self):
        """Test kill switch reset."""
        ks = KillSwitch(enable_auto_recovery=False)

        ks.manual_trigger()
        assert ks.is_triggered

        # Should fail without manual override
        result = ks.reset(manual_override=False)
        assert result is False
        assert ks.is_triggered

        # Should succeed with manual override
        result = ks.reset(manual_override=True)
        assert result is True
        assert not ks.is_triggered
