# 테스트 공통 설정. 개인 .env가 공유 Supabase Storage를 가리켜도 테스트는 항상 로컬 임시 폴더만 쓴다.
import pytest

from backend.app.config import settings


@pytest.fixture(autouse=True)
def local_image_storage(monkeypatch):
    monkeypatch.setattr(settings, 'image_storage_backend', 'local')
