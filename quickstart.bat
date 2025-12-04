@echo off
REM RepoGuard Scanner - Quick Start Script for Windows

echo.
echo 🚀 RepoGuard Scanner - Quick Start
echo ==================================
echo.

REM Check if Node.js is installed
where node >nul 2>nul
if %ERRORLEVEL% NEQ 0 (
    echo ❌ Node.js is not installed. Please install Node.js first.
    echo Visit: https://nodejs.org/
    pause
    exit /b 1
)

for /f "tokens=*" %%i in ('node --version') do set NODE_VERSION=%%i
echo ✅ Node.js detected: %NODE_VERSION%
echo.

REM Check if Python is installed
where python >nul 2>nul
if %ERRORLEVEL% NEQ 0 (
    echo ❌ Python is not installed. Please install Python first.
    echo Visit: https://www.python.org/
    pause
    exit /b 1
)

for /f "tokens=*" %%i in ('python --version') do set PYTHON_VERSION=%%i
echo ✅ Python detected: %PYTHON_VERSION%
echo.

REM Install backend dependencies
echo 📦 Installing backend dependencies...
cd backend
pip install -r requirements.txt
if %ERRORLEVEL% NEQ 0 (
    echo ❌ Failed to install backend dependencies
    pause
    exit /b 1
)
echo ✅ Backend dependencies installed
echo.

REM Go back to root
cd ..

REM Install frontend dependencies
echo 📦 Installing frontend dependencies...
cd frontend
call npm install
if %ERRORLEVEL% NEQ 0 (
    echo ❌ Failed to install frontend dependencies
    pause
    exit /b 1
)
echo ✅ Frontend dependencies installed
echo.

REM Go back to root
cd ..

echo.
echo 🎉 Setup complete!
echo.
echo 📝 Next steps:
echo.
echo 1. Start the backend server (in one terminal)
echo    cd backend
echo    python main.py
echo.
echo 2. Start the frontend dev server (in another terminal)
echo    cd frontend
echo    npm run dev
echo.
echo 3. Open browser and go to:
echo    http://localhost:5173
echo.
echo 🔗 Backend will be running at: http://localhost:8000
echo.
pause
