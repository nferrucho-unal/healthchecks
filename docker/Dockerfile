# Se recomienda usar el tag exacto de la última versión menor para forzar parches actualizados
FROM python:3.12-alpine AS builder

# En Alpine usamos /bin/sh con control de tuberías seguro
SHELL ["/bin/sh", "-o", "pipefail", "-c"]

# COPY requirements.txt /tmp

RUN \
    apk update && \
    apk upgrade && \
    # Equivalente completo de dependencias de compilación para C en Alpine Linux
    apk add --no-cache \
        build-base \
        python3-dev \
        libffi-dev \
        postgresql-dev \
        mariadb-dev \
        curl-dev \
        linux-headers \
        openssl-dev \
        zlib-dev \
        pkgconfig

# Asegurar que pip, setuptools y wheel estén en su última versión antes de compilar
RUN pip install --no-cache-dir --upgrade pip setuptools wheel

RUN pip wheel --wheel-dir /wheels apprise uwsgi mysqlclient minio==7.2.20 "psycopg[c]" \
    "msgpack>=1.2.1" "setuptools>=78.1.1" -r /tmp/requirements.txt

COPY . /opt/healthchecks/
RUN \
    rm -rf /opt/healthchecks/.git && \
    rm -rf /opt/healthchecks/stuff

# --- Segunda Etapa (Imagen Final) ---
FROM python:3.12-alpine

# Creación de usuario del sistema de forma restrictiva usando comandos nativos de Alpine
RUN adduser --system --no-create-home --shell /bin/false hc
ENV PYTHONUNBUFFERED=1
WORKDIR /opt/healthchecks

RUN \
    apk update && \
    apk upgrade && \
    # Instalación de librerías en tiempo de ejecución equivalentes y bash para compatibilidad
    apk add --no-cache libcurl libpq mariadb-connector-c bash && \
    # CORRECCIÓN: Ruta exacta para eliminar de raíz las cachés de paquetes en Alpine
    rm -rf /var/cache/apk/*

RUN --mount=type=bind,target=/wheels,source=/wheels,from=builder \
    pip install --no-cache-dir /wheels/*

COPY --from=builder /opt/healthchecks/ /opt/healthchecks/
# COPY docker/fetchstatus.py /opt/healthchecks/

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
