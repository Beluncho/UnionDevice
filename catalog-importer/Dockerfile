FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1

WORKDIR /workspace
COPY requirements.txt pyproject.toml ./
COPY src ./src
RUN pip install --no-cache-dir -r requirements.txt

RUN addgroup --system importer && adduser --system --ingroup importer importer \
    && mkdir -p /workspace/examples/inputs /data \
    && chown -R importer:importer /workspace /data

USER importer
ENTRYPOINT ["python", "-m", "catalog_importer"]
CMD ["--help"]

