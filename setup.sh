#!/usr/bin/env bash
# Quick setup script for Instagram Fact-Checker

set -e

echo "╔════════════════════════════════════════════════════════╗"
echo "║   Instagram Fact-Checker — Setup Script               ║"
echo "╚════════════════════════════════════════════════════════╝"
echo ""

# Check Python version
python_version=$(python3 --version 2>&1 | awk '{print $2}')
echo "[✓] Python version: $python_version"

if ! [[ "$python_version" =~ ^3\.1[3-9] ]]; then
    echo "[✗] ERROR: Python 3.13+ required. Current: $python_version"
    exit 1
fi

# Create virtual environment
if [ ! -d ".venv" ]; then
    echo "[→] Creating virtual environment..."
    python3 -m venv .venv
    echo "[✓] Virtual environment created"
else
    echo "[✓] Virtual environment already exists"
fi

# Activate virtual environment
echo "[→] Activating virtual environment..."
source .venv/bin/activate

# Upgrade pip
echo "[→] Upgrading pip..."
pip install --upgrade pip setuptools wheel > /dev/null 2>&1

# Install dependencies
echo "[→] Installing dependencies from pyproject.toml..."
pip install -e . > /dev/null 2>&1
echo "[✓] Dependencies installed"

# Create .env file if it doesn't exist
if [ ! -f ".env" ]; then
    echo "[→] Creating .env file from template..."
    cp .env.example .env
    echo "[!] IMPORTANT: Edit .env and add your GROQ_API_KEY"
    echo "    Get it free at: https://console.groq.com"
else
    echo "[✓] .env file already exists"
fi

# Create data directory
mkdir -p data/images
echo "[✓] Data directories created"

echo ""
echo "╔════════════════════════════════════════════════════════╗"
echo "║   Setup Complete!                                      ║"
echo "╚════════════════════════════════════════════════════════╝"
echo ""
echo "Next steps:"
echo "  1. Edit .env and add your GROQ_API_KEY"
echo "  2. Run: python main.py (v1) or python main_v2.py (v2)"
echo "  3. Provide an Instagram post URL when prompted"
echo ""
echo "For detailed setup: see README.md"
echo ""
