"""
Top-Down Analysis (TDA) Workflow
=================================

Implements systematic multi-timeframe analysis for building trading narratives.

Process: Weekly/Daily → 4H → 1H → 15M
- High timeframes: Establish bias, direction, momentum, targets (the "story")
- Medium timeframes: Identify Points of Interest (POIs), create "if/then" scenarios
- Low timeframes: Precise entry refinement and execution

This creates "if this, then that" scenarios rather than predictions.
"""

import pandas as pd
from typing import Dict, List, Optional, Tuple
from datetime import datetime
from .professional_price_action import ProfessionalPriceAction
from ..utils.logger import setup_logger

logger = setup_logger(__name__)


class TopDownAnalysis:
    """
    Top-Down Analysis system for multi-timeframe confluence.

    Timeframes:
    - HTF (High): Weekly, Daily (bias and overall structure)
    - MTF (Medium): 4H, 1H (POIs and scenarios)
    - LTF (Low): 15M, 5M (execution and refinement)
    """

    def __init__(self):
        """Initialize TDA system."""
        self.pa = ProfessionalPriceAction()

    def analyze_htf_bias(
        self,
        daily_df: pd.DataFrame,
        weekly_df: Optional[pd.DataFrame] = None
    ) -> Dict:
        """
        Analyze High Time Frame for overall bias and direction.

        Establishes:
        - Overall trend direction
        - Major structure levels
        - Momentum assessment
        - Bias (bullish/bearish/neutral)

        Args:
            daily_df: Daily timeframe data
            weekly_df: Weekly timeframe data (optional, for longer-term view)

        Returns:
            HTF bias analysis
        """
        # Daily analysis
        daily_trend = self.pa.identify_trend(daily_df, lookback=100)
        daily_momentum = self.pa.read_momentum_quality(daily_df, window=20)
        daily_impulse = self.pa.detect_impulse_vs_correction(daily_df, window=20)

        # Weekly analysis if available
        if weekly_df is not None and len(weekly_df) >= 50:
            weekly_trend = self.pa.identify_trend(weekly_df, lookback=50)
            weekly_momentum = self.pa.read_momentum_quality(weekly_df, window=10)

            # Check confluence
            trends_aligned = (
                (daily_trend['trend'] == 'UPTREND' and weekly_trend['trend'] == 'UPTREND') or
                (daily_trend['trend'] == 'DOWNTREND' and weekly_trend['trend'] == 'DOWNTREND')
            )

            if trends_aligned:
                bias = daily_trend['trend']
                confidence = 0.9
                note = "Daily and Weekly trends aligned - strong bias"
            else:
                bias = daily_trend['trend']
                confidence = 0.6
                note = "Daily and Weekly trends diverging - cautious bias"
        else:
            bias = daily_trend['trend']
            confidence = daily_trend['confidence']
            note = "Bias based on Daily timeframe only"
            weekly_trend = None
            weekly_momentum = None

        # Identify major swing levels (targets/invalidation)
        major_high = daily_df['high'].tail(100).max()
        major_low = daily_df['low'].tail(100).min()
        current_price = daily_df['close'].iloc[-1]

        # Calculate range position
        range_size = major_high - major_low
        price_position = (current_price - major_low) / range_size if range_size > 0 else 0.5

        return {
            'bias': bias,
            'confidence': confidence,
            'note': note,
            'daily_trend': daily_trend,
            'weekly_trend': weekly_trend,
            'daily_momentum': daily_momentum,
            'weekly_momentum': weekly_momentum,
            'daily_impulse': daily_impulse,
            'major_high': major_high,
            'major_low': major_low,
            'price_position': price_position,  # 0 = at low, 1 = at high
            'recommendation': (
                f"HTF Bias: {bias} | "
                f"Momentum: {daily_momentum['quality']} | "
                f"Position: {price_position*100:.0f}% of range | "
                f"{note}"
            )
        }

    def identify_mtf_pois(
        self,
        h4_df: pd.DataFrame,
        h1_df: pd.DataFrame,
        htf_bias: str
    ) -> Dict:
        """
        Identify Medium Time Frame Points of Interest (POIs).

        Creates actionable zones and "if/then" scenarios:
        - "IF price reaches this zone, THEN look for X setup"
        - "IF structure breaks here, THEN target Y level"

        Args:
            h4_df: 4-hour timeframe data
            h1_df: 1-hour timeframe data
            htf_bias: HTF bias ('UPTREND', 'DOWNTREND', 'CONSOLIDATION')

        Returns:
            MTF POIs and scenarios
        """
        # 4H zones (primary POIs)
        h4_zones = self.pa.identify_supply_demand_zones(h4_df, htf_bias)
        h4_trend = self.pa.identify_trend(h4_df, lookback=50)

        # 1H zones (refined POIs)
        h1_zones = self.pa.identify_supply_demand_zones(h1_df, htf_bias)
        h1_trend = self.pa.identify_trend(h1_df, lookback=30)

        # Identify extreme zones (highest priority)
        current_price = h1_df['close'].iloc[-1]

        h4_extreme = self.pa.identify_extreme_zone(h4_zones, current_price, htf_bias)
        h1_extreme = self.pa.identify_extreme_zone(h1_zones, current_price, htf_bias)

        # Create scenarios
        scenarios = []

        if htf_bias == 'UPTREND':
            # Bullish scenarios
            if h4_extreme and h4_extreme['type'] == 'DEMAND':
                scenarios.append({
                    'condition': f"IF price retraces to {h4_extreme['price']:.2f}",
                    'action': "THEN look for bullish confirmation entry on LTF",
                    'zone': h4_extreme,
                    'priority': 'HIGH',
                    'type': 'CONTINUATION'
                })

            # Target scenarios
            if h4_trend.get('swing_highs'):
                next_target = max(h['price'] for h in h4_trend['swing_highs'])
                scenarios.append({
                    'condition': f"IF bullish entry confirms",
                    'action': f"THEN target {next_target:.2f} (next swing high)",
                    'target': next_target,
                    'priority': 'MEDIUM',
                    'type': 'TARGET'
                })

        elif htf_bias == 'DOWNTREND':
            # Bearish scenarios
            if h4_extreme and h4_extreme['type'] == 'SUPPLY':
                scenarios.append({
                    'condition': f"IF price rallies to {h4_extreme['price']:.2f}",
                    'action': "THEN look for bearish confirmation entry on LTF",
                    'zone': h4_extreme,
                    'priority': 'HIGH',
                    'type': 'CONTINUATION'
                })

            # Target scenarios
            if h4_trend.get('swing_lows'):
                next_target = min(l['price'] for l in h4_trend['swing_lows'])
                scenarios.append({
                    'condition': f"IF bearish entry confirms",
                    'action': f"THEN target {next_target:.2f} (next swing low)",
                    'target': next_target,
                    'priority': 'MEDIUM',
                    'type': 'TARGET'
                })

        return {
            'h4_zones': h4_zones,
            'h1_zones': h1_zones,
            'h4_extreme': h4_extreme,
            'h1_extreme': h1_extreme,
            'h4_trend': h4_trend,
            'h1_trend': h1_trend,
            'scenarios': scenarios,
            'active_pois': len([z for z in h4_zones if z['valid']]),
            'recommendation': (
                f"MTF: {len(scenarios)} scenarios identified | "
                f"Primary POI: {h4_extreme['type'] if h4_extreme else 'None'} @ "
                f"{h4_extreme['price']:.2f if h4_extreme else 0}"
            )
        }

    def refine_ltf_entry(
        self,
        m15_df: pd.DataFrame,
        m5_df: pd.DataFrame,
        mtf_poi: Optional[Dict],
        htf_bias: str,
        current_time: datetime
    ) -> Dict:
        """
        Refine entry on Low Time Frame for precise execution.

        Multi-Timeframe Zone Refinement:
        - 4H zone → 1H zone → 15M zone (sniper entries)
        - Avoid over-refining to very low TFs (< 5M gets too noisy)
        - Balance between precision and valid signal

        Args:
            m15_df: 15-minute timeframe data
            m5_df: 5-minute timeframe data
            mtf_poi: Medium timeframe Point of Interest
            htf_bias: HTF bias
            current_time: Current datetime

        Returns:
            LTF refined entry signal
        """
        # 15M analysis
        m15_zones = self.pa.identify_supply_demand_zones(
            m15_df,
            htf_bias,
            min_impulse_percent=0.8
        )
        m15_trend = self.pa.identify_trend(m15_df, lookback=20)
        m15_bos = self.pa.detect_break_of_structure(m15_df, use_closure=True)
        m15_momentum = self.pa.read_momentum_quality(m15_df, window=10)

        # 5M analysis (very precise)
        m5_zones = self.pa.identify_supply_demand_zones(
            m5_df,
            htf_bias,
            min_impulse_percent=0.5
        )
        m5_trend = self.pa.identify_trend(m5_df, lookback=15)
        m5_bos = self.pa.detect_break_of_structure(m5_df, use_closure=True)
        m5_momentum = self.pa.read_momentum_quality(m5_df, window=5)

        # Session analysis
        session = self.pa.analyze_session_characteristics(current_time, m5_df)

        # Check if currently in MTF POI
        current_price = m5_df['close'].iloc[-1]

        if mtf_poi:
            in_mtf_poi = mtf_poi['low'] <= current_price <= mtf_poi['high']
        else:
            in_mtf_poi = False

        # Zone refinement process
        refined_zone = None
        refinement_path = []

        if in_mtf_poi and m15_zones:
            # Refine from MTF to 15M
            for zone in m15_zones:
                if zone['type'] == mtf_poi['type']:
                    # Check if 15M zone is within MTF zone
                    if mtf_poi['low'] <= zone['price'] <= mtf_poi['high']:
                        refined_zone = zone
                        refinement_path.append('MTF → 15M')

                        # Further refine to 5M if available
                        if m5_zones:
                            for m5_zone in m5_zones:
                                if m5_zone['type'] == zone['type']:
                                    if zone['low'] <= m5_zone['price'] <= zone['high']:
                                        refined_zone = m5_zone
                                        refinement_path.append('15M → 5M')
                                        break
                        break

        # Structural confirmation
        ltf_structure_aligned = False

        if htf_bias == 'UPTREND':
            ltf_structure_aligned = (
                m15_bos.get('type') == 'BULLISH' or
                m5_bos.get('type') == 'BULLISH'
            )
        elif htf_bias == 'DOWNTREND':
            ltf_structure_aligned = (
                m15_bos.get('type') == 'BEARISH' or
                m5_bos.get('type') == 'BEARISH'
            )

        # Generate entry signal
        if not in_mtf_poi:
            return {
                'entry_signal': 'WAIT',
                'reason': 'Price not in MTF POI yet',
                'confidence': 0.0,
                'current_price': current_price,
                'mtf_poi': mtf_poi
            }

        if not ltf_structure_aligned:
            return {
                'entry_signal': 'WAIT',
                'reason': 'In POI but waiting for LTF structural confirmation',
                'confidence': 0.3,
                'm15_trend': m15_trend,
                'm5_trend': m5_trend
            }

        if not refined_zone:
            return {
                'entry_signal': 'WAIT',
                'reason': 'Waiting for refined LTF entry zone to form',
                'confidence': 0.5
            }

        # Calculate confidence based on confluence
        confidence = 0.7  # Base for LTF entry

        if refined_zone.get('has_imbalance'):
            confidence += 0.05
        if m5_momentum['quality'] == 'HIGH':
            confidence += 0.05
        if m15_momentum['quality'] == 'HIGH':
            confidence += 0.05
        if session['is_prime_time']:
            confidence += 0.05
        if len(refinement_path) == 2:  # Full refinement
            confidence += 0.05

        confidence = min(confidence, 1.0)

        # Entry parameters
        signal = 'BUY' if refined_zone['type'] == 'DEMAND' else 'SELL'

        if signal == 'BUY':
            entry_price = refined_zone['high']  # Top of demand zone
            stop_loss = refined_zone['low'] * 0.998
        else:
            entry_price = refined_zone['low']  # Bottom of supply zone
            stop_loss = refined_zone['high'] * 1.002

        risk = abs(entry_price - stop_loss)
        take_profit_1 = entry_price + (risk * 2) if signal == 'BUY' else entry_price - (risk * 2)
        take_profit_2 = entry_price + (risk * 3) if signal == 'BUY' else entry_price - (risk * 3)

        return {
            'entry_signal': signal,
            'confidence': confidence,
            'entry_price': entry_price,
            'stop_loss': stop_loss,
            'take_profit_1': take_profit_1,
            'take_profit_2': take_profit_2,
            'risk_reward_1': 2.0,
            'risk_reward_2': 3.0,
            'refined_zone': refined_zone,
            'refinement_path': ' → '.join(refinement_path),
            'm15_momentum': m15_momentum,
            'm5_momentum': m5_momentum,
            'session': session,
            'reason': (
                f"LTF ENTRY: {signal} @ {entry_price:.2f} | "
                f"Refined: {' → '.join(refinement_path)} | "
                f"M5 Momentum: {m5_momentum['quality']} | "
                f"Session: {session['session']} | "
                f"SL: {stop_loss:.2f} | TP1: {take_profit_1:.2f} (1:2) | TP2: {take_profit_2:.2f} (1:3)"
            )
        }

    def complete_top_down_analysis(
        self,
        daily_df: pd.DataFrame,
        h4_df: pd.DataFrame,
        h1_df: pd.DataFrame,
        m15_df: pd.DataFrame,
        m5_df: pd.DataFrame,
        current_time: datetime,
        weekly_df: Optional[pd.DataFrame] = None
    ) -> Dict:
        """
        Execute complete Top-Down Analysis workflow.

        Full process:
        1. HTF Analysis: Establish bias and direction
        2. MTF Analysis: Identify POIs and create scenarios
        3. LTF Analysis: Refine entry and execute

        Args:
            daily_df: Daily data
            h4_df: 4-hour data
            h1_df: 1-hour data
            m15_df: 15-minute data
            m5_df: 5-minute data
            current_time: Current datetime
            weekly_df: Weekly data (optional)

        Returns:
            Complete TDA with actionable trading plan
        """
        logger.info("Starting complete Top-Down Analysis...")

        # Step 1: HTF Bias
        htf = self.analyze_htf_bias(daily_df, weekly_df)
        logger.info(f"HTF Bias: {htf['bias']} (confidence: {htf['confidence']:.2f})")

        # Step 2: MTF POIs
        mtf = self.identify_mtf_pois(h4_df, h1_df, htf['bias'])
        logger.info(f"MTF: {mtf['active_pois']} POIs, {len(mtf['scenarios'])} scenarios")

        # Step 3: LTF Entry
        primary_poi = mtf.get('h4_extreme') or mtf.get('h1_extreme')
        ltf = self.refine_ltf_entry(m15_df, m5_df, primary_poi, htf['bias'], current_time)
        logger.info(f"LTF: {ltf['entry_signal']} (confidence: {ltf.get('confidence', 0):.2f})")

        # Build trading narrative
        narrative = self._build_narrative(htf, mtf, ltf)

        # Overall signal
        if ltf['entry_signal'] in ['BUY', 'SELL']:
            overall_signal = ltf['entry_signal']
            overall_confidence = ltf['confidence']
        else:
            overall_signal = 'WAIT'
            overall_confidence = 0.0

        return {
            'signal': overall_signal,
            'confidence': overall_confidence,
            'htf_analysis': htf,
            'mtf_analysis': mtf,
            'ltf_analysis': ltf,
            'narrative': narrative,
            'entry_params': ltf if ltf['entry_signal'] in ['BUY', 'SELL'] else None,
            'summary': (
                f"TDA Complete | {overall_signal} ({overall_confidence:.0%}) | "
                f"{narrative}"
            )
        }

    def _build_narrative(self, htf: Dict, mtf: Dict, ltf: Dict) -> str:
        """Build trading narrative from analysis."""
        narrative_parts = []

        # HTF story
        narrative_parts.append(
            f"HTF: {htf['bias']} bias with {htf['daily_momentum']['quality']} momentum"
        )

        # MTF scenarios
        if mtf['scenarios']:
            primary_scenario = mtf['scenarios'][0]
            narrative_parts.append(
                f"MTF: {primary_scenario['action']}"
            )

        # LTF execution
        if ltf['entry_signal'] in ['BUY', 'SELL']:
            narrative_parts.append(
                f"LTF: {ltf['entry_signal']} setup confirmed"
            )
        else:
            narrative_parts.append(
                f"LTF: {ltf['reason']}"
            )

        return " | ".join(narrative_parts)
