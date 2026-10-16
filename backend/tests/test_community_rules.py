from datetime import datetime, timezone
from uuid import uuid4

import pytest

from backend.app.services.community_rules import week_start, meal_summary, encode_cursor, decode_cursor


@pytest.mark.parametrize('instant', ['2026-10-14T01:00:00+09:00', '2026-10-18T23:30:00+09:00'])
def test_korean_week_boundary(instant):
    assert week_start(datetime.fromisoformat(instant)) == datetime(2026, 10, 11, 15, tzinfo=timezone.utc)


def test_next_week_and_naive_rejection():
    assert week_start(datetime.fromisoformat('2026-10-19T00:00:00+09:00')).isoformat() == '2026-10-18T15:00:00+00:00'
    with pytest.raises(ValueError):
        week_start(datetime(2026, 10, 15))


def test_main_side_summary_and_original_values_preserved():
    items = [dict(food_name=name, category=category) for name, category in [
        ('잡곡밥', '밥류'), ('된장찌개', '국/탕/찌개'), ('제육볶음', '육류'),
        ('배추김치', '김치류'), ('시금치나물', '채소/나물'), ('감자조림', '반찬류')]]
    assert meal_summary(items) == '잡곡밥 · 된장찌개 · 제육볶음 + 반찬 3가지'
    assert meal_summary(items[:1]) == '잡곡밥'
    assert meal_summary(items[3:]) == '배추김치 · 시금치나물 · 감자조림'
    assert meal_summary(items[:3] + [dict(food_name='곰탕_설렁탕', category='국 및 탕류')]) == '잡곡밥 · 된장찌개 · 제육볶음 외 1개'
    assert meal_summary([]) == ''


def test_sides_only_overflow():
    assert meal_summary([dict(food_name=str(i), category='김치류') for i in range(5)]) == '0 · 1 · 2 외 2개'


def test_cursor_preserves_timestamp_and_unique_tiebreaker():
    instant = datetime(2026, 10, 15, 1, 2, 3, 123456, tzinfo=timezone.utc)
    first, second = str(uuid4()), str(uuid4())
    assert decode_cursor(encode_cursor(instant, first)) == (instant, first)
    assert encode_cursor(instant, first) != encode_cursor(instant, second)


@pytest.mark.parametrize('value', ['', '*', 'x'*513, 'bnVsbA', 'W10', 'WyIyMDI2LTEwLTE1IiwiaW52YWxpZCJd'])
def test_invalid_cursor(value):
    with pytest.raises(ValueError, match='피드 조회'):
        decode_cursor(value)
