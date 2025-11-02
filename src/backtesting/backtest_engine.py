"""Production-grade backtesting engine."""
import pandas as pd
import numpy as np
from typing import Dict, List, Optional, Any, Callable
from datetime import datetime, timedelta
from dataclasses import dataclass, field
from ..utils.logger import setup_logger

logger = setup_logger(__name__)


@dataclass
class BacktestTrade:
    """Represents a single trade in backtest."""
    entry_time: datetime
    exit_time: Optional[datetime]
    symbol: str
    side: str  # 'long' or 'short'
    entry_price: float
    exit_price: Optional[float]
    quantity: float
    leverage: int
    stop_loss: Optional[float]
    take_profit: Optional[float]
    pnl: float = 0.0
    pnl_percent: float = 0.0
    fees: float = 0.0
    status: str = 'open'  # open, closed, stopped
    max_drawdown: float = 0.0
    signal_confidence: float = 0.0
    signal_reason: str = ''


@dataclass
class BacktestMetrics:
    """Backtest performance metrics."""
    total_trades: int = 0
    winning_trades: int = 0
    losing_trades: int = 0
    win_rate: float = 0.0
    total_pnl: float = 0.0
    total_pnl_percent: float = 0.0
    total_fees: float = 0.0
    net_pnl: float = 0.0
    average_win: float = 0.0
    average_loss: float = 0.0
    largest_win: float = 0.0
    largest_loss: float = 0.0
    profit_factor: float = 0.0
    sharpe_ratio: float = 0.0
    max_drawdown: float = 0.0
    max_drawdown_percent: float = 0.0
    recovery_factor: float = 0.0
    average_trade_duration: timedelta = timedelta()
    trades_per_day: float = 0.0
    equity_curve: List[float] = field(default_factory=list)
    daily_returns: List[float] = field(default_factory=list)


class BacktestEngine:
    """
    Professional backtesting engine with realistic simulation.

    Features:
    - Slippage simulation
    - Transaction fees
    - Realistic order filling
    - Stop-loss and take-profit execution
    - Position sizing
    - Multiple timeframes
    - Walk-forward analysis support
    """

    def __init__(
        self,
        initial_capital: float,
        fee_rate: float = 0.0004,  # 0.04% (Binance futures maker fee)
        slippage: float = 0.0005,  # 0.05% slippage
        use_leverage: bool = True
    ):
        """
        Initialize backtest engine.

        Args:
            initial_capital: Starting capital
            fee_rate: Transaction fee rate
            slippage: Slippage percentage
            use_leverage: Whether to use leverage
        """
        self.initial_capital = initial_capital
        self.current_capital = initial_capital
        self.fee_rate = fee_rate
        self.slippage = slippage
        self.use_leverage = use_leverage

        self.trades: List[BacktestTrade] = []
        self.open_trades: List[BacktestTrade] = []
        self.equity_history: List[Dict[str, Any]] = []

        logger.info(
            f"Backtest engine initialized - Capital: ${initial_capital:,.2f}, "
            f"Fee: {fee_rate*100:.3f}%, Slippage: {slippage*100:.3f}%"
        )

    def reset(self) -> None:
        """Reset backtest state."""
        self.current_capital = self.initial_capital
        self.trades = []
        self.open_trades = []
        self.equity_history = []

    def calculate_position_size(
        self,
        price: float,
        leverage: int,
        risk_percent: float,
        stop_loss_percent: float
    ) -> float:
        """
        Calculate position size based on risk management.

        Args:
            price: Entry price
            leverage: Leverage multiplier
            risk_percent: Percent of capital to risk
            stop_loss_percent: Stop loss percentage

        Returns:
            Position size in contracts
        """
        risk_amount = self.current_capital * (risk_percent / 100)
        stop_distance = price * (stop_loss_percent / 100)

        if stop_distance == 0:
            return 0

        position_value = risk_amount / (stop_loss_percent / 100)

        if self.use_leverage:
            position_value *= leverage

        quantity = position_value / price

        return quantity

    def apply_slippage(self, price: float, side: str) -> float:
        """
        Apply slippage to price.

        Args:
            price: Original price
            side: 'buy' or 'sell'

        Returns:
            Price with slippage
        """
        if side == 'buy':
            return price * (1 + self.slippage)
        else:
            return price * (1 - self.slippage)

    def calculate_fees(self, quantity: float, price: float) -> float:
        """
        Calculate transaction fees.

        Args:
            quantity: Trade quantity
            price: Trade price

        Returns:
            Fee amount
        """
        return quantity * price * self.fee_rate

    def open_position(
        self,
        timestamp: datetime,
        symbol: str,
        signal: Dict[str, Any],
        current_price: float,
        leverage: int,
        position_size_percent: float,
        stop_loss_percent: float,
        take_profit_percent: float
    ) -> Optional[BacktestTrade]:
        """
        Open a new position.

        Args:
            timestamp: Entry timestamp
            symbol: Trading symbol
            signal: Trading signal
            current_price: Current market price
            leverage: Leverage multiplier
            position_size_percent: Position size as % of capital
            stop_loss_percent: Stop loss percentage
            take_profit_percent: Take profit percentage

        Returns:
            BacktestTrade if opened, None otherwise
        """
        side = 'long' if signal['signal'] == 'BUY' else 'short'

        # Calculate position size
        quantity = self.calculate_position_size(
            current_price,
            leverage,
            position_size_percent,
            stop_loss_percent
        )

        if quantity == 0:
            return None

        # Apply slippage
        entry_price = self.apply_slippage(
            current_price,
            'buy' if side == 'long' else 'sell'
        )

        # Calculate fees
        entry_fees = self.calculate_fees(quantity, entry_price)

        # Calculate stop loss and take profit
        if side == 'long':
            stop_loss = entry_price * (1 - stop_loss_percent / 100)
            take_profit = entry_price * (1 + take_profit_percent / 100)
        else:
            stop_loss = entry_price * (1 + stop_loss_percent / 100)
            take_profit = entry_price * (1 - take_profit_percent / 100)

        # Create trade
        trade = BacktestTrade(
            entry_time=timestamp,
            exit_time=None,
            symbol=symbol,
            side=side,
            entry_price=entry_price,
            exit_price=None,
            quantity=quantity,
            leverage=leverage,
            stop_loss=stop_loss,
            take_profit=take_profit,
            fees=entry_fees,
            signal_confidence=signal.get('confidence', 0),
            signal_reason=signal.get('reason', '')
        )

        self.open_trades.append(trade)
        self.trades.append(trade)

        logger.debug(
            f"Position opened: {side.upper()} {quantity:.4f} {symbol} @ {entry_price:.2f}"
        )

        return trade

    def close_position(
        self,
        trade: BacktestTrade,
        timestamp: datetime,
        exit_price: float,
        reason: str = 'signal'
    ) -> None:
        """
        Close an open position.

        Args:
            trade: Trade to close
            timestamp: Exit timestamp
            exit_price: Exit price
            reason: Close reason
        """
        # Apply slippage
        exit_price = self.apply_slippage(
            exit_price,
            'sell' if trade.side == 'long' else 'buy'
        )

        # Calculate exit fees
        exit_fees = self.calculate_fees(trade.quantity, exit_price)
        trade.fees += exit_fees

        # Calculate P&L
        if trade.side == 'long':
            pnl = (exit_price - trade.entry_price) * trade.quantity * trade.leverage
        else:
            pnl = (trade.entry_price - exit_price) * trade.quantity * trade.leverage

        pnl -= trade.fees
        pnl_percent = (pnl / (trade.quantity * trade.entry_price)) * 100

        # Update trade
        trade.exit_time = timestamp
        trade.exit_price = exit_price
        trade.pnl = pnl
        trade.pnl_percent = pnl_percent
        trade.status = 'closed'

        # Update capital
        self.current_capital += pnl

        # Remove from open trades
        if trade in self.open_trades:
            self.open_trades.remove(trade)

        logger.debug(
            f"Position closed: {trade.side.upper()} {trade.symbol} @ {exit_price:.2f}, "
            f"P&L: ${pnl:.2f} ({pnl_percent:.2f}%)"
        )

    def update_positions(
        self,
        timestamp: datetime,
        current_high: float,
        current_low: float,
        current_close: float
    ) -> None:
        """
        Update open positions and check for stop-loss/take-profit.

        Args:
            timestamp: Current timestamp
            current_high: Current candle high
            current_low: Current candle low
            current_close: Current candle close
        """
        positions_to_close = []

        for trade in self.open_trades:
            # Check stop loss
            if trade.side == 'long' and current_low <= trade.stop_loss:
                positions_to_close.append((trade, trade.stop_loss, 'stop_loss'))
            elif trade.side == 'short' and current_high >= trade.stop_loss:
                positions_to_close.append((trade, trade.stop_loss, 'stop_loss'))

            # Check take profit
            elif trade.side == 'long' and current_high >= trade.take_profit:
                positions_to_close.append((trade, trade.take_profit, 'take_profit'))
            elif trade.side == 'short' and current_low <= trade.take_profit:
                positions_to_close.append((trade, trade.take_profit, 'take_profit'))

            # Track drawdown
            if trade.side == 'long':
                unrealized_pnl = (current_close - trade.entry_price) * trade.quantity
                if unrealized_pnl < 0:
                    trade.max_drawdown = min(trade.max_drawdown, unrealized_pnl)
            else:
                unrealized_pnl = (trade.entry_price - current_close) * trade.quantity
                if unrealized_pnl < 0:
                    trade.max_drawdown = min(trade.max_drawdown, unrealized_pnl)

        # Close positions
        for trade, exit_price, reason in positions_to_close:
            self.close_position(trade, timestamp, exit_price, reason)
            trade.status = reason

    def record_equity(self, timestamp: datetime, current_price: float) -> None:
        """
        Record current equity for equity curve.

        Args:
            timestamp: Current timestamp
            current_price: Current market price
        """
        # Calculate unrealized P&L
        unrealized_pnl = 0
        for trade in self.open_trades:
            if trade.side == 'long':
                unrealized_pnl += (current_price - trade.entry_price) * trade.quantity * trade.leverage
            else:
                unrealized_pnl += (trade.entry_price - current_price) * trade.quantity * trade.leverage

        total_equity = self.current_capital + unrealized_pnl

        self.equity_history.append({
            'timestamp': timestamp,
            'equity': total_equity,
            'realized_pnl': self.current_capital - self.initial_capital,
            'unrealized_pnl': unrealized_pnl,
            'open_positions': len(self.open_trades)
        })

    def run_backtest(
        self,
        data: pd.DataFrame,
        strategy: Any,
        config: Dict[str, Any]
    ) -> BacktestMetrics:
        """
        Run complete backtest.

        Args:
            data: Historical OHLCV data
            strategy: Trading strategy instance
            config: Backtest configuration

        Returns:
            Backtest metrics
        """
        logger.info(f"Starting backtest with {len(data)} candles")

        self.reset()

        for i in range(len(data)):
            if i < 100:  # Need enough history for indicators
                continue

            row = data.iloc[i]
            timestamp = row.name if isinstance(row.name, datetime) else datetime.now()

            # Get historical data slice
            hist_data = data.iloc[max(0, i - 100):i + 1]

            # Generate signal
            signal = strategy.generate_signal(hist_data)

            # Update existing positions
            self.update_positions(
                timestamp,
                row['high'],
                row['low'],
                row['close']
            )

            # Open new position if signal and no open positions
            if len(self.open_trades) < config.get('max_positions', 3):
                if signal['signal'] in ['BUY', 'SELL'] and signal['confidence'] >= config.get('min_confidence', 0.6):
                    self.open_position(
                        timestamp=timestamp,
                        symbol=config.get('symbol', 'BTC/USDT'),
                        signal=signal,
                        current_price=row['close'],
                        leverage=config.get('leverage', 1),
                        position_size_percent=config.get('position_size_percent', 2.0),
                        stop_loss_percent=config.get('stop_loss_percent', 2.0),
                        take_profit_percent=config.get('take_profit_percent', 4.0)
                    )

            # Record equity
            self.record_equity(timestamp, row['close'])

        # Close any remaining open positions
        final_price = data.iloc[-1]['close']
        final_timestamp = data.index[-1] if isinstance(data.index[0], datetime) else datetime.now()

        for trade in self.open_trades.copy():
            self.close_position(trade, final_timestamp, final_price, 'backtest_end')

        # Calculate metrics
        metrics = self.calculate_metrics()

        logger.info(
            f"Backtest completed - Trades: {metrics.total_trades}, "
            f"Win Rate: {metrics.win_rate*100:.2f}%, Net P&L: ${metrics.net_pnl:.2f}"
        )

        return metrics

    def calculate_metrics(self) -> BacktestMetrics:
        """
        Calculate comprehensive backtest metrics.

        Returns:
            BacktestMetrics object
        """
        closed_trades = [t for t in self.trades if t.status in ['closed', 'stop_loss', 'take_profit', 'backtest_end']]

        if not closed_trades:
            return BacktestMetrics()

        winning_trades = [t for t in closed_trades if t.pnl > 0]
        losing_trades = [t for t in closed_trades if t.pnl <= 0]

        total_pnl = sum(t.pnl for t in closed_trades)
        total_fees = sum(t.fees for t in closed_trades)
        net_pnl = total_pnl

        # Calculate profit factor
        total_wins = sum(t.pnl for t in winning_trades) if winning_trades else 0
        total_losses = abs(sum(t.pnl for t in losing_trades)) if losing_trades else 1
        profit_factor = total_wins / total_losses if total_losses > 0 else 0

        # Calculate Sharpe ratio
        if self.equity_history:
            equity_values = [e['equity'] for e in self.equity_history]
            returns = pd.Series(equity_values).pct_change().dropna()
            sharpe_ratio = (returns.mean() / returns.std()) * np.sqrt(252) if len(returns) > 0 else 0
        else:
            sharpe_ratio = 0

        # Calculate max drawdown
        if self.equity_history:
            equity_curve = [e['equity'] for e in self.equity_history]
            peak = equity_curve[0]
            max_dd = 0
            for equity in equity_curve:
                if equity > peak:
                    peak = equity
                dd = peak - equity
                if dd > max_dd:
                    max_dd = dd
            max_dd_percent = (max_dd / peak * 100) if peak > 0 else 0
        else:
            max_dd = 0
            max_dd_percent = 0

        # Calculate trade durations
        durations = [(t.exit_time - t.entry_time) for t in closed_trades if t.exit_time]
        avg_duration = sum(durations, timedelta()) / len(durations) if durations else timedelta()

        metrics = BacktestMetrics(
            total_trades=len(closed_trades),
            winning_trades=len(winning_trades),
            losing_trades=len(losing_trades),
            win_rate=len(winning_trades) / len(closed_trades) if closed_trades else 0,
            total_pnl=total_pnl,
            total_pnl_percent=(total_pnl / self.initial_capital) * 100,
            total_fees=total_fees,
            net_pnl=net_pnl,
            average_win=sum(t.pnl for t in winning_trades) / len(winning_trades) if winning_trades else 0,
            average_loss=sum(t.pnl for t in losing_trades) / len(losing_trades) if losing_trades else 0,
            largest_win=max([t.pnl for t in winning_trades]) if winning_trades else 0,
            largest_loss=min([t.pnl for t in losing_trades]) if losing_trades else 0,
            profit_factor=profit_factor,
            sharpe_ratio=sharpe_ratio,
            max_drawdown=max_dd,
            max_drawdown_percent=max_dd_percent,
            recovery_factor=net_pnl / max_dd if max_dd > 0 else 0,
            average_trade_duration=avg_duration,
            equity_curve=[e['equity'] for e in self.equity_history],
            daily_returns=[e['realized_pnl'] for e in self.equity_history]
        )

        return metrics

    def generate_report(self, metrics: BacktestMetrics) -> str:
        """
        Generate detailed backtest report.

        Args:
            metrics: Backtest metrics

        Returns:
            Formatted report string
        """
        report = f"""
{'='*60}
BACKTEST REPORT
{'='*60}

Initial Capital: ${self.initial_capital:,.2f}
Final Capital: ${self.current_capital:,.2f}
Net P&L: ${metrics.net_pnl:,.2f} ({metrics.total_pnl_percent:.2f}%)

TRADE STATISTICS
{'-'*60}
Total Trades: {metrics.total_trades}
Winning Trades: {metrics.winning_trades}
Losing Trades: {metrics.losing_trades}
Win Rate: {metrics.win_rate*100:.2f}%

PROFIT/LOSS
{'-'*60}
Total Fees: ${metrics.total_fees:,.2f}
Average Win: ${metrics.average_win:,.2f}
Average Loss: ${metrics.average_loss:,.2f}
Largest Win: ${metrics.largest_win:,.2f}
Largest Loss: ${metrics.largest_loss:,.2f}
Profit Factor: {metrics.profit_factor:.2f}

RISK METRICS
{'-'*60}
Max Drawdown: ${metrics.max_drawdown:,.2f} ({metrics.max_drawdown_percent:.2f}%)
Recovery Factor: {metrics.recovery_factor:.2f}
Sharpe Ratio: {metrics.sharpe_ratio:.2f}

PERFORMANCE
{'-'*60}
Average Trade Duration: {metrics.average_trade_duration}

{'='*60}
        """

        return report
