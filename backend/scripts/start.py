# 컨테이너 Backend 시작 진입점. DB migration·음식 seed·허용된 로컬 테스트 계정을 준비한 뒤 서버를 실행한다.
import subprocess
import sys

from backend.scripts.seed_local_test_account import local_test_account_enabled

# 같은 Python으로 migration 후 음식 seed를 순서대로 실행한다. check=True라 준비 실패 시 서버를 시작하지 않는다.
for command in [
    [sys.executable, '-m', 'alembic', '-c', 'backend/alembic.ini', 'upgrade', 'head'],
    [sys.executable, '-m', 'backend.scripts.seed_foods'],
]:
    subprocess.run(command, check=True)
if local_test_account_enabled():
    subprocess.run([sys.executable, '-m', 'backend.scripts.seed_local_test_account'], check=True)

# 모든 준비가 성공한 후 컨테이너 외부 연결을 받을 0.0.0.0:8000에서 API를 실행한다.
subprocess.run([sys.executable, '-m', 'uvicorn', 'backend.app.main:app',
                '--host', '0.0.0.0', '--port', '8000'], check=True)
