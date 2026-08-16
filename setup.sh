#!/bin/bash

# Setup script for Vaaksudhi project on Linux/Mac

echo "========================================"
echo "  Vaaksudhi Project Setup (Linux/Mac)"
echo "========================================"
echo ""

# Check if uv is installed
if ! command -v uv &> /dev/null; then
    echo "ERROR: uv is not installed"
    echo "Please install uv with: pip install uv"
    echo "Or visit https://github.com/astral-sh/uv"
    exit 1
fi

# Check if Node.js is installed
if ! command -v node &> /dev/null; then
    echo "ERROR: Node.js is not installed"
    echo "Please install Node.js 18 or higher from https://nodejs.org/"
    exit 1
fi

echo "[1/7] Creating Python virtual environment with uv..."
uv venv
if [ $? -ne 0 ]; then
    echo "ERROR: Failed to create virtual environment"
    exit 1
fi

echo "[2/7] Activating virtual environment..."
source .venv/bin/activate
if [ $? -ne 0 ]; then
    echo "ERROR: Failed to activate virtual environment"
    exit 1
fi

echo "[3/7] Installing Python dependencies with uv..."
cd backend
uv pip install -r requirements.txt
if [ $? -ne 0 ]; then
    echo "ERROR: Failed to install Python dependencies"
    exit 1
fi

echo "[4/7] Setting up environment file..."
if [ ! -f .env ]; then
    cp .env.example .env
    echo "Created .env file from template"
    echo "Please edit backend/.env with your database credentials"
else
    echo ".env file already exists"
fi

echo "[5/7] Downloading NLTK data..."
python -c "import nltk; nltk.download('averaged_perceptron_tagger_eng'); nltk.download('averaged_perceptron_tagger'); nltk.download('cmudict'); nltk.download('punkt')"

echo "[6/7] Installing Node.js dependencies..."
cd ../frontend
npm install
if [ $? -ne 0 ]; then
    echo "ERROR: Failed to install Node.js dependencies"
    exit 1
fi

echo "[7/7] Setup complete!"
echo ""
echo "========================================"
echo "  Setup Complete!"
echo "========================================"
echo ""
echo "To run the project:"
echo ""
echo "1. Backend:"
echo "   cd backend"
echo "   source ../.venv/bin/activate"
echo "   uvicorn app.main:app --reload"
echo ""
echo "2. Frontend (in new terminal):"
echo "   cd frontend"
echo "   npm run dev"
echo ""
echo "Note: Make sure PostgreSQL is running and database 'vaaksudhi' exists"
echo ""
