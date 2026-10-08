# 시간을 Asia/Seoul 기준 식단 날짜로 변환하는 공통 함수. 서버 운영체제의 현지 시간에 의존하지 않는다.
from datetime import datetime
from zoneinfo import ZoneInfo

KST = ZoneInfo('Asia/Seoul')


# 전달된 시각을 한국 시간대로 변환해 날짜만 반환한다.
def korean_date(instant: datetime):
    # 시간대 없는 입력을 운영체제 현지 시간으로 추측하지 않고 거부해 날짜 경계 오류를 방지한다.
    if instant.tzinfo is None:
        raise ValueError('Timezone-aware datetime is required')
    return instant.astimezone(KST).date()
