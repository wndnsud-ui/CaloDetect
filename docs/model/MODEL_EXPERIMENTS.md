# 모델 현황

> 2026-10-20 사용자 결정: 모델 개선(재학습)·관리자 재학습 QA·모델 개선 동의는 폐기했고 관련 API·Streamlit `admin_qa.py`·`retraining_samples` 테이블·동의 컬럼을 삭제했다. 아래 내용 중 해당 부분은 과거 기록이다.

- best.pt: 44,511,415 bytes. 실제 로드 결과 DetectionModel / scale m / yolo26m.yaml.
- 150개 클래스가 data.yaml 및 기존 영양 CSV와 일치.
- 빈 이미지 CPU 추론(imgsz=960, conf=0.11, iou=0.45) 정상 실행. 정확도 평가가 아님.
- last.pt, args.yaml, results.csv, confusion matrix, PR/F1 curve: 현재 프로젝트 루트에서 확인되지 않음.
- 기존 파일 유지. 실제 음식 검증셋 성능 수치는 미측정.
- 실제 재학습/모델 교체/registry는 P1. Correction QA 승인 없이 학습하지 않음.
