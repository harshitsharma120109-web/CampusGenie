@echo off
title CampusGenie Node.js Server
echo ========================================================
echo   Starting CampusGenie - Node.js Express Backend
echo   SkillUp Hackathon with IBM SkillsBuild
echo ========================================================
echo.

set PATH=C:\Program Files\nodejs;%PATH%

where node >nul 2>nul
if %errorlevel% neq 0 (
    echo [ERROR] Node.js not found in PATH!
    pause
    exit /b 1
)

echo [1/2] Verifying Node packages...
if not exist "node_modules" (
    echo Installing dependencies...
    call npm install
)

echo [2/2] Launching CampusGenie Node.js Server on port 5000...
start "" http://localhost:5000
node server.js
pause
