# Crypto Futures Trading Agent (AI-Powered)

An advanced AI-powered automated trading agent for cryptocurrency futures markets. This system combines technical analysis, machine learning predictions, and robust risk management to execute trades on popular cryptocurrency exchanges.

## Features

### Core Capabilities
- **AI-Enhanced Decision Making**: Combines traditional technical analysis with machine learning predictions
- **Multiple Trading Strategies**: Built-in momentum strategy with RSI, MACD, EMA, and Bollinger Bands
- **Advanced Risk Management**: Automated position sizing, stop-loss, take-profit, and daily loss limits
- **Real-time Market Analysis**: Live price feeds, order book data, and funding rate monitoring
- **Paper & Live Trading**: Safe testing environment with paper trading mode before going live
- **Multi-Exchange Support**: Compatible with Binance, Bybit, and other CCXT-supported exchanges

### Technical Features
- Asynchronous architecture for high performance
- Comprehensive logging and monitoring
- Configurable parameters via environment variables
- Position management with automatic SL/TP
- Daily P&L tracking and limits
- Leverage support (1x-125x)

## Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                     Trading Agent                            │
├─────────────────────────────────────────────────────────────┤
│                                                              │
│  ┌──────────────┐    ┌──────────────┐    ┌──────────────┐ │
│  │ Market Data  │───▶│   Strategy   │───▶│  AI Engine   │ │
│  │   Handler    │    │   Engine     │    │              │ │
│  └──────────────┘    └──────────────┘    └──────────────┘ │
│         │                    │                    │         │
│         │                    │                    │         │
│         ▼                    ▼                    ▼         │
│  ┌──────────────────────────────────────────────────────┐  │
│  │              Risk Manager                            │  │
│  └──────────────────────────────────────────────────────┘  │
│                           │                                 │
│                           ▼                                 │
│  ┌──────────────────────────────────────────────────────┐  │
│  │           Order Executor & Position Manager          │  │
│  └──────────────────────────────────────────────────────┘  │
│                           │                                 │
└───────────────────────────┼─────────────────────────────────┘
                            │
                            ▼
                  ┌──────────────────┐
                  │    Exchange API   │
                  └──────────────────┘
```

## Installation

### Prerequisites
- Python 3.8 or higher
- pip package manager
- Git

### Setup Instructions

1. **Clone the repository**
```bash
git clone <repository-url>
cd Multi-trading
```

2. **Create virtual environment**
```bash
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
```

3. **Install dependencies**
```bash
pip install -r requirements.txt
```

4. **Configure environment variables**
```bash
cp .env.example .env
# Edit .env with your settings
```

5. **Configure your exchange API**
Edit the `.env` file with your exchange API credentials:
```bash
EXCHANGE_NAME=binance
EXCHANGE_API_KEY=your_api_key_here
EXCHANGE_API_SECRET=your_api_secret_here
EXCHANGE_TESTNET=true  # Start with testnet!
```

## Configuration

All configuration is done via the `.env` file. Key parameters:

### Exchange Settings
```bash
EXCHANGE_NAME=binance           # binance, bybit, etc.
EXCHANGE_TESTNET=true           # Use testnet for testing
TRADING_MODE=paper              # paper or live
```

### Trading Parameters
```bash
DEFAULT_SYMBOL=BTC/USDT         # Trading pair
LEVERAGE=10                     # Leverage multiplier (1-125)
TIMEFRAME=5m                    # Candle timeframe
POSITION_SIZE_PERCENT=2.0       # % of portfolio per trade
```

### Risk Management
```bash
MAX_DAILY_LOSS_PERCENT=5.0      # Max daily loss limit
STOP_LOSS_PERCENT=2.0           # Stop loss percentage
TAKE_PROFIT_PERCENT=4.0         # Take profit percentage
```

### AI Configuration
```bash
USE_AI_PREDICTIONS=true         # Enable AI predictions
CONFIDENCE_THRESHOLD=0.7        # Minimum confidence to trade
```

## Usage

### Running the Agent

**Paper Trading (Recommended for testing)**
```bash
# Set TRADING_MODE=paper in .env
python main.py
```

**Live Trading (Use with caution)**
```bash
# Set TRADING_MODE=live in .env
python main.py
```

### Understanding the Output

The agent will log information about:
- Market analysis (price, indicators, signals)
- Trading decisions and reasons
- Position management (entries, exits, P&L)
- Risk metrics (daily P&L, open positions)

Example output:
```
[INFO] Market Analysis - Price: $43250.00, Signal: BUY, Confidence: 0.75
[INFO] Trade executed: BUY 0.0231 BTC/USDT at $43250.00 - Reason: MACD bullish crossover; EMA bullish alignment
[INFO] Daily P&L: $125.50
```

## Trading Strategies

### Momentum Strategy (Default)

The built-in momentum strategy uses:

1. **RSI (Relative Strength Index)**
   - Oversold (<30): Bullish signal
   - Overbought (>70): Bearish signal

2. **MACD (Moving Average Convergence Divergence)**
   - Bullish crossover: Buy signal
   - Bearish crossover: Sell signal

3. **Moving Averages**
   - EMA 9 > EMA 21: Bullish
   - EMA 9 < EMA 21: Bearish

4. **Bollinger Bands**
   - Price below lower band: Oversold
   - Price above upper band: Overbought

### Adding Custom Strategies

Create a new strategy by extending `BaseStrategy`:

```python
from src.strategies.base_strategy import BaseStrategy

class MyCustomStrategy(BaseStrategy):
    def __init__(self):
        super().__init__("My Custom Strategy")

    def calculate_indicators(self, df):
        # Add your indicators
        return df

    def generate_signal(self, df, **kwargs):
        # Generate buy/sell/hold signals
        return {
            'signal': 'BUY',
            'confidence': 0.8,
            'reason': 'Custom logic triggered'
        }
```

## Risk Management

The agent includes comprehensive risk management:

### Position Sizing
- Calculated based on account balance and signal confidence
- Respects maximum position size limits
- Adjusts for leverage

### Stop Loss & Take Profit
- Automatic SL/TP placement on each trade
- Configurable percentages
- Monitored in real-time

### Daily Loss Limits
- Stops trading if daily loss limit reached
- Resets each trading day
- Protects account from excessive losses

### Maximum Concurrent Positions
- Limited to 3 open positions simultaneously
- Prevents over-exposure

## AI Decision Engine

The AI engine enhances trading decisions:

### Features
- Random Forest classifier for predictions
- Combines technical indicators with ML
- Confidence-based signal weighting
- Agrees/overrides strategy signals

### Training the Model

```python
from src.agent.ai_engine import AIDecisionEngine
import pandas as pd

# Prepare historical data with indicators
df = prepare_historical_data()

# Labels: 0=SELL, 1=HOLD, 2=BUY
labels = create_labels(df)

# Train
ai_engine = AIDecisionEngine()
ai_engine.train_model(df, labels)
ai_engine.save_model('models/trading_model.pkl')
```

## Project Structure

```
Multi-trading/
├── src/
│   ├── agent/              # Main agent controller and AI engine
│   │   ├── trading_agent.py
│   │   └── ai_engine.py
│   ├── data/               # Market data handling
│   │   └── market_data.py
│   ├── strategies/         # Trading strategies
│   │   ├── base_strategy.py
│   │   ├── momentum_strategy.py
│   │   └── indicators.py
│   ├── risk/               # Risk management
│   │   └── risk_manager.py
│   ├── execution/          # Order execution
│   │   └── order_executor.py
│   └── utils/              # Utilities
│       ├── config.py
│       └── logger.py
├── config/                 # Configuration files
├── logs/                   # Log files
├── models/                 # AI models
├── main.py                 # Application entry point
├── requirements.txt        # Python dependencies
├── .env.example           # Environment variables template
└── README.md              # This file
```

## Safety & Best Practices

### Before Live Trading

1. **Test with Paper Trading**: Always test your configuration in paper mode first
2. **Use Testnet**: Start with exchange testnet environments
3. **Small Positions**: Begin with small position sizes
4. **Monitor Closely**: Watch the agent's behavior for several days
5. **Set Conservative Limits**: Use strict risk management parameters

### Security

- Never commit `.env` file to version control
- Keep API keys secure
- Use API keys with trading permissions only (no withdrawal)
- Enable IP whitelisting on exchange
- Use 2FA on exchange account

### Risk Warning

⚠️ **IMPORTANT**: Cryptocurrency futures trading involves substantial risk of loss. This software is provided for educational purposes. Always:
- Only trade with money you can afford to lose
- Understand the risks of leveraged trading
- Start with small amounts
- Monitor the bot regularly
- Never leave the bot unattended for long periods

## Monitoring & Logs

### Log Files
Logs are stored in `logs/trading_YYYYMMDD.log`

### Key Metrics to Monitor
- Daily P&L
- Win rate
- Average trade duration
- Number of trades per day
- Drawdown

### Performance Analysis

Check the logs for trade history and analyze:
```bash
# View today's trading log
tail -f logs/trading_$(date +%Y%m%d).log

# Search for executed trades
grep "Trade executed" logs/trading_*.log
```

## Troubleshooting

### Common Issues

**API Connection Errors**
- Verify API credentials in `.env`
- Check exchange API status
- Ensure IP is whitelisted (if enabled)

**Insufficient Balance**
- Check account balance
- Reduce `POSITION_SIZE_PERCENT`
- Lower `LEVERAGE`

**No Trades Executed**
- Check signal confidence threshold
- Review strategy parameters (RSI levels, etc.)
- Verify market conditions are suitable

**Exchange Errors**
- Check exchange-specific requirements
- Verify symbol format (e.g., BTC/USDT vs BTCUSDT)
- Check leverage limits for the symbol

## Development

### Running Tests
```bash
# Install dev dependencies
pip install pytest pytest-asyncio

# Run tests
pytest tests/
```

### Contributing
1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Add tests
5. Submit a pull request

## Support & Resources

### Exchange Documentation
- [Binance Futures API](https://binance-docs.github.io/apidocs/futures/en/)
- [Bybit API](https://bybit-exchange.github.io/docs/)
- [CCXT Documentation](https://docs.ccxt.com/)

### Technical Analysis
- [TA-Lib](https://ta-lib.org/)
- [TradingView](https://www.tradingview.com/)

## License

This project is provided as-is for educational purposes.

## Disclaimer

This software is for educational and research purposes only. Cryptocurrency trading carries a high level of risk and may not be suitable for all investors. The developers of this software are not responsible for any financial losses incurred through its use. Always do your own research and consult with financial advisors before trading.