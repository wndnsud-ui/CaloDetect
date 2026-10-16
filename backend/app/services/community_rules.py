"""커뮤니티 v5의 DB 독립 규칙. 원본 식단·포인트를 변경하지 않는다."""
import base64
import binascii
import json
from datetime import datetime, timedelta, timezone
from uuid import UUID
from zoneinfo import ZoneInfo

KST = ZoneInfo('Asia/Seoul')
SIDE_CATEGORIES = frozenset({'반찬류', '김치류', '생채·무침류', '채소/나물', '안주/반찬'})
RECEIVED_REASONS = frozenset({'like_received', 'recommend_received',
    'like_received_revoked', 'recommend_received_revoked'})


def week_start(instant=None):
    """KST 월요일 00:00을 UTC aware datetime으로 반환한다."""
    instant = instant or datetime.now(timezone.utc)
    if instant.tzinfo is None:
        raise ValueError('시간대 정보가 필요합니다.')
    local = instant.astimezone(KST)
    monday = (local - timedelta(days=local.weekday())).replace(hour=0, minute=0, second=0, microsecond=0)
    return monday.astimezone(timezone.utc)


def meal_summary(items):
    """저장 순서의 카탈로그 음식명·category로만 한 상 요약을 구성한다.

    원본 food_name의 밑줄은 유지한다. 표시 변환은 프론트 한 곳에서 수행한다.
    """
    items = list(items)
    mains = [item['food_name'] for item in items if item['category'] not in SIDE_CATEGORIES]
    sides = [item['food_name'] for item in items if item['category'] in SIDE_CATEGORIES]
    shown = mains if mains else sides
    summary = ' · '.join(shown[:3])
    if len(shown) > 3:
        summary += f' 외 {len(shown) - 3}개'
    if mains and sides:
        summary += f' + 반찬 {len(sides)}가지'
    return summary


def encode_cursor(created_at, post_id):
    if created_at.tzinfo is None:
        raise ValueError('시간대 정보가 필요합니다.')
    payload = [created_at.astimezone(timezone.utc).isoformat(), str(UUID(post_id))]
    return base64.urlsafe_b64encode(json.dumps(payload, separators=(',', ':')).encode()).decode().rstrip('=')


def decode_cursor(cursor):
    """외부 cursor는 길이·구조·시간대·UUID를 모두 검사한다. 실패는 API가 422로 변환한다."""
    try:
        if not isinstance(cursor, str) or not 1 <= len(cursor) <= 512:
            raise ValueError
        raw = base64.b64decode(cursor + '=' * (-len(cursor) % 4), altchars=b'-_', validate=True)
        payload = json.loads(raw)
        if not isinstance(payload, list) or len(payload) != 2 or any(type(v) is not str for v in payload):
            raise ValueError
        instant = datetime.fromisoformat(payload[0])
        if instant.tzinfo is None:
            raise ValueError
        return instant.astimezone(timezone.utc), str(UUID(payload[1]))
    except (ValueError, TypeError, UnicodeError, binascii.Error):
        raise ValueError('피드 조회 위치가 올바르지 않습니다.') from None
