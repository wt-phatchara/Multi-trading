"""Base strategy class for trading strategies."""
from abc import ABC, abstractmethod
from typing import Dict, Optional, Literal
import pandas as pd
from ..utils.logger import setup_logger

logger = setup_logger(__name__)

SignalType = Literal['BUY', 'SELL', 'HOLD']


class BaseStrategy(ABC):
    """Abstract base class for trading strategies."""

    def __init__(self, name: str):
        """
        Initialize base strategy.

        Args:
            name: Strategy name
        """
        self.name = name
        logger.info(f"Initialized strategy: {name}")

    @abstractmethod
    def generate_signal(self, df: pd.DataFrame, **kwargs) -> Dict:
        """
        Generate trading signal based on market data.

        Args:
            df: DataFrame with OHLCV data
            **kwargs: Additional parameters

        Returns:
            Dictionary with signal information
            {
                'signal': 'BUY' | 'SELL' | 'HOLD',
                'confidence': float (0-1),
                'reason': str,
                'indicators': dict
            }
        """
        pass

    @abstractmethod
    def calculate_indicators(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        Calculate strategy-specific indicators.

        Args:
            df: DataFrame with OHLCV data

        Returns:
            DataFrame with added indicator columns
        """
        pass

    def validate_signal(self, signal: Dict) -> bool:
        """
        Validate signal structure.

        Args:
            signal: Signal dictionary

        Returns:
            True if valid, False otherwise
        """
        required_keys = ['signal', 'confidence', 'reason']
        if not all(key in signal for key in required_keys):
            logger.warning(f"Invalid signal structure: {signal}")
            return False

        if signal['signal'] not in ['BUY', 'SELL', 'HOLD']:
            logger.warning(f"Invalid signal type: {signal['signal']}")
            return False

        if not 0 <= signal['confidence'] <= 1:
            logger.warning(f"Invalid confidence value: {signal['confidence']}")
            return False

        return True
