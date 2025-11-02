"""Configuration management for the trading agent."""
import os
from typing import Any, Dict
from dotenv import load_dotenv

load_dotenv()


class Config:
    """Configuration class for trading agent."""

    # Exchange Configuration
    EXCHANGE_NAME: str = os.getenv('EXCHANGE_NAME', 'binance')
    EXCHANGE_API_KEY: str = os.getenv('EXCHANGE_API_KEY', '')
    EXCHANGE_API_SECRET: str = os.getenv('EXCHANGE_API_SECRET', '')
    EXCHANGE_TESTNET: bool = os.getenv('EXCHANGE_TESTNET', 'true').lower() == 'true'

    # Trading Configuration
    TRADING_MODE: str = os.getenv('TRADING_MODE', 'paper')
    DEFAULT_SYMBOL: str = os.getenv('DEFAULT_SYMBOL', 'BTC/USDT')
    LEVERAGE: int = int(os.getenv('LEVERAGE', '10'))
    POSITION_SIZE_PERCENT: float = float(os.getenv('POSITION_SIZE_PERCENT', '2.0'))

    # Risk Management
    MAX_DAILY_LOSS_PERCENT: float = float(os.getenv('MAX_DAILY_LOSS_PERCENT', '5.0'))
    MAX_POSITION_SIZE: float = float(os.getenv('MAX_POSITION_SIZE', '1000'))
    STOP_LOSS_PERCENT: float = float(os.getenv('STOP_LOSS_PERCENT', '2.0'))
    TAKE_PROFIT_PERCENT: float = float(os.getenv('TAKE_PROFIT_PERCENT', '4.0'))

    # Strategy Configuration
    STRATEGY: str = os.getenv('STRATEGY', 'ai_momentum')
    TIMEFRAME: str = os.getenv('TIMEFRAME', '5m')
    RSI_PERIOD: int = int(os.getenv('RSI_PERIOD', '14'))
    RSI_OVERBOUGHT: int = int(os.getenv('RSI_OVERBOUGHT', '70'))
    RSI_OVERSOLD: int = int(os.getenv('RSI_OVERSOLD', '30'))

    # AI Model Configuration
    AI_MODEL_PATH: str = os.getenv('AI_MODEL_PATH', 'models/trading_model.h5')
    USE_AI_PREDICTIONS: bool = os.getenv('USE_AI_PREDICTIONS', 'true').lower() == 'true'
    CONFIDENCE_THRESHOLD: float = float(os.getenv('CONFIDENCE_THRESHOLD', '0.7'))

    # Logging
    LOG_LEVEL: str = os.getenv('LOG_LEVEL', 'INFO')

    @classmethod
    def to_dict(cls) -> Dict[str, Any]:
        """Convert configuration to dictionary."""
        return {
            key: value for key, value in cls.__dict__.items()
            if not key.startswith('_') and not callable(value)
        }

    @classmethod
    def validate(cls) -> bool:
        """Validate configuration."""
        if cls.TRADING_MODE not in ['paper', 'live']:
            raise ValueError("TRADING_MODE must be 'paper' or 'live'")

        if cls.TRADING_MODE == 'live' and (not cls.EXCHANGE_API_KEY or not cls.EXCHANGE_API_SECRET):
            raise ValueError("API credentials required for live trading")

        if cls.LEVERAGE < 1 or cls.LEVERAGE > 125:
            raise ValueError("LEVERAGE must be between 1 and 125")

        return True
