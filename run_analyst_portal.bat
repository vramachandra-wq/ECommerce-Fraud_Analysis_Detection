@echo off
title Metro Cart Analyst Portal
cd /d "%~dp0"

echo.
echo  Metro Cart Analyst Portal (no Node.js required)
echo  ================================================
echo.

where python >nul 2>&1
if errorlevel 1 (
  echo ERROR: Python not found in PATH.
  pause
  exit /b 1
)

echo Starting API + web portal on http://127.0.0.1:8000/portal/
echo Press Ctrl+C to stop.
echo.

start "" "http://127.0.0.1:8000/portal/"
python -m uvicorn api.main:app --host 127.0.0.1 --port 8000 --reload
