@echo off
chcp 65001 > nul
setlocal
cd /d "%~dp0"

echo ============================================================
echo  CaloDetect Streamlit - 최초 설치 + 실행
echo ============================================================
echo.

if exist "%LocalAppData%\Python\pythoncore-3.14-64\python.exe" (
    set "PYTHON_CMD="%LocalAppData%\Python\pythoncore-3.14-64\python.exe""
) else (
    where py >nul 2>nul
    if errorlevel 1 (
        set "PYTHON_CMD=python"
    ) else (
        set "PYTHON_CMD=py -3"
    )
)

if not exist ".venv\Scripts\python.exe" (
    echo [1/4] 가상환경 생성 중...
    %PYTHON_CMD% -m venv .venv
    if errorlevel 1 goto :error
) else (
    echo [1/4] 기존 가상환경 사용
)

echo [2/4] pip 업데이트 중...
".venv\Scripts\python.exe" -m pip install --upgrade pip
if errorlevel 1 goto :error

echo [3/4] 필요한 패키지 설치 중...
".venv\Scripts\python.exe" -m pip install -r requirements.txt
if errorlevel 1 goto :error

echo [4/4] 모델 및 영양 컬럼 검증 중...
".venv\Scripts\python.exe" validate_data.py
if errorlevel 1 goto :error

echo.
echo ============================================================
echo  앱을 시작합니다.
echo  브라우저가 자동으로 열리지 않으면:
echo  http://localhost:8501
echo ============================================================
echo.

".venv\Scripts\python.exe" -m streamlit run app.py

exit /b 0

:error
echo.
echo [오류] 설치 또는 실행 과정에서 문제가 발생했습니다.
echo 위 오류 메시지를 복사해서 ChatGPT에 보내 주세요.
pause
exit /b 1
