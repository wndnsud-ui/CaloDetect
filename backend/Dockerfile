# Backend 실행 이미지. API 의존성과 CPU용 YOLO 환경, 기존 모델·데이터를 포함한다. 컨테이너 시작은 backend.scripts.start가 담당한다.
# API의 기본 Python 런타임과 최소 운영체제 이미지를 선택한다.
FROM python:3.12-slim
# 이후 복사/실행의 기준 작업 폴더를 고정한다.
WORKDIR /workspace
# 이미지 빌드에 필요한 기존 파일만 지정된 위치로 복사한다.
COPY backend/requirements.txt /tmp/requirements.txt
# 런타임 의존성을 이미지에 설치한다. CPU 패키지와 기존 YOLO 버전 범위를 유지한다.
RUN pip install --no-cache-dir -r /tmp/requirements.txt
# 런타임 의존성을 이미지에 설치한다. CPU 패키지와 기존 YOLO 버전 범위를 유지한다.
RUN pip install --no-cache-dir torch torchvision --index-url https://download.pytorch.org/whl/cpu
# 런타임 의존성을 이미지에 설치한다. CPU 패키지와 기존 YOLO 버전 범위를 유지한다.
RUN pip install --no-cache-dir "ultralytics>=8.4,<9"
# 이미지 빌드에 필요한 기존 파일만 지정된 위치로 복사한다.
COPY backend /workspace/backend
# 이미지 빌드에 필요한 기존 파일만 지정된 위치로 복사한다.
COPY data_config.py data.yaml CaloDetect_nutrition_all_matched.csv best.pt /workspace/
# API가 사용하는 컨테이너 포트를 문서화한다. 호스트 공개는 Compose 설정이 담당한다.
EXPOSE 8000
# 컨테이너 시작 시 Backend 준비/서버 진입 모듈을 실행한다.
CMD ["python", "-m", "backend.scripts.start"]
