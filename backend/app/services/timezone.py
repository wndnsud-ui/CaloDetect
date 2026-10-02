from datetime import datetime
from zoneinfo import ZoneInfo

KST = ZoneInfo('Asia/Seoul')


def korean_date(instant: datetime):
    if instant.tzinfo is None:
        raise ValueError('Timezone-aware datetime is required')
    return instant.astimezone(KST).date()
