# Quick Start Guide

Get your crypto futures trading agent running in 5 minutes!

## Prerequisites

- Python 3.8+
- Exchange account (Binance/Bybit recommended)
- API keys from your exchange

## Step 1: Installation

```bash
# Clone and enter directory
git clone <repo-url>
cd Multi-trading

# Create virtual environment
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt
```

## Step 2: Configuration

```bash
# Copy example config
cp .env.example .env

# Edit .env file
nano .env  # or use your favorite editor
```

**Minimal configuration for testing:**
```bash
# Use Binance Testnet (safe for testing)
EXCHANGE_NAME=binance
EXCHANGE_TESTNET=true
TRADING_MODE=paper

# You can use dummy keys for paper trading
EXCHANGE_API_KEY=test_key
EXCHANGE_API_SECRET=test_secret

# Trading settings
DEFAULT_SYMBOL=BTC/USDT
LEVERAGE=5
POSITION_SIZE_PERCENT=1.0
```

## Step 3: Run the Agent

```bash
python main.py
```

You should see:
```
╔═══════════════════════════════════════════════════════════╗
║                                                           ║
║       CRYPTO FUTURES TRADING AGENT (AI-POWERED)          ║
║                                                           ║
╚═══════════════════════════════════════════════════════════╝

[INFO] Configuration loaded successfully
[INFO] Exchange: binance (testnet=True)
[INFO] Trading Mode: paper
[INFO] Starting Crypto Futures Trading Agent...
```

## Step 4: Monitor Trading

Watch the console output for:
- Market analysis updates
- Trading signals
- Position entries/exits
- P&L tracking

Example:
```
[INFO] Market Analysis - Price: $43250.00, Signal: BUY, Confidence: 0.75
[INFO] Trade executed: BUY 0.0231 BTC/USDT at $43250.00
```

## Step 5: Going Live (When Ready)

⚠️ **Only after thorough testing!**

1. Get real API keys from your exchange
2. Update `.env`:
   ```bash
   EXCHANGE_TESTNET=false
   TRADING_MODE=live
   EXCHANGE_API_KEY=your_real_api_key
   EXCHANGE_API_SECRET=your_real_api_secret
   ```
3. Start with small positions:
   ```bash
   POSITION_SIZE_PERCENT=0.5
   LEVERAGE=1
   ```

## Common Commands

**Stop the agent:**
```bash
Ctrl+C
```

**View logs:**
```bash
tail -f logs/trading_$(date +%Y%m%d).log
```

**Check positions:**
Positions are logged to console and log files

## Next Steps

- Read the full [README.md](README.md)
- Adjust risk parameters in `.env`
- Customize trading strategies
- Train AI model with historical data

## Need Help?

- Check [README.md](README.md) for detailed documentation
- Review logs in `logs/` directory
- Verify exchange API status
- Test with paper trading first!

## Safety Reminders

✅ Start with paper trading
✅ Use testnet first
✅ Small position sizes
✅ Conservative leverage
✅ Monitor regularly

❌ Don't trade with money you can't lose
❌ Don't use high leverage initially
❌ Don't leave unattended
❌ Don't skip testing phase
