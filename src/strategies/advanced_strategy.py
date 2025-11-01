"""Advanced trading strategy combining multiple methodologies."""
import pandas as pd
from typing import Dict
from .base_strategy import BaseStrategy
from .indicators import TechnicalIndicators
from .support_resistance import SupportResistance
from .price_action import PriceActionPatterns
from .smart_money import SmartMoneyConcepts
from .elliott_wave import ElliottWave
from ..utils.logger import setup_logger

logger = setup_logger(__name__)


class AdvancedStrategy(BaseStrategy):
    """
    Advanced trading strategy combining:
    - Technical Indicators (RSI, MACD, etc.)
    - Support & Resistance zones
    - Price Action patterns
    - Smart Money Concepts
    - Elliott Wave analysis
    """

    def __init__(self):
        """Initialize advanced strategy."""
        super().__init__("Advanced Multi-Method Strategy")
        self.weights = {
            'technical': 0.20,
            'support_resistance': 0.20,
            'price_action': 0.20,
            'smart_money': 0.25,
            'elliott_wave': 0.15
        }

    def calculate_indicators(self, df: pd.DataFrame) -> pd.DataFrame:
        """Calculate all technical indicators."""
        df = df.copy()

        # RSI
        df['rsi'] = TechnicalIndicators.calculate_rsi(df['close'], 14)

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

        # ATR for volatility
        df['atr'] = TechnicalIndicators.calculate_atr(
            df['high'], df['low'], df['close']
        )

        # Stochastic
        k, d = TechnicalIndicators.calculate_stochastic(
            df['high'], df['low'], df['close']
        )
        df['stoch_k'] = k
        df['stoch_d'] = d

        return df

    def analyze_technical_indicators(self, df: pd.DataFrame) -> Dict:
        """Analyze technical indicators for signal."""
        df = self.calculate_indicators(df)
        latest = df.iloc[-1]
        prev = df.iloc[-2]

        signal = 'HOLD'
        confidence = 0.0
        reasons = []

        # RSI
        if latest['rsi'] < 30:
            signal = 'BUY'
            confidence += 0.3
            reasons.append('RSI oversold')
        elif latest['rsi'] > 70:
            signal = 'SELL'
            confidence += 0.3
            reasons.append('RSI overbought')

        # MACD crossover
        if latest['macd'] > latest['macd_signal'] and prev['macd'] <= prev['macd_signal']:
            signal = 'BUY'
            confidence += 0.4
            reasons.append('MACD bullish crossover')
        elif latest['macd'] < latest['macd_signal'] and prev['macd'] >= prev['macd_signal']:
            signal = 'SELL'
            confidence += 0.4
            reasons.append('MACD bearish crossover')

        # EMA trend
        if latest['ema_9'] > latest['ema_21']:
            if signal != 'SELL':
                confidence += 0.2
                reasons.append('Bullish EMA trend')
        else:
            if signal != 'BUY':
                confidence += 0.2
                reasons.append('Bearish EMA trend')

        # Stochastic
        if latest['stoch_k'] < 20:
            if signal == 'BUY':
                confidence += 0.1
        elif latest['stoch_k'] > 80:
            if signal == 'SELL':
                confidence += 0.1

        return {
            'signal': signal,
            'confidence': min(confidence, 1.0),
            'reasons': reasons
        }

    def generate_signal(self, df: pd.DataFrame, **kwargs) -> Dict:
        """
        Generate comprehensive signal using all methodologies.

        Args:
            df: DataFrame with OHLCV data

        Returns:
            Combined signal dictionary
        """
        if len(df) < 50:
            return {
                'signal': 'HOLD',
                'confidence': 0.0,
                'reason': 'Insufficient data',
                'breakdown': {}
            }

        current_price = float(df['close'].iloc[-1])

        # Get signals from each methodology
        technical = self.analyze_technical_indicators(df)
        sr_signal = SupportResistance.generate_sr_signal(df, current_price)
        pa_signal = PriceActionPatterns.generate_signal(df)
        smc_signal = SmartMoneyConcepts.generate_signal(df, current_price)
        ew_signal = ElliottWave.generate_signal(df, current_price)

        # Combine signals with weights
        buy_score = 0.0
        sell_score = 0.0
        all_reasons = []

        # Technical indicators
        if technical['signal'] == 'BUY':
            buy_score += self.weights['technical'] * technical['confidence']
            all_reasons.extend([f"Tech: {r}" for r in technical['reasons']])
        elif technical['signal'] == 'SELL':
            sell_score += self.weights['technical'] * technical['confidence']
            all_reasons.extend([f"Tech: {r}" for r in technical['reasons']])

        # Support/Resistance
        if sr_signal['signal'] == 'BUY':
            buy_score += self.weights['support_resistance'] * sr_signal['confidence']
            all_reasons.append(f"S/R: {sr_signal['reason']}")
        elif sr_signal['signal'] == 'SELL':
            sell_score += self.weights['support_resistance'] * sr_signal['confidence']
            all_reasons.append(f"S/R: {sr_signal['reason']}")

        # Price Action
        if pa_signal['signal'] == 'BUY':
            buy_score += self.weights['price_action'] * pa_signal['confidence']
            all_reasons.append(f"PA: {pa_signal['reason']}")
        elif pa_signal['signal'] == 'SELL':
            sell_score += self.weights['price_action'] * pa_signal['confidence']
            all_reasons.append(f"PA: {pa_signal['reason']}")

        # Smart Money Concepts
        if smc_signal['signal'] == 'BUY':
            buy_score += self.weights['smart_money'] * smc_signal['confidence']
            all_reasons.append(f"SMC: {smc_signal['reason']}")
        elif smc_signal['signal'] == 'SELL':
            sell_score += self.weights['smart_money'] * smc_signal['confidence']
            all_reasons.append(f"SMC: {smc_signal['reason']}")

        # Elliott Wave
        if ew_signal['signal'] == 'BUY':
            buy_score += self.weights['elliott_wave'] * ew_signal['confidence']
            all_reasons.append(f"EW: {ew_signal['reason']}")
        elif ew_signal['signal'] == 'SELL':
            sell_score += self.weights['elliott_wave'] * ew_signal['confidence']
            all_reasons.append(f"EW: {ew_signal['reason']}")

        # Determine final signal
        if buy_score > sell_score and buy_score > 0.4:
            final_signal = 'BUY'
            final_confidence = buy_score
        elif sell_score > buy_score and sell_score > 0.4:
            final_signal = 'SELL'
            final_confidence = sell_score
        else:
            final_signal = 'HOLD'
            final_confidence = 0.0

        result = {
            'signal': final_signal,
            'confidence': min(final_confidence, 1.0),
            'reason': '; '.join(all_reasons) if all_reasons else 'No clear signal',
            'breakdown': {
                'technical': technical,
                'support_resistance': sr_signal,
                'price_action': pa_signal,
                'smart_money': smc_signal,
                'elliott_wave': ew_signal
            },
            'scores': {
                'buy_score': buy_score,
                'sell_score': sell_score
            }
        }

        logger.info(
            f"Advanced Signal: {final_signal} (confidence: {final_confidence:.2f}, "
            f"buy: {buy_score:.2f}, sell: {sell_score:.2f})"
        )

        return result
