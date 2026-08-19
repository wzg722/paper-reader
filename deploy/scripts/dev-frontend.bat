@echo off
cd /d %~dp0\..\..\frontend
call npm install
echo Frontend: http://127.0.0.1:5173
call npm run dev
