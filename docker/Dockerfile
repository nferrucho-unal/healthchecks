FROM python:3.12-slim-bookworm AS builder

SHELL ["/bin/bash", "-o", "pipefail", "-c"]

COPY requirements.txt /tmp

RUN \
    apt-get update && \
    apt-get upgrade -y && \
    # Uso de --no-install-recommends para evitar dependencias innecesarias
    apt-get install -y --no-install-recommends \
        build-essential \
        libffi-dev \
        libpq-dev \
        libmariadb-dev \
        libcurl4-openssl-dev \
        pkg-config && \
    rm -rf /var/lib/apt/lists/*

RUN pip wheel --wheel-dir /wheels apprise uwsgi mysqlclient minio==7.2.20 "psycopg[c]" \
    "msgpack>=1.2.1" "setuptools>=78.1.1" -r /tmp/requirements.txt

COPY . /opt/healthchecks/
RUN \
    rm -rf /opt/healthchecks/.git && \
    rm -rf /opt/healthchecks/stuff

FROM python:3.12-slim-bookworm

# Creación de usuario del sistema de forma restrictiva
RUN useradd --system --no-create-home --shell /bin/false hc
ENV PYTHONUNBUFFERED=1
WORKDIR /opt/healthchecks

RUN \
    apt-get update && \
    apt-get upgrade -y && \
    apt-get install -y --no-install-recommends libcurl4 libpq5 libmariadb3 && \
    rm -rf /var/apt/cache && \
    rm -rf /var/lib/apt/lists/*

RUN --mount=type=bind,target=/wheels,source=/wheels,from=builder \
    pip install --no-cache-dir /wheels/*

COPY --from=builder /opt/healthchecks/ /opt/healthchecks/
COPY docker/fetchstatus.py /opt/healthchecks/

# --- Variables de entorno requeridas para la compilación estática offline ---
ENV USE_GZIP_MIDDLEWARE=True
ENV DEBUG=False
ENV SECRET_KEY=temporary-build-placeholder-key
ENV COMPRESS_ENABLED=True

RUN \
    rm -f /opt/healthchecks/hc/local_settings.py && \
    ./manage.py collectstatic --noinput && \
    ./manage.py compress --force

RUN mkdir /data && chown hc:hc /data

USER hc

HEALTHCHECK --start-period=20s --start-interval=5s --interval=60s --retries=1 CMD ./fetchstatus.py
CMD [ "uwsgi", "/opt/healthchecks/docker/uwsgi.ini"]
