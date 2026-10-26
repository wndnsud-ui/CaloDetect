# 업로드 사진 저장소. 키(예: 'abc.jpg', 'community/xyz.png')로 저장·조회·삭제한다.
# IMAGE_STORAGE_BACKEND=local은 IMAGE_STORAGE_DIR 폴더, supabase는 Supabase Storage 비공개 버킷을 쓴다.
# 접근 권한은 호출하는 라우트가 먼저 검사한다. 버킷은 공개하지 않고 서버 키로만 읽는다.
import logging
import os
import tempfile
from contextlib import contextmanager
from functools import lru_cache
from pathlib import Path
from urllib.parse import quote

import httpx

from .config import ROOT, settings

log = logging.getLogger(__name__)


# 현재 설정으로 사진 저장이 가능한지. 미설정이면 호출자가 503 안내를 반환한다.
def configured():
    if settings.image_storage_backend == 'supabase':
        return bool(settings.supabase_url and settings.supabase_service_role_key and settings.supabase_storage_bucket)
    return bool(settings.image_storage_dir)


def _local_path(key):
    folder = Path(settings.image_storage_dir or '')
    folder = (folder if folder.is_absolute() else ROOT / folder).resolve()
    path = (folder / key).resolve()
    # 서버가 만든 키만 쓰지만 폴더 밖 경로는 거부한다.
    if not path.is_relative_to(folder) or path == folder:
        raise ValueError('Invalid storage key')
    return path


@lru_cache
def _client():
    key = settings.supabase_service_role_key
    return httpx.Client(timeout=30, headers={'apikey': key, 'Authorization': f'Bearer {key}'})


def _object_url(key):
    base = settings.supabase_url.rstrip('/')
    return f'{base}/storage/v1/object/{settings.supabase_storage_bucket}/{quote(key)}'


# 새 키로 저장한다. 같은 키가 이미 있으면 덮어쓰지 않고 오류를 낸다.
def put(key, data, content_type='image/jpeg'):
    if settings.image_storage_backend == 'supabase':
        response = _client().post(_object_url(key), content=data,
                                  headers={'Content-Type': content_type, 'x-upsert': 'false'})
        if response.status_code >= 300:
            raise OSError(f'Storage upload failed ({response.status_code})')
        return
    path = _local_path(key)
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_name(path.name + '.part')
    # 임시 파일을 완성한 뒤 이름을 바꿔 반쯤 쓴 파일이 조회되지 않게 한다.
    with temporary.open('wb') as output:
        output.write(data)
    temporary.replace(path)


# 저장된 바이트를 반환한다. 없거나 읽을 수 없으면 None.
def get(key):
    if settings.image_storage_backend == 'supabase':
        try:
            response = _client().get(_object_url(key))
        except httpx.HTTPError:
            log.warning('storage download failed')
            return None
        if response.status_code == 200:
            return response.content
        if response.status_code not in (400, 404):
            log.warning('storage download status %s', response.status_code)
        return None
    try:
        path = _local_path(key)
    except ValueError:
        return None
    return path.read_bytes() if path.is_file() else None


# 실패 정리용 삭제. 없는 키는 무시한다.
def delete(key):
    if settings.image_storage_backend == 'supabase':
        try:
            _client().request('DELETE', f'{settings.supabase_url.rstrip("/")}/storage/v1/object/'
                              f'{settings.supabase_storage_bucket}', json={'prefixes': [key]})
        except httpx.HTTPError:
            log.warning('storage delete failed')
        return
    try:
        _local_path(key).unlink(missing_ok=True)
    except ValueError:
        pass


# YOLO worker처럼 파일 경로가 필요한 처리용. local은 원본 경로, supabase는 내려받은 임시 파일을 준다.
# data를 넘기면 다시 내려받지 않고 그 바이트로 임시 파일을 만든다.
@contextmanager
def local_file(key, data=None):
    if settings.image_storage_backend != 'supabase':
        yield _local_path(key)
        return
    if data is None:
        data = get(key)
        if data is None:
            raise FileNotFoundError(key)
    handle, name = tempfile.mkstemp(suffix=Path(key).suffix or '.jpg')
    try:
        with os.fdopen(handle, 'wb') as output:
            output.write(data)
        yield Path(name)
    finally:
        Path(name).unlink(missing_ok=True)
