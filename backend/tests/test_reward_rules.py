"""리워드 DB 독립 규칙(reward_rules) 단위 검사."""
from datetime import date, datetime, timedelta, timezone
from backend.app.services import reward_rules as rules


def test_streak_bonus_cycle():
    assert [n for n in range(1, 22) if rules.streak_bonus(n)] == [3, 7, 10, 14, 17, 21]
    assert rules.streak_bonus(3) == 'streak3' and rules.streak_bonus(14) == 'streak7'
    assert rules.next_streak_bonus(5) == (2, 'streak7')


def test_streak_days_and_current():
    today = date(2026, 10, 21)
    active = {today - timedelta(days=i) for i in (1, 2, 3)}
    assert rules.current_streak(active, today) == 3
    assert rules.current_streak(active | {today}, today) == 4
    assert rules.streak_days(active, today) == 0


def test_window_and_keys():
    today = date(2026, 10, 21)
    assert rules.in_grant_window(today, today) and rules.in_grant_window(today - timedelta(days=1), today)
    assert not rules.in_grant_window(today - timedelta(days=2), today)
    assert rules.iso_week_key(today) == '2026-W43' and rules.month_key(today) == '2026-10'
    assert rules.week_monday(today) == date(2026, 10, 19) and rules.month_end(date(2026, 12, 3)) == date(2026, 12, 31)


def test_mission_reductions():
    monday = date(2026, 10, 19)
    assert rules.weekly_required_days(date(2026, 10, 23), monday) == 3
    assert rules.weekly_required_days(date(2026, 10, 1), monday) == 5
    assert rules.monthly_required_days(date(2026, 10, 25), date(2026, 10, 27)) == 5
    assert rules.monthly_required_days(date(2026, 10, 31), date(2026, 10, 31)) == 1
    assert rules.monthly_required_days(date(2026, 9, 1), date(2026, 10, 2)) == 20


def test_three_meal_gap():
    base = datetime(2026, 10, 21, tzinfo=timezone.utc)
    assert rules.three_meal_gap_ok([base, base + timedelta(hours=2), base + timedelta(hours=5)], 120)
    assert not rules.three_meal_gap_ok([base, base + timedelta(minutes=119), base + timedelta(hours=5)], 120)


def test_levels_and_eta():
    assert [rules.level_for(x) for x in (0, 299, 300, 999, 1000, 5000, 9999)] == [1, 1, 2, 2, 3, 5, 5]
    assert rules.next_level_xp(1) == 300 and rules.next_level_xp(5) is None
    assert rules.levelup_points(3) == 50 and rules.levelup_points(2) == 0
    assert rules.eta_days(147, 70, 7) == 15 and rules.eta_days(10, 0, 7) is None and rules.eta_days(0, 0, 7) == 0
    assert rules.eta_window(date(2026, 10, 20), date(2026, 10, 21)) == 2
    assert rules.eta_window(date(2026, 9, 1), date(2026, 10, 21)) == 7


def test_generated_nickname_is_valid():
    for digits in (4, 6):
        for _ in range(50):
            value = rules.generate_nickname(digits=digits)
            assert rules.nickname_problem(value) is None, value
