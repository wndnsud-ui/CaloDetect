"""홈과 추천에서 함께 쓰는 기존 개발 영양 상한 기준."""
SODIUM_DAILY_LIMIT_MG = 2000.0
SUGAR_ENERGY_RATIO = 0.20


def daily_limits(target_calories):
    return {'sodium': SODIUM_DAILY_LIMIT_MG,
            'sugar': max(target_calories * SUGAR_ENERGY_RATIO / 4.0, 1.0)
            if target_calories and target_calories > 0 else None}
