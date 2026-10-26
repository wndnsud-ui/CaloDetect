# 사진 저장소 local/supabase 동작. supabase는 httpx MockTransport로 흉내 내며 실제 버킷에 접속하지 않는다.
import httpx
import pytest

from backend.app import storage
from backend.app.config import settings


def test_local_roundtrip_and_traversal(monkeypatch, tmp_path):
    monkeypatch.setattr(settings, 'image_storage_dir', str(tmp_path))
    assert storage.configured()
    storage.put('community/a.jpg', b'abc')
    assert (tmp_path / 'community' / 'a.jpg').read_bytes() == b'abc'
    assert not list((tmp_path / 'community').glob('*.part'))
    assert storage.get('community/a.jpg') == b'abc'
    with storage.local_file('community/a.jpg') as path:
        assert path == (tmp_path / 'community' / 'a.jpg').resolve()
    storage.delete('community/a.jpg')
    assert storage.get('community/a.jpg') is None
    assert storage.get('../outside.jpg') is None
    with pytest.raises(ValueError):
        storage.put('../outside.jpg', b'x')


def test_local_requires_folder(monkeypatch):
    monkeypatch.setattr(settings, 'image_storage_dir', None)
    assert not storage.configured()


@pytest.fixture
def fake_supabase(monkeypatch):
    objects, calls = {}, []

    def handler(request):
        calls.append(request)
        assert request.headers['apikey'] == 'secret' and request.headers['authorization'] == 'Bearer secret'
        prefix = '/storage/v1/object/bucket'
        if request.method == 'DELETE':
            import json
            for key in json.loads(request.content)['prefixes']:
                objects.pop(key, None)
            return httpx.Response(200, json=[])
        key = request.url.path.removeprefix(prefix + '/')
        if request.method == 'POST':
            if key in objects:
                return httpx.Response(400, json={'error': 'Duplicate'})
            objects[key] = request.content
            return httpx.Response(200, json={'Key': key})
        if key in objects:
            return httpx.Response(200, content=objects[key])
        return httpx.Response(400, json={'error': 'not_found'})

    monkeypatch.setattr(settings, 'image_storage_backend', 'supabase')
    monkeypatch.setattr(settings, 'supabase_url', 'https://example.supabase.co/')
    monkeypatch.setattr(settings, 'supabase_service_role_key', 'secret')
    monkeypatch.setattr(settings, 'supabase_storage_bucket', 'bucket')
    client = httpx.Client(transport=httpx.MockTransport(handler),
                          headers={'apikey': 'secret', 'Authorization': 'Bearer secret'})
    monkeypatch.setattr(storage, '_client', lambda: client)
    return objects, calls


def test_supabase_roundtrip(fake_supabase):
    objects, calls = fake_supabase
    assert storage.configured()
    storage.put('community/a.png', b'png', 'image/png')
    assert calls[-1].headers['content-type'] == 'image/png' and calls[-1].headers['x-upsert'] == 'false'
    assert objects == {'community/a.png': b'png'}
    with pytest.raises(OSError):
        storage.put('community/a.png', b'other')
    assert storage.get('community/a.png') == b'png'
    assert storage.get('missing.jpg') is None
    storage.delete('community/a.png')
    assert objects == {}


def test_supabase_local_file_is_temporary(fake_supabase):
    objects, calls = fake_supabase
    objects['x.jpg'] = b'jpeg'
    with storage.local_file('x.jpg') as path:
        assert path.read_bytes() == b'jpeg'
    assert not path.exists()
    before = len(calls)
    with storage.local_file('y.jpg', b'given') as path:
        assert path.read_bytes() == b'given'
    assert len(calls) == before  # 바이트를 넘기면 다시 내려받지 않는다.
    with pytest.raises(FileNotFoundError):
        with storage.local_file('missing.jpg'):
            pass


def test_supabase_requires_all_settings(fake_supabase, monkeypatch):
    monkeypatch.setattr(settings, 'supabase_service_role_key', None)
    assert not storage.configured()
