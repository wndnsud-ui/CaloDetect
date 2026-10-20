# 사용자가 수정한 음식명을 탐지 기록에 반영한다.
# 2026-10-20 사용자 결정: 모델 개선(재학습) 폐기. 학습 후보를 만들지 않는다.


# 수정 음식명을 탐지 기록에 남긴다. commit은 호출 측에서 수행한다. user는 기존 호출 형태를 유지하려고 받는다.
def apply_correction(db, detection, food_name, user):
    detection.corrected_label = food_name
