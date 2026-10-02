# 모델 현황

- best.pt: 44,511,415 bytes. 실제 로드 결과 DetectionModel / scale m / yolo26m.yaml.
- 150개 클래스가 data.yaml 및 기존 영양 CSV와 일치.
- 빈 이미지 CPU 추론(imgsz=960, conf=0.11, iou=0.45) 정상 실행. 정확도 평가가 아님.
- last.pt, args.yaml, results.csv, confusion matrix, PR/F1 curve: 현재 프로젝트 루트에서 확인되지 않음.
- 기존 파일 유지. 실제 음식 검증셋 성능 수치는 미측정.
- 실제 재학습/모델 교체/registry는 P1. Correction QA 승인 없이 학습하지 않음.
