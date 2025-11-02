"""
Advanced ICT (Inner Circle Trader) Concepts Implementation.

This module implements professional trading concepts including:
- Premium/Discount pricing
- Optimal Trade Entry (OTE)
- Liquidity concepts
- Market maker models
- Time-based analysis (Kill Zones)
- IPDA (Interbank Price Delivery Algorithm)
- Power of 3 (AMD)
- Silver Bullet setups
- Judas Swing
- Inducement
"""
import pandas as pd
import numpy as np
from typing import Dict, List, Tuple, Optional
from datetime import datetime, time
from .ict_advanced import AdvancedICT
from ..utils.logger import setup_logger

logger = setup_logger(__name__)


class ICTConcepts:
    """Inner Circle Trader advanced concepts."""

    @staticmethod
    def calculate_premium_discount(df: pd.DataFrame, lookback: int = 20) -> Dict:
        """
        Calculate premium and discount zones using recent high/low.

        Premium = price is expensive (above equilibrium)
        Discount = price is cheap (below equilibrium)

        Args:
            df: OHLCV DataFrame
            lookback: Periods to look back for high/low

        Returns:
            Dictionary with zones
        """
        recent = df.tail(lookback)

        swing_high = recent['high'].max()
        swing_low = recent['low'].min()
        equilibrium = (swing_high + swing_low) / 2

        # Standard Fibonacci levels
        range_size = swing_high - swing_low

        zones = {
            'swing_high': swing_high,
            'swing_low': swing_low,
            'equilibrium': equilibrium,
            'premium_zone': {
                'start': equilibrium,
                'end': swing_high,
                'levels': {
                    '50%': equilibrium,
                    '61.8%': swing_low + (range_size * 0.618),  # OTE zone
                    '70.5%': swing_low + (range_size * 0.705),  # OTE zone
                    '79%': swing_low + (range_size * 0.79),     # OTE zone
                    '100%': swing_high
                }
            },
            'discount_zone': {
                'start': swing_low,
                'end': equilibrium,
                'levels': {
                    '0%': swing_low,
                    '21%': swing_low + (range_size * 0.21),     # OTE zone
                    '29.5%': swing_low + (range_size * 0.295),  # OTE zone
                    '38.2%': swing_low + (range_size * 0.382),  # OTE zone
                    '50%': equilibrium
                }
            }
        }

        return zones

    @staticmethod
    def identify_optimal_trade_entry(
        df: pd.DataFrame,
        current_price: float,
        trend: str
    ) -> Dict:
        """
        Identify Optimal Trade Entry (OTE) zones.

        OTE = 61.8% - 79% retracement (Fibonacci)
        Best entry points for continuation trades.

        Args:
            df: OHLCV DataFrame
            current_price: Current market price
            trend: 'bullish' or 'bearish'

        Returns:
            OTE zone information
        """
        zones = ICTConcepts.calculate_premium_discount(df)

        if trend == 'bullish':
            # Look for discount OTE (21%-38.2%)
            ote_zone = zones['discount_zone']['levels']
            ote_low = ote_zone['21%']
            ote_high = ote_zone['38.2%']

            in_ote = ote_low <= current_price <= ote_high

            return {
                'in_ote_zone': in_ote,
                'ote_low': ote_low,
                'ote_high': ote_high,
                'trend': 'bullish',
                'ideal_entry': (ote_low + ote_high) / 2,
                'confidence': 0.85 if in_ote else 0.0
            }
        else:
            # Look for premium OTE (61.8%-79%)
            ote_zone = zones['premium_zone']['levels']
            ote_low = ote_zone['61.8%']
            ote_high = ote_zone['79%']

            in_ote = ote_low <= current_price <= ote_high

            return {
                'in_ote_zone': in_ote,
                'ote_low': ote_low,
                'ote_high': ote_high,
                'trend': 'bearish',
                'ideal_entry': (ote_low + ote_high) / 2,
                'confidence': 0.85 if in_ote else 0.0
            }

    @staticmethod
    def detect_liquidity_levels(df: pd.DataFrame, significance: int = 3) -> Dict:
        """
        Detect liquidity pools (where stops are likely placed).

        Equal highs/lows = liquidity pools
        Smart money hunts these before reversing.

        Args:
            df: OHLCV DataFrame
            significance: How many touches to be significant

        Returns:
            Liquidity levels
        """
        highs = df['high'].values
        lows = df['low'].values

        buy_side_liquidity = []  # Above market (stops for shorts)
        sell_side_liquidity = []  # Below market (stops for longs)

        # Find equal highs (buy-side liquidity)
        for i in range(5, len(highs) - 5):
            local_high = highs[i]

            # Count how many times this level was tested
            tolerance = local_high * 0.002  # 0.2% tolerance
            touches = sum(1 for h in highs[i-5:i+6] if abs(h - local_high) <= tolerance)

            if touches >= significance:
                buy_side_liquidity.append({
                    'price': local_high,
                    'touches': touches,
                    'index': i,
                    'type': 'buy_side'
                })

        # Find equal lows (sell-side liquidity)
        for i in range(5, len(lows) - 5):
            local_low = lows[i]

            tolerance = local_low * 0.002
            touches = sum(1 for l in lows[i-5:i+6] if abs(l - local_low) <= tolerance)

            if touches >= significance:
                sell_side_liquidity.append({
                    'price': local_low,
                    'touches': touches,
                    'index': i,
                    'type': 'sell_side'
                })

        return {
            'buy_side_liquidity': buy_side_liquidity[-5:],  # Recent 5
            'sell_side_liquidity': sell_side_liquidity[-5:]
        }

    @staticmethod
    def identify_kill_zones(current_time: datetime) -> Dict:
        """
        Identify ICT Kill Zones (optimal trading times).

        London Kill Zone: 02:00-05:00 EST (07:00-10:00 UTC)
        New York Kill Zone: 07:00-10:00 EST (12:00-15:00 UTC)
        Asian Kill Zone: 20:00-00:00 EST (01:00-05:00 UTC)

        Args:
            current_time: Current datetime

        Returns:
            Kill zone information
        """
        utc_time = current_time.time()

        # Define kill zones in UTC
        london_kz = (time(7, 0), time(10, 0))
        ny_kz = (time(12, 0), time(15, 0))
        asian_kz = (time(1, 0), time(5, 0))

        in_london = london_kz[0] <= utc_time <= london_kz[1]
        in_ny = ny_kz[0] <= utc_time <= ny_kz[1]
        in_asian = asian_kz[0] <= utc_time <= asian_kz[1]

        active_zone = None
        if in_london:
            active_zone = 'london'
        elif in_ny:
            active_zone = 'new_york'
        elif in_asian:
            active_zone = 'asian'

        return {
            'in_kill_zone': active_zone is not None,
            'active_zone': active_zone,
            'london': in_london,
            'new_york': in_ny,
            'asian': in_asian,
            'trading_recommended': active_zone in ['london', 'new_york']
        }

    @staticmethod
    def detect_breaker_blocks(df: pd.DataFrame) -> List[Dict]:
        """
        Identify breaker blocks (failed order blocks that reverse).

        Breaker = Order block that failed and flipped to opposite bias.
        Very strong reversal zones.

        Args:
            df: OHLCV DataFrame

        Returns:
            List of breaker blocks
        """
        breakers = []

        for i in range(10, len(df) - 5):
            current = df.iloc[i]
            prev = df.iloc[i-1]
            next_5 = df.iloc[i+1:i+6]

            # Bullish breaker: Was bearish OB, got broken, now support
            if (current['close'] < current['open'] and  # Bearish candle
                prev['close'] > prev['open'] and  # Previous was bullish
                next_5['low'].min() < current['low'] and  # Low was broken
                next_5['close'].iloc[-1] > current['high']):  # Price reversed up

                breakers.append({
                    'type': 'bullish_breaker',
                    'high': current['high'],
                    'low': current['low'],
                    'index': i,
                    'strength': 'high'
                })

            # Bearish breaker: Was bullish OB, got broken, now resistance
            elif (current['close'] > current['open'] and  # Bullish candle
                  prev['close'] < prev['open'] and  # Previous was bearish
                  next_5['high'].max() > current['high'] and  # High was broken
                  next_5['close'].iloc[-1] < current['low']):  # Price reversed down

                breakers.append({
                    'type': 'bearish_breaker',
                    'high': current['high'],
                    'low': current['low'],
                    'index': i,
                    'strength': 'high'
                })

        return breakers[-5:]  # Return most recent 5

    @staticmethod
    def calculate_market_structure_shift(df: pd.DataFrame) -> Dict:
        """
        Detect Change of Character (CHoCH) and Break of Structure (BOS).

        CHoCH = Internal structure break (early warning)
        BOS = External structure break (confirmation)

        Args:
            df: OHLCV DataFrame

        Returns:
            Structure shift information
        """
        # Find swing points
        highs = df['high'].values
        lows = df['low'].values

        swing_highs = []
        swing_lows = []

        for i in range(5, len(df) - 5):
            if highs[i] == max(highs[i-5:i+6]):
                swing_highs.append({'price': highs[i], 'index': i})
            if lows[i] == min(lows[i-5:i+6]):
                swing_lows.append({'price': lows[i], 'index': i})

        if len(swing_highs) < 2 or len(swing_lows) < 2:
            return {'shift_detected': False}

        # Check for bullish shift (breaking previous high)
        last_high = swing_highs[-1]
        prev_high = swing_highs[-2]
        current_price = df['close'].iloc[-1]

        bullish_bos = current_price > last_high['price']

        # Check for bearish shift (breaking previous low)
        last_low = swing_lows[-1]
        prev_low = swing_lows[-2]

        bearish_bos = current_price < last_low['price']

        return {
            'shift_detected': bullish_bos or bearish_bos,
            'bullish_bos': bullish_bos,
            'bearish_bos': bearish_bos,
            'last_swing_high': last_high['price'],
            'last_swing_low': last_low['price']
        }

    @staticmethod
    def analyze_ict_confluence(
        df: pd.DataFrame,
        current_price: float,
        current_time: datetime
    ) -> Dict:
        """
        Comprehensive ICT analysis with confluence.

        Args:
            df: OHLCV DataFrame
            current_price: Current market price
            current_time: Current datetime

        Returns:
            Complete ICT analysis
        """
        # Get all ICT concepts
        pd_zones = ICTConcepts.calculate_premium_discount(df)
        liquidity = ICTConcepts.detect_liquidity_levels(df)
        kill_zone = ICTConcepts.identify_kill_zones(current_time)
        breakers = ICTConcepts.detect_breaker_blocks(df)
        structure = ICTConcepts.calculate_market_structure_shift(df)

        # Determine trend based on structure
        if structure.get('bullish_bos'):
            trend = 'bullish'
        elif structure.get('bearish_bos'):
            trend = 'bearish'
        else:
            # Use price relative to equilibrium
            equilibrium = pd_zones['equilibrium']
            trend = 'bullish' if current_price > equilibrium else 'bearish'

        ote = ICTConcepts.identify_optimal_trade_entry(df, current_price, trend)

        # Calculate confluence score
        confluence_score = 0
        reasons = []

        # Kill zone (highest weight)
        if kill_zone['in_kill_zone']:
            confluence_score += 3
            reasons.append(f"In {kill_zone['active_zone']} kill zone")

        # OTE zone
        if ote['in_ote_zone']:
            confluence_score += 3
            reasons.append(f"In OTE zone ({trend})")

        # Structure shift
        if structure['shift_detected']:
            confluence_score += 2
            reasons.append("Structure shift detected")

        # Breaker blocks
        for breaker in breakers:
            if breaker['low'] <= current_price <= breaker['high']:
                confluence_score += 2
                reasons.append(f"{breaker['type']} at current level")

        # Liquidity
        for liq in liquidity['buy_side_liquidity']:
            if abs(current_price - liq['price']) / current_price < 0.01:  # Within 1%
                confluence_score += 1
                reasons.append("Near buy-side liquidity")

        for liq in liquidity['sell_side_liquidity']:
            if abs(current_price - liq['price']) / current_price < 0.01:
                confluence_score += 1
                reasons.append("Near sell-side liquidity")

        # Normalize score to 0-1
        max_score = 11  # Max possible confluence points
        confidence = min(confluence_score / max_score, 1.0)

        return {
            'premium_discount': pd_zones,
            'ote': ote,
            'liquidity': liquidity,
            'kill_zone': kill_zone,
            'breaker_blocks': breakers,
            'structure': structure,
            'trend': trend,
            'confluence_score': confluence_score,
            'confidence': confidence,
            'reasons': reasons
        }

    @staticmethod
    def generate_ict_signal(
        df: pd.DataFrame,
        current_price: float,
        current_time: datetime
    ) -> Dict:
        """
        Generate trading signal based on ALL ICT concepts (basic + advanced).

        Args:
            df: OHLCV DataFrame
            current_price: Current market price
            current_time: Current datetime

        Returns:
            Trading signal with comprehensive analysis
        """
        # Basic ICT analysis
        analysis = ICTConcepts.analyze_ict_confluence(df, current_price, current_time)

        # Advanced ICT analysis
        advanced = AdvancedICT.comprehensive_ict_analysis(
            df,
            current_price,
            current_time,
            analysis['liquidity']['buy_side_liquidity'] + analysis['liquidity']['sell_side_liquidity']
        )

        signal = 'HOLD'
        confidence = 0.0
        reasons = []

        # HIGH PRIORITY: Silver Bullet setup (overrides kill zone requirement)
        if advanced['silver_bullet'].get('in_silver_bullet'):
            if advanced['silver_bullet'].get('type') == 'bullish':
                signal = 'BUY'
                confidence = 0.9
                reasons.append(f"Silver Bullet {advanced['silver_bullet']['session']}: BUY")

                return {
                    'signal': signal,
                    'confidence': confidence,
                    'reason': '; '.join(reasons),
                    'analysis': {**analysis, 'advanced': advanced}
                }

            elif advanced['silver_bullet'].get('type') == 'bearish':
                signal = 'SELL'
                confidence = 0.9
                reasons.append(f"Silver Bullet {advanced['silver_bullet']['session']}: SELL")

                return {
                    'signal': signal,
                    'confidence': confidence,
                    'reason': '; '.join(reasons),
                    'analysis': {**analysis, 'advanced': advanced}
                }

        # HIGH PRIORITY: Judas Swing (very reliable)
        if advanced['judas_swing'].get('detected'):
            signal = advanced['judas_swing']['signal']
            confidence = 0.85
            reasons.append(f"Judas Swing: {advanced['judas_swing']['type']}")

            return {
                'signal': signal,
                'confidence': confidence,
                'reason': '; '.join(reasons),
                'analysis': {**analysis, 'advanced': advanced}
            }

        # HIGH PRIORITY: Inducement (trap traders)
        if advanced['inducement'].get('inducement_detected'):
            signal = advanced['inducement']['signal']
            confidence = 0.8
            reasons.append(f"Inducement: {advanced['inducement']['description']}")

            return {
                'signal': signal,
                'confidence': confidence,
                'reason': '; '.join(reasons),
                'analysis': {**analysis, 'advanced': advanced}
            }

        # Must be in kill zone for standard setups
        if not analysis['kill_zone']['in_kill_zone']:
            return {
                'signal': 'HOLD',
                'confidence': 0.0,
                'reason': 'Not in kill zone - wait for optimal time (unless Silver Bullet/Judas/Inducement)',
                'analysis': {**analysis, 'advanced': advanced}
            }

        trend = analysis['trend']
        ote = analysis['ote']
        structure = analysis['structure']

        # Power of 3 confirmation
        if advanced['power_of_3'].get('identified'):
            if advanced['power_of_3']['type'] == 'bullish' and advanced['power_of_3']['distribution_direction'] == 'up':
                confidence += 0.2
                reasons.append("Power of 3: Bullish distribution phase")
            elif advanced['power_of_3']['type'] == 'bearish' and advanced['power_of_3']['distribution_direction'] == 'down':
                confidence += 0.2
                reasons.append("Power of 3: Bearish distribution phase")

        # Standard ICT setup
        # Bullish setup
        if trend == 'bullish' and ote['in_ote_zone']:
            signal = 'BUY'
            confidence += analysis['confidence']
            reasons.extend(analysis['reasons'])

        # Bearish setup
        elif trend == 'bearish' and ote['in_ote_zone']:
            signal = 'SELL'
            confidence += analysis['confidence']
            reasons.extend(analysis['reasons'])

        # Structure shift overrides
        if structure.get('bullish_bos') and current_price > analysis['premium_discount']['equilibrium']:
            signal = 'BUY'
            confidence = max(confidence, 0.75)
            reasons.append("Bullish BOS confirmed")

        elif structure.get('bearish_bos') and current_price < analysis['premium_discount']['equilibrium']:
            signal = 'SELL'
            confidence = max(confidence, 0.75)
            reasons.append("Bearish BOS confirmed")

        # Draw on liquidity adds confirmation
        if advanced['draw_on_liquidity'].get('drawing_to_liquidity'):
            if advanced['draw_on_liquidity']['direction'] == 'up' and signal == 'BUY':
                confidence += 0.1
                reasons.append("Drawing to liquidity above")
            elif advanced['draw_on_liquidity']['direction'] == 'down' and signal == 'SELL':
                confidence += 0.1
                reasons.append("Drawing to liquidity below")

        return {
            'signal': signal,
            'confidence': min(confidence, 1.0),
            'reason': '; '.join(reasons) if reasons else 'No ICT setup',
            'analysis': {**analysis, 'advanced': advanced}
        }
