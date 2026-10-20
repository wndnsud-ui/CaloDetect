"""팀원용 더미 한 번에 만들기: 테스트 계정 → 최근 30일 식단 → 리워드 아이템 → 리워드 더미.

실행(로컬): python -m backend.scripts.seed_test_demo
실행(Docker): docker compose exec backend python -m backend.scripts.seed_test_demo
개발 환경(APP_ENV=development, LOCAL_TEST_SIGNUP=true)에서만 동작한다. 각 단계는 다시 실행해도 중복을 만들지 않는다.
리워드 더미 값은 seed_reward_demo 옵션을 그대로 받는다(예: --points 500 --xp 2600 --reset).
"""
import subprocess
import sys
from backend.scripts.seed_local_test_account import local_test_account_enabled

STEPS = [
    ('테스트 계정', ['backend.scripts.seed_local_test_account']),
    ('관리자 계정', ['backend.scripts.seed_local_admin']),
    ('최근 30일 식단', ['backend.scripts.seed_demo_meals']),
    ('리워드 아이템', ['backend.scripts.seed_reward_items']),
]

if __name__ == '__main__':
    if not local_test_account_enabled():
        raise SystemExit('Local development test settings required (APP_ENV=development, LOCAL_TEST_SIGNUP=true).')
    for label, module in STEPS + [('리워드 더미', ['backend.scripts.seed_reward_demo', *sys.argv[1:]])]:
        print(f'== {label}', flush=True)
        subprocess.run([sys.executable, '-m', *module], check=True)
    print('Done. Log in at http://localhost:5174 with test@calodetect.local / CaloTest!2026')
