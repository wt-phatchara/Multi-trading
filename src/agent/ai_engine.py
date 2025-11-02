"""AI decision engine for trading predictions."""
import numpy as np
import pandas as pd
from typing import Dict, Optional, Tuple
from sklearn.preprocessing import StandardScaler
from sklearn.ensemble import RandomForestClassifier
import pickle
from pathlib import Path
from ..utils.logger import setup_logger

logger = setup_logger(__name__)


class AIDecisionEngine:
    """AI-powered decision engine for trading signals."""

    def __init__(self, model_path: Optional[str] = None, confidence_threshold: float = 0.7):
        """
        Initialize AI decision engine.

        Args:
            model_path: Path to saved model file
            confidence_threshold: Minimum confidence for acting on predictions
        """
        self.model_path = model_path
        self.confidence_threshold = confidence_threshold
        self.model = None
        self.scaler = StandardScaler()
        self.is_trained = False

        if model_path and Path(model_path).exists():
            self.load_model(model_path)

        logger.info(f"Initialized AI Decision Engine (confidence_threshold={confidence_threshold})")

    def prepare_features(self, df: pd.DataFrame) -> np.ndarray:
        """
        Prepare features for ML model.

        Args:
            df: DataFrame with OHLCV and indicator data

        Returns:
            Feature array
        """
        features = []

        # Price-based features
        if 'close' in df.columns:
            features.append(df['close'].pct_change().fillna(0))
            features.append(df['close'].pct_change(5).fillna(0))
            features.append(df['close'].pct_change(10).fillna(0))

        # Volume features
        if 'volume' in df.columns:
            features.append(df['volume'].pct_change().fillna(0))

        # Technical indicators
        indicator_columns = ['rsi', 'macd', 'macd_histogram', 'ema_9', 'ema_21']
        for col in indicator_columns:
            if col in df.columns:
                features.append(df[col].fillna(0))

        # Volatility
        if 'close' in df.columns:
            features.append(df['close'].rolling(20).std().fillna(0))

        # Combine features
        feature_matrix = np.column_stack(features) if features else np.array([])

        return feature_matrix

    def create_model(self) -> RandomForestClassifier:
        """
        Create a new Random Forest model.

        Returns:
            Initialized model
        """
        model = RandomForestClassifier(
            n_estimators=100,
            max_depth=10,
            min_samples_split=5,
            min_samples_leaf=2,
            random_state=42,
            class_weight='balanced'
        )
        logger.info("Created new Random Forest model")
        return model

    def train_model(self, historical_data: pd.DataFrame, labels: np.ndarray) -> None:
        """
        Train the AI model on historical data.

        Args:
            historical_data: DataFrame with OHLCV and indicators
            labels: Target labels (0=SELL, 1=HOLD, 2=BUY)
        """
        try:
            features = self.prepare_features(historical_data)

            if features.size == 0:
                logger.error("No features to train on")
                return

            # Scale features
            features_scaled = self.scaler.fit_transform(features)

            # Create and train model
            self.model = self.create_model()
            self.model.fit(features_scaled, labels)

            self.is_trained = True
            logger.info(f"Model trained on {len(labels)} samples")

        except Exception as e:
            logger.error(f"Error training model: {e}")
            raise

    def predict(self, df: pd.DataFrame) -> Tuple[str, float]:
        """
        Make prediction using the AI model.

        Args:
            df: DataFrame with current market data and indicators

        Returns:
            Tuple of (signal, confidence)
        """
        if not self.is_trained or self.model is None:
            logger.warning("Model not trained, using default strategy")
            return 'HOLD', 0.0

        try:
            features = self.prepare_features(df)

            if features.size == 0:
                return 'HOLD', 0.0

            # Use only the last row for prediction
            features_latest = features[-1:].reshape(1, -1)
            features_scaled = self.scaler.transform(features_latest)

            # Get prediction and probability
            prediction = self.model.predict(features_scaled)[0]
            probabilities = self.model.predict_proba(features_scaled)[0]

            # Map prediction to signal
            signal_map = {0: 'SELL', 1: 'HOLD', 2: 'BUY'}
            signal = signal_map.get(prediction, 'HOLD')
            confidence = float(probabilities[prediction])

            logger.debug(f"AI Prediction: {signal} (confidence: {confidence:.2f})")

            return signal, confidence

        except Exception as e:
            logger.error(f"Error making prediction: {e}")
            return 'HOLD', 0.0

    def combine_with_strategy(self, strategy_signal: Dict, df: pd.DataFrame) -> Dict:
        """
        Combine AI prediction with strategy signal.

        Args:
            strategy_signal: Signal from trading strategy
            df: DataFrame with market data

        Returns:
            Combined signal dictionary
        """
        if not self.is_trained:
            return strategy_signal

        ai_signal, ai_confidence = self.predict(df)

        # Weight signals
        strategy_weight = 0.4
        ai_weight = 0.6

        # Combine signals
        if strategy_signal['signal'] == ai_signal:
            # Signals agree - increase confidence
            combined_confidence = min(
                (strategy_signal['confidence'] * strategy_weight + ai_confidence * ai_weight) * 1.2,
                1.0
            )
            final_signal = strategy_signal['signal']
            reason = f"Strategy + AI agree: {strategy_signal['reason']}"

        elif ai_confidence > self.confidence_threshold:
            # AI has high confidence
            combined_confidence = ai_confidence * ai_weight
            final_signal = ai_signal
            reason = f"AI override (confidence: {ai_confidence:.2f})"

        elif strategy_signal['confidence'] > 0.6:
            # Strategy has high confidence
            combined_confidence = strategy_signal['confidence'] * strategy_weight
            final_signal = strategy_signal['signal']
            reason = strategy_signal['reason']

        else:
            # Conflicting low-confidence signals - HOLD
            combined_confidence = 0.0
            final_signal = 'HOLD'
            reason = "Conflicting signals - holding"

        return {
            'signal': final_signal,
            'confidence': combined_confidence,
            'reason': reason,
            'strategy_signal': strategy_signal['signal'],
            'ai_signal': ai_signal,
            'ai_confidence': ai_confidence,
            'indicators': strategy_signal.get('indicators', {})
        }

    def save_model(self, path: str) -> None:
        """Save model to file."""
        try:
            Path(path).parent.mkdir(parents=True, exist_ok=True)
            with open(path, 'wb') as f:
                pickle.dump({
                    'model': self.model,
                    'scaler': self.scaler,
                    'is_trained': self.is_trained
                }, f)
            logger.info(f"Model saved to {path}")
        except Exception as e:
            logger.error(f"Error saving model: {e}")

    def load_model(self, path: str) -> None:
        """Load model from file."""
        try:
            with open(path, 'rb') as f:
                data = pickle.load(f)
                self.model = data['model']
                self.scaler = data['scaler']
                self.is_trained = data['is_trained']
            logger.info(f"Model loaded from {path}")
        except Exception as e:
            logger.error(f"Error loading model: {e}")
