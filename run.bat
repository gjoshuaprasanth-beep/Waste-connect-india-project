@echo off
setlocal
echo ===============================================================
echo  WasteConnect India - Full-Stack Waste Coordination Platform
echo  React (Vite) + Tailwind CSS + Node.js Express + Drizzle ORM
echo ===============================================================

set "PORTABLE_NODE=C:\Users\PRASANTH\.gemini\antigravity\scratch\node-v20.18.0-win-x64"
if exist "%PORTABLE_NODE%\node.exe" (
    set "PATH=%PORTABLE_NODE%;%PATH%"
)

echo Starting backend server and client SPA on http://localhost:5000 ...
set PORT=5000
set RUN_SERVER=true
node server/index.js
pause
