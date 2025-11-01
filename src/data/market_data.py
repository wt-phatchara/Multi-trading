"""Market data handling for crypto futures trading."""
import ccxt
import pandas as pd
import numpy as np
from typing import Dict, List, Optional, Any
from datetime import datetime
import asyncio
from ..utils.logger import setup_logger

logger = setup_logger(__name__)


class MarketDataHandler:
    """Handles market data fetching and processing for crypto futures."""

    def __init__(self, exchange_name: str, api_key: str = '', api_secret: str = '', testnet: bool = True):
        """
        Initialize market data handler.

        Args:
            exchange_name: Name of the exchange (e.g., 'binance', 'bybit')
            api_key: Exchange API key
            api_secret: Exchange API secret
            testnet: Whether to use testnet
        """
        self.exchange_name = exchange_name
        self.exchange = self._initialize_exchange(exchange_name, api_key, api_secret, testnet)
        self.testnet = testnet
        logger.info(f"Initialized {exchange_name} market data handler (testnet={testnet})")

    def _initialize_exchange(self, name: str, api_key: str, api_secret: str, testnet: bool) -> ccxt.Exchange:
        """Initialize exchange instance."""
        try:
            exchange_class = getattr(ccxt, name)
            config = {
                'apiKey': api_key,
                'secret': api_secret,
                'enableRateLimit': True,
                'options': {'defaultType': 'future'}
            }

            if testnet:
                config['options']['testnet'] = True

            exchange = exchange_class(config)
            return exchange
        except Exception as e:
            logger.error(f"Failed to initialize exchange {name}: {e}")
            raise

    async def fetch_ohlcv(self, symbol: str, timeframe: str = '5m', limit: int = 100) -> pd.DataFrame:
        """
        Fetch OHLCV (candlestick) data.

        Args:
            symbol: Trading pair symbol (e.g., 'BTC/USDT')
            timeframe: Candle timeframe (1m, 5m, 15m, 1h, 4h, 1d)
            limit: Number of candles to fetch

        Returns:
            DataFrame with OHLCV data
        """
        try:
            ohlcv = await asyncio.to_thread(
                self.exchange.fetch_ohlcv,
                symbol,
                timeframe,
                limit=limit
            )

            df = pd.DataFrame(
                ohlcv,
                columns=['timestamp', 'open', 'high', 'low', 'close', 'volume']
            )
            df['timestamp'] = pd.to_datetime(df['timestamp'], unit='ms')
            df.set_index('timestamp', inplace=True)

            logger.debug(f"Fetched {len(df)} candles for {symbol} ({timeframe})")
            return df

        except Exception as e:
            logger.error(f"Error fetching OHLCV for {symbol}: {e}")
            raise

    async def fetch_ticker(self, symbol: str) -> Dict[str, Any]:
        """
        Fetch current ticker data.

        Args:
            symbol: Trading pair symbol

        Returns:
            Ticker data dictionary
        """
        try:
            ticker = await asyncio.to_thread(self.exchange.fetch_ticker, symbol)
            logger.debug(f"Ticker for {symbol}: {ticker['last']}")
            return ticker
        except Exception as e:
            logger.error(f"Error fetching ticker for {symbol}: {e}")
            raise

    async def fetch_order_book(self, symbol: str, limit: int = 20) -> Dict[str, Any]:
        """
        Fetch order book data.

        Args:
            symbol: Trading pair symbol
            limit: Depth of order book

        Returns:
            Order book data with bids and asks
        """
        try:
            order_book = await asyncio.to_thread(
                self.exchange.fetch_order_book,
                symbol,
                limit
            )
            logger.debug(f"Order book for {symbol}: {len(order_book['bids'])} bids, {len(order_book['asks'])} asks")
            return order_book
        except Exception as e:
            logger.error(f"Error fetching order book for {symbol}: {e}")
            raise

    async def fetch_funding_rate(self, symbol: str) -> Optional[float]:
        """
        Fetch current funding rate for futures.

        Args:
            symbol: Trading pair symbol

        Returns:
            Current funding rate
        """
        try:
            if hasattr(self.exchange, 'fetch_funding_rate'):
                funding = await asyncio.to_thread(
                    self.exchange.fetch_funding_rate,
                    symbol
                )
                rate = funding.get('fundingRate', 0)
                logger.debug(f"Funding rate for {symbol}: {rate}")
                return rate
            else:
                logger.warning(f"Exchange {self.exchange_name} doesn't support funding rates")
                return None
        except Exception as e:
            logger.error(f"Error fetching funding rate for {symbol}: {e}")
            return None

    async def fetch_balance(self) -> Dict[str, Any]:
        """
        Fetch account balance.

        Returns:
            Balance information
        """
        try:
            balance = await asyncio.to_thread(self.exchange.fetch_balance)
            logger.info(f"Fetched balance: {balance.get('total', {})}")
            return balance
        except Exception as e:
            logger.error(f"Error fetching balance: {e}")
            raise

    async def fetch_positions(self) -> List[Dict[str, Any]]:
        """
        Fetch open positions.

        Returns:
            List of open positions
        """
        try:
            if hasattr(self.exchange, 'fetch_positions'):
                positions = await asyncio.to_thread(self.exchange.fetch_positions)
                open_positions = [p for p in positions if float(p.get('contracts', 0)) != 0]
                logger.info(f"Fetched {len(open_positions)} open positions")
                return open_positions
            else:
                logger.warning(f"Exchange {self.exchange_name} doesn't support position fetching")
                return []
        except Exception as e:
            logger.error(f"Error fetching positions: {e}")
            raise

    def calculate_market_metrics(self, df: pd.DataFrame) -> Dict[str, float]:
        """
        Calculate market metrics from OHLCV data.

        Args:
            df: DataFrame with OHLCV data

        Returns:
            Dictionary with market metrics
        """
        if df.empty:
            return {}

        metrics = {
            'current_price': float(df['close'].iloc[-1]),
            'price_change_24h': float((df['close'].iloc[-1] - df['close'].iloc[0]) / df['close'].iloc[0] * 100),
            'high_24h': float(df['high'].max()),
            'low_24h': float(df['low'].min()),
            'volume_24h': float(df['volume'].sum()),
            'volatility': float(df['close'].pct_change().std() * 100)
        }

        return metrics
