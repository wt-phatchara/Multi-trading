"""Support and Resistance zone detection."""
import pandas as pd
import numpy as np
from typing import List, Dict, Tuple
from ..utils.logger import setup_logger

logger = setup_logger(__name__)


class SupportResistance:
    """Detect support and resistance zones using multiple methods."""

    @staticmethod
    def find_pivot_points(df: pd.DataFrame, window: int = 5) -> Tuple[List[Dict], List[Dict]]:
        """
        Find pivot highs and lows (potential S/R levels).

        Args:
            df: DataFrame with OHLC data
            window: Window size for pivot detection

        Returns:
            Tuple of (support_levels, resistance_levels)
        """
        highs = df['high'].values
        lows = df['low'].values
        closes = df['close'].values

        resistance_levels = []
        support_levels = []

        # Find pivot highs (resistance)
        for i in range(window, len(highs) - window):
            if highs[i] == max(highs[i - window:i + window + 1]):
                resistance_levels.append({
                    'price': highs[i],
                    'index': i,
                    'strength': 1,
                    'touches': 1
                })

        # Find pivot lows (support)
        for i in range(window, len(lows) - window):
            if lows[i] == min(lows[i - window:i + window + 1]):
                support_levels.append({
                    'price': lows[i],
                    'index': i,
                    'strength': 1,
                    'touches': 1
                })

        return support_levels, resistance_levels

    @staticmethod
    def cluster_levels(levels: List[Dict], tolerance_percent: float = 0.5) -> List[Dict]:
        """
        Cluster nearby price levels into zones.

        Args:
            levels: List of price levels
            tolerance_percent: Percentage tolerance for clustering

        Returns:
            Clustered zones
        """
        if not levels:
            return []

        # Sort by price
        sorted_levels = sorted(levels, key=lambda x: x['price'])
        zones = []
        current_zone = [sorted_levels[0]]

        for level in sorted_levels[1:]:
            # Check if level is close to current zone
            zone_avg = np.mean([l['price'] for l in current_zone])
            if abs(level['price'] - zone_avg) / zone_avg * 100 <= tolerance_percent:
                current_zone.append(level)
            else:
                # Create zone from current cluster
                zones.append({
                    'price': np.mean([l['price'] for l in current_zone]),
                    'upper': max([l['price'] for l in current_zone]),
                    'lower': min([l['price'] for l in current_zone]),
                    'strength': sum([l['strength'] for l in current_zone]),
                    'touches': len(current_zone)
                })
                current_zone = [level]

        # Add last zone
        if current_zone:
            zones.append({
                'price': np.mean([l['price'] for l in current_zone]),
                'upper': max([l['price'] for l in current_zone]),
                'lower': min([l['price'] for l in current_zone]),
                'strength': sum([l['strength'] for l in current_zone]),
                'touches': len(current_zone)
            })

        return zones

    @staticmethod
    def calculate_volume_profile(df: pd.DataFrame, bins: int = 20) -> List[Dict]:
        """
        Calculate volume profile to identify high-volume areas (potential S/R).

        Args:
            df: DataFrame with OHLCV data
            bins: Number of price bins

        Returns:
            Volume profile levels
        """
        price_min = df['low'].min()
        price_max = df['high'].max()
        price_range = price_max - price_min
        bin_size = price_range / bins

        volume_profile = []

        for i in range(bins):
            bin_low = price_min + (i * bin_size)
            bin_high = bin_low + bin_size
            bin_mid = (bin_low + bin_high) / 2

            # Calculate volume in this price range
            mask = (df['low'] <= bin_high) & (df['high'] >= bin_low)
            bin_volume = df.loc[mask, 'volume'].sum()

            volume_profile.append({
                'price': bin_mid,
                'upper': bin_high,
                'lower': bin_low,
                'volume': bin_volume
            })

        # Sort by volume and get top zones
        volume_profile = sorted(volume_profile, key=lambda x: x['volume'], reverse=True)

        return volume_profile[:10]  # Return top 10 high-volume zones

    @staticmethod
    def find_nearest_levels(current_price: float, support_zones: List[Dict],
                           resistance_zones: List[Dict]) -> Dict:
        """
        Find nearest support and resistance levels to current price.

        Args:
            current_price: Current market price
            support_zones: List of support zones
            resistance_zones: List of resistance zones

        Returns:
            Dictionary with nearest levels
        """
        # Find nearest support (below current price)
        supports_below = [s for s in support_zones if s['price'] < current_price]
        nearest_support = max(supports_below, key=lambda x: x['price']) if supports_below else None

        # Find nearest resistance (above current price)
        resistances_above = [r for r in resistance_zones if r['price'] > current_price]
        nearest_resistance = min(resistances_above, key=lambda x: x['price']) if resistances_above else None

        return {
            'nearest_support': nearest_support,
            'nearest_resistance': nearest_resistance,
            'distance_to_support': abs(current_price - nearest_support['price']) / current_price * 100 if nearest_support else None,
            'distance_to_resistance': abs(nearest_resistance['price'] - current_price) / current_price * 100 if nearest_resistance else None
        }

    @staticmethod
    def analyze_zones(df: pd.DataFrame, current_price: float) -> Dict:
        """
        Complete support/resistance analysis.

        Args:
            df: DataFrame with OHLCV data
            current_price: Current market price

        Returns:
            Complete S/R analysis
        """
        # Find pivot points
        support_levels, resistance_levels = SupportResistance.find_pivot_points(df)

        # Cluster into zones
        support_zones = SupportResistance.cluster_levels(support_levels)
        resistance_zones = SupportResistance.cluster_levels(resistance_levels)

        # Get volume profile
        volume_zones = SupportResistance.calculate_volume_profile(df)

        # Find nearest levels
        nearest = SupportResistance.find_nearest_levels(
            current_price,
            support_zones,
            resistance_zones
        )

        logger.debug(
            f"S/R Analysis - Support zones: {len(support_zones)}, "
            f"Resistance zones: {len(resistance_zones)}"
        )

        return {
            'support_zones': support_zones,
            'resistance_zones': resistance_zones,
            'volume_zones': volume_zones,
            'nearest_support': nearest['nearest_support'],
            'nearest_resistance': nearest['nearest_resistance'],
            'distance_to_support': nearest['distance_to_support'],
            'distance_to_resistance': nearest['distance_to_resistance']
        }

    @staticmethod
    def generate_sr_signal(df: pd.DataFrame, current_price: float) -> Dict:
        """
        Generate trading signals based on S/R zones.

        Args:
            df: DataFrame with OHLCV data
            current_price: Current market price

        Returns:
            Signal dictionary
        """
        analysis = SupportResistance.analyze_zones(df, current_price)

        signal = 'HOLD'
        confidence = 0.0
        reasons = []

        # Check if price is near support (potential buy)
        if analysis['distance_to_support'] and analysis['distance_to_support'] < 0.5:
            signal = 'BUY'
            confidence = 0.7
            reasons.append(f"Price near strong support at {analysis['nearest_support']['price']:.2f}")

        # Check if price is near resistance (potential sell)
        elif analysis['distance_to_resistance'] and analysis['distance_to_resistance'] < 0.5:
            signal = 'SELL'
            confidence = 0.7
            reasons.append(f"Price near strong resistance at {analysis['nearest_resistance']['price']:.2f}")

        # Check if price broke above resistance (bullish breakout)
        if analysis['nearest_resistance'] and current_price > analysis['nearest_resistance']['upper']:
            recent_close = df['close'].iloc[-2]
            if recent_close <= analysis['nearest_resistance']['upper']:
                signal = 'BUY'
                confidence = 0.8
                reasons.append(f"Breakout above resistance at {analysis['nearest_resistance']['price']:.2f}")

        # Check if price broke below support (bearish breakdown)
        if analysis['nearest_support'] and current_price < analysis['nearest_support']['lower']:
            recent_close = df['close'].iloc[-2]
            if recent_close >= analysis['nearest_support']['lower']:
                signal = 'SELL'
                confidence = 0.8
                reasons.append(f"Breakdown below support at {analysis['nearest_support']['price']:.2f}")

        return {
            'signal': signal,
            'confidence': confidence,
            'reason': '; '.join(reasons) if reasons else 'No S/R signal',
            'analysis': analysis
        }
