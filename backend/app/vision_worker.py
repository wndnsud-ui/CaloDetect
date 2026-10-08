# YOLO 추론을 별도 Python 프로세스에서 수행하는 worker.
# 서버가 읽는 표준 출력은 JSON 결과로 유지하고 라이브러리 안내 출력은 분리한다.
"""Reuse the existing YOLO environment without changing the legacy application."""
import contextlib
import hashlib
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]


# YOLO 추론을 별도 Python 프로세스에서 수행하는 worker.
# 명령행으로 실행할 때 아래 초기화·검사·출력 순서를 수행한다.
def main():
    # YOLO 초기 안내 등 라이브러리 stdout을 stderr로 보내 마지막 결과 JSON과 섞이지 않게 한다.
    with contextlib.redirect_stdout(sys.stderr):
        from PIL import Image
        from ultralytics import YOLO
        model = YOLO(str(ROOT / 'best.pt'))
        import yaml
        names = yaml.safe_load((ROOT / 'data.yaml').read_text(encoding='utf-8-sig'))['names']
        # 로드한 모델 클래스와 기존 YAML 이름/순서가 일치하지 않으면 잘못된 영양 연결을 막기 위해 추론을 중단한다.
        if [model.names[i] for i in range(len(model.names))] != [names[i] for i in range(len(names))]:
            raise ValueError('Model class mismatch')
        with Image.open(sys.argv[1]) as source:
            # 기존 conf=0.11, iou=0.45, 입력 960, CPU 설정으로 추론한다. 주석 작업으로 모델 설정을 바꾸지 않는다.
            result = model.predict(source.convert('RGB'), conf=0.11, iou=0.45,
                                   imgsz=960, device='cpu', verbose=False)[0]
    detections = [{'class_id': int(box.cls[0]), 'predicted_label': model.names[int(box.cls[0])],
                   'confidence': float(box.conf[0]), 'bbox': box.xyxy[0].tolist()} for box in result.boxes]
    # 모델 파일 해시 앞 16자리를 기록해 같은 파일명의 다른 모델 결과를 구분한다.
    digest = hashlib.sha256((ROOT / 'best.pt').read_bytes()).hexdigest()[:16]
    print(json.dumps({'detections': detections, 'model_version': f'yolo26m-{digest}'}, ensure_ascii=True))


if __name__ == '__main__':
    main()
