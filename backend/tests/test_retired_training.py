"""2026-10-20 사용자 결정: 모델 개선(재학습) 폐기. 음식 수정은 학습 후보를 만들지 않고 탐지 기록에만 남는다."""
from types import SimpleNamespace
from unittest.mock import Mock
from backend.app.services.correction import apply_correction


def test_correction_only_updates_detection():
    db = Mock()
    detection = SimpleNamespace(id=1, predicted_label='old', corrected_label=None)
    apply_correction(db, detection, 'new', SimpleNamespace())
    assert detection.corrected_label == 'new'
    db.add.assert_not_called()
    db.scalars.assert_not_called()
