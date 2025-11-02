"""Database layer for production state persistence."""
from sqlalchemy import create_engine, Column, Integer, String, Float, DateTime, Boolean, Text, JSON
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, Session
from sqlalchemy.pool import QueuePool
from datetime import datetime
from typing import List, Optional, Dict, Any
from contextlib import contextmanager
from ..utils.logger import setup_logger

logger = setup_logger(__name__)

Base = declarative_base()


class Trade(Base):
    """Trade execution record."""
    __tablename__ = 'trades'

    id = Column(Integer, primary_key=True)
    order_id = Column(String(100), unique=True, nullable=False)
    symbol = Column(String(20), nullable=False)
    side = Column(String(10), nullable=False)  # buy/sell
    type = Column(String(20), nullable=False)  # market/limit
    quantity = Column(Float, nullable=False)
    price = Column(Float, nullable=False)
    leverage = Column(Integer, default=1)
    status = Column(String(20), nullable=False)  # open/closed/cancelled
    entry_time = Column(DateTime, nullable=False)
    exit_time = Column(DateTime, nullable=True)
    pnl = Column(Float, default=0.0)
    fees = Column(Float, default=0.0)
    stop_loss = Column(Float, nullable=True)
    take_profit = Column(Float, nullable=True)
    strategy = Column(String(50), nullable=False)
    signal_confidence = Column(Float, nullable=True)
    signal_reason = Column(Text, nullable=True)
    metadata = Column(JSON, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


class Position(Base):
    """Current open positions."""
    __tablename__ = 'positions'

    id = Column(Integer, primary_key=True)
    symbol = Column(String(20), nullable=False, unique=True)
    side = Column(String(10), nullable=False)  # long/short
    quantity = Column(Float, nullable=False)
    entry_price = Column(Float, nullable=False)
    current_price = Column(Float, nullable=True)
    leverage = Column(Integer, nullable=False)
    unrealized_pnl = Column(Float, default=0.0)
    stop_loss = Column(Float, nullable=True)
    take_profit = Column(Float, nullable=True)
    entry_time = Column(DateTime, nullable=False)
    last_updated = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


class MarketData(Base):
    """Historical market data snapshots."""
    __tablename__ = 'market_data'

    id = Column(Integer, primary_key=True)
    symbol = Column(String(20), nullable=False)
    timestamp = Column(DateTime, nullable=False)
    open = Column(Float, nullable=False)
    high = Column(Float, nullable=False)
    low = Column(Float, nullable=False)
    close = Column(Float, nullable=False)
    volume = Column(Float, nullable=False)
    timeframe = Column(String(10), nullable=False)


class AgentState(Base):
    """Agent runtime state for recovery."""
    __tablename__ = 'agent_state'

    id = Column(Integer, primary_key=True)
    timestamp = Column(DateTime, default=datetime.utcnow)
    is_running = Column(Boolean, default=False)
    current_balance = Column(Float, nullable=True)
    daily_pnl = Column(Float, default=0.0)
    open_positions_count = Column(Integer, default=0)
    total_trades_today = Column(Integer, default=0)
    last_health_check = Column(DateTime, nullable=True)
    error_count = Column(Integer, default=0)
    last_error = Column(Text, nullable=True)
    metadata = Column(JSON, nullable=True)


class AuditLog(Base):
    """Audit trail for all operations."""
    __tablename__ = 'audit_logs'

    id = Column(Integer, primary_key=True)
    timestamp = Column(DateTime, default=datetime.utcnow)
    event_type = Column(String(50), nullable=False)  # trade_open, trade_close, config_change, etc.
    severity = Column(String(20), nullable=False)  # info, warning, error, critical
    description = Column(Text, nullable=False)
    user = Column(String(50), nullable=True)
    metadata = Column(JSON, nullable=True)


class DatabaseManager:
    """Production database manager with connection pooling."""

    def __init__(self, database_url: str, pool_size: int = 10, max_overflow: int = 20):
        """
        Initialize database manager.

        Args:
            database_url: Database connection URL
            pool_size: Connection pool size
            max_overflow: Max overflow connections
        """
        self.engine = create_engine(
            database_url,
            poolclass=QueuePool,
            pool_size=pool_size,
            max_overflow=max_overflow,
            pool_pre_ping=True,  # Test connections before use
            pool_recycle=3600,  # Recycle connections every hour
            echo=False
        )

        self.SessionLocal = sessionmaker(
            autocommit=False,
            autoflush=False,
            bind=self.engine
        )

        logger.info(f"Database manager initialized (pool_size={pool_size})")

    def create_tables(self) -> None:
        """Create all tables."""
        Base.metadata.create_all(bind=self.engine)
        logger.info("Database tables created")

    @contextmanager
    def get_session(self) -> Session:
        """
        Get database session with automatic cleanup.

        Yields:
            Database session
        """
        session = self.SessionLocal()
        try:
            yield session
            session.commit()
        except Exception as e:
            session.rollback()
            logger.error(f"Database session error: {e}")
            raise
        finally:
            session.close()

    def log_trade(self, trade_data: Dict[str, Any]) -> int:
        """
        Log a trade to database.

        Args:
            trade_data: Trade information

        Returns:
            Trade ID
        """
        with self.get_session() as session:
            trade = Trade(**trade_data)
            session.add(trade)
            session.flush()
            trade_id = trade.id
            logger.info(f"Trade logged: {trade_id}")
            return trade_id

    def update_position(self, symbol: str, position_data: Dict[str, Any]) -> None:
        """
        Update or create position.

        Args:
            symbol: Trading symbol
            position_data: Position data
        """
        with self.get_session() as session:
            position = session.query(Position).filter(Position.symbol == symbol).first()

            if position:
                for key, value in position_data.items():
                    setattr(position, key, value)
            else:
                position = Position(symbol=symbol, **position_data)
                session.add(position)

            logger.debug(f"Position updated: {symbol}")

    def close_position(self, symbol: str) -> None:
        """
        Remove position from database.

        Args:
            symbol: Trading symbol
        """
        with self.get_session() as session:
            session.query(Position).filter(Position.symbol == symbol).delete()
            logger.info(f"Position closed: {symbol}")

    def get_open_positions(self) -> List[Position]:
        """
        Get all open positions.

        Returns:
            List of open positions
        """
        with self.get_session() as session:
            return session.query(Position).all()

    def save_market_data(self, data: Dict[str, Any]) -> None:
        """
        Save market data snapshot.

        Args:
            data: Market data
        """
        with self.get_session() as session:
            market_data = MarketData(**data)
            session.add(market_data)

    def update_agent_state(self, state_data: Dict[str, Any]) -> None:
        """
        Update agent state for recovery.

        Args:
            state_data: Agent state data
        """
        with self.get_session() as session:
            # Get or create latest state
            state = session.query(AgentState).order_by(
                AgentState.timestamp.desc()
            ).first()

            if state:
                for key, value in state_data.items():
                    setattr(state, key, value)
                state.timestamp = datetime.utcnow()
            else:
                state = AgentState(**state_data)
                session.add(state)

    def get_agent_state(self) -> Optional[AgentState]:
        """
        Get latest agent state.

        Returns:
            Latest agent state or None
        """
        with self.get_session() as session:
            return session.query(AgentState).order_by(
                AgentState.timestamp.desc()
            ).first()

    def audit_log(self, event_type: str, description: str,
                   severity: str = 'info', metadata: Dict = None) -> None:
        """
        Add audit log entry.

        Args:
            event_type: Type of event
            description: Event description
            severity: Log severity
            metadata: Additional metadata
        """
        with self.get_session() as session:
            log = AuditLog(
                event_type=event_type,
                description=description,
                severity=severity,
                metadata=metadata
            )
            session.add(log)

    def get_trade_history(self, limit: int = 100, symbol: Optional[str] = None) -> List[Trade]:
        """
        Get trade history.

        Args:
            limit: Number of trades to retrieve
            symbol: Filter by symbol (optional)

        Returns:
            List of trades
        """
        with self.get_session() as session:
            query = session.query(Trade)
            if symbol:
                query = query.filter(Trade.symbol == symbol)

            return query.order_by(Trade.created_at.desc()).limit(limit).all()

    def get_performance_metrics(self, days: int = 30) -> Dict[str, Any]:
        """
        Calculate performance metrics.

        Args:
            days: Number of days to analyze

        Returns:
            Performance metrics
        """
        with self.get_session() as session:
            from sqlalchemy import func
            from datetime import timedelta

            cutoff_date = datetime.utcnow() - timedelta(days=days)

            trades = session.query(Trade).filter(
                Trade.created_at >= cutoff_date,
                Trade.status == 'closed'
            ).all()

            if not trades:
                return {}

            total_trades = len(trades)
            winning_trades = len([t for t in trades if t.pnl > 0])
            losing_trades = len([t for t in trades if t.pnl < 0])
            total_pnl = sum(t.pnl for t in trades)
            total_fees = sum(t.fees for t in trades)

            return {
                'total_trades': total_trades,
                'winning_trades': winning_trades,
                'losing_trades': losing_trades,
                'win_rate': winning_trades / total_trades if total_trades > 0 else 0,
                'total_pnl': total_pnl,
                'total_fees': total_fees,
                'net_pnl': total_pnl - total_fees,
                'average_pnl': total_pnl / total_trades if total_trades > 0 else 0
            }
