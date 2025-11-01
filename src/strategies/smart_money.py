"""Smart Money Concepts (SMC) implementation."""
import pandas as pd
import numpy as np
from typing import Dict, List, Optional, Tuple
from ..utils.logger import setup_logger

logger = setup_logger(__name__)


class SmartMoneyConcepts:
    """Implement Smart Money Concepts (SMC) trading methodology."""

    @staticmethod
    def identify_market_structure(df: pd.DataFrame, lookback: int = 10) -> Dict:
        """
        Identify market structure (Higher Highs, Higher Lows, etc.).

        Args:
            df: DataFrame with OHLC data
            lookback: Number of periods to analyze

        Returns:
            Market structure analysis
        """
        if len(df) < lookback:
            return {'structure': 'UNKNOWN'}

        recent = df.tail(lookback)
        highs = recent['high'].values
        lows = recent['low'].values

        # Find swing highs and lows
        swing_highs = []
        swing_lows = []

        for i in range(1, len(highs) - 1):
            if highs[i] > highs[i-1] and highs[i] > highs[i+1]:
                swing_highs.append(highs[i])
            if lows[i] < lows[i-1] and lows[i] < lows[i+1]:
                swing_lows.append(lows[i])

        if len(swing_highs) < 2 or len(swing_lows) < 2:
            return {'structure': 'UNKNOWN'}

        # Determine structure
        higher_highs = swing_highs[-1] > swing_highs[-2] if len(swing_highs) >= 2 else False
        higher_lows = swing_lows[-1] > swing_lows[-2] if len(swing_lows) >= 2 else False
        lower_highs = swing_highs[-1] < swing_highs[-2] if len(swing_highs) >= 2 else False
        lower_lows = swing_lows[-1] < swing_lows[-2] if len(swing_lows) >= 2 else False

        if higher_highs and higher_lows:
            structure = 'BULLISH'
        elif lower_highs and lower_lows:
            structure = 'BEARISH'
        else:
            structure = 'RANGING'

        return {
            'structure': structure,
            'swing_highs': swing_highs,
            'swing_lows': swing_lows
        }

    @staticmethod
    def find_order_blocks(df: pd.DataFrame, lookback: int = 50) -> Dict:
        """
        Identify order blocks (areas where institutions placed orders).

        Order blocks are the last bullish/bearish candle before a strong move.

        Args:
            df: DataFrame with OHLC data
            lookback: Number of periods to analyze

        Returns:
            Bullish and bearish order blocks
        """
        if len(df) < lookback:
            return {'bullish_ob': [], 'bearish_ob': []}

        recent = df.tail(lookback).copy()
        recent['body'] = abs(recent['close'] - recent['open'])
        recent['range'] = recent['high'] - recent['low']

        bullish_ob = []
        bearish_ob = []

        for i in range(2, len(recent) - 2):
            current = recent.iloc[i]
            next_candle = recent.iloc[i + 1]

            # Bullish order block: Last down candle before strong up move
            if (current['close'] < current['open'] and  # Current is bearish
                next_candle['close'] > next_candle['open'] and  # Next is bullish
                next_candle['body'] > current['body'] * 2):  # Next is strong

                bullish_ob.append({
                    'high': current['high'],
                    'low': current['low'],
                    'price': (current['high'] + current['low']) / 2,
                    'index': i,
                    'type': 'BULLISH'
                })

            # Bearish order block: Last up candle before strong down move
            if (current['close'] > current['open'] and  # Current is bullish
                next_candle['close'] < next_candle['open'] and  # Next is bearish
                next_candle['body'] > current['body'] * 2):  # Next is strong

                bearish_ob.append({
                    'high': current['high'],
                    'low': current['low'],
                    'price': (current['high'] + current['low']) / 2,
                    'index': i,
                    'type': 'BEARISH'
                })

        return {
            'bullish_ob': bullish_ob[-3:] if bullish_ob else [],  # Last 3
            'bearish_ob': bearish_ob[-3:] if bearish_ob else []
        }

    @staticmethod
    def identify_fair_value_gaps(df: pd.DataFrame, lookback: int = 50) -> Dict:
        """
        Identify Fair Value Gaps (FVG) - imbalances in price.

        FVG occurs when there's a gap between candles indicating inefficiency.

        Args:
            df: DataFrame with OHLC data
            lookback: Number of periods to analyze

        Returns:
            Bullish and bearish FVGs
        """
        if len(df) < lookback:
            return {'bullish_fvg': [], 'bearish_fvg': []}

        recent = df.tail(lookback)
        bullish_fvg = []
        bearish_fvg = []

        for i in range(2, len(recent)):
            candle1 = recent.iloc[i - 2]
            candle2 = recent.iloc[i - 1]
            candle3 = recent.iloc[i]

            # Bullish FVG: Gap between candle1 high and candle3 low
            if candle3['low'] > candle1['high']:
                bullish_fvg.append({
                    'upper': candle3['low'],
                    'lower': candle1['high'],
                    'price': (candle3['low'] + candle1['high']) / 2,
                    'index': i,
                    'type': 'BULLISH'
                })

            # Bearish FVG: Gap between candle1 low and candle3 high
            if candle3['high'] < candle1['low']:
                bearish_fvg.append({
                    'upper': candle1['low'],
                    'lower': candle3['high'],
                    'price': (candle1['low'] + candle3['high']) / 2,
                    'index': i,
                    'type': 'BEARISH'
                })

        return {
            'bullish_fvg': bullish_fvg[-3:] if bullish_fvg else [],
            'bearish_fvg': bearish_fvg[-3:] if bearish_fvg else []
        }

    @staticmethod
    def find_liquidity_zones(df: pd.DataFrame, lookback: int = 50) -> Dict:
        """
        Find liquidity zones (areas where stop losses are likely placed).

        These are typically around swing highs/lows.

        Args:
            df: DataFrame with OHLC data
            lookback: Number of periods to analyze

        Returns:
            Buy-side and sell-side liquidity zones
        """
        if len(df) < lookback:
            return {'buy_side': [], 'sell_side': []}

        recent = df.tail(lookback)

        # Find significant swing highs (sell-side liquidity above)
        sell_side_liquidity = []
        for i in range(5, len(recent) - 5):
            if recent['high'].iloc[i] == recent['high'].iloc[i-5:i+6].max():
                sell_side_liquidity.append({
                    'price': recent['high'].iloc[i],
                    'index': i,
                    'type': 'SELL_SIDE'
                })

        # Find significant swing lows (buy-side liquidity below)
        buy_side_liquidity = []
        for i in range(5, len(recent) - 5):
            if recent['low'].iloc[i] == recent['low'].iloc[i-5:i+6].min():
                buy_side_liquidity.append({
                    'price': recent['low'].iloc[i],
                    'index': i,
                    'type': 'BUY_SIDE'
                })

        return {
            'buy_side': buy_side_liquidity[-3:] if buy_side_liquidity else [],
            'sell_side': sell_side_liquidity[-3:] if sell_side_liquidity else []
        }

    @staticmethod
    def detect_break_of_structure(df: pd.DataFrame) -> Optional[str]:
        """
        Detect Break of Structure (BOS) - when price breaks previous structure.

        Returns:
            'BULLISH_BOS', 'BEARISH_BOS', or None
        """
        if len(df) < 20:
            return None

        structure = SmartMoneyConcepts.identify_market_structure(df)

        if structure['structure'] == 'UNKNOWN':
            return None

        recent_high = df['high'].tail(10).max()
        previous_high = df['high'].tail(20).head(10).max()
        recent_low = df['low'].tail(10).min()
        previous_low = df['low'].tail(20).head(10).min()

        # Bullish BOS: Breaking above previous high in uptrend
        if recent_high > previous_high and structure['structure'] == 'BULLISH':
            return 'BULLISH_BOS'

        # Bearish BOS: Breaking below previous low in downtrend
        if recent_low < previous_low and structure['structure'] == 'BEARISH':
            return 'BEARISH_BOS'

        return None

    @staticmethod
    def analyze_smc(df: pd.DataFrame, current_price: float) -> Dict:
        """
        Complete Smart Money Concepts analysis.

        Args:
            df: DataFrame with OHLC data
            current_price: Current market price

        Returns:
            Complete SMC analysis
        """
        market_structure = SmartMoneyConcepts.identify_market_structure(df)
        order_blocks = SmartMoneyConcepts.find_order_blocks(df)
        fvg = SmartMoneyConcepts.identify_fair_value_gaps(df)
        liquidity = SmartMoneyConcepts.find_liquidity_zones(df)
        bos = SmartMoneyConcepts.detect_break_of_structure(df)

        logger.debug(
            f"SMC Analysis - Structure: {market_structure['structure']}, "
            f"BOS: {bos}, OBs: {len(order_blocks['bullish_ob']) + len(order_blocks['bearish_ob'])}"
        )

        return {
            'market_structure': market_structure,
            'order_blocks': order_blocks,
            'fair_value_gaps': fvg,
            'liquidity_zones': liquidity,
            'break_of_structure': bos
        }

    @staticmethod
    def generate_signal(df: pd.DataFrame, current_price: float) -> Dict:
        """
        Generate trading signal based on SMC.

        Args:
            df: DataFrame with OHLC data
            current_price: Current market price

        Returns:
            Signal dictionary
        """
        analysis = SmartMoneyConcepts.analyze_smc(df, current_price)

        signal = 'HOLD'
        confidence = 0.0
        reasons = []

        # Check market structure
        if analysis['market_structure']['structure'] == 'BULLISH':
            signal = 'BUY'
            confidence = 0.5
            reasons.append('Bullish market structure')
        elif analysis['market_structure']['structure'] == 'BEARISH':
            signal = 'SELL'
            confidence = 0.5
            reasons.append('Bearish market structure')

        # Check for break of structure
        if analysis['break_of_structure'] == 'BULLISH_BOS':
            signal = 'BUY'
            confidence = 0.75
            reasons.append('Bullish break of structure')
        elif analysis['break_of_structure'] == 'BEARISH_BOS':
            signal = 'SELL'
            confidence = 0.75
            reasons.append('Bearish break of structure')

        # Check if price is at bullish order block
        for ob in analysis['order_blocks']['bullish_ob']:
            if ob['low'] <= current_price <= ob['high']:
                signal = 'BUY'
                confidence = max(confidence, 0.8)
                reasons.append('Price at bullish order block')
                break

        # Check if price is at bearish order block
        for ob in analysis['order_blocks']['bearish_ob']:
            if ob['low'] <= current_price <= ob['high']:
                signal = 'SELL'
                confidence = max(confidence, 0.8)
                reasons.append('Price at bearish order block')
                break

        # Check for FVG fill opportunities
        for fvg in analysis['fair_value_gaps']['bullish_fvg']:
            if fvg['lower'] <= current_price <= fvg['upper']:
                signal = 'BUY'
                confidence = max(confidence, 0.7)
                reasons.append('Price in bullish fair value gap')
                break

        for fvg in analysis['fair_value_gaps']['bearish_fvg']:
            if fvg['lower'] <= current_price <= fvg['upper']:
                signal = 'SELL'
                confidence = max(confidence, 0.7)
                reasons.append('Price in bearish fair value gap')
                break

        return {
            'signal': signal,
            'confidence': confidence,
            'reason': '; '.join(reasons) if reasons else 'No clear SMC signal',
            'analysis': analysis
        }
