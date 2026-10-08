# 신체 정보·활동 수준·목표 유형으로 BMR, TDEE와 목표 칼로리 범위를 계산한다.
# 팀 회의 기준의 성인용 계산이며 프로필 저장·회원 인증은 호출한 API가 담당한다.
# Mifflin-St Jeor BMR과 활동 계수의 TDEE를 계산하고 목표 유형별 권장 범위·최소 허용값을 반환한다.
def calculate_calorie_range(profile):
    # Mifflin-St Jeor: 체중 kg·키 cm·만 나이를 사용하고 남성 +5/여성 -161 상수를 적용한다.
    bmr = (10 * profile.weight + 6.25 * profile.height - 5 * profile.age
           + (5 if profile.sex == 'male' else -161))
    if bmr <= 0:
        raise ValueError('입력값으로 유효한 BMR을 계산할 수 없습니다.')
    # 활동 계수 1.2/1.375/1.55/1.725를 BMR에 곱해 하루 소비량을 추정한다.
    tdee = bmr * {'sedentary': 1.2, 'light': 1.375,
                  'moderate': 1.55, 'active': 1.725}[profile.activity_level]
    # 기초대사량과 성별 절대 최소값(남성 1500, 여성 1200 kcal) 중 큰 값이 저장 하한이다.
    minimum = max(bmr, 1500 if profile.sex == 'male' else 1200)
    # 목표별 TDEE 보정 범위: 감량 -750~-300, 유지 -100~+100, 증가 +300~+500 kcal.
    offsets = {'weight_loss': (-750, -300), 'maintain': (-100, 100),
               'muscle_gain': (300, 500)}
    low, high = offsets[profile.goal_type]
    # 권장 하한뿐 아니라 상한도 minimum보다 낮아지지 않도록 보정한다.
    low, high = max(minimum, tdee + low), max(minimum, tdee + high)
    # 하한이 전체 입력 상한보다 크면 유효한 목표가 없으므로 신체 정보 확인을 요청한다.
    if minimum > 5000:
        raise ValueError('최소 칼로리가 입력 상한을 초과합니다. 신체 정보를 확인하세요.')
    if profile.target_calories is not None and profile.target_calories < minimum:
        raise ValueError('목표 칼로리는 최소 허용값 이상이어야 합니다.')
    # 입력 목표가 권장 범위 밖이어도 최소 허용값 이상이면 안내 플래그와 함께 반환한다. 저장 여부는 API가 결정한다.
    return {'bmr': round(bmr, 2), 'tdee': round(tdee, 2),
            'minimum_calories': round(minimum, 2),
            'recommended_calorie_min': round(low, 2),
            'recommended_calorie_max': round(high, 2),
            'target_calories': profile.target_calories,
            'outside_recommended_range': profile.target_calories is not None
                and not low <= profile.target_calories <= high,
            'notice': '팀 회의 기준 계산입니다. 성인 대상이며 의료 진단이 아닙니다.'}
