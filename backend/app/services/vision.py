# 기존 YOLO 환경을 재사용해 추론 worker를 실행하고 JSON 결과를 읽는 서버 서비스.
# 프로세스 내부 잠금으로 추론을 직렬화하며 시간 제한·종료 코드를 검사한다.
import json
import os
import subprocess
import sys
from threading import Lock
from ..config import ROOT

inference_lock = Lock()


# 기존 .venv Python이 있으면 재사용하고 추론 worker를 120초 제한으로 실행해 JSON을 반환한다.
def detect_image(path):
    # 기존 Streamlit/YOLO 가상환경 경로를 OS별로 찾는다. 없으면 Backend를 실행한 Python을 사용한다.
    legacy_python = ROOT / '.venv' / ('Scripts/python.exe' if os.name == 'nt' else 'bin/python')
    executable = str(legacy_python) if legacy_python.is_file() else sys.executable
    config_dir = ROOT / '.runtime-logs' / 'ultralytics'
    config_dir.mkdir(parents=True, exist_ok=True)
    # 이 서버 프로세스에서 여러 요청이 동시에 모델 worker를 실행하지 않게 한다. 여러 worker 전체를 묶는 전역 잠금은 아니다.
    with inference_lock:
        result = subprocess.run([executable, str(ROOT / 'backend/app/vision_worker.py'), str(path)],
                                capture_output=True, text=True, encoding='utf-8', errors='replace',
                                timeout=120, cwd=ROOT, env={**os.environ, 'YOLO_CONFIG_DIR': str(config_dir)},
                                creationflags=subprocess.CREATE_NO_WINDOW if os.name == 'nt' else 0)
    # worker 실패를 먼저 검사해 오류 출력이 정상 JSON 결과로 처리되지 않게 한다.
    if result.returncode:
        raise RuntimeError('YOLO inference failed')
    return json.loads(result.stdout)
