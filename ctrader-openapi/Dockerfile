FROM python:3.11-slim
WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY . .
RUN mkdir -p /app/state
VOLUME ["/app/state"]
ENV CTRADER_ENV=demo AUREON_EXECUTION_ENABLED=false
CMD ["python","executor.py"]
