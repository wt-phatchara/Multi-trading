@echo off
REM Easy start script for Windows

echo ==========================================
echo Starting Crypto Futures Trading Agent
echo ==========================================
echo.

REM Check if virtual environment exists
if not exist venv (
    echo [X] Virtual environment not found!
    echo Please run setup.bat first
    pause
    exit /b 1
)

REM Activate virtual environment
echo [*] Activating virtual environment...
call venv\Scripts\activate.bat

REM Check if .env file exists
if not exist .env (
    echo [X] Configuration file (.env) not found!
    echo Please copy .env.example to .env and configure it
    pause
    exit /b 1
)

REM Display current configuration
echo [*] Current Configuration:
findstr "EXCHANGE_NAME" .env
findstr "TRADING_MODE" .env
findstr "DEFAULT_SYMBOL" .env
echo.

REM Confirm before starting
set /p confirm="Start the trading agent? (y/n): "
if /i "%confirm%"=="y" (
    echo [*] Starting agent...
    echo    Press Ctrl+C to stop
    echo.
    python main.py
) else (
    echo [X] Cancelled
)

pause
