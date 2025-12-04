#!/bin/bash

# RepoGuard Scanner - Quick Start Script

echo "🚀 RepoGuard Scanner - Quick Start"
echo "=================================="
echo ""

# Check if Node.js is installed
if ! command -v node &> /dev/null; then
    echo "❌ Node.js is not installed. Please install Node.js first."
    echo "Visit: https://nodejs.org/"
    exit 1
fi

echo "✅ Node.js detected: $(node --version)"
echo ""

# Check if Python is installed
if ! command -v python &> /dev/null; then
    echo "❌ Python is not installed. Please install Python first."
    echo "Visit: https://www.python.org/"
    exit 1
fi

echo "✅ Python detected: $(python --version)"
echo ""

# Install backend dependencies
echo "📦 Installing backend dependencies..."
cd backend
pip install -r requirements.txt
echo "✅ Backend dependencies installed"
echo ""

# Go back to root
cd ..

# Install frontend dependencies
echo "📦 Installing frontend dependencies..."
cd frontend
npm install
echo "✅ Frontend dependencies installed"
echo ""

# Go back to root
cd ..

echo ""
echo "🎉 Setup complete!"
echo ""
echo "📝 Next steps:"
echo ""
echo "1. Start the backend server (in one terminal):"
echo "   cd backend"
echo "   python main.py"
echo ""
echo "2. Start the frontend dev server (in another terminal):"
echo "   cd frontend"
echo "   npm run dev"
echo ""
echo "3. Open browser and go to:"
echo "   http://localhost:5173"
echo ""
echo "🔗 Backend will be running at: http://localhost:8000"
echo ""
