def calculate_calorie_range(profile):
    bmr = (10 * profile.weight + 6.25 * profile.height - 5 * profile.age
           + (5 if profile.sex == 'male' else -161))
    if bmr <= 0:
        raise ValueError('입력값으로 유효한 BMR을 계산할 수 없습니다.')
    tdee = bmr * {'sedentary': 1.2, 'light': 1.375,
                  'moderate': 1.55, 'active': 1.725}[profile.activity_level]
    minimum = max(bmr, 1500 if profile.sex == 'male' else 1200)
    offsets = {'weight_loss': (-750, -300), 'maintain': (-100, 100),
               'muscle_gain': (300, 500)}
    low, high = offsets[profile.goal_type]
    low, high = max(minimum, tdee + low), max(minimum, tdee + high)
    if minimum > 5000:
        raise ValueError('최소 칼로리가 입력 상한을 초과합니다. 신체 정보를 확인하세요.')
    if profile.target_calories is not None and profile.target_calories < minimum:
        raise ValueError('목표 칼로리는 최소 허용값 이상이어야 합니다.')
    return {'bmr': round(bmr, 2), 'tdee': round(tdee, 2),
            'minimum_calories': round(minimum, 2),
            'recommended_calorie_min': round(low, 2),
            'recommended_calorie_max': round(high, 2),
            'target_calories': profile.target_calories,
            'outside_recommended_range': profile.target_calories is not None
                and not low <= profile.target_calories <= high,
            'notice': '팀 회의 기준 계산입니다. 성인 대상이며 의료 진단이 아닙니다.'}
