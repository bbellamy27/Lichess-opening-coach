#!/bin/bash

echo "=========================================="
echo "  Chess Improvement Coach - Setup Script"
echo "=========================================="

# 1. Check for Python
if ! command -v python3 &> /dev/null; then
    echo "[ERROR] Python 3 is not installed."
    echo "Please install Python 3 using your package manager (brew, apt, etc.)"
    exit 1
fi

# 2. Create Virtual Environment
if [ ! -d ".venv" ]; then
    echo "[INFO] Creating virtual environment..."
    python3 -m venv .venv
fi

# 3. Activate and Install
echo "[INFO] Activating virtual environment..."
source .venv/bin/activate

echo "[INFO] Installing dependencies..."
pip install -r requirements.txt

# 4. Run App
echo "[INFO] Launching App..."
echo ""
streamlit run app.py
