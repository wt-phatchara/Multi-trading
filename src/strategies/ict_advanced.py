"""
Advanced ICT Concepts - Part 2
Additional professional trading methodologies commonly taught in ICT courses.

Includes:
- Power of 3 (Accumulation, Manipulation, Distribution)
- Silver Bullet setups
- Judas Swing
- Mitigation blocks
- Session high/low targeting
- Draw on liquidity
- Inducement patterns
"""
import pandas as pd
import numpy as np
from typing import Dict, List, Optional, Tuple
from datetime import datetime, time
from ..utils.logger import setup_logger

logger = setup_logger(__name__)


class AdvancedICT:
    """Advanced ICT concepts for professional trading."""

    @staticmethod
    def identify_power_of_3(df: pd.DataFrame, session_start_idx: int) -> Dict:
        """
        Identify Power of 3 pattern (AMD):
        - Accumulation: Consolidation phase
        - Manipulation: False move to trigger stops
        - Distribution: True directional move

        Args:
            df: OHLCV DataFrame
            session_start_idx: Index where session starts

        Returns:
            Power of 3 analysis
        """
        if session_start_idx + 20 > len(df):
            return {'identified': False}

        session = df.iloc[session_start_idx:session_start_idx + 20]

        # Phase 1: Accumulation (first 1/3 of session)
        accumulation = session.iloc[:7]
        acc_range = accumulation['high'].max() - accumulation['low'].min()
        acc_avg_range = acc_range / len(accumulation)

        # Phase 2: Manipulation (middle 1/3)
        manipulation = session.iloc[7:14]

        # Look for expansion beyond accumulation range
        manip_high = manipulation['high'].max()
        manip_low = manipulation['low'].min()

        acc_high = accumulation['high'].max()
        acc_low = accumulation['low'].min()

        # Check for manipulation (breaking accumulation range)
        bullish_manipulation = manip_low < acc_low and manipulation['close'].iloc[-1] > acc_low
        bearish_manipulation = manip_high > acc_high and manipulation['close'].iloc[-1] < acc_high

        # Phase 3: Distribution (final 1/3)
        distribution = session.iloc[14:]

        if bullish_manipulation:
            # Check for upward distribution
            dist_direction = distribution['close'].iloc[-1] > manipulation['close'].iloc[0]

            return {
                'identified': True,
                'type': 'bullish',
                'accumulation_range': (acc_low, acc_high),
                'manipulation_low': manip_low,
                'distribution_direction': 'up' if dist_direction else 'consolidating',
                'confidence': 0.8 if dist_direction else 0.5
            }

        elif bearish_manipulation:
            # Check for downward distribution
            dist_direction = distribution['close'].iloc[-1] < manipulation['close'].iloc[0]

            return {
                'identified': True,
                'type': 'bearish',
                'accumulation_range': (acc_low, acc_high),
                'manipulation_high': manip_high,
                'distribution_direction': 'down' if dist_direction else 'consolidating',
                'confidence': 0.8 if dist_direction else 0.5
            }

        return {'identified': False}

    @staticmethod
    def detect_judas_swing(df: pd.DataFrame, session_start_idx: int) -> Dict:
        """
        Identify Judas Swing (false breakout at session open).

        Common at London open - price breaks one direction then reverses.

        Args:
            df: OHLCV DataFrame
            session_start_idx: Index where session starts

        Returns:
            Judas swing detection
        """
        if session_start_idx + 10 > len(df):
            return {'detected': False}

        # Get previous session high/low
        prev_session = df.iloc[max(0, session_start_idx-20):session_start_idx]
        prev_high = prev_session['high'].max()
        prev_low = prev_session['low'].min()

        # Check first 5-10 candles of new session
        new_session = df.iloc[session_start_idx:session_start_idx + 10]

        # Bullish Judas: Breaks below previous low then reverses up
        first_low = new_session['low'].min()
        if first_low < prev_low:
            # Check for reversal
            reversal_idx = new_session['low'].idxmin()
            after_reversal = new_session.loc[reversal_idx:]

            if len(after_reversal) > 0 and after_reversal['close'].iloc[-1] > prev_low:
                return {
                    'detected': True,
                    'type': 'bullish',
                    'fake_low': first_low,
                    'previous_low': prev_low,
                    'reversal_price': after_reversal['close'].iloc[-1],
                    'confidence': 0.85,
                    'signal': 'BUY'
                }

        # Bearish Judas: Breaks above previous high then reverses down
        first_high = new_session['high'].max()
        if first_high > prev_high:
            reversal_idx = new_session['high'].idxmax()
            after_reversal = new_session.loc[reversal_idx:]

            if len(after_reversal) > 0 and after_reversal['close'].iloc[-1] < prev_high:
                return {
                    'detected': True,
                    'type': 'bearish',
                    'fake_high': first_high,
                    'previous_high': prev_high,
                    'reversal_price': after_reversal['close'].iloc[-1],
                    'confidence': 0.85,
                    'signal': 'SELL'
                }

        return {'detected': False}

    @staticmethod
    def identify_mitigation_blocks(df: pd.DataFrame) -> List[Dict]:
        """
        Identify mitigation blocks (last opposing candle before strong move).

        Similar to order blocks but specifically the last opposite candle
        before price reverses sharply.

        Args:
            df: OHLCV DataFrame

        Returns:
            List of mitigation blocks
        """
        mitigation_blocks = []

        for i in range(10, len(df) - 5):
            current = df.iloc[i]
            prev = df.iloc[i-1]
            next_5 = df.iloc[i+1:i+6]

            # Bullish mitigation: Last bearish candle before strong up move
            if (current['close'] < current['open'] and  # Bearish candle
                prev['close'] > prev['open']):  # Previous was bullish

                # Check for strong upward move after
                strong_up = (next_5['close'].iloc[-1] - current['close']) / current['close'] > 0.015  # 1.5% move

                if strong_up and next_5['low'].min() > current['low']:
                    mitigation_blocks.append({
                        'type': 'bullish_mitigation',
                        'high': current['high'],
                        'low': current['low'],
                        'price': (current['high'] + current['low']) / 2,
                        'index': i,
                        'strength': 'high',
                        'description': 'Last supply before demand takes over'
                    })

            # Bearish mitigation: Last bullish candle before strong down move
            elif (current['close'] > current['open'] and
                  prev['close'] < prev['open']):

                strong_down = (current['close'] - next_5['close'].iloc[-1]) / current['close'] > 0.015

                if strong_down and next_5['high'].max() < current['high']:
                    mitigation_blocks.append({
                        'type': 'bearish_mitigation',
                        'high': current['high'],
                        'low': current['low'],
                        'price': (current['high'] + current['low']) / 2,
                        'index': i,
                        'strength': 'high',
                        'description': 'Last demand before supply takes over'
                    })

        return mitigation_blocks[-5:]  # Return most recent 5

    @staticmethod
    def detect_silver_bullet(df: pd.DataFrame, current_time: datetime) -> Dict:
        """
        Identify Silver Bullet setup (ICT's high-probability setup).

        Occurs during specific times:
        - 03:00-04:00 EST (London open)
        - 10:00-11:00 EST (New York AM)
        - 14:00-15:00 EST (New York PM)

        Args:
            df: OHLCV DataFrame
            current_time: Current datetime

        Returns:
            Silver bullet analysis
        """
        utc_time = current_time.time()

        # Convert EST times to UTC (EST = UTC-5)
        london_sb = (time(8, 0), time(9, 0))      # 03:00-04:00 EST
        ny_am_sb = (time(15, 0), time(16, 0))    # 10:00-11:00 EST
        ny_pm_sb = (time(19, 0), time(20, 0))    # 14:00-15:00 EST

        in_sb_window = False
        sb_session = None

        if london_sb[0] <= utc_time <= london_sb[1]:
            in_sb_window = True
            sb_session = 'london'
        elif ny_am_sb[0] <= utc_time <= ny_am_sb[1]:
            in_sb_window = True
            sb_session = 'ny_am'
        elif ny_pm_sb[0] <= utc_time <= ny_pm_sb[1]:
            in_sb_window = True
            sb_session = 'ny_pm'

        if not in_sb_window:
            return {'in_silver_bullet': False}

        # Look for specific pattern in last 12 candles (1 hour on 5m chart)
        recent = df.tail(12)

        # Silver bullet characteristics:
        # 1. Strong directional move
        # 2. Pullback to premium/discount
        # 3. Continuation

        swing_high = recent['high'].max()
        swing_low = recent['low'].min()
        current_price = recent['close'].iloc[-1]

        # Calculate if in optimal entry zone
        range_size = swing_high - swing_low
        fifty_percent = swing_low + (range_size * 0.5)

        # Bullish silver bullet: Price in discount, bouncing up
        if current_price < fifty_percent:
            momentum = recent['close'].iloc[-3:].diff().mean()
            if momentum > 0:  # Upward momentum
                return {
                    'in_silver_bullet': True,
                    'session': sb_session,
                    'type': 'bullish',
                    'confidence': 0.85,
                    'entry_zone': (swing_low, fifty_percent),
                    'signal': 'BUY'
                }

        # Bearish silver bullet: Price in premium, dropping
        elif current_price > fifty_percent:
            momentum = recent['close'].iloc[-3:].diff().mean()
            if momentum < 0:  # Downward momentum
                return {
                    'in_silver_bullet': True,
                    'session': sb_session,
                    'type': 'bearish',
                    'confidence': 0.85,
                    'entry_zone': (fifty_percent, swing_high),
                    'signal': 'SELL'
                }

        return {
            'in_silver_bullet': True,
            'session': sb_session,
            'type': 'consolidating',
            'confidence': 0.0
        }

    @staticmethod
    def analyze_session_highs_lows(df: pd.DataFrame) -> Dict:
        """
        Analyze session highs and lows for targeting.

        Smart money often targets:
        - Previous session high/low
        - Asian session high/low
        - London session high/low

        Args:
            df: OHLCV DataFrame with datetime index

        Returns:
            Session analysis
        """
        if len(df) < 288:  # Need at least 24 hours of 5m data
            return {}

        recent_24h = df.tail(288)

        # Identify sessions (rough estimates based on UTC time)
        sessions = {
            'asian': [],
            'london': [],
            'ny': []
        }

        for idx, row in recent_24h.iterrows():
            hour = idx.hour if hasattr(idx, 'hour') else 0

            if 0 <= hour < 7:  # Asian session
                sessions['asian'].append(row)
            elif 7 <= hour < 12:  # London session
                sessions['london'].append(row)
            elif 12 <= hour < 20:  # New York session
                sessions['ny'].append(row)

        result = {}

        for session_name, candles in sessions.items():
            if candles:
                session_df = pd.DataFrame(candles)
                result[f'{session_name}_high'] = session_df['high'].max()
                result[f'{session_name}_low'] = session_df['low'].min()

        return result

    @staticmethod
    def detect_draw_on_liquidity(
        df: pd.DataFrame,
        current_price: float,
        liquidity_levels: List[Dict]
    ) -> Dict:
        """
        Identify when price is being drawn to liquidity.

        Price magnetically moves toward liquidity pools.

        Args:
            df: OHLCV DataFrame
            current_price: Current market price
            liquidity_levels: List of liquidity levels

        Returns:
            Draw on liquidity analysis
        """
        if not liquidity_levels:
            return {'drawing_to_liquidity': False}

        # Find nearest liquidity above and below
        liq_above = [l for l in liquidity_levels if l['price'] > current_price]
        liq_below = [l for l in liquidity_levels if l['price'] < current_price]

        nearest_above = min(liq_above, key=lambda x: x['price'] - current_price) if liq_above else None
        nearest_below = max(liq_below, key=lambda x: current_price - x['price']) if liq_below else None

        # Check price momentum direction
        recent_5 = df.tail(5)
        momentum = recent_5['close'].diff().mean()

        # Determine which liquidity is being targeted
        if momentum > 0 and nearest_above:
            distance_pct = ((nearest_above['price'] - current_price) / current_price) * 100

            if distance_pct < 2.0:  # Within 2% of liquidity
                return {
                    'drawing_to_liquidity': True,
                    'target': nearest_above,
                    'direction': 'up',
                    'distance_percent': distance_pct,
                    'confidence': 0.75,
                    'description': f"Drawing to liquidity at {nearest_above['price']:.2f}"
                }

        elif momentum < 0 and nearest_below:
            distance_pct = ((current_price - nearest_below['price']) / current_price) * 100

            if distance_pct < 2.0:
                return {
                    'drawing_to_liquidity': True,
                    'target': nearest_below,
                    'direction': 'down',
                    'distance_percent': distance_pct,
                    'confidence': 0.75,
                    'description': f"Drawing to liquidity at {nearest_below['price']:.2f}"
                }

        return {'drawing_to_liquidity': False}

    @staticmethod
    def identify_inducement(df: pd.DataFrame) -> Dict:
        """
        Identify inducement (false move to trap traders).

        Smart money creates false signals to induce retail traders
        to enter wrong side before reversing.

        Args:
            df: OHLCV DataFrame

        Returns:
            Inducement analysis
        """
        if len(df) < 20:
            return {'inducement_detected': False}

        recent = df.tail(20)

        # Look for pattern:
        # 1. Break of recent high/low
        # 2. Immediate reversal
        # 3. Strong move in opposite direction

        prev_10 = recent.iloc[:10]
        last_10 = recent.iloc[10:]

        prev_high = prev_10['high'].max()
        prev_low = prev_10['low'].min()

        # Check for bullish inducement (fake breakdown)
        lowest_point = last_10['low'].min()
        if lowest_point < prev_low:
            # Find where it broke
            break_idx = last_10['low'].idxmin()
            after_break = last_10.loc[break_idx:]

            # Check for reversal
            if len(after_break) > 2:
                reversal_strength = (after_break['close'].iloc[-1] - lowest_point) / lowest_point

                if reversal_strength > 0.01 and after_break['close'].iloc[-1] > prev_low:
                    return {
                        'inducement_detected': True,
                        'type': 'bullish',
                        'fake_low': lowest_point,
                        'previous_low': prev_low,
                        'current_price': after_break['close'].iloc[-1],
                        'confidence': 0.8,
                        'signal': 'BUY',
                        'description': 'Bearish traders induced, now reversing up'
                    }

        # Check for bearish inducement (fake breakout)
        highest_point = last_10['high'].max()
        if highest_point > prev_high:
            break_idx = last_10['high'].idxmax()
            after_break = last_10.loc[break_idx:]

            if len(after_break) > 2:
                reversal_strength = (highest_point - after_break['close'].iloc[-1]) / highest_point

                if reversal_strength > 0.01 and after_break['close'].iloc[-1] < prev_high:
                    return {
                        'inducement_detected': True,
                        'type': 'bearish',
                        'fake_high': highest_point,
                        'previous_high': prev_high,
                        'current_price': after_break['close'].iloc[-1],
                        'confidence': 0.8,
                        'signal': 'SELL',
                        'description': 'Bullish traders induced, now reversing down'
                    }

        return {'inducement_detected': False}

    @staticmethod
    def comprehensive_ict_analysis(
        df: pd.DataFrame,
        current_price: float,
        current_time: datetime,
        liquidity_levels: List[Dict]
    ) -> Dict:
        """
        Comprehensive analysis using all advanced ICT concepts.

        Args:
            df: OHLCV DataFrame
            current_price: Current market price
            current_time: Current datetime
            liquidity_levels: Liquidity levels from basic ICT analysis

        Returns:
            Complete advanced ICT analysis
        """
        # Get session start index (approximate)
        session_start = len(df) - 84  # Last ~7 hours on 5m chart

        power_of_3 = AdvancedICT.identify_power_of_3(df, max(0, session_start))
        judas = AdvancedICT.detect_judas_swing(df, max(0, session_start))
        mitigation = AdvancedICT.identify_mitigation_blocks(df)
        silver_bullet = AdvancedICT.detect_silver_bullet(df, current_time)
        session_levels = AdvancedICT.analyze_session_highs_lows(df)
        draw_liq = AdvancedICT.detect_draw_on_liquidity(df, current_price, liquidity_levels)
        inducement = AdvancedICT.identify_inducement(df)

        # Calculate confidence score
        confidence = 0.0
        signals = []

        if power_of_3.get('identified'):
            confidence += 0.2
            signals.append(f"Power of 3: {power_of_3['type']}")

        if judas.get('detected'):
            confidence += 0.25
            signals.append(f"Judas swing: {judas['signal']}")

        if silver_bullet.get('in_silver_bullet') and silver_bullet.get('type') != 'consolidating':
            confidence += 0.3
            signals.append(f"Silver Bullet: {silver_bullet['signal']}")

        if draw_liq.get('drawing_to_liquidity'):
            confidence += 0.15
            signals.append(f"Drawing to liquidity: {draw_liq['direction']}")

        if inducement.get('inducement_detected'):
            confidence += 0.25
            signals.append(f"Inducement: {inducement['signal']}")

        return {
            'power_of_3': power_of_3,
            'judas_swing': judas,
            'mitigation_blocks': mitigation,
            'silver_bullet': silver_bullet,
            'session_levels': session_levels,
            'draw_on_liquidity': draw_liq,
            'inducement': inducement,
            'confidence': min(confidence, 1.0),
            'signals': signals
        }
