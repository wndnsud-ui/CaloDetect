@echo off
chcp 65001 > nul
setlocal
cd /d "%~dp0"

if not exist ".venv\Scripts\python.exe" (
    echo 가상환경이 없습니다.
    echo 먼저 01_SETUP_AND_RUN.bat 을 실행해 주세요.
    pause
    exit /b 1
)

".venv\Scripts\python.exe" -m streamlit run app.py
