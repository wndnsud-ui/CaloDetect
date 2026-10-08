#!/usr/bin/env bash
# Linux/macOS 기존 Streamlit 재실행. 기존 가상환경을 사용하고 미설치 상태는 최초 설치 스크립트로 연결한다.
# 설치·검사 명령이 실패하면 다음 실행 단계를 진행하지 않는다.
set -e
cd "$(dirname "$0")"
if [ ! -f ".venv/bin/python" ]; then
  echo "먼저 ./01_SETUP_AND_RUN.sh 를 실행해 주세요."
  exit 1
fi
# 준비한 Python 환경에서 기존 Streamlit 앱을 시작한다.
.venv/bin/python -m streamlit run app.py
