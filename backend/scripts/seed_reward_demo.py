"""로컬 테스트 계정에 리워드 더미 포인트·XP·연속 기록·보호권을 넣는다(실행 가능성 확인용).

실행: python -m backend.scripts.seed_reward_demo [--points 200] [--xp 1200] [--streak 5] [--protectors 1] [--reset]
개발 환경·테스트 계정에서만 동작한다. --reset은 테스트 계정의 리워드 기록만 지운 뒤 다시 넣는다(식단·닉네임 유지).
"""
import argparse
import sys
from sqlalchemy import select
from sqlalchemy.orm import Session
from backend.app.db import get_engine
from backend.app.models import User
from backend.app.services import reward_demo
from backend.scripts.seed_local_test_account import local_test_account_enabled, TEST_ACCOUNT_EMAIL


def main(argv=None):
    parser = argparse.ArgumentParser()
    parser.add_argument('--points', type=int, default=200)
    parser.add_argument('--xp', type=int, default=1200, help='레벨용 XP 총량(연속 기록 XP 포함)')
    parser.add_argument('--streak', type=int, default=5, help='어제까지 이어진 기록 일수')
    parser.add_argument('--protectors', type=int, default=1)
    parser.add_argument('--reset', action='store_true', help='리워드 기록을 지우고 다시 넣기')
    args = parser.parse_args(argv)
    if not local_test_account_enabled():
        raise SystemExit('Local development test settings required (APP_ENV=development, LOCAL_TEST_SIGNUP=true).')
    with Session(get_engine()) as db:
        user = db.scalar(select(User).where(User.email == TEST_ACCOUNT_EMAIL))
        if user is None or user.role != 'user':
            raise SystemExit('Local test account missing. Run: python -m backend.scripts.seed_local_test_account')
        if args.reset:
            reward_demo.reset(db, user)
        result = reward_demo.seed(db, user, args.points, args.xp, args.streak, args.protectors)
        db.commit()
    print(f'Reward demo ready: {result["balance"]}P, XP {result["xp_total"]}, LV.{result["level"]}, '
          f'streak {result["streak_days"]} days, protectors {result["protectors"]}')


if __name__ == '__main__':
    sys.stdout.reconfigure(encoding='utf-8')
    main()
