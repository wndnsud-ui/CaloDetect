# 회귀 테스트: local_setup 관련 기능의 성공·오류·권한 조건을 검사한다.
# fixture/monkeypatch로 테스트 의존성을 준비하며 실제 외부 인증·메일 발송 검증과는 구분한다.
"""Exercise private settings reuse in isolated fake clone directories (no Docker/DB)."""
import os
import shutil
import subprocess
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]


# 회귀 검사: 재클론 · 보존 · 비공개 · 설정 · DB.
# 아래 요청·준비 데이터와 assert로 성공 결과 및 실패 시 제한이 유지되는지 확인한다.
@pytest.mark.skipif(os.name != 'nt', reason='Windows PowerShell local setup')
def test_reclone_preserves_private_settings_without_touching_db(tmp_path):
    env = dict(os.environ, LOCALAPPDATA=str(tmp_path / 'private'))

    # clone: 이 파일의 테스트용 환경·입력 또는 대체 클라이언트를 준비한다. 외부 기능과 분리된 검사에 사용한다.
    def clone(name):
        root = tmp_path / name
        (root / 'scripts').mkdir(parents=True)
        shutil.copyfile(ROOT / 'scripts/setup_local.ps1', root / 'scripts/setup_local.ps1')
        shutil.copyfile(ROOT / '.env.example', root / '.env.example')
        return root

    # setup: 이 파일의 테스트용 환경·입력 또는 대체 클라이언트를 준비한다. 외부 기능과 분리된 검사에 사용한다.
    def setup(root):
        result = subprocess.run(['powershell.exe', '-NoProfile', '-NonInteractive',
            '-ExecutionPolicy', 'Bypass', '-File', str(root / 'scripts/setup_local.ps1'),
            '-SettingsOnly'], env=env, capture_output=True, text=True)
        assert result.returncode == 0, result.stderr
        return (root / '.env').read_text(encoding='utf-8-sig')

    first = clone('first')
    config = setup(first)
    assert 'APP_ENV=development' in config
    assert '\nOAUTH_STATE_SECRET=' in config
    assert '\nPASSWORD_RESET_SECRET=' in config
    assert '\nDATABASE_URL_DOCKER=' in config
    # Simulate private credentials and approved local consent added through the IDE.
    with (first / '.env').open('a', encoding='utf-8') as file:
        file.write('\nGOOGLE_CLIENT_SECRET=test-private-client-secret\n'
                   'SERVICE_CONSENT_TEXT=test-private-consent\n'
                   'SMTP_USERNAME=test-private-sender@example.com\n'
                   'SMTP_FROM=test-private-sender@example.com\n'
                   'SMTP_PASSWORD=test-private-app-password\n')
    saved = setup(first)
    assert setup(first) == saved
    second = clone('second')
    assert setup(second) == saved
    assert (tmp_path / 'private/CaloDetect/local.env').read_text(encoding='utf-8-sig') == saved
