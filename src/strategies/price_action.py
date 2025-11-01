"""Price Action pattern recognition and analysis."""
import pandas as pd
import numpy as np
from typing import Dict, List, Optional
from ..utils.logger import setup_logger

logger = setup_logger(__name__)


class PriceActionPatterns:
    """Recognize and analyze price action patterns."""

    @staticmethod
    def is_bullish_engulfing(df: pd.DataFrame, idx: int = -1) -> bool:
        """Check for bullish engulfing pattern."""
        if idx < -len(df) + 1:
            return False

        current = df.iloc[idx]
        previous = df.iloc[idx - 1]

        # Previous candle is bearish, current is bullish
        prev_bearish = previous['close'] < previous['open']
        curr_bullish = current['close'] > current['open']

        # Current body engulfs previous body
        engulfs = (current['open'] <= previous['close'] and
                  current['close'] >= previous['open'])

        return prev_bearish and curr_bullish and engulfs

    @staticmethod
    def is_bearish_engulfing(df: pd.DataFrame, idx: int = -1) -> bool:
        """Check for bearish engulfing pattern."""
        if idx < -len(df) + 1:
            return False

        current = df.iloc[idx]
        previous = df.iloc[idx - 1]

        # Previous candle is bullish, current is bearish
        prev_bullish = previous['close'] > previous['open']
        curr_bearish = current['close'] < current['open']

        # Current body engulfs previous body
        engulfs = (current['open'] >= previous['close'] and
                  current['close'] <= previous['open'])

        return prev_bullish and curr_bearish and engulfs

    @staticmethod
    def is_hammer(df: pd.DataFrame, idx: int = -1) -> bool:
        """Check for hammer pattern (bullish reversal)."""
        candle = df.iloc[idx]

        body = abs(candle['close'] - candle['open'])
        lower_wick = min(candle['open'], candle['close']) - candle['low']
        upper_wick = candle['high'] - max(candle['open'], candle['close'])

        # Long lower wick, small body, small upper wick
        return (lower_wick > body * 2 and
                upper_wick < body * 0.5 and
                body > 0)

    @staticmethod
    def is_shooting_star(df: pd.DataFrame, idx: int = -1) -> bool:
        """Check for shooting star pattern (bearish reversal)."""
        candle = df.iloc[idx]

        body = abs(candle['close'] - candle['open'])
        lower_wick = min(candle['open'], candle['close']) - candle['low']
        upper_wick = candle['high'] - max(candle['open'], candle['close'])

        # Long upper wick, small body, small lower wick
        return (upper_wick > body * 2 and
                lower_wick < body * 0.5 and
                body > 0)

    @staticmethod
    def is_doji(df: pd.DataFrame, idx: int = -1, tolerance: float = 0.1) -> bool:
        """Check for doji pattern (indecision)."""
        candle = df.iloc[idx]

        body = abs(candle['close'] - candle['open'])
        total_range = candle['high'] - candle['low']

        # Very small body compared to total range
        return body / total_range < tolerance if total_range > 0 else False

    @staticmethod
    def is_morning_star(df: pd.DataFrame, idx: int = -1) -> bool:
        """Check for morning star pattern (bullish reversal)."""
        if idx < -len(df) + 2:
            return False

        first = df.iloc[idx - 2]
        second = df.iloc[idx - 1]
        third = df.iloc[idx]

        # First: Large bearish candle
        first_bearish = first['close'] < first['open']
        first_body = abs(first['close'] - first['open'])

        # Second: Small body (star)
        second_body = abs(second['close'] - second['open'])
        is_star = second_body < first_body * 0.3

        # Third: Large bullish candle
        third_bullish = third['close'] > third['open']
        third_body = abs(third['close'] - third['open'])

        # Third closes above midpoint of first
        closes_high = third['close'] > (first['open'] + first['close']) / 2

        return first_bearish and is_star and third_bullish and closes_high

    @staticmethod
    def is_evening_star(df: pd.DataFrame, idx: int = -1) -> bool:
        """Check for evening star pattern (bearish reversal)."""
        if idx < -len(df) + 2:
            return False

        first = df.iloc[idx - 2]
        second = df.iloc[idx - 1]
        third = df.iloc[idx]

        # First: Large bullish candle
        first_bullish = first['close'] > first['open']
        first_body = abs(first['close'] - first['open'])

        # Second: Small body (star)
        second_body = abs(second['close'] - second['open'])
        is_star = second_body < first_body * 0.3

        # Third: Large bearish candle
        third_bearish = third['close'] < third['open']

        # Third closes below midpoint of first
        closes_low = third['close'] < (first['open'] + first['close']) / 2

        return first_bullish and is_star and third_bearish and closes_low

    @staticmethod
    def detect_trend(df: pd.DataFrame, period: int = 20) -> str:
        """
        Detect current trend using price action.

        Returns:
            'UPTREND', 'DOWNTREND', or 'SIDEWAYS'
        """
        if len(df) < period:
            return 'SIDEWAYS'

        recent = df.tail(period)
        highs = recent['high']
        lows = recent['low']

        # Higher highs and higher lows = uptrend
        higher_highs = all(highs.iloc[i] >= highs.iloc[i-1] for i in range(1, min(5, len(highs))))
        higher_lows = all(lows.iloc[i] >= lows.iloc[i-1] for i in range(1, min(5, len(lows))))

        # Lower highs and lower lows = downtrend
        lower_highs = all(highs.iloc[i] <= highs.iloc[i-1] for i in range(1, min(5, len(highs))))
        lower_lows = all(lows.iloc[i] <= lows.iloc[i-1] for i in range(1, min(5, len(lows))))

        if higher_highs and higher_lows:
            return 'UPTREND'
        elif lower_highs and lower_lows:
            return 'DOWNTREND'
        else:
            return 'SIDEWAYS'

    @staticmethod
    def analyze_patterns(df: pd.DataFrame) -> Dict:
        """
        Analyze all price action patterns.

        Returns:
            Dictionary with pattern analysis
        """
        patterns = {
            'bullish_engulfing': PriceActionPatterns.is_bullish_engulfing(df),
            'bearish_engulfing': PriceActionPatterns.is_bearish_engulfing(df),
            'hammer': PriceActionPatterns.is_hammer(df),
            'shooting_star': PriceActionPatterns.is_shooting_star(df),
            'doji': PriceActionPatterns.is_doji(df),
            'morning_star': PriceActionPatterns.is_morning_star(df),
            'evening_star': PriceActionPatterns.is_evening_star(df),
            'trend': PriceActionPatterns.detect_trend(df)
        }

        logger.debug(f"Price action patterns detected: {patterns}")
        return patterns

    @staticmethod
    def generate_signal(df: pd.DataFrame) -> Dict:
        """
        Generate trading signal based on price action.

        Returns:
            Signal dictionary
        """
        patterns = PriceActionPatterns.analyze_patterns(df)

        signal = 'HOLD'
        confidence = 0.0
        reasons = []

        # Bullish patterns
        if patterns['bullish_engulfing']:
            signal = 'BUY'
            confidence = 0.75
            reasons.append('Bullish engulfing pattern')

        if patterns['hammer'] and patterns['trend'] == 'DOWNTREND':
            signal = 'BUY'
            confidence = max(confidence, 0.7)
            reasons.append('Hammer pattern in downtrend (reversal)')

        if patterns['morning_star']:
            signal = 'BUY'
            confidence = 0.8
            reasons.append('Morning star pattern (strong reversal)')

        # Bearish patterns
        if patterns['bearish_engulfing']:
            signal = 'SELL'
            confidence = 0.75
            reasons.append('Bearish engulfing pattern')

        if patterns['shooting_star'] and patterns['trend'] == 'UPTREND':
            signal = 'SELL'
            confidence = max(confidence, 0.7)
            reasons.append('Shooting star in uptrend (reversal)')

        if patterns['evening_star']:
            signal = 'SELL'
            confidence = 0.8
            reasons.append('Evening star pattern (strong reversal)')

        # Doji indicates indecision
        if patterns['doji'] and not reasons:
            reasons.append('Doji - market indecision')

        # Trend following
        if patterns['trend'] == 'UPTREND' and not reasons:
            signal = 'BUY'
            confidence = 0.5
            reasons.append('Clear uptrend')
        elif patterns['trend'] == 'DOWNTREND' and not reasons:
            signal = 'SELL'
            confidence = 0.5
            reasons.append('Clear downtrend')

        return {
            'signal': signal,
            'confidence': confidence,
            'reason': '; '.join(reasons) if reasons else 'No clear price action signal',
            'patterns': patterns
        }
