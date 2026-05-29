FROM python:3.11-slim

WORKDIR /app

ENV AGH_DATA_DIR=/data
ENV PYTHONUNBUFFERED=1
ENV UV_SYSTEM_PYTHON=1
ENV PATH="/app/.venv/bin:${PATH}"

COPY --from=ghcr.io/astral-sh/uv:latest /uv /usr/local/bin/uv

COPY pyproject.toml uv.lock README.md ./
COPY agh ./agh

RUN uv sync --locked --no-dev

RUN mkdir -p /data/logs /data/secrets /data/packs

EXPOSE 8912

HEALTHCHECK --interval=30s --timeout=5s --start-period=10s --retries=3 \
  CMD python -c "import urllib.request; urllib.request.urlopen('http://127.0.0.1:8912/api/v1/health')" || exit 1

CMD ["uvicorn", "agh.server.app:app", "--host", "0.0.0.0", "--port", "8912"]
