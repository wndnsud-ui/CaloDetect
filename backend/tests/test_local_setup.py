"""Exercise private settings reuse in isolated fake clone directories (no Docker/DB)."""
import os
import shutil
import subprocess
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]


@pytest.mark.skipif(os.name != 'nt', reason='Windows PowerShell local setup')
def test_reclone_preserves_private_settings_without_touching_db(tmp_path):
    env = dict(os.environ, LOCALAPPDATA=str(tmp_path / 'private'))

    def clone(name):
        root = tmp_path / name
        (root / 'scripts').mkdir(parents=True)
        shutil.copyfile(ROOT / 'scripts/setup_local.ps1', root / 'scripts/setup_local.ps1')
        shutil.copyfile(ROOT / '.env.example', root / '.env.example')
        return root

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
