"""리워드 지시서 v3의 DB 독립 규칙: 날짜·연속 기록·레벨·미션·간격·예상 일수·닉네임.

모든 일·주·월 경계는 KST(services/timezone.korean_date). 수치는 settings에서 읽고 여기서 정하지 않는다.
"""
import math
import random
import re
import unicodedata
from datetime import date, datetime, timedelta
from pathlib import Path
from ..config import settings

MEAL_TYPES = ('breakfast', 'lunch', 'dinner')
MEAL_LABELS = {'breakfast': '아침', 'lunch': '점심', 'dinner': '저녁', 'snack': '간식'}
# 기획안 5.2 레벨 이름. 시트 문구("예뻐지는", "가벼워진 몸")는 쓰지 않는다.
LEVEL_NAMES = {1: '시작', 2: '기록하는', 3: '움직이는', 4: '균형 잡힌', 5: '건강 습관'}
# 레벨업 때 함께 주는 레벨 전용 아이템(§6-4). LV.1 배경은 가입 시 기본 지급.
LEVEL_ITEMS = {1: ('bg_lv1',), 2: ('bg_lv2',), 3: ('bg_lv3',), 4: ('bg_lv4',),
               5: ('title_lv5', 'bg_lv5')}

# 지급 출처별 화면 문구. 프런트는 하드코딩하지 않고 API의 label을 쓴다.
GRANT_LABELS = {
    'onboarding:signup': '가입 축하', 'onboarding:goal': '목표 설정', 'onboarding:first_meal': '첫 식단 기록',
    'three': '하루 3끼 완료', 'streak3': '연속 기록 보너스', 'streak7': '연속 기록 보너스',
    'mission': '오늘의 미션', 'weekly': '주간 미션', 'monthly': '월간 목표', 'level': '레벨업 보상',
    'share': '식단 공유', 'reaction': '커뮤니티 반응', 'community_legacy': '커뮤니티 포인트 이관',
}

# §6-5 대체 미션 정의(C11: 채소 미션은 음식 태그 확정 전 미구현). 화면 문구는 API에서 내려준다.
MISSIONS = (
    {'id': 'daily', 'title': '오늘의 미션', 'text': '사진으로 두 끼 기록하기', 'goal': 2},
    {'id': 'weekly', 'title': '주간 미션', 'text': '이번 주 {goal}일 기록하기'},
    {'id': 'monthly', 'title': '월간 목표', 'text': '이번 달 {goal}일 기록하기'},
)

# 닉네임 자동 생성 단어(형용사 + 음식 + 4자리 숫자). 최대 길이 12자 안에 들도록 3자·2자 단어만 쓴다.
NICK_ADJECTIVES = ('씩씩한', '든든한', '상큼한', '포근한', '차분한', '꾸준한', '산뜻한', '즐거운', '다정한', '똑똑한')
NICK_FOODS = ('당근', '두부', '사과', '현미', '오이', '배추', '감자', '버섯', '호박', '연근')
IMPERSONATION = ('운영자', '관리자', 'calodetect', '칼로디텍트')
BLOCKLIST_PATH = Path(__file__).resolve().parents[1] / 'data' / 'nickname_blocklist.txt'
# 한글·영문·숫자·_, 단어 사이 공백은 1칸만.
NICK_CHARS = re.compile(r'^[0-9A-Za-z_가-힣]+( [0-9A-Za-z_가-힣]+)*$')


# ---- 날짜 ----

def in_grant_window(meal_date, today):
    """기록 인정 기간: KST 오늘 또는 어제만 지급·연속 기록 반영."""
    return meal_date in (today, today - timedelta(days=1))


def week_monday(day):
    return day - timedelta(days=day.weekday())


def iso_week_key(day):
    year, week, _ = day.isocalendar()
    return f'{year}-W{week:02d}'


def month_key(day):
    return f'{day.year:04d}-{day.month:02d}'


def month_end(day):
    first_next = date(day.year + (day.month == 12), day.month % 12 + 1, 1)
    return first_next - timedelta(days=1)


# ---- 3끼 간격 ----

def three_meal_gap_ok(created_times, minutes=None):
    """세 끼 기록 시각 사이 간격이 모두 기준 이상이면 True."""
    minutes = settings.reward_three_meal_min_gap_minutes if minutes is None else minutes
    times = sorted(created_times)
    if len(times) != 3:
        return False
    return all((b - a) >= timedelta(minutes=minutes) for a, b in zip(times, times[1:]))


# ---- 연속 기록 ----

def streak_days(active_days, end):
    """end부터 거꾸로 '기록한 날 또는 보호된 날'이 이어진 일수."""
    count, day = 0, end
    while day in active_days:
        count += 1
        day -= timedelta(days=1)
    return count


def current_streak(active_days, today):
    """오늘(오늘 기록 전이면 어제)부터의 연속 일수."""
    return streak_days(active_days, today if today in active_days else today - timedelta(days=1))


def streak_bonus(n):
    """연속 3·7·10·14·17·21…일째 보너스 종류. 해당 없으면 None."""
    if n < 3:
        return None
    if n % 7 == 3:
        return 'streak3'
    if n % 7 == 0:
        return 'streak7'
    return None


def next_streak_bonus(n):
    """지금 n일 연속일 때 다음 보너스까지 남은 일수와 종류."""
    step = 1
    while streak_bonus(n + step) is None:
        step += 1
    return step, streak_bonus(n + step)


# ---- 레벨 ----

def level_for(xp, thresholds=None):
    thresholds = thresholds or settings.reward_levels
    level = 1
    for index, needed in enumerate(thresholds):
        if xp >= needed:
            level = index + 1
    return level


def next_level_xp(level, thresholds=None):
    thresholds = thresholds or settings.reward_levels
    return thresholds[level] if level < len(thresholds) else None


def levelup_points(level):
    points = settings.reward_levelup_point_list
    return points[level - 1] if 0 < level <= len(points) else 0


# ---- 미션 ----

def weekly_required_days(signup_day, week_start):
    """가입한 주는 min(5, 가입일~그 주 일요일 일수)로 줄인다."""
    base = settings.reward_weekly_mission_days
    sunday = week_start + timedelta(days=6)
    if week_start <= signup_day <= sunday:
        return max(1, min(base, (sunday - signup_day).days + 1))
    return base


def monthly_required_days(signup_day, day):
    """가입한 달은 min(20, 가입일~말일 일수 − 2), 최소 1."""
    base = settings.reward_monthly_goal_days
    if (signup_day.year, signup_day.month) == (day.year, day.month):
        return max(1, min(base, (month_end(day) - signup_day).days + 1 - 2))
    return base


def balance_ok(totals, target_calories, sugar_limit, sodium_limit, tolerance=None):
    """영양 균형 XP 조건. 목표 ±15% 안이고 당류·나트륨 기준 이내일 때만.

    기준이 하나라도 없으면 판정하지 않는다(C7: 당류·나트륨 기준은 TBD, 임의 기준을 만들지 않음).
    """
    if not target_calories or sugar_limit is None or sodium_limit is None:
        return False
    tolerance = settings.reward_balance_cal_tolerance if tolerance is None else tolerance
    low, high = target_calories * (1 - tolerance), target_calories * (1 + tolerance)
    return low <= totals['cal'] <= high and totals['sugar'] <= sugar_limit and totals['sodium'] <= sodium_limit


# ---- 예상 일수 (§6-12) ----

def eta_window(signup_day, today):
    """창 길이 W = min(REWARD_ETA_WINDOW_DAYS, 가입일부터 오늘까지 일수, 오늘 포함)."""
    return max(1, min(settings.reward_eta_window_days, (today - signup_day).days + 1))


def eta_days(remaining, recent_total, window):
    """예상 일수 = ceil(남은 양 / 하루 평균). 하루 평균이 0이면 None(화면은 '기록을 이어가면 계산돼요')."""
    if remaining <= 0:
        return 0
    if recent_total <= 0 or window <= 0:
        return None
    return math.ceil(remaining / (recent_total / window))


# ---- 닉네임 (§6-13) ----

def normalize_nickname(value):
    return unicodedata.normalize('NFC', value or '').strip()


def nickname_key(value):
    return re.sub(r'\s+', '', normalize_nickname(value).lower())


def blocklist():
    try:
        lines = BLOCKLIST_PATH.read_text(encoding='utf-8').splitlines()
    except OSError:
        return ()
    return tuple(nickname_key(line) for line in lines if line.strip() and not line.startswith('#'))


def nickname_problem(value, name=None, email=None):
    """저장 전 형식 검사. 문제가 있으면 reason 문자열, 없으면 None. 중복·변경 주기는 DB에서 검사한다."""
    nickname = normalize_nickname(value)
    if not settings.reward_nickname_min_len <= len(nickname) <= settings.reward_nickname_max_len:
        return 'length'
    if '@' in nickname:
        return 'blocked'
    if not NICK_CHARS.match(nickname):
        return 'chars'
    key = nickname_key(nickname)
    if re.fullmatch(r'\d{7,}', key):
        return 'blocked'
    if any(word in key for word in (*IMPERSONATION, *blocklist()) if word):
        return 'blocked'
    if name and key == nickname_key(name):
        return 'same_as_name'
    if email and key == nickname_key(email.split('@')[0]):
        return 'same_as_email'
    return None


def generate_nickname(rng=None, digits=4):
    """예: '씩씩한 당근 4821'. 중복으로 5회 실패하면 6자리 숫자('씩씩한당근 482193')로 길이 안에 맞춘다."""
    rng = rng or random.SystemRandom()
    number = rng.randrange(10 ** (digits - 1), 10 ** digits)
    adjective, food = rng.choice(NICK_ADJECTIVES), rng.choice(NICK_FOODS)
    return f'{adjective} {food} {number}' if digits == 4 else f'{adjective}{food} {number}'


def nickname_message(reason, next_date=None):
    return {
        'length': f'닉네임은 {settings.reward_nickname_min_len}~{settings.reward_nickname_max_len}자로 정해 주세요.',
        'chars': '한글·영문·숫자와 _만 쓸 수 있어요.',
        'blocked': '쓸 수 없는 단어가 들어 있어요.',
        'taken': '이미 쓰고 있는 닉네임이에요.',
        'same_as_name': '이름이나 이메일과 같은 닉네임은 쓸 수 없어요.',
        'same_as_email': '이름이나 이메일과 같은 닉네임은 쓸 수 없어요.',
        'cooldown': f'닉네임은 {next_date.month}월 {next_date.day}일부터 다시 바꿀 수 있어요.' if next_date else '잠시 후 다시 시도해 주세요.',
    }.get(reason, '잠시 후 다시 시도해 주세요.')


def kst_today(now):
    from .timezone import korean_date
    return korean_date(now)


def as_aware(value):
    """SQLite가 돌려준 naive datetime을 UTC로 본다."""
    from datetime import timezone
    if isinstance(value, datetime) and value.tzinfo is None:
        return value.replace(tzinfo=timezone.utc)
    return value
