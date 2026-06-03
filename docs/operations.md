# Operations

Run AGH as a Docker service and keep `/data` persistent. That directory holds the database, packs, logs, and bootstrap secret.

## Runtime layout

The image sets:

```text
AGH_DATA_DIR=/data
```

| Path | Contents |
|------|----------|
| `/data/agh.sqlite3` | SQLite metadata database. |
| `/data/packs/` | Published pack files. |
| `/data/logs/agh.log` | Server log file. |
| `/data/secrets/initial_owner_token` | First owner token, written once. |

## Run with Docker Compose

```bash
docker compose up -d
```

The compose file uses the published release image and a named volume that survives container replacement:

```text
ghcr.io/giulianotesta7/agent-guidance-hub:0.1.0
```

## Direct run command

```bash
docker run --rm -p 8912:8912 -v agh-data:/data \
  -e AGH_BOOTSTRAP_OWNER_EMAIL=owner@example.com \
  ghcr.io/giulianotesta7/agent-guidance-hub:0.1.0
```

Use a named volume, bind mount, or platform volume that survives container replacement.

## Healthcheck

The container healthcheck calls:

```text
http://127.0.0.1:8912/api/v1/health
```

Manual check:

```bash
curl http://127.0.0.1:8912/api/v1/health
```

## First owner token

On first startup with `AGH_BOOTSTRAP_OWNER_EMAIL`, AGH creates the owner user and writes one plaintext token:

```text
/data/secrets/initial_owner_token
```

Read it once and use it with `agh login`. Treat the file as a secret. AGH stores only token hashes in SQLite.

## Backup

Back up `/data` while the service is stopped, or use your platform's volume snapshot mechanism.

Keep at least:

- `/data/agh.sqlite3`
- `/data/packs/`
- `/data/secrets/`

Keep or rotate `/data/logs/` according to your retention policy.

## Upgrade

1. Stop the AGH container.
2. Back up `/data`.
3. Pull the new image or update `compose.yaml` to the new version tag.
4. Start the new container with the same `/data` volume.
5. Check `/api/v1/health`.
6. Run `agh config show` and `agh project list`.

Database migrations run when the server starts.

## Local development

For development without Docker:

```bash
uv sync
AGH_BOOTSTRAP_OWNER_EMAIL=owner@example.com \
  uv run uvicorn agh.server.app:app --host 0.0.0.0 --port 8912
uv run pytest
```

Local development writes server data under `.agh-data/` by default. E2E/dev overrides commonly use ignored files such as `.agh-data-dev/` and `.agh-cli-dev.toml`.
