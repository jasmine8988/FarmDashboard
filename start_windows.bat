@echo off
REM Windows 版啟動腳本（取代 Linux 用的 startup.sh / tmux）
REM 同時啟動 Dashboard 網站與 DA，關閉此視窗即停止
cd /d "%~dp0"
"%~dp0venv\Scripts\python.exe" server.py
pause
