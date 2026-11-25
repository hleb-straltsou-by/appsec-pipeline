# Demo image for the pipeline. Scanned by Trivy (image + config) on Thursday, attacked by ZAP baseline on Friday.
FROM python:3.12-slim

RUN apt-get update \
 && apt-get install -y --no-install-recommends iputils-ping \
 && rm -rf /var/lib/apt/lists/*

WORKDIR /srv
COPY app/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY app/ ./app/

# Run as an unprivileged user, not root.
RUN useradd --system --uid 10001 appuser
USER appuser

ENV PORT=8080 DB_PATH=/tmp/notes.db
EXPOSE 8080
CMD ["python", "app/app.py"]
