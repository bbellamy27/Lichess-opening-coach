#!/bin/bash

# Lichess Opening Coach - Setup and Run Script for Mac/Linux

echo "==================================================="
echo "   Lichess Opening Coach - Setup & Run (Mac/Linux)"
echo "==================================================="

# 1. Check for Python
if ! command -v python3 &> /dev/null; then
    echo "[ERROR] Python 3 is not installed."
    echo "Please install Python 3 using your package manager (e.g., brew install python3, sudo apt install python3)."
    exit 1
fi

# 2. Create Virtual Environment if it doesn't exist
if [ ! -d ".venv" ]; then
    echo "[INFO] Creating virtual environment..."
    python3 -m venv .venv
else
    echo "[INFO] Virtual environment found."
fi

# 3. Activate Virtual Environment
source .venv/bin/activate

# 4. Install Dependencies
echo "[INFO] Checking dependencies..."
pip install -r requirements.txt

# 5. Check for Stockfish
if [ ! -f "stockfish" ] && ! command -v stockfish &> /dev/null; then
    echo "[WARNING] Stockfish engine not found in project folder or PATH."
    echo "Analysis features might be limited."
    echo "To fix: Install stockfish (brew install stockfish / sudo apt install stockfish)"
    echo "Or download the binary and place it in this folder named 'stockfish'."
    read -p "Press Enter to continue anyway..."
fi

# 6. Run the App
echo "[INFO] Starting Lichess Opening Coach..."
streamlit run app.py
