@echo off
REM Crypto Futures Trading Agent - Easy Setup Script for Windows

echo ==========================================
echo Crypto Futures Trading Agent Setup
echo ==========================================
echo.

REM Check if Python is installed
python --version >nul 2>&1
if errorlevel 1 (
    echo X Python is not installed!
    echo Please install Python 3.8 or higher from https://www.python.org/downloads/
    pause
    exit /b 1
)

echo [OK] Python found
python --version
echo.

REM Create virtual environment
echo [*] Creating virtual environment...
python -m venv venv

REM Activate virtual environment
echo [*] Activating virtual environment...
call venv\Scripts\activate.bat

REM Upgrade pip
echo [*] Upgrading pip...
python -m pip install --upgrade pip

REM Install dependencies
echo [*] Installing dependencies (this may take a few minutes)...
pip install -r requirements.txt

REM Create .env file if it doesn't exist
if not exist .env (
    echo [*] Creating configuration file...
    copy .env.example .env
    echo [OK] Configuration file created at .env
    echo.
    echo [!] IMPORTANT: Please edit the .env file with your settings:
    echo    - Add your exchange API keys
    echo    - Configure your trading preferences
    echo    - Start with TRADING_MODE=paper for testing
) else (
    echo [OK] Configuration file already exists
)

REM Create necessary directories
if not exist logs mkdir logs
if not exist models mkdir models
if not exist data mkdir data

echo.
echo ==========================================
echo [OK] Setup Complete!
echo ==========================================
echo.
echo Next steps:
echo 1. Edit the .env file with your exchange API credentials
echo 2. Review the BEGINNER_GUIDE.md for detailed instructions
echo 3. Run the bot with: start.bat
echo.
echo For testing (recommended):
echo    Set TRADING_MODE=paper in .env
echo    Set EXCHANGE_TESTNET=true in .env
echo.
pause
