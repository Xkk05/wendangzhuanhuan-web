FROM docker.m.daocloud.io/python:3.11-slim-bookworm

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_INDEX_URL=https://pypi.tuna.tsinghua.edu.cn/simple \
    BACKEND_PORT=8002 \
    BACKEND_UPLOAD_DIR=/data/uploads \
    BACKEND_DOWNLOAD_DIR=/data/downloads \
    BACKEND_LOG_DIR=/data/logs \
    CONVERTER_UID=10001 \
    CONVERTER_GID=10001 \
    HOME=/home/converter \
    XDG_CACHE_HOME=/tmp/.cache \
    XDG_CONFIG_HOME=/tmp/.config

WORKDIR /app

RUN sed -i 's|deb.debian.org|mirrors.tencent.com|g; s|security.debian.org|mirrors.tencent.com|g' /etc/apt/sources.list.d/debian.sources && \
    apt-get -o Acquire::Retries=5 -o Acquire::http::Timeout=30 update && \
    apt-get -o Acquire::Retries=5 -o Acquire::http::Timeout=30 -o Dpkg::Use-Pty=0 install -y --no-install-recommends --fix-missing \
    chromium \
    ffmpeg \
    fonts-dejavu-core \
    fonts-noto-cjk \
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

EXPOSE 8002

# Bug#13: Run as a stable non-root user. The writable HOME/cache paths keep
# browser and LibreOffice conversions from falling back to root-owned locations.
RUN groupadd -g ${CONVERTER_GID} converter && \
    useradd -u ${CONVERTER_UID} -g converter -d ${HOME} -s /usr/sbin/nologin -M converter && \
    mkdir -p /data/uploads /data/downloads /data/logs ${HOME} ${XDG_CACHE_HOME} ${XDG_CONFIG_HOME} && \
    chown -R converter:converter /app /data ${HOME} ${XDG_CACHE_HOME} ${XDG_CONFIG_HOME}

USER converter

CMD ["python", "-m", "uvicorn", "backend.main:app", "--host", "0.0.0.0", "--port", "8002", "--timeout-keep-alive", "900"]
