@echo off
REM Windows 기존 Streamlit 재실행. 준비된 가상환경을 사용하고 환경이 없으면 최초 설치 스크립트로 연결한다.
chcp 65001 > nul
setlocal
cd /d "%~dp0"

if not exist ".venv\Scripts\python.exe" (
    echo 가상환경이 없습니다.
    echo 먼저 01_SETUP_AND_RUN.bat 을 실행해 주세요.
    pause
    exit /b 1
)

REM 준비한 Python 환경에서 기존 Streamlit 앱을 시작한다.
".venv\Scripts\python.exe" -m streamlit run app.py
