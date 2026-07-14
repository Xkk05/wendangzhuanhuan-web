FROM docker.m.daocloud.io/python:3.11-slim-bookworm

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_INDEX_URL=https://pypi.tuna.tsinghua.edu.cn/simple \
    BACKEND_PORT=8002 \
    BACKEND_UPLOAD_DIR=/data/uploads \
    BACKEND_DOWNLOAD_DIR=/data/downloads \
    BACKEND_LOG_DIR=/data/logs

WORKDIR /app

RUN sed -i 's|deb.debian.org|mirrors.aliyun.com|g; s|security.debian.org|mirrors.aliyun.com|g' /etc/apt/sources.list.d/debian.sources && \
    apt-get update && apt-get install -y --no-install-recommends --fix-missing \
    chromium \
    ffmpeg \
    fonts-dejavu-core \
    fonts-noto-cjk \
    libreoffice \
    libreoffice-calc \
    libreoffice-impress \
    libreoffice-writer \
    && rm -rf /var/lib/apt/lists/*

COPY backend/requirements.txt /tmp/requirements.txt
COPY conversion_core/requirements.txt /tmp/conversion_core_requirements.txt
RUN python -m pip install --upgrade pip -i ${PIP_INDEX_URL} && \
    pip install -i ${PIP_INDEX_URL} -r /tmp/requirements.txt && \
    pip install -i ${PIP_INDEX_URL} -r /tmp/conversion_core_requirements.txt

COPY backend /app/backend
COPY conversion_core /app/conversion_core

RUN mkdir -p /data/uploads /data/downloads /data/logs

EXPOSE 8002

CMD ["python", "-m", "uvicorn", "backend.main:app", "--host", "0.0.0.0", "--port", "8002", "--timeout-keep-alive", "900"]
