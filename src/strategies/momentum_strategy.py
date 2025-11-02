"""Momentum-based trading strategy."""
import pandas as pd
from typing import Dict
from .base_strategy import BaseStrategy
from .indicators import TechnicalIndicators
from ..utils.logger import setup_logger

logger = setup_logger(__name__)


class MomentumStrategy(BaseStrategy):
    """Momentum trading strategy using RSI, MACD, and moving averages."""

    def __init__(self, rsi_period: int = 14, rsi_overbought: int = 70, rsi_oversold: int = 30):
        """
        Initialize momentum strategy.

        Args:
            rsi_period: RSI calculation period
            rsi_overbought: RSI overbought threshold
            rsi_oversold: RSI oversold threshold
        """
        super().__init__("Momentum Strategy")
        self.rsi_period = rsi_period
        self.rsi_overbought = rsi_overbought
        self.rsi_oversold = rsi_oversold

    def calculate_indicators(self, df: pd.DataFrame) -> pd.DataFrame:
        """Calculate momentum indicators."""
        df = df.copy()

        # RSI
        df['rsi'] = TechnicalIndicators.calculate_rsi(df['close'], self.rsi_period)

        # MACD
        macd, signal, histogram = TechnicalIndicators.calculate_macd(df['close'])
        df['macd'] = macd
        df['macd_signal'] = signal
        df['macd_histogram'] = histogram

        # Moving Averages
        df['ema_9'] = TechnicalIndicators.calculate_ema(df['close'], 9)
        df['ema_21'] = TechnicalIndicators.calculate_ema(df['close'], 21)
        df['sma_50'] = TechnicalIndicators.calculate_sma(df['close'], 50)

        # Bollinger Bands
        upper, middle, lower = TechnicalIndicators.calculate_bollinger_bands(df['close'])
        df['bb_upper'] = upper
        df['bb_middle'] = middle
        df['bb_lower'] = lower

        return df

    def generate_signal(self, df: pd.DataFrame, **kwargs) -> Dict:
        """Generate trading signal based on momentum indicators."""
        df = self.calculate_indicators(df)

        if len(df) < 50:
            return {
                'signal': 'HOLD',
                'confidence': 0.0,
                'reason': 'Insufficient data',
                'indicators': {}
            }

        # Get latest values
        latest = df.iloc[-1]
        prev = df.iloc[-2]

        rsi = latest['rsi']
        macd = latest['macd']
        macd_signal = latest['macd_signal']
        macd_hist = latest['macd_histogram']
        ema_9 = latest['ema_9']
        ema_21 = latest['ema_21']
        price = latest['close']
        bb_upper = latest['bb_upper']
        bb_lower = latest['bb_lower']

        # Signal logic
        buy_signals = 0
        sell_signals = 0
        reasons = []

        # RSI signals
        if rsi < self.rsi_oversold:
            buy_signals += 2
            reasons.append(f"RSI oversold ({rsi:.2f})")
        elif rsi > self.rsi_overbought:
            sell_signals += 2
            reasons.append(f"RSI overbought ({rsi:.2f})")

        # MACD signals
        if macd > macd_signal and prev['macd'] <= prev['macd_signal']:
            buy_signals += 3
            reasons.append("MACD bullish crossover")
        elif macd < macd_signal and prev['macd'] >= prev['macd_signal']:
            sell_signals += 3
            reasons.append("MACD bearish crossover")

        # Moving average signals
        if ema_9 > ema_21:
            buy_signals += 1
            reasons.append("EMA bullish alignment")
        else:
            sell_signals += 1
            reasons.append("EMA bearish alignment")

        # Bollinger Bands
        if price < bb_lower:
            buy_signals += 1
            reasons.append("Price below lower BB")
        elif price > bb_upper:
            sell_signals += 1
            reasons.append("Price above upper BB")

        # Determine signal
        total_signals = buy_signals + sell_signals
        if total_signals == 0:
            signal = 'HOLD'
            confidence = 0.0
        elif buy_signals > sell_signals:
            signal = 'BUY'
            confidence = min(buy_signals / 7.0, 1.0)  # Normalize to 0-1
        elif sell_signals > buy_signals:
            signal = 'SELL'
            confidence = min(sell_signals / 7.0, 1.0)
        else:
            signal = 'HOLD'
            confidence = 0.0

        result = {
            'signal': signal,
            'confidence': confidence,
            'reason': '; '.join(reasons) if reasons else 'No clear signal',
            'indicators': {
                'rsi': float(rsi),
                'macd': float(macd),
                'macd_signal': float(macd_signal),
                'macd_histogram': float(macd_hist),
                'ema_9': float(ema_9),
                'ema_21': float(ema_21),
                'price': float(price)
            }
        }

        logger.debug(f"Signal generated: {result}")
        return result
