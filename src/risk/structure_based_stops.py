"""
Structure-Based Trailing Stops
===============================

Professional stop loss management based on market structure rather than arbitrary %.

Key Principles:
1. Initial stop: Beyond the invalidation point (swing low/high of validation structure)
2. Move to breakeven: Once structure validates (BOS in trade direction)
3. Trail stops: Follow new validated structural highs/lows
4. Never move stop against trade direction

This creates "win-win scenarios" where worst case is breakeven after BOS.
"""

import pandas as pd
from typing import Dict, Optional
from ..utils.logger import setup_logger

logger = setup_logger(__name__)


class StructureBasedStops:
    """
    Manages stop losses based on market structure validation.

    This is superior to fixed % stops because:
    - Respects market structure logic
    - Prevents premature stops before invalidation
    - Locks in profits systematically
    - Creates asymmetric risk/reward
    """

    @staticmethod
    def calculate_initial_stop(
        entry_price: float,
        side: str,
        validation_structure: Dict,
        buffer_percent: float = 0.2
    ) -> float:
        """
        Calculate initial stop loss beyond validation structure.

        For longs: Stop below the swing low that validates the entry
        For shorts: Stop above the swing high that validates the entry

        Args:
            entry_price: Entry price
            side: 'long' or 'short'
            validation_structure: Dict with swing high/low that validates entry
            buffer_percent: Buffer beyond structure (default 0.2%)

        Returns:
            Initial stop loss price
        """
        if side.lower() == 'long':
            # Stop below swing low
            swing_low = validation_structure.get('swing_low', entry_price * 0.98)
            buffer = swing_low * (buffer_percent / 100)
            stop_loss = swing_low - buffer

        else:  # short
            # Stop above swing high
            swing_high = validation_structure.get('swing_high', entry_price * 1.02)
            buffer = swing_high * (buffer_percent / 100)
            stop_loss = swing_high + buffer

        logger.info(
            f"Initial stop calculated for {side}: {stop_loss:.4f} "
            f"(Structure: {validation_structure.get('swing_low' if side.lower() == 'long' else 'swing_high', 0):.4f})"
        )

        return stop_loss

    @staticmethod
    def should_move_to_breakeven(
        df: pd.DataFrame,
        entry_price: float,
        current_price: float,
        side: str,
        entry_structure: Dict
    ) -> Dict:
        """
        Determine if stop should be moved to breakeven.

        Condition: Structure breaks in favor of trade (BOS confirmed).

        For longs: Price breaks above previous swing high with body close
        For shorts: Price breaks below previous swing low with body close

        Args:
            df: Recent OHLCV data
            entry_price: Entry price
            current_price: Current market price
            side: 'long' or 'short'
            entry_structure: Structure at entry time

        Returns:
            Decision dict with recommendation
        """
        if len(df) < 10:
            return {
                'move_to_breakeven': False,
                'reason': 'Insufficient data'
            }

        # Find recent swing points
        recent = df.tail(20)
        swing_highs = []
        swing_lows = []

        for i in range(5, len(recent) - 1):
            if recent['high'].iloc[i] == recent['high'].iloc[i-5:i+6].max():
                swing_highs.append(recent['high'].iloc[i])
            if recent['low'].iloc[i] == recent['low'].iloc[i-5:i+6].min():
                swing_lows.append(recent['low'].iloc[i])

        current_close = df['close'].iloc[-1]

        if side.lower() == 'long':
            # Check if broke above swing high
            if swing_highs:
                last_swing_high = max(swing_highs)

                # BOS: Close above previous high
                if current_close > last_swing_high:
                    return {
                        'move_to_breakeven': True,
                        'reason': f'Bullish BOS confirmed - closed above {last_swing_high:.4f}',
                        'breakeven_price': entry_price,
                        'structure_broken': last_swing_high,
                        'confidence': 0.9
                    }

        else:  # short
            # Check if broke below swing low
            if swing_lows:
                last_swing_low = min(swing_lows)

                # BOS: Close below previous low
                if current_close < last_swing_low:
                    return {
                        'move_to_breakeven': True,
                        'reason': f'Bearish BOS confirmed - closed below {last_swing_low:.4f}',
                        'breakeven_price': entry_price,
                        'structure_broken': last_swing_low,
                        'confidence': 0.9
                    }

        return {
            'move_to_breakeven': False,
            'reason': 'Structure not yet broken in trade direction'
        }

    @staticmethod
    def calculate_trailing_stop(
        df: pd.DataFrame,
        entry_price: float,
        current_stop: float,
        side: str,
        min_profit_to_trail: float = 1.0
    ) -> Dict:
        """
        Calculate trailing stop based on new validated structure.

        Process:
        1. Identify new swing lows (for longs) or highs (for shorts)
        2. Validate that structure is confirmed (not just a temporary swing)
        3. Move stop to follow structure, locking in profit
        4. Never move stop against trade

        Args:
            df: Recent OHLCV data
            entry_price: Entry price
            current_stop: Current stop loss price
            side: 'long' or 'short'
            min_profit_to_trail: Minimum R multiple profit before trailing (default 1.0)

        Returns:
            New stop loss and recommendation
        """
        if len(df) < 15:
            return {
                'trail_stop': False,
                'new_stop': current_stop,
                'reason': 'Insufficient data for trailing'
            }

        current_price = df['close'].iloc[-1]

        # Check if in profit enough to trail
        if side.lower() == 'long':
            profit = current_price - entry_price
            initial_risk = entry_price - current_stop
        else:
            profit = entry_price - current_price
            initial_risk = current_stop - entry_price

        if initial_risk <= 0:
            return {
                'trail_stop': False,
                'new_stop': current_stop,
                'reason': 'Invalid risk calculation'
            }

        profit_r = profit / initial_risk

        if profit_r < min_profit_to_trail:
            return {
                'trail_stop': False,
                'new_stop': current_stop,
                'reason': f'Profit ({profit_r:.2f}R) below minimum trail threshold ({min_profit_to_trail}R)'
            }

        # Find validated swing points
        recent = df.tail(30)
        validated_swings = []

        for i in range(10, len(recent) - 5):
            if side.lower() == 'long':
                # Look for validated swing lows (lows that held and price moved up)
                if recent['low'].iloc[i] == recent['low'].iloc[i-5:i+6].min():
                    # Validate: subsequent price action moved higher
                    subsequent_close = recent['close'].iloc[i+5:].min()
                    if subsequent_close > recent['low'].iloc[i]:
                        validated_swings.append({
                            'price': recent['low'].iloc[i],
                            'index': i,
                            'type': 'SWING_LOW'
                        })

            else:  # short
                # Look for validated swing highs (highs that held and price moved down)
                if recent['high'].iloc[i] == recent['high'].iloc[i-5:i+6].max():
                    subsequent_close = recent['close'].iloc[i+5:].max()
                    if subsequent_close < recent['high'].iloc[i]:
                        validated_swings.append({
                            'price': recent['high'].iloc[i],
                            'index': i,
                            'type': 'SWING_HIGH'
                        })

        if not validated_swings:
            return {
                'trail_stop': False,
                'new_stop': current_stop,
                'reason': 'No validated swing points found for trailing'
            }

        # Get most recent validated swing
        latest_swing = validated_swings[-1]

        # Calculate new stop
        buffer = 0.002  # 0.2% buffer

        if side.lower() == 'long':
            new_stop = latest_swing['price'] * (1 - buffer)

            # Only move stop up, never down
            if new_stop > current_stop:
                return {
                    'trail_stop': True,
                    'new_stop': new_stop,
                    'previous_stop': current_stop,
                    'swing_point': latest_swing['price'],
                    'reason': f'Trailing to validated swing low at {latest_swing["price"]:.4f}',
                    'profit_locked': new_stop - entry_price,
                    'confidence': 0.85
                }

        else:  # short
            new_stop = latest_swing['price'] * (1 + buffer)

            # Only move stop down, never up
            if new_stop < current_stop:
                return {
                    'trail_stop': True,
                    'new_stop': new_stop,
                    'previous_stop': current_stop,
                    'swing_point': latest_swing['price'],
                    'reason': f'Trailing to validated swing high at {latest_swing["price"]:.4f}',
                    'profit_locked': entry_price - new_stop,
                    'confidence': 0.85
                }

        return {
            'trail_stop': False,
            'new_stop': current_stop,
            'reason': 'New swing would move stop against trade - keeping current stop'
        }

    @staticmethod
    def manage_stop_loss(
        df: pd.DataFrame,
        position: Dict,
        current_price: float
    ) -> Dict:
        """
        Complete stop loss management for an open position.

        Progressive process:
        1. Start with initial stop (beyond validation structure)
        2. Move to breakeven on BOS confirmation
        3. Trail stops on new validated structure
        4. Lock in profits systematically

        Args:
            df: Recent OHLCV data
            position: Position dict with entry, stop, side, structure info
            current_price: Current market price

        Returns:
            Updated stop loss recommendation
        """
        entry_price = position['entry_price']
        current_stop = position['stop_loss']
        side = position['side']
        at_breakeven = position.get('at_breakeven', False)

        # Step 1: Check if should move to breakeven
        if not at_breakeven:
            be_check = StructureBasedStops.should_move_to_breakeven(
                df, entry_price, current_price, side,
                position.get('entry_structure', {})
            )

            if be_check['move_to_breakeven']:
                logger.info(f"Moving stop to breakeven: {be_check['reason']}")
                return {
                    'action': 'MOVE_TO_BREAKEVEN',
                    'new_stop': entry_price,
                    'previous_stop': current_stop,
                    'reason': be_check['reason'],
                    'at_breakeven': True,
                    'confidence': be_check['confidence']
                }

        # Step 2: Check if should trail stop (only after breakeven)
        if at_breakeven or current_stop == entry_price:
            trail_check = StructureBasedStops.calculate_trailing_stop(
                df, entry_price, current_stop, side,
                min_profit_to_trail=1.0  # Trail after 1R profit
            )

            if trail_check['trail_stop']:
                logger.info(f"Trailing stop: {trail_check['reason']}")
                return {
                    'action': 'TRAIL_STOP',
                    'new_stop': trail_check['new_stop'],
                    'previous_stop': current_stop,
                    'reason': trail_check['reason'],
                    'profit_locked': trail_check.get('profit_locked', 0),
                    'confidence': trail_check.get('confidence', 0.8)
                }

        # Step 3: Keep current stop
        return {
            'action': 'KEEP_CURRENT',
            'new_stop': current_stop,
            'reason': 'No stop adjustment needed at this time'
        }

    @staticmethod
    def calculate_position_targets(
        entry_price: float,
        stop_loss: float,
        side: str,
        r_multiples: list = [2.0, 3.0]
    ) -> Dict:
        """
        Calculate position targets based on R-multiples.

        R = Risk (distance from entry to stop)
        Targets at 1:2 (2R), 1:3 (3R), etc.

        Recommendation: Take 50% at 2R, 50% at 3R+ (or trail)

        Args:
            entry_price: Entry price
            stop_loss: Stop loss price
            side: 'long' or 'short'
            r_multiples: List of R multiples for targets

        Returns:
            Target prices and management plan
        """
        risk = abs(entry_price - stop_loss)

        targets = {}
        if side.lower() == 'long':
            for r in r_multiples:
                targets[f'target_{r}R'] = entry_price + (risk * r)
        else:
            for r in r_multiples:
                targets[f'target_{r}R'] = entry_price - (risk * r)

        # Professional management plan
        management_plan = {
            'entry': entry_price,
            'stop_loss': stop_loss,
            'risk': risk,
            'risk_percent': (risk / entry_price) * 100,
            'targets': targets,
            'management': (
                f"Take 50% profit at {targets['target_2.0R']:.4f} (2R), "
                f"move stop to breakeven. "
                f"Take remaining 50% at {targets['target_3.0R']:.4f} (3R) or trail to maximize."
            ),
            'expected_rr': r_multiples[-1]  # Best case R:R
        }

        return management_plan
