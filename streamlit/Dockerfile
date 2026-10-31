FROM python:3.12-slim
WORKDIR /app
COPY requirements-charts.txt ./requirements-charts.txt
RUN pip install --no-cache-dir -r requirements-charts.txt
COPY charts.py ./charts.py
ENV PORT=8502
EXPOSE 8502
CMD ["sh", "-c", "exec python -m streamlit run charts.py --server.address=0.0.0.0 --server.port=${PORT:-8502} --server.headless=true --browser.gatherUsageStats=false"]
