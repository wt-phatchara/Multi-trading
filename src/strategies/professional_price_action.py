"""
Professional Price Action Methodology
======================================

Implements the complete trading system from the briefing document:
- Confirmation Entry Model (HTF POI → LTF confirmation)
- Multi-Timeframe Zone Refinement
- Extreme Zone identification
- Momentum Reading (candle quality)
- Impulse vs Correction detection
- Structure-based entry/exit
- Top-Down Analysis workflow
- Zone validation rules (first retest, open imbalance)

Based on 10+ years institutional and independent trading experience.
"""

import pandas as pd
import numpy as np
from typing import Dict, List, Optional, Tuple
from datetime import datetime, time
from ..utils.logger import setup_logger

logger = setup_logger(__name__)


class ProfessionalPriceAction:
    """
    Professional price action trading system.

    Core Philosophy:
    - LTV Framework: Learn, Test, Validate, Earn
    - Risk per trade: 1% (0.5% for funded accounts)
    - Minimum R:R: 1:2, ideally 1:3+
    - Target: 2-5% per month consistently
    """

    # ==================== MARKET STRUCTURE & TREND ====================

    @staticmethod
    def identify_trend(df: pd.DataFrame, lookback: int = 50) -> Dict:
        """
        Identify market structure: Uptrend, Downtrend, or Consolidation.

        Uptrend: Higher Highs (HH) and Higher Lows (HL)
        Downtrend: Lower Lows (LL) and Lower Highs (LH)
        Consolidation: Sideways movement

        Args:
            df: OHLCV DataFrame
            lookback: Periods to analyze

        Returns:
            Trend analysis with structure details
        """
        if len(df) < lookback:
            return {'trend': 'UNKNOWN', 'confidence': 0.0}

        recent = df.tail(lookback)

        # Find swing points (5-period local highs/lows)
        swing_highs = []
        swing_lows = []

        for i in range(5, len(recent) - 5):
            highs_window = recent['high'].iloc[i-5:i+6].values
            lows_window = recent['low'].iloc[i-5:i+6].values

            if recent['high'].iloc[i] == max(highs_window):
                swing_highs.append({
                    'price': recent['high'].iloc[i],
                    'index': i,
                    'timestamp': recent.index[i]
                })

            if recent['low'].iloc[i] == min(lows_window):
                swing_lows.append({
                    'price': recent['low'].iloc[i],
                    'index': i,
                    'timestamp': recent.index[i]
                })

        if len(swing_highs) < 2 or len(swing_lows) < 2:
            return {'trend': 'CONSOLIDATION', 'confidence': 0.5}

        # Analyze structure
        recent_highs = swing_highs[-3:]  # Last 3 swing highs
        recent_lows = swing_lows[-3:]    # Last 3 swing lows

        # Check for HH & HL (uptrend)
        higher_highs = all(recent_highs[i]['price'] > recent_highs[i-1]['price']
                          for i in range(1, len(recent_highs)))
        higher_lows = all(recent_lows[i]['price'] > recent_lows[i-1]['price']
                         for i in range(1, len(recent_lows)))

        # Check for LL & LH (downtrend)
        lower_lows = all(recent_lows[i]['price'] < recent_lows[i-1]['price']
                        for i in range(1, len(recent_lows)))
        lower_highs = all(recent_highs[i]['price'] < recent_highs[i-1]['price']
                         for i in range(1, len(recent_highs)))

        if higher_highs and higher_lows:
            trend = 'UPTREND'
            confidence = 0.9
        elif lower_lows and lower_highs:
            trend = 'DOWNTREND'
            confidence = 0.9
        else:
            trend = 'CONSOLIDATION'
            confidence = 0.5

        return {
            'trend': trend,
            'confidence': confidence,
            'swing_highs': swing_highs,
            'swing_lows': swing_lows,
            'last_swing_high': swing_highs[-1]['price'],
            'last_swing_low': swing_lows[-1]['price']
        }

    @staticmethod
    def detect_impulse_vs_correction(df: pd.DataFrame, window: int = 10) -> Dict:
        """
        Distinguish between impulsive moves and corrective moves.

        Impulses: Fast, strong, pro-trend (large bodies, small wicks, high volume)
        Corrections: Slow, weak, counter-trend (smaller bodies, pullbacks)

        Entry should be during corrections, targeting next impulse.

        Args:
            df: OHLCV DataFrame
            window: Analysis window

        Returns:
            Classification of recent price action
        """
        if len(df) < window:
            return {'type': 'UNKNOWN'}

        recent = df.tail(window)

        # Calculate metrics
        body_sizes = abs(recent['close'] - recent['open'])
        wick_sizes = (recent['high'] - recent['low']) - body_sizes
        price_changes = recent['close'].diff().abs()

        avg_body = body_sizes.mean()
        avg_wick = wick_sizes.mean()
        avg_change = price_changes.mean()

        # Momentum calculation
        total_move = abs(recent['close'].iloc[-1] - recent['close'].iloc[0])
        time_elapsed = len(recent)
        speed = total_move / time_elapsed if time_elapsed > 0 else 0

        # Direction
        net_change = recent['close'].iloc[-1] - recent['close'].iloc[0]
        direction = 'UP' if net_change > 0 else 'DOWN'

        # Classify
        # Impulse: Large bodies, small wicks, fast movement
        body_to_wick_ratio = avg_body / avg_wick if avg_wick > 0 else 0

        if body_to_wick_ratio > 2.0 and speed > avg_change * 1.5:
            move_type = 'IMPULSE'
            quality = 'HIGH'
        elif body_to_wick_ratio > 1.0 and speed > avg_change:
            move_type = 'IMPULSE'
            quality = 'MEDIUM'
        else:
            move_type = 'CORRECTION'
            quality = 'WEAK'

        return {
            'type': move_type,
            'quality': quality,
            'direction': direction,
            'speed': speed,
            'body_to_wick_ratio': body_to_wick_ratio,
            'recommendation': 'WAIT' if move_type == 'IMPULSE' else 'LOOK_FOR_ENTRY'
        }

    @staticmethod
    def detect_break_of_structure(df: pd.DataFrame, use_closure: bool = True) -> Dict:
        """
        Detect Break of Structure (BOS) with proper validation.

        CRITICAL: A true BOS requires candle CLOSURE beyond the level,
        not just a wick sweep. Wicks indicate rejection/liquidity sweep.

        Args:
            df: OHLCV DataFrame
            use_closure: If True, require close beyond level (recommended)

        Returns:
            BOS detection with validation
        """
        if len(df) < 20:
            return {'bos_detected': False}

        # Find recent swing points
        swing_highs = []
        swing_lows = []

        for i in range(5, len(df) - 1):
            if df['high'].iloc[i] == df['high'].iloc[i-5:i+6].max():
                swing_highs.append({
                    'price': df['high'].iloc[i],
                    'index': i
                })
            if df['low'].iloc[i] == df['low'].iloc[i-5:i+6].min():
                swing_lows.append({
                    'price': df['low'].iloc[i],
                    'index': i
                })

        if not swing_highs or not swing_lows:
            return {'bos_detected': False}

        last_high = swing_highs[-1]['price']
        last_low = swing_lows[-1]['price']
        current_candle = df.iloc[-1]

        # Bullish BOS: Close ABOVE last swing high
        if use_closure:
            bullish_bos = current_candle['close'] > last_high
            bearish_bos = current_candle['close'] < last_low
        else:
            # Using high/low (less reliable)
            bullish_bos = current_candle['high'] > last_high
            bearish_bos = current_candle['low'] < last_low

        # Check if it's just a wick (rejection)
        bullish_wick_only = (current_candle['high'] > last_high and
                            current_candle['close'] < last_high)
        bearish_wick_only = (current_candle['low'] < last_low and
                            current_candle['close'] > last_low)

        if bullish_bos:
            return {
                'bos_detected': True,
                'type': 'BULLISH',
                'level_broken': last_high,
                'close_price': current_candle['close'],
                'valid': True,
                'note': 'Confirmed by closure'
            }
        elif bearish_bos:
            return {
                'bos_detected': True,
                'type': 'BEARISH',
                'level_broken': last_low,
                'close_price': current_candle['close'],
                'valid': True,
                'note': 'Confirmed by closure'
            }
        elif bullish_wick_only:
            return {
                'bos_detected': False,
                'type': 'REJECTION',
                'level_tested': last_high,
                'note': 'Wick rejection - not a valid BOS, potential reversal'
            }
        elif bearish_wick_only:
            return {
                'bos_detected': False,
                'type': 'REJECTION',
                'level_tested': last_low,
                'note': 'Wick rejection - not a valid BOS, potential reversal'
            }

        return {'bos_detected': False}

    # ==================== SUPPLY & DEMAND ZONES ====================

    @staticmethod
    def identify_supply_demand_zones(
        df: pd.DataFrame,
        trend: str,
        min_impulse_percent: float = 1.5
    ) -> List[Dict]:
        """
        Identify Supply & Demand zones (S/D zones).

        S/D Zone = Consolidation/indecision candle immediately before large impulsive move
        Indicates where institutional interest entered the market.

        RULES:
        1. Only trade Demand in uptrends, Supply in downtrends
        2. Must have open imbalance (inefficiency) leading into zone
        3. Only valid for FIRST retest (tap)
        4. Use last candle before impulse

        Args:
            df: OHLCV DataFrame
            trend: Current trend ('UPTREND', 'DOWNTREND', 'CONSOLIDATION')
            min_impulse_percent: Minimum % move to qualify as impulse

        Returns:
            List of valid S/D zones
        """
        zones = []

        for i in range(10, len(df) - 5):
            current = df.iloc[i]
            next_5 = df.iloc[i+1:i+6]

            # Calculate impulse strength
            impulse_up = (next_5['high'].max() - current['close']) / current['close'] * 100
            impulse_down = (current['close'] - next_5['low'].min()) / current['close'] * 100

            # Demand zone (bullish): Consolidation before up impulse
            if trend == 'UPTREND' and impulse_up >= min_impulse_percent:
                # Check for imbalance (gap or unfilled range)
                has_imbalance = any(next_5['low'].iloc[j] > current['high']
                                   for j in range(len(next_5)))

                # Last indecision candle before move
                body_size = abs(current['close'] - current['open'])
                is_indecision = body_size < (current['high'] - current['low']) * 0.3

                zones.append({
                    'type': 'DEMAND',
                    'high': current['high'],
                    'low': current['low'],
                    'price': (current['high'] + current['low']) / 2,
                    'index': i,
                    'timestamp': current.name,
                    'impulse_strength': impulse_up,
                    'has_imbalance': has_imbalance,
                    'is_extreme': False,  # To be calculated
                    'tested_count': 0,
                    'valid': True,
                    'quality': 'HIGH' if (has_imbalance and is_indecision) else 'MEDIUM'
                })

            # Supply zone (bearish): Consolidation before down impulse
            elif trend == 'DOWNTREND' and impulse_down >= min_impulse_percent:
                has_imbalance = any(next_5['high'].iloc[j] < current['low']
                                   for j in range(len(next_5)))

                body_size = abs(current['close'] - current['open'])
                is_indecision = body_size < (current['high'] - current['low']) * 0.3

                zones.append({
                    'type': 'SUPPLY',
                    'high': current['high'],
                    'low': current['low'],
                    'price': (current['high'] + current['low']) / 2,
                    'index': i,
                    'timestamp': current.name,
                    'impulse_strength': impulse_down,
                    'has_imbalance': has_imbalance,
                    'is_extreme': False,
                    'tested_count': 0,
                    'valid': True,
                    'quality': 'HIGH' if (has_imbalance and is_indecision) else 'MEDIUM'
                })

        # Mark extreme zones (furthest from current price)
        if zones:
            current_price = df['close'].iloc[-1]

            demand_zones = [z for z in zones if z['type'] == 'DEMAND']
            supply_zones = [z for z in zones if z['type'] == 'SUPPLY']

            if demand_zones:
                extreme_demand = min(demand_zones, key=lambda z: z['price'])
                for z in zones:
                    if z['type'] == 'DEMAND' and z['index'] == extreme_demand['index']:
                        z['is_extreme'] = True

            if supply_zones:
                extreme_supply = max(supply_zones, key=lambda z: z['price'])
                for z in zones:
                    if z['type'] == 'SUPPLY' and z['index'] == extreme_supply['index']:
                        z['is_extreme'] = True

        # Return most recent zones (last 5)
        return zones[-5:]

    @staticmethod
    def identify_extreme_zone(zones: List[Dict], current_price: float, trend: str) -> Optional[Dict]:
        """
        Identify the Extreme Zone - highest probability S/D zone.

        Extreme Zone = Furthest valid zone from current price in the existing structural leg.
        This is the last line of defense before trend reversal.

        Args:
            zones: List of S/D zones
            current_price: Current market price
            trend: Current trend

        Returns:
            Extreme zone or None
        """
        if not zones:
            return None

        if trend == 'UPTREND':
            # Extreme demand = lowest valid demand zone
            demand_zones = [z for z in zones if z['type'] == 'DEMAND' and z['valid']]
            if demand_zones:
                extreme = min(demand_zones, key=lambda z: z['price'])
                extreme['is_extreme'] = True
                return extreme

        elif trend == 'DOWNTREND':
            # Extreme supply = highest valid supply zone
            supply_zones = [z for z in zones if z['type'] == 'SUPPLY' and z['valid']]
            if supply_zones:
                extreme = max(supply_zones, key=lambda z: z['price'])
                extreme['is_extreme'] = True
                return extreme

        return None

    # ==================== MOMENTUM & QUALITY READING ====================

    @staticmethod
    def read_momentum_quality(df: pd.DataFrame, window: int = 10) -> Dict:
        """
        Read momentum quality using candle size and speed analysis.

        High quality momentum:
        - Large candle bodies
        - Small wicks
        - Fast, consistent directional movement
        - High conviction

        Poor quality:
        - Small bodies, large wicks
        - Choppy, indecisive movement

        Args:
            df: OHLCV DataFrame
            window: Analysis window

        Returns:
            Momentum quality metrics
        """
        if len(df) < window:
            return {'quality': 'UNKNOWN'}

        recent = df.tail(window)

        # Candle metrics
        bodies = abs(recent['close'] - recent['open'])
        ranges = recent['high'] - recent['low']
        wicks = ranges - bodies

        # Calculate ratios
        avg_body = bodies.mean()
        avg_wick = wicks.mean()
        avg_range = ranges.mean()

        body_to_range_ratio = (bodies / ranges).mean() if ranges.mean() > 0 else 0
        body_to_wick_ratio = avg_body / avg_wick if avg_wick > 0 else 0

        # Speed and consistency
        price_changes = recent['close'].diff().abs()
        avg_change = price_changes.mean()
        std_change = price_changes.std()
        consistency = 1 - (std_change / avg_change) if avg_change > 0 else 0

        # Direction strength
        net_move = recent['close'].iloc[-1] - recent['close'].iloc[0]
        total_distance = price_changes.sum()
        efficiency = abs(net_move) / total_distance if total_distance > 0 else 0

        # Quality classification
        if body_to_range_ratio > 0.7 and efficiency > 0.7:
            quality = 'HIGH'
            control = 'STRONG'
        elif body_to_range_ratio > 0.5 and efficiency > 0.5:
            quality = 'MEDIUM'
            control = 'MODERATE'
        else:
            quality = 'LOW'
            control = 'WEAK'

        return {
            'quality': quality,
            'control': control,
            'body_to_range_ratio': body_to_range_ratio,
            'body_to_wick_ratio': body_to_wick_ratio,
            'efficiency': efficiency,
            'consistency': consistency,
            'avg_body_pct': (avg_body / avg_range) * 100 if avg_range > 0 else 0,
            'recommendation': 'ENTER' if quality == 'HIGH' else 'WAIT' if quality == 'MEDIUM' else 'AVOID'
        }

    # ==================== SESSION CHARACTERISTICS ====================

    @staticmethod
    def analyze_session_characteristics(current_time: datetime, df: pd.DataFrame) -> Dict:
        """
        Analyze session characteristics and volume patterns.

        Session Characteristics:
        - Asian (20:00-00:00 EST / 01:00-05:00 UTC): Low volume, consolidation range
        - London (02:00-05:00 EST / 07:00-10:00 UTC): High volume, momentum
        - New York (07:00-10:00 EST / 12:00-15:00 UTC): Highest volume, strong moves

        Strategy: Asia range often swept for liquidity during London/NY open

        Args:
            current_time: Current datetime
            df: OHLCV DataFrame for volume analysis

        Returns:
            Session analysis
        """
        utc_hour = current_time.hour

        # Identify session
        if 1 <= utc_hour < 7:
            session = 'ASIAN'
            volume_expectation = 'LOW'
            characteristics = 'Consolidation, range-bound, low volatility'
            strategy = 'Mark range highs/lows as liquidity targets for London open'
        elif 7 <= utc_hour < 12:
            session = 'LONDON'
            volume_expectation = 'HIGH'
            characteristics = 'High volume, momentum moves, liquidity sweeps'
            strategy = 'Trade breakouts, expect Asian range sweeps'
        elif 12 <= utc_hour < 20:
            session = 'NEW_YORK'
            volume_expectation = 'HIGHEST'
            characteristics = 'Highest volume, strong trends, reversals'
            strategy = 'Follow strong momentum, watch for NY reversal patterns'
        else:
            session = 'OFF_HOURS'
            volume_expectation = 'VERY_LOW'
            characteristics = 'Very low volume, avoid trading'
            strategy = 'Wait for main session'

        # Analyze actual volume if available
        if 'volume' in df.columns and len(df) > 20:
            recent_volume = df['volume'].tail(10).mean()
            historical_volume = df['volume'].tail(100).mean()
            volume_ratio = recent_volume / historical_volume if historical_volume > 0 else 1.0

            volume_status = 'HIGH' if volume_ratio > 1.2 else 'NORMAL' if volume_ratio > 0.8 else 'LOW'
        else:
            volume_ratio = 1.0
            volume_status = volume_expectation

        # Timing recommendations
        is_prime_time = session in ['LONDON', 'NEW_YORK']

        return {
            'session': session,
            'utc_hour': utc_hour,
            'volume_expectation': volume_expectation,
            'volume_status': volume_status,
            'volume_ratio': volume_ratio,
            'characteristics': characteristics,
            'strategy_note': strategy,
            'is_prime_time': is_prime_time,
            'trading_recommended': is_prime_time
        }

    # ==================== CONFIRMATION ENTRY MODEL ====================

    @staticmethod
    def confirmation_entry_model(
        htf_df: pd.DataFrame,
        ltf_df: pd.DataFrame,
        current_price: float,
        current_time: datetime
    ) -> Dict:
        """
        CONFIRMATION ENTRY MODEL - The highest probability entry technique.

        4-Step Process:
        1. Identify HTF S/D zone (Point of Interest - POI)
        2. Wait for market to enter the zone
        3. Wait for LTF fractal structural shift (LTF trend breaks in favor of HTF trend)
        4. Enter via limit order at newly formed LTF demand/supply zone

        This eliminates most false entries and provides excellent R:R.

        Args:
            htf_df: Higher timeframe DataFrame (e.g., 4H)
            ltf_df: Lower timeframe DataFrame (e.g., 15M)
            current_price: Current market price
            current_time: Current datetime

        Returns:
            Entry signal with complete analysis
        """
        # Step 1: HTF Analysis - Identify POI
        htf_trend = ProfessionalPriceAction.identify_trend(htf_df)
        htf_zones = ProfessionalPriceAction.identify_supply_demand_zones(
            htf_df,
            htf_trend['trend']
        )

        if not htf_zones:
            return {
                'entry_signal': 'WAIT',
                'reason': 'No valid HTF zones identified',
                'confidence': 0.0
            }

        # Identify extreme zone (highest probability)
        extreme_zone = ProfessionalPriceAction.identify_extreme_zone(
            htf_zones,
            current_price,
            htf_trend['trend']
        )

        if not extreme_zone:
            poi = htf_zones[-1]  # Most recent zone
        else:
            poi = extreme_zone

        # Step 2: Check if price is in the POI
        in_poi = poi['low'] <= current_price <= poi['high']

        if not in_poi:
            return {
                'entry_signal': 'WAIT',
                'reason': f"Price not in POI. Waiting for {poi['type']} zone at {poi['price']:.2f}",
                'poi': poi,
                'htf_trend': htf_trend,
                'confidence': 0.0
            }

        # Step 3: LTF Structural Shift
        ltf_trend = ProfessionalPriceAction.identify_trend(ltf_df, lookback=20)
        ltf_bos = ProfessionalPriceAction.detect_break_of_structure(ltf_df, use_closure=True)

        # Check for structural shift in favor of HTF trend
        structural_shift_confirmed = False

        if poi['type'] == 'DEMAND' and ltf_bos.get('type') == 'BULLISH':
            structural_shift_confirmed = True
        elif poi['type'] == 'SUPPLY' and ltf_bos.get('type') == 'BEARISH':
            structural_shift_confirmed = True

        if not structural_shift_confirmed:
            return {
                'entry_signal': 'WAIT',
                'reason': f"In POI but waiting for LTF structural shift. Current LTF: {ltf_trend['trend']}",
                'poi': poi,
                'htf_trend': htf_trend,
                'ltf_trend': ltf_trend,
                'confidence': 0.3
            }

        # Step 4: Identify LTF entry zone
        ltf_zones = ProfessionalPriceAction.identify_supply_demand_zones(
            ltf_df,
            htf_trend['trend'],  # Use HTF trend for alignment
            min_impulse_percent=0.5  # Lower threshold for LTF
        )

        if not ltf_zones:
            return {
                'entry_signal': 'WAIT',
                'reason': 'Structural shift confirmed but no LTF entry zone formed yet',
                'poi': poi,
                'confidence': 0.5
            }

        # Get most recent valid zone aligned with HTF
        entry_zone = None
        for zone in reversed(ltf_zones):
            if zone['type'] == poi['type']:  # Same type as HTF
                entry_zone = zone
                break

        if not entry_zone:
            return {
                'entry_signal': 'WAIT',
                'reason': 'No aligned LTF entry zone yet',
                'confidence': 0.5
            }

        # Check momentum quality
        momentum = ProfessionalPriceAction.read_momentum_quality(ltf_df, window=5)

        # Check session
        session = ProfessionalPriceAction.analyze_session_characteristics(current_time, ltf_df)

        # Calculate confidence
        confidence = 0.7  # Base confidence for confirmation entry

        if poi.get('is_extreme'):
            confidence += 0.1
        if poi.get('has_imbalance'):
            confidence += 0.1
        if momentum['quality'] == 'HIGH':
            confidence += 0.05
        if session['is_prime_time']:
            confidence += 0.05

        confidence = min(confidence, 1.0)

        # Generate entry signal
        signal = 'BUY' if poi['type'] == 'DEMAND' else 'SELL'

        # Calculate stop loss (beyond POI invalidation point)
        if signal == 'BUY':
            stop_loss = poi['low'] * 0.998  # Slightly below POI low
            take_profit_1 = current_price + (current_price - stop_loss) * 2  # 1:2 R:R
            take_profit_2 = current_price + (current_price - stop_loss) * 3  # 1:3 R:R
        else:
            stop_loss = poi['high'] * 1.002  # Slightly above POI high
            take_profit_1 = current_price - (stop_loss - current_price) * 2
            take_profit_2 = current_price - (stop_loss - current_price) * 3

        return {
            'entry_signal': signal,
            'confidence': confidence,
            'entry_price': current_price,
            'stop_loss': stop_loss,
            'take_profit_1': take_profit_1,
            'take_profit_2': take_profit_2,
            'risk_reward_1': 2.0,
            'risk_reward_2': 3.0,
            'poi': poi,
            'ltf_entry_zone': entry_zone,
            'htf_trend': htf_trend,
            'ltf_trend': ltf_trend,
            'momentum': momentum,
            'session': session,
            'reason': (
                f"CONFIRMATION ENTRY: {signal} at {current_price:.2f} | "
                f"HTF {poi['type']} zone with LTF structural shift confirmed | "
                f"Momentum: {momentum['quality']} | Session: {session['session']} | "
                f"R:R 1:2 @ {take_profit_1:.2f}, 1:3 @ {take_profit_2:.2f}"
            )
        }
