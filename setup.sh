#!/bin/bash

# Crypto Futures Trading Agent - Easy Setup Script
# This script helps non-technical users set up the trading agent

echo "=========================================="
echo "Crypto Futures Trading Agent Setup"
echo "=========================================="
echo ""

# Check if Python is installed
if ! command -v python3 &> /dev/null; then
    echo "❌ Python 3 is not installed!"
    echo "Please install Python 3.8 or higher from https://www.python.org/downloads/"
    exit 1
fi

echo "✅ Python 3 found: $(python3 --version)"
echo ""

# Create virtual environment
echo "📦 Creating virtual environment..."
python3 -m venv venv

# Activate virtual environment
echo "🔧 Activating virtual environment..."
if [[ "$OSTYPE" == "msys" || "$OSTYPE" == "win32" ]]; then
    source venv/Scripts/activate
else
    source venv/bin/activate
fi

# Upgrade pip
echo "⬆️  Upgrading pip..."
python -m pip install --upgrade pip

# Install dependencies
echo "📥 Installing dependencies (this may take a few minutes)..."
pip install -r requirements.txt

# Create .env file if it doesn't exist
if [ ! -f .env ]; then
    echo "⚙️  Creating configuration file..."
    cp .env.example .env
    echo "✅ Configuration file created at .env"
    echo ""
    echo "⚠️  IMPORTANT: Please edit the .env file with your settings:"
    echo "   - Add your exchange API keys"
    echo "   - Configure your trading preferences"
    echo "   - Start with TRADING_MODE=paper for testing"
else
    echo "✅ Configuration file already exists"
fi

# Create necessary directories
mkdir -p logs models data

echo ""
echo "=========================================="
echo "✅ Setup Complete!"
echo "=========================================="
echo ""
echo "Next steps:"
echo "1. Edit the .env file with your exchange API credentials"
echo "2. Review the BEGINNER_GUIDE.md for detailed instructions"
echo "3. Run the bot with: ./start.sh"
echo ""
echo "For testing (recommended):"
echo "   Set TRADING_MODE=paper in .env"
echo "   Set EXCHANGE_TESTNET=true in .env"
echo ""
