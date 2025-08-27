@echo off
set PORT=%1
if "%PORT%"=="" set PORT=11434

where ollama >nul 2>nul
if %errorlevel% neq 0 (
  echo ollama not found
  exit /b 1
)

set OLLAMA_PORT=%PORT%
start "" /b ollama serve
