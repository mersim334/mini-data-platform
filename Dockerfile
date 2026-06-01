FROM python:3.11-slim-bookworm

RUN set -eu; \
    apt-get update; \
    apt-get install -y --no-install-recommends openjdk-17-jre-headless; \
    rm -rf /var/lib/apt/lists/*; \
    ARCH="$(dpkg --print-architecture)"; \
    ln -sf "/usr/lib/jvm/java-17-openjdk-${ARCH}" /usr/lib/jvm/current-java

ENV JAVA_HOME=/usr/lib/jvm/current-java
ENV PYTHONUNBUFFERED=1
ENV PYTHONDONTWRITEBYTECODE=1

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

RUN chmod +x docker/pipeline/entrypoint.sh docker/postgres/init/00-init-databases.sh

ENTRYPOINT ["docker/pipeline/entrypoint.sh"]
