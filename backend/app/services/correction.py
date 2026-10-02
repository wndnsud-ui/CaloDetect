from sqlalchemy import select
from ..models import RetrainingSample


def apply_correction(db, detection, food_name, user):
    detection.corrected_label = food_name
    # Approved snapshots are immutable; only pending work is superseded.
    pending = db.scalars(select(RetrainingSample).where(
        RetrainingSample.detection_log_id == detection.id,
        RetrainingSample.qa_status == 'PENDING', RetrainingSample.excluded == False)).all()
    for sample in pending:
        sample.excluded = True
    if user.model_improvement_consent and food_name != detection.predicted_label:
        db.add(RetrainingSample(detection_log_id=detection.id, image_path=detection.image_path,
            predicted_label=detection.predicted_label, corrected_label=food_name))
