# Beginner's Guide - Crypto Futures Trading Agent

**Perfect for Non-Technical Users!**

This guide will help you set up and run your crypto futures trading agent, even if you have no programming experience.

---

## 📚 Table of Contents

1. [What You Need](#what-you-need)
2. [Installation (Step-by-Step)](#installation-step-by-step)
3. [Configuration](#configuration)
4. [Running the Agent](#running-the-agent)
5. [Understanding the Output](#understanding-the-output)
6. [Safety Tips](#safety-tips)
7. [Troubleshooting](#troubleshooting)

---

## What You Need

Before starting, make sure you have:

### Required:
- [ ] A computer (Windows, Mac, or Linux)
- [ ] Internet connection
- [ ] Exchange account (Binance or Bybit recommended)
- [ ] API keys from your exchange (we'll show you how to get these)

### Optional but Recommended:
- [ ] Testnet account for safe testing
- [ ] Basic understanding of crypto trading

---

## Installation (Step-by-Step)

### For Windows Users:

1. **Download and Install Python**
   - Go to https://www.python.org/downloads/
   - Download Python 3.8 or higher
   - Run the installer
   - ✅ **IMPORTANT**: Check "Add Python to PATH" during installation
   - Click "Install Now"

2. **Download the Trading Agent**
   - Download this project as a ZIP file
   - Extract it to a folder (e.g., `C:\TradingBot`)

3. **Run the Setup**
   - Open the folder in File Explorer
   - Double-click `setup.bat`
   - Wait for installation to complete (2-5 minutes)

### For Mac/Linux Users:

1. **Install Python** (if not already installed)
   ```bash
   # Mac (using Homebrew)
   brew install python3

   # Linux (Ubuntu/Debian)
   sudo apt-get install python3 python3-pip python3-venv
   ```

2. **Download and Extract the Trading Agent**

3. **Run the Setup**
   ```bash
   # Make the script executable
   chmod +x setup.sh

   # Run setup
   ./setup.sh
   ```

---

## Configuration

After setup, you need to configure the agent:

### Step 1: Get Exchange API Keys

#### For Binance:
1. Log into your Binance account
2. Go to **Profile** → **API Management**
3. Create a new API key
4. Set permissions:
   - ✅ Enable Reading
   - ✅ Enable Spot & Margin Trading
   - ✅ Enable Futures
   - ❌ Disable Withdrawals (for security!)
5. Save your API Key and Secret Key

#### For Bybit:
1. Log into Bybit
2. Go to **Account & Security** → **API**
3. Create new API key
4. Enable only trading permissions
5. Save your keys

### Step 2: Configure the Bot

1. Open the `.env` file in a text editor (Notepad, TextEdit, etc.)

2. **Edit these settings:**

```bash
# Exchange Settings
EXCHANGE_NAME=binance          # or 'bybit'
EXCHANGE_API_KEY=your_key_here
EXCHANGE_API_SECRET=your_secret_here
EXCHANGE_TESTNET=true          # Use 'true' for testing!

# Trading Settings
TRADING_MODE=paper             # Use 'paper' for safe testing!
DEFAULT_SYMBOL=BTC/USDT        # Trading pair
LEVERAGE=5                     # Start with low leverage!
POSITION_SIZE_PERCENT=1.0      # Use only 1% per trade

# Risk Management
MAX_DAILY_LOSS_PERCENT=3.0     # Stop if you lose 3% in a day
STOP_LOSS_PERCENT=2.0          # Exit if trade loses 2%
TAKE_PROFIT_PERCENT=4.0        # Take profit at 4% gain

# Strategy (Choose one)
STRATEGY=advanced              # Options: momentum, advanced
```

3. **Save the file**

### Important Settings Explained:

| Setting | What It Does | Recommended for Beginners |
|---------|-------------|---------------------------|
| `EXCHANGE_TESTNET` | Use fake money for testing | `true` |
| `TRADING_MODE` | Paper trading vs real money | `paper` |
| `LEVERAGE` | Multiplier for your trades | `1` to `5` |
| `POSITION_SIZE_PERCENT` | % of balance per trade | `0.5` to `2.0` |
| `MAX_DAILY_LOSS_PERCENT` | Daily loss limit | `2.0` to `5.0` |

---

## Running the Agent

### Windows:
1. Double-click `start.bat`
2. Review the configuration shown
3. Type `y` and press Enter to start
4. **To stop**: Press `Ctrl+C`

### Mac/Linux:
```bash
./start.sh
# To stop: Press Ctrl+C
```

---

## Understanding the Output

When the agent runs, you'll see messages like:

```
✅ Good Signs:
[INFO] Trading Agent initialized - Symbol: BTC/USDT, Mode: paper
[INFO] Market Analysis - Price: $43250.00, Signal: BUY, Confidence: 0.75
[INFO] Trade executed: BUY 0.0231 BTC/USDT at $43250.00

⚠️ Pay Attention:
[WARNING] Daily loss limit reached: 3.5%
[WARNING] Low confidence: 0.45

❌ Errors:
[ERROR] Error fetching balance: Invalid API key
```

### What Each Strategy Does:

1. **Momentum Strategy** (Simple)
   - Uses RSI, MACD, moving averages
   - Good for trending markets
   - Easier to understand

2. **Advanced Strategy** (Recommended)
   - Combines 5 different methods:
     - Technical indicators
     - Support/Resistance zones
     - Price Action patterns
     - Smart Money Concepts
     - Elliott Wave analysis
   - More accurate signals
   - Better for all market conditions

---

## Safety Tips

### ⚠️ CRITICAL - Read This First!

1. **ALWAYS Start with Paper Trading**
   - Set `TRADING_MODE=paper` in `.env`
   - Test for at least 1-2 weeks
   - Learn how it works without risk

2. **ALWAYS Use Testnet First**
   - Set `EXCHANGE_TESTNET=true`
   - Practice with fake money
   - Only go live when confident

3. **Start Small**
   - Use low leverage (1x-3x)
   - Small position sizes (0.5%-1%)
   - Only risk money you can afford to lose

4. **Monitor Regularly**
   - Check the bot daily
   - Review trades in the logs
   - Adjust settings based on performance

5. **Set Strict Limits**
   - Low daily loss limit (2%-3%)
   - Tight stop losses
   - Take profits regularly

### 🚫 Never Do This:

- ❌ Use high leverage (>10x) as a beginner
- ❌ Give API keys withdrawal permissions
- ❌ Share your API keys with anyone
- ❌ Leave the bot running unattended for days
- ❌ Skip the testing phase
- ❌ Trade with money you need

---

## Troubleshooting

### Problem: "Python not found"
**Solution**: Make sure Python is installed and added to PATH

### Problem: "Invalid API key"
**Solution**:
- Check your API key is correct in `.env`
- Make sure API key has correct permissions
- Try creating a new API key

### Problem: "No trades being executed"
**Solution**:
- Check that `TRADING_MODE` is set correctly
- Lower the `CONFIDENCE_THRESHOLD` in `.env`
- Check market conditions (might be ranging)

### Problem: "Insufficient balance"
**Solution**:
- Reduce `POSITION_SIZE_PERCENT`
- Reduce `LEVERAGE`
- Add more funds to your account

### Problem: Bot stops unexpectedly
**Solution**:
- Check the log files in `logs/` folder
- Look for error messages
- Make sure your internet connection is stable

---

## Getting Help

### Check These First:
1. Read the error message in the console
2. Check the log files in the `logs/` folder
3. Review this guide and README.md

### Still Stuck?
- Check the exchange API status
- Verify your API keys are active
- Try restarting the bot
- Review your `.env` configuration

---

## Next Steps

Once comfortable with paper trading:

1. **Test for 1-2 weeks** with paper trading
2. **Analyze Results**
   - Check win rate
   - Review log files
   - Understand why trades were made
3. **Adjust Settings** based on results
4. **Go Live Slowly**
   - Start with very small amounts
   - Use low leverage (1x-2x)
   - Gradually increase as you gain confidence

---

## Quick Reference

### Starting the Bot:
- **Windows**: Double-click `start.bat`
- **Mac/Linux**: `./start.sh`

### Stopping the Bot:
- Press `Ctrl+C` in the console window

### Viewing Logs:
- Open `logs/` folder
- Look for `trading_YYYYMMDD.log`

### Changing Settings:
- Edit `.env` file
- Restart the bot

---

## Glossary

- **API Key**: Secret code to access your exchange account
- **Paper Trading**: Trading with fake money for practice
- **Leverage**: Borrowing money to increase position size
- **Stop Loss**: Automatic exit when losing too much
- **Take Profit**: Automatic exit when reaching profit target
- **RSI**: Indicator showing if asset is overbought/oversold
- **MACD**: Indicator showing trend and momentum
- **Support/Resistance**: Price levels where bounces often occur

---

## Remember:

> 🎯 **The goal is to learn and be profitable consistently, not to get rich quick!**

> 💡 **Start slow, test thoroughly, and never risk more than you can afford to lose.**

> 📚 **Keep learning! The more you understand, the better you can configure the bot.**

---

**Good luck and trade safely!** 🚀
