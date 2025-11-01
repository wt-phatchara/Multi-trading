#!/bin/bash

# Easy start script for the trading agent

echo "=========================================="
echo "Starting Crypto Futures Trading Agent"
echo "=========================================="
echo ""

# Check if virtual environment exists
if [ ! -d "venv" ]; then
    echo "❌ Virtual environment not found!"
    echo "Please run ./setup.sh first"
    exit 1
fi

# Activate virtual environment
echo "🔧 Activating virtual environment..."
if [[ "$OSTYPE" == "msys" || "$OSTYPE" == "win32" ]]; then
    source venv/Scripts/activate
else
    source venv/bin/activate
fi

# Check if .env file exists
if [ ! -f .env ]; then
    echo "❌ Configuration file (.env) not found!"
    echo "Please copy .env.example to .env and configure it"
    exit 1
fi

# Display current configuration
echo "📋 Current Configuration:"
echo "   Exchange: $(grep EXCHANGE_NAME .env | cut -d '=' -f2)"
echo "   Trading Mode: $(grep TRADING_MODE .env | cut -d '=' -f2)"
echo "   Symbol: $(grep DEFAULT_SYMBOL .env | cut -d '=' -f2)"
echo ""

# Confirm before starting
read -p "Start the trading agent? (y/n): " -n 1 -r
echo ""

if [[ $REPLY =~ ^[Yy]$ ]]; then
    echo "🚀 Starting agent..."
    echo "   Press Ctrl+C to stop"
    echo ""
    python main.py
else
    echo "❌ Cancelled"
fi
