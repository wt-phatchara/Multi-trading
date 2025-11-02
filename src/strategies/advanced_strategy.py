"""Advanced trading strategy combining multiple methodologies."""
import pandas as pd
from typing import Dict, Optional
from datetime import datetime
from .base_strategy import BaseStrategy
from .indicators import TechnicalIndicators
from .support_resistance import SupportResistance
from .price_action import PriceActionPatterns
from .smart_money import SmartMoneyConcepts
from .elliott_wave import ElliottWave
from .ict_concepts import ICTConcepts
from .professional_price_action import ProfessionalPriceAction
from .top_down_analysis import TopDownAnalysis
from ..utils.logger import setup_logger

logger = setup_logger(__name__)


class AdvancedStrategy(BaseStrategy):
    """
    Advanced trading strategy with two modes:

    Mode 1 - Multi-Method (default):
    - ICT Concepts (Premium/Discount, OTE, Kill Zones) - HIGHEST WEIGHT
    - Smart Money Concepts (Order Blocks, FVG, Market Structure)
    - Price Action patterns
    - Support & Resistance zones
    - Technical Indicators (RSI, MACD, etc.)
    - Elliott Wave analysis

    Mode 2 - Professional Price Action (use_professional_mode=True):
    - Pure professional trading system from briefing
    - Confirmation Entry Model
    - Top-Down Analysis workflow
    - Structure-based entries/exits
    - Highest probability setups only
    """

    def __init__(self, use_professional_mode: bool = False):
        """
        Initialize advanced strategy.

        Args:
            use_professional_mode: If True, use pure professional price action system
        """
        super().__init__(
            "Professional Price Action Strategy" if use_professional_mode
            else "Advanced Multi-Method Strategy with ICT"
        )

        self.use_professional_mode = use_professional_mode

        # Multi-method weights
        self.weights = {
            'ict': 0.30,                # ICT concepts - highest weight
            'smart_money': 0.20,        # SMC
            'price_action': 0.15,       # Price action
            'support_resistance': 0.15, # S/R
            'technical': 0.12,          # Indicators
            'elliott_wave': 0.08        # Elliott Wave
        }

        # Professional mode components
        if use_professional_mode:
            self.professional_pa = ProfessionalPriceAction()
            self.tda = TopDownAnalysis()
            logger.info("✅ Professional Price Action Mode Activated")
        else:
            logger.info("✅ Multi-Method Mode Activated")

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

    def generate_signal_professional(
        self,
        df: pd.DataFrame,
        daily_df: Optional[pd.DataFrame] = None,
        h4_df: Optional[pd.DataFrame] = None,
        h1_df: Optional[pd.DataFrame] = None,
        m15_df: Optional[pd.DataFrame] = None,
        **kwargs
    ) -> Dict:
        """
        Generate signal using Professional Price Action methodology.

        Requires multi-timeframe data for Top-Down Analysis.
        If not all timeframes provided, uses Confirmation Entry Model on single TF.

        Args:
            df: Current timeframe DataFrame (typically 5M)
            daily_df: Daily timeframe data (optional)
            h4_df: 4-hour data (optional)
            h1_df: 1-hour data (optional)
            m15_df: 15-minute data (optional)

        Returns:
            Professional signal with complete analysis
        """
        current_price = float(df['close'].iloc[-1])
        current_time = datetime.utcnow()

        # Full Top-Down Analysis if all timeframes available
        if all([daily_df is not None, h4_df is not None, h1_df is not None, m15_df is not None]):
            logger.info("Running complete Top-Down Analysis...")

            tda_result = self.tda.complete_top_down_analysis(
                daily_df=daily_df,
                h4_df=h4_df,
                h1_df=h1_df,
                m15_df=m15_df,
                m5_df=df,
                current_time=current_time
            )

            return {
                'signal': tda_result['signal'],
                'confidence': tda_result['confidence'],
                'reason': tda_result['summary'],
                'mode': 'PROFESSIONAL_TDA',
                'entry_params': tda_result.get('entry_params'),
                'analysis': tda_result,
                'breakdown': {
                    'htf': tda_result['htf_analysis'],
                    'mtf': tda_result['mtf_analysis'],
                    'ltf': tda_result['ltf_analysis']
                }
            }

        # Confirmation Entry Model if HTF and LTF available
        elif h4_df is not None:
            logger.info("Running Confirmation Entry Model...")

            confirmation = self.professional_pa.confirmation_entry_model(
                htf_df=h4_df,
                ltf_df=df,
                current_price=current_price,
                current_time=current_time
            )

            return {
                'signal': confirmation['entry_signal'],
                'confidence': confirmation.get('confidence', 0.0),
                'reason': confirmation['reason'],
                'mode': 'PROFESSIONAL_CONFIRMATION',
                'entry_params': confirmation if confirmation['entry_signal'] != 'WAIT' else None,
                'analysis': confirmation
            }

        # Fallback: Single timeframe professional analysis
        else:
            logger.info("Running single-TF professional analysis...")

            trend = self.professional_pa.identify_trend(df)
            zones = self.professional_pa.identify_supply_demand_zones(df, trend['trend'])
            momentum = self.professional_pa.read_momentum_quality(df)
            session = self.professional_pa.analyze_session_characteristics(current_time, df)

            # Simple signal based on zones and momentum
            signal = 'HOLD'
            confidence = 0.0
            reasons = []

            for zone in zones:
                if zone['low'] <= current_price <= zone['high']:
                    if zone['type'] == 'DEMAND' and trend['trend'] == 'UPTREND':
                        signal = 'BUY'
                        confidence = 0.7
                        reasons.append(f"In DEMAND zone with uptrend")
                    elif zone['type'] == 'SUPPLY' and trend['trend'] == 'DOWNTREND':
                        signal = 'SELL'
                        confidence = 0.7
                        reasons.append(f"In SUPPLY zone with downtrend")

                    if momentum['quality'] == 'HIGH':
                        confidence += 0.1
                        reasons.append(f"High momentum quality")

                    if session['is_prime_time']:
                        confidence += 0.1
                        reasons.append(f"{session['session']} session")

                    break

            return {
                'signal': signal,
                'confidence': min(confidence, 1.0),
                'reason': '; '.join(reasons) if reasons else 'No professional setup',
                'mode': 'PROFESSIONAL_SINGLE_TF',
                'analysis': {
                    'trend': trend,
                    'zones': zones,
                    'momentum': momentum,
                    'session': session
                }
            }

    def generate_signal(self, df: pd.DataFrame, **kwargs) -> Dict:
        """
        Generate comprehensive signal using selected methodology.

        Args:
            df: DataFrame with OHLCV data
            **kwargs: Additional parameters (e.g., multi-timeframe data for professional mode)

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

        # Route to professional mode if enabled
        if self.use_professional_mode:
            return self.generate_signal_professional(df, **kwargs)

        # Multi-method mode (original logic)
        current_price = float(df['close'].iloc[-1])
        current_time = datetime.utcnow()  # Use UTC for kill zones

        # Get signals from each methodology (ICT has highest priority)
        ict_signal = ICTConcepts.generate_ict_signal(df, current_price, current_time)
        smc_signal = SmartMoneyConcepts.generate_signal(df, current_price)
        pa_signal = PriceActionPatterns.generate_signal(df)
        sr_signal = SupportResistance.generate_sr_signal(df, current_price)
        technical = self.analyze_technical_indicators(df)
        ew_signal = ElliottWave.generate_signal(df, current_price)

        # Combine signals with weights
        buy_score = 0.0
        sell_score = 0.0
        all_reasons = []

        # ICT Concepts (HIGHEST WEIGHT - 30%)
        if ict_signal['signal'] == 'BUY':
            buy_score += self.weights['ict'] * ict_signal['confidence']
            all_reasons.append(f"ICT: {ict_signal['reason']}")
        elif ict_signal['signal'] == 'SELL':
            sell_score += self.weights['ict'] * ict_signal['confidence']
            all_reasons.append(f"ICT: {ict_signal['reason']}")

        # Smart Money Concepts (20%)
        if smc_signal['signal'] == 'BUY':
            buy_score += self.weights['smart_money'] * smc_signal['confidence']
            all_reasons.append(f"SMC: {smc_signal['reason']}")
        elif smc_signal['signal'] == 'SELL':
            sell_score += self.weights['smart_money'] * smc_signal['confidence']
            all_reasons.append(f"SMC: {smc_signal['reason']}")

        # Price Action (15%)
        if pa_signal['signal'] == 'BUY':
            buy_score += self.weights['price_action'] * pa_signal['confidence']
            all_reasons.append(f"PA: {pa_signal['reason']}")
        elif pa_signal['signal'] == 'SELL':
            sell_score += self.weights['price_action'] * pa_signal['confidence']
            all_reasons.append(f"PA: {pa_signal['reason']}")

        # Support/Resistance (15%)
        if sr_signal['signal'] == 'BUY':
            buy_score += self.weights['support_resistance'] * sr_signal['confidence']
            all_reasons.append(f"S/R: {sr_signal['reason']}")
        elif sr_signal['signal'] == 'SELL':
            sell_score += self.weights['support_resistance'] * sr_signal['confidence']
            all_reasons.append(f"S/R: {sr_signal['reason']}")

        # Technical indicators (12%)
        if technical['signal'] == 'BUY':
            buy_score += self.weights['technical'] * technical['confidence']
            all_reasons.extend([f"Tech: {r}" for r in technical['reasons']])
        elif technical['signal'] == 'SELL':
            sell_score += self.weights['technical'] * technical['confidence']
            all_reasons.extend([f"Tech: {r}" for r in technical['reasons']])

        # Elliott Wave (8%)
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
                'ict': ict_signal,
                'smart_money': smc_signal,
                'price_action': pa_signal,
                'support_resistance': sr_signal,
                'technical': technical,
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
