"""Reuse the existing YOLO environment without changing the legacy application."""
import contextlib
import hashlib
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]


def main():
    from PIL import Image
    from ultralytics import YOLO
    with contextlib.redirect_stdout(sys.stderr):
        model = YOLO(str(ROOT / 'best.pt'))
        import yaml
        names = yaml.safe_load((ROOT / 'data.yaml').read_text(encoding='utf-8-sig'))['names']
        if [model.names[i] for i in range(len(model.names))] != [names[i] for i in range(len(names))]:
            raise ValueError('Model class mismatch')
        with Image.open(sys.argv[1]) as source:
            result = model.predict(source.convert('RGB'), conf=0.11, iou=0.45,
                                   imgsz=960, device='cpu', verbose=False)[0]
    detections = [{'class_id': int(box.cls[0]), 'predicted_label': model.names[int(box.cls[0])],
                   'confidence': float(box.conf[0]), 'bbox': box.xyxy[0].tolist()} for box in result.boxes]
    digest = hashlib.sha256((ROOT / 'best.pt').read_bytes()).hexdigest()[:16]
    print(json.dumps({'detections': detections, 'model_version': f'yolo26m-{digest}'}, ensure_ascii=True))


if __name__ == '__main__':
    main()
