"""이 PC의 IMAGE_STORAGE_DIR 사진 중 공유 DB가 참조하는 것만 Supabase Storage로 올린다.

실행: python -m backend.scripts.upload_local_images [--dry-run]
IMAGE_STORAGE_BACKEND=supabase 설정이 필요하다. 로컬 Docker DB에서만 쓰던 사진은 올리지 않는다.
이미 버킷에 있는 키는 덮어쓰지 않고 건너뛰며, 로컬 파일은 지우지 않는다.
"""
import argparse
import sys
from pathlib import Path

from sqlalchemy import text

from backend.app import storage
from backend.app.config import ROOT, settings
from backend.app.db import get_engine

REFERENCED_KEYS = text("""
    SELECT image_path FROM image_uploads
    UNION SELECT storage_key FROM chat_attachments
    UNION SELECT 'community/' || storage_key FROM community_post_images
""")


def main(argv=None):
    parser = argparse.ArgumentParser()
    parser.add_argument('--dry-run', action='store_true', help='올릴 파일 수만 확인')
    args = parser.parse_args(argv)
    if settings.image_storage_backend != 'supabase' or not storage.configured():
        raise SystemExit('IMAGE_STORAGE_BACKEND=supabase and SUPABASE_* settings are required.')
    if not settings.image_storage_dir:
        raise SystemExit('IMAGE_STORAGE_DIR (local photo folder) is required.')
    folder = Path(settings.image_storage_dir)
    folder = folder if folder.is_absolute() else ROOT / folder
    with get_engine().connect() as connection:
        keys = sorted(row[0] for row in connection.execute(REFERENCED_KEYS) if row[0])
    counts = {'uploaded': 0, 'already': 0, 'not_on_this_pc': 0, 'failed': 0}
    for key in keys:
        path = folder / key
        if not path.is_file():
            counts['not_on_this_pc'] += 1
            continue
        if storage.get(key) is not None:
            counts['already'] += 1
            continue
        if args.dry_run:
            counts['uploaded'] += 1
            continue
        try:
            storage.put(key, path.read_bytes(), 'image/png' if path.suffix == '.png' else 'image/jpeg')
            counts['uploaded'] += 1
        except OSError:
            counts['failed'] += 1
    label = 'would upload' if args.dry_run else 'uploaded'
    print(f"{label} {counts['uploaded']}, already in storage {counts['already']}, "
          f"not on this PC {counts['not_on_this_pc']}, failed {counts['failed']}")
    if counts['failed']:
        raise SystemExit(1)


if __name__ == '__main__':
    sys.stdout.reconfigure(encoding='utf-8')
    main()
