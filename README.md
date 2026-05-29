# Agent Guidance Hub (AGH)

Self-hosted FastAPI service and `agh` CLI for distributing versioned agent guidance packs.

## Development

```bash
python -m venv .venv
. .venv/bin/activate
pip install -e .
python -m pytest
```

## Server

Local development writes data under `.agh-data/` by default. The Docker image sets
`AGH_DATA_DIR=/data` for the self-hosted volume layout.

```bash
uvicorn agh.server.app:app --host 0.0.0.0 --port 8912
```

Health: `GET /api/v1/health`
