import json
import os
import subprocess
import sys
from threading import Lock
from ..config import ROOT

inference_lock = Lock()


def detect_image(path):
    legacy_python = ROOT / '.venv' / ('Scripts/python.exe' if os.name == 'nt' else 'bin/python')
    executable = str(legacy_python) if legacy_python.is_file() else sys.executable
    config_dir = ROOT / '.runtime-logs' / 'ultralytics'
    config_dir.mkdir(parents=True, exist_ok=True)
    with inference_lock:
        result = subprocess.run([executable, str(ROOT / 'backend/app/vision_worker.py'), str(path)],
                                capture_output=True, text=True, encoding='utf-8', errors='replace',
                                timeout=120, cwd=ROOT, env={**os.environ, 'YOLO_CONFIG_DIR': str(config_dir)},
                                creationflags=subprocess.CREATE_NO_WINDOW if os.name == 'nt' else 0)
    if result.returncode:
        raise RuntimeError('YOLO inference failed')
    return json.loads(result.stdout)
