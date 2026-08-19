@echo off
setlocal
cd /d "%~dp0"

if not exist ".venv\Scripts\ourtts-api.exe" (
  echo ourTTS is not installed in .venv yet.
  echo Run this first from PowerShell:
  echo   powershell -ExecutionPolicy Bypass -File .\install-windows.ps1
  pause
  exit /b 1
)

echo.
echo Starting ourTTS Studio...
echo Open http://127.0.0.1:7860/ in your browser if it does not open automatically.
echo Press Ctrl+C here to stop the local server.
echo.

start "" http://127.0.0.1:7860/
".venv\Scripts\ourtts-api.exe"
