FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

COPY sandbox/worker.py /opt/muralha/worker.py
COPY sandbox/invoke_candidate.py /opt/muralha/invoke_candidate.py

RUN chmod 0555 /opt/muralha/worker.py /opt/muralha/invoke_candidate.py

WORKDIR /tmp
