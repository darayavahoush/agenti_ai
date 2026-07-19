#!/bin/bash

# Setup script for Vaaksudhi project on Linux/Mac

echo "========================================"
echo "  Vaaksudhi Project Setup (Linux/Mac)"
echo "========================================"
echo ""

# Check if Python is installed
if ! command -v python3 &> /dev/null; then
    echo "ERROR: Python 3 is not installed"
    echo "Please install Python 3.10 or higher"
    exit 1
fi

# Check if Node.js is installed
if ! command -v node &> /dev/null; then
    echo "ERROR: Node.js is not installed"
    echo "Please install Node.js 18 or higher from https://nodejs.org/"
    exit 1
fi

echo "[1/7] Creating Python virtual environment..."
python3 -m venv venv
if [ $? -ne 0 ]; then
    echo "ERROR: Failed to create virtual environment"
    exit 1
fi

echo "[2/7] Activating virtual environment..."
source venv/bin/activate
if [ $? -ne 0 ]; then
    echo "ERROR: Failed to activate virtual environment"
    exit 1
fi

echo "[3/7] Installing Python dependencies..."
cd backend
pip install --upgrade pip
pip install -r requirements.txt
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
echo "   source ../venv/bin/activate"
echo "   uvicorn app.main:app --reload"
echo ""
echo "2. Frontend (in new terminal):"
echo "   cd frontend"
echo "   npm run dev"
echo ""
echo "Note: Make sure PostgreSQL is running and database 'vaaksudhi' exists"
echo ""
