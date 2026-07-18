#!/bin/bash
# Start the backend server with full logging

echo "🚀 Starting VaakSuddhi Backend Server..."
echo "📋 Logs will be displayed below..."

cd "$(dirname "$0")"

# Activate virtual environment if it exists
if [ -d ".venv" ]; then
    echo "🔧 Activating virtual environment..."
    source .venv/bin/activate
fi

# Start server with full logging
uvicorn app.main:app --host 0.0.0.0 --port 8000 --log-level debug --reload
