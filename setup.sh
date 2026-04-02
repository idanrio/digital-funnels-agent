#!/bin/bash
# ============================================================
# PrimeFlow AI - One-Click Setup Script
# Run this in your terminal:  bash setup.sh
# ============================================================

set -e
echo ""
echo "============================================"
echo "  PrimeFlow AI - Environment Setup"
echo "============================================"
echo ""

# --- Step 1: Install Homebrew ---
if ! command -v brew &> /dev/null; then
    echo "[1/6] Installing Homebrew..."
    /bin/bash -c "$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)"

    # Add brew to PATH for Apple Silicon
    if [ -f /opt/homebrew/bin/brew ]; then
        echo 'eval "$(/opt/homebrew/bin/brew shellenv)"' >> ~/.zprofile
        eval "$(/opt/homebrew/bin/brew shellenv)"
    fi
    echo "  ✅ Homebrew installed"
else
    echo "[1/6] Homebrew already installed ✅"
fi

# --- Step 2: Install Python 3.12 ---
if ! python3.12 --version &> /dev/null 2>&1; then
    echo "[2/6] Installing Python 3.12..."
    brew install python@3.12
    echo "  ✅ Python 3.12 installed"
else
    echo "[2/6] Python 3.12 already installed ✅"
fi

# --- Step 3: Install Node.js ---
if ! command -v node &> /dev/null; then
    echo "[3/6] Installing Node.js..."
    brew install node
    echo "  ✅ Node.js installed"
else
    echo "[3/6] Node.js already installed ✅"
fi

# --- Step 4: Create virtual environment ---
echo "[4/6] Creating Python virtual environment..."
cd "$(dirname "$0")"
python3.12 -m venv venv
source venv/bin/activate
echo "  ✅ Virtual environment created"

# --- Step 5: Install Python dependencies ---
echo "[5/6] Installing Python dependencies..."
pip install --upgrade pip
pip install -r requirements.txt
echo "  ✅ Python dependencies installed"

# --- Step 6: Install Playwright browsers ---
echo "[6/6] Installing Playwright browsers (for browser automation)..."
playwright install chromium
echo "  ✅ Playwright Chromium installed"

# --- Create .env from example ---
if [ ! -f .env ]; then
    cp .env.example .env
    echo ""
    echo "============================================"
    echo "  ⚠️  IMPORTANT: Edit your .env file!"
    echo "============================================"
    echo ""
    echo "  Open this file and fill in your keys:"
    echo "  $(pwd)/.env"
    echo ""
    echo "  You need:"
    echo "  1. ANTHROPIC_API_KEY=sk-ant-xxxxx"
    echo "  2. GHL_API_KEY=your-key"
    echo "  3. GHL_LOCATION_ID=your-location-id"
    echo ""
fi

echo ""
echo "============================================"
echo "  ✅ Setup Complete!"
echo "============================================"
echo ""
echo "  Next steps:"
echo "  1. Edit .env with your API keys"
echo "  2. Run: source venv/bin/activate"
echo "  3. Run: python -m server.main"
echo ""
echo "  Python: $(python3.12 --version)"
echo "  Node:   $(node --version 2>/dev/null || echo 'pending')"
echo "  Path:   $(pwd)"
echo ""
