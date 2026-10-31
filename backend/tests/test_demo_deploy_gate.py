import os
from pathlib import Path
import subprocess
import sys
import pytest

@pytest.mark.parametrize('enabled,expected', [('false', False), ('true', True)])
def test_production_demo_requires_explicit_flag(enabled, expected):
    env = {**os.environ, 'APP_ENV': 'production', 'LOCAL_TEST_SIGNUP': 'false',
           'FRONTEND_ORIGIN': 'https://calo-detect.vercel.app', 'TEST_ACCOUNT_DEMO_ENABLED': enabled}
    code = "from backend.app.main import app; print('/dev/demo/status' in app.openapi()['paths'])"
    result = subprocess.run([sys.executable, '-c', code], cwd=str(Path(__file__).resolve().parents[2]), env=env, capture_output=True, text=True, check=True)
    assert result.stdout.strip() == str(expected)
