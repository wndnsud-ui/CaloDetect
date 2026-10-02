import subprocess
import sys

for command in [
    [sys.executable, '-m', 'alembic', '-c', 'backend/alembic.ini', 'upgrade', 'head'],
    [sys.executable, '-m', 'backend.scripts.seed_foods'],
    [sys.executable, '-m', 'uvicorn', 'backend.app.main:app', '--host', '0.0.0.0', '--port', '8000'],
]:
    subprocess.run(command, check=True)
