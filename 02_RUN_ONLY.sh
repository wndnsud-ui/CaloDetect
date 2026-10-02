#!/usr/bin/env bash
set -e
cd "$(dirname "$0")"
if [ ! -f ".venv/bin/python" ]; then
  echo "먼저 ./01_SETUP_AND_RUN.sh 를 실행해 주세요."
  exit 1
fi
.venv/bin/python -m streamlit run app.py
