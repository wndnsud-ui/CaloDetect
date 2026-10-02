FROM python:3.12-slim
WORKDIR /workspace
COPY backend/requirements.txt /tmp/requirements.txt
RUN pip install --no-cache-dir -r /tmp/requirements.txt
RUN pip install --no-cache-dir torch torchvision --index-url https://download.pytorch.org/whl/cpu
RUN pip install --no-cache-dir "ultralytics>=8.4,<9"
COPY backend /workspace/backend
COPY data_config.py data.yaml CaloDetect_nutrition_all_matched.csv best.pt /workspace/
EXPOSE 8000
CMD ["python", "-m", "backend.scripts.start"]
