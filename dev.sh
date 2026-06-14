#!/usr/bin/env bash
# Development server that runs both npm watch and mkdocs serve

set -e

echo "🚀 Starting development servers..."
echo ""

# Check if dependencies are installed
if [ ! -d "node_modules" ]; then
    echo "📦 Installing npm dependencies..."
    npm install
fi

if [ ! -d ".venv" ]; then
    echo "🐍 Installing Python dependencies..."
    uv sync
fi

# Build React component once before starting
echo "⚛️  Building React component..."
npm run build

echo ""
echo "🔧 Starting watch processes..."
echo "  - React build (watch mode)"
echo "  - MkDocs serve (http://localhost:8000)"
echo ""

# Run both processes in parallel
trap 'kill 0' EXIT
npm run dev &
uv run mkdocs serve &
wait
