#!/usr/bin/env bash
# Linux/macOS 기존 Streamlit 최초 설치/실행. 사용할 Python을 찾고 가상환경·패키지·데이터 검사를 준비한다.
# 설치·검사 명령이 실패하면 다음 실행 단계를 진행하지 않는다.
set -e
cd "$(dirname "$0")"

echo "============================================================"
echo " CaloDetect Streamlit - 최초 설치 + 실행"
echo "============================================================"

PYTHON_CMD=""
if command -v python3 >/dev/null 2>&1; then
  PYTHON_CMD="python3"
elif command -v python >/dev/null 2>&1; then
  PYTHON_CMD="python"
else
  echo "[오류] Python 3.10 이상을 설치해 주세요."
  exit 1
fi

if [ ! -f ".venv/bin/python" ]; then
  echo "[1/4] 가상환경 생성"
  "$PYTHON_CMD" -m venv .venv
else
  echo "[1/4] 기존 가상환경 사용"
fi

echo "[2/4] pip 업데이트"
.venv/bin/python -m pip install --upgrade pip

echo "[3/4] 패키지 설치"
.venv/bin/python -m pip install -r requirements.txt

echo "[4/4] 모델 및 영양 컬럼 검증"
# 모델·YAML·CSV 연결을 검사한 뒤 앱 실행으로 진행한다.
.venv/bin/python validate_data.py

echo "앱 실행: http://localhost:8501"
# 준비한 Python 환경에서 기존 Streamlit 앱을 시작한다.
.venv/bin/python -m streamlit run app.py
