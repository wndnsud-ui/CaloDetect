import subprocess
import sys

from backend.scripts.seed_local_test_account import local_test_account_enabled

for command in [
    [sys.executable, '-m', 'alembic', '-c', 'backend/alembic.ini', 'upgrade', 'head'],
    [sys.executable, '-m', 'backend.scripts.seed_foods'],
]:
    subprocess.run(command, check=True)
if local_test_account_enabled():
    subprocess.run([sys.executable, '-m', 'backend.scripts.seed_local_test_account'], check=True)

subprocess.run([sys.executable, '-m', 'uvicorn', 'backend.app.main:app',
                '--host', '0.0.0.0', '--port', '8000'], check=True)
