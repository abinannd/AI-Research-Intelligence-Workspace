FROM python:3.11-slim

WORKDIR /app

RUN apt-get update && apt-get install -y --no-install-recommends \
        build-essential \
        libglib2.0-0 \
        libgl1 \
    && rm -rf /var/lib/apt/lists/*

COPY backend/requirements.txt backend/requirements-ml.txt /tmp/
RUN pip install --no-cache-dir --upgrade pip \
    && pip install --no-cache-dir torch --index-url https://download.pytorch.org/whl/cpu \
    && pip install --no-cache-dir -r /tmp/requirements.txt -r /tmp/requirements-ml.txt

COPY backend/ /app/
COPY workers /app/workers

ENV PYTHONPATH=/app \
    PYTHONUNBUFFERED=1 \
    HF_HOME=/models

CMD ["python", "-m", "workers.worker"]
