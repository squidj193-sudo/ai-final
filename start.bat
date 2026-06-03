@echo off
title AI Research Assistant Launcher
echo ===================================================
echo   Starting AI Research Assistant Agent...
echo ===================================================

:: Start Backend FastAPI
echo Launching Backend FastAPI Server...
start "Backend - FastAPI" cmd /c "cd backend && python main.py"

:: Start Frontend Vite
echo Launching Frontend Vite Development Server...
start "Frontend - Vite" cmd /c "cd frontend && npm run dev"

echo.
echo ===================================================
echo   Servers are launching!
echo   - Backend: http://127.0.0.1:8000
echo   - Frontend: http://localhost:5173
echo   (Press any key to close this launcher console)
echo ===================================================
pause
