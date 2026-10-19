FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    MURALHA_DB_PATH=/var/lib/muralha/muralha.sqlite3

WORKDIR /app

COPY pyproject.toml README.md ./
COPY muralha ./muralha
COPY catalog ./catalog
COPY challenges ./challenges

RUN python -m pip install --no-cache-dir . \
    && useradd --create-home --uid 10001 muralha \
    && mkdir -p /var/lib/muralha \
    && chown -R muralha:muralha /var/lib/muralha /app

USER muralha

EXPOSE 8000
CMD ["uvicorn", "muralha.main:app", "--host", "0.0.0.0", "--port", "8000"]
