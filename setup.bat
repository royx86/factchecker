@echo off
REM Instagram Fact-Checker — Setup Script for Windows
REM This script sets up everything needed to run the fact-checker

setlocal enabledelayedexpansion

echo.
echo ╔═══════════════════════════════════════════════════════╗
echo ║   Instagram Fact-Checker — Windows Setup              ║
echo ╚═══════════════════════════════════════════════════════╝
echo.

REM Check if Python is installed
python --version >nul 2>&1
if errorlevel 1 (
    echo [X] ERROR: Python not found or not in PATH
    echo.
    echo Please install Python 3.13+ from: https://www.python.org/downloads/
    echo Make sure to check "Add python.exe to PATH" during installation
    echo.
    pause
    exit /b 1
)

for /f "tokens=2" %%i in ('python --version 2^>^&1') do set "python_version=%%i"
echo [✓] Python version: %python_version%
echo.

REM Create virtual environment
if not exist ".venv" (
    echo [→] Creating virtual environment...
    python -m venv .venv
    if errorlevel 1 (
        echo [X] ERROR: Failed to create virtual environment
        pause
        exit /b 1
    )
    echo [✓] Virtual environment created
) else (
    echo [✓] Virtual environment already exists
)
echo.

REM Activate virtual environment
echo [→] Activating virtual environment...
call .venv\Scripts\activate.bat
if errorlevel 1 (
    echo [X] ERROR: Failed to activate virtual environment
    pause
    exit /b 1
)
echo [✓] Virtual environment activated
echo.

REM Upgrade pip
echo [→] Upgrading pip, setuptools, and wheel...
python -m pip install --upgrade pip setuptools wheel --quiet
if errorlevel 1 (
    echo [X] ERROR: Failed to upgrade pip
    pause
    exit /b 1
)
echo [✓] pip upgraded
echo.

REM Install dependencies
echo [→] Installing dependencies from pyproject.toml...
pip install -e . --quiet
if errorlevel 1 (
    echo [X] ERROR: Failed to install dependencies
    echo.
    echo Try running this command manually for more details:
    echo   pip install -e .
    echo.
    pause
    exit /b 1
)
echo [✓] Dependencies installed
echo.

REM Create .env file from template
if not exist ".env" (
    echo [→] Creating .env file from template...
    if exist ".env.example" (
        copy .env.example .env >nul 2>&1
        echo [✓] .env created from .env.example
    ) else (
        echo [!] WARNING: .env.example not found, could not create .env
    )
) else (
    echo [✓] .env file already exists
)
echo.

REM Create data directories
if not exist "data\images" (
    echo [→] Creating data directories...
    mkdir data\images >nul 2>&1
)
if exist "data\images" (
    echo [✓] Data directories ready: data\images\
) else (
    echo [!] WARNING: Could not create data\images directory
)
echo.

REM Final instructions
echo ╔═══════════════════════════════════════════════════════╗
echo ║   Setup Complete!                                     ║
echo ╚═══════════════════════════════════════════════════════╝
echo.
echo NEXT STEPS:
echo.
echo 1. [IMPORTANT] Edit .env and add your GROQ_API_KEY
echo    - Open .env in a text editor (Notepad, VS Code, etc.)
echo    - Get free API key: https://console.groq.com
echo    - Find the line: GROQ_API_KEY=your_groq_api_key_here
echo    - Replace with your actual key
echo.
echo 2. Run the fact-checker:
echo    - For v1 (traditional):  python main.py
echo    - For v2 (agentic):      python main_v2.py
echo.
echo 3. When prompted, paste an Instagram post URL:
echo    https://www.instagram.com/p/DUDmwcmjFX-/?img_index=1
echo.
echo For detailed information, see:
echo    - README.md (comprehensive documentation)
echo    - QUICK_START.md (quick reference)
echo.

REM Offer to open .env
set /p edit_env="Do you want to edit .env now? (y/n): "
if /i "%edit_env%"=="y" (
    if exist ".env" (
        start notepad .env
    ) else (
        echo [X] .env file not found
    )
)

echo.
echo Setup is complete. You can now run:
echo   python main.py
echo   python main_v2.py
echo.
pause
