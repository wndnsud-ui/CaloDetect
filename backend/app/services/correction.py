# 사용자가 수정한 음식명을 탐지 기록과 QA 후보에 반영하는 서비스.
# 모델 개선 동의가 있는 오탐 수정만 후보를 만들며 기존 승인 이력을 보존하고 대기 후보만 제외한다.
from sqlalchemy import select
from ..models import RetrainingSample


# 수정 음식명을 기록하고 기존 대기 후보를 제외한 뒤 동의한 오탐 수정에 새 QA 후보를 추가한다. commit은 호출 측에서 수행한다.
def apply_correction(db, detection, food_name, user):
    detection.corrected_label = food_name
    # Approved snapshots are immutable; only pending work is superseded.
    # 이미 승인/거절된 이력은 보존하고 같은 탐지의 아직 유효한 PENDING 후보만 찾는다.
    pending = db.scalars(select(RetrainingSample).where(
        RetrainingSample.detection_log_id == detection.id,
        RetrainingSample.qa_status == 'PENDING', RetrainingSample.excluded == False)).all()
    for sample in pending:
        # 재수정으로 이전 대기 후보가 오래된 답이 되었으므로 새 후보와 함께 검수되지 않게 제외한다.
        sample.excluded = True
    # 현재 선택 동의 상태를 확인해 모델 개선 후보의 등록/검수 가능 여부를 제한한다.
    if user.model_improvement_consent and food_name != detection.predicted_label:
        db.add(RetrainingSample(detection_log_id=detection.id, image_path=detection.image_path,
            predicted_label=detection.predicted_label, corrected_label=food_name))
