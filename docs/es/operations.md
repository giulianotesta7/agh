# Operaciones

Corré AGH como servicio Docker y mantené `/data` persistente. Ese directorio guarda la base, packs, logs y el secreto de bootstrap.

## Layout runtime

La imagen define:

```text
AGH_DATA_DIR=/data
```

| Path | Contenido |
|------|-----------|
| `/data/agh.sqlite3` | Base SQLite de metadata. |
| `/data/packs/` | Archivos de packs publicados. |
| `/data/logs/agh.log` | Log del server. |
| `/data/secrets/initial_owner_token` | Primer owner token, escrito una vez. |

## Correr con Docker Compose

```bash
docker compose up -d
```

El compose file usa la imagen publicada del release y un named volume que sobrevive reemplazos del container:

```text
ghcr.io/giulianotesta7/agent-guidance-hub:0.1.0
```

## Comando directo

```bash
docker run --rm -p 8912:8912 -v agh-data:/data \
  -e AGH_BOOTSTRAP_OWNER_EMAIL=owner@example.com \
  ghcr.io/giulianotesta7/agent-guidance-hub:0.1.0
```

Usá un named volume, bind mount o volumen de la plataforma que sobreviva reemplazos del container.

## Healthcheck

El healthcheck del container llama a:

```text
http://127.0.0.1:8912/api/v1/health
```

Chequeo manual:

```bash
curl http://127.0.0.1:8912/api/v1/health
```

## Primer owner token

En el primer startup con `AGH_BOOTSTRAP_OWNER_EMAIL`, AGH crea el owner y escribe un token plaintext:

```text
/data/secrets/initial_owner_token
```

Leelo una vez y usalo con `agh login`. Tratá ese archivo como secreto. AGH guarda solo hashes de tokens en SQLite.

## Backup

Hacé backup de `/data` con el servicio parado, o usá snapshots del volumen en tu plataforma.

Guardá al menos:

- `/data/agh.sqlite3`
- `/data/packs/`
- `/data/secrets/`

Guardá o rotá `/data/logs/` según tu política de retención.

## Upgrade

1. Parar el container de AGH.
2. Hacer backup de `/data`.
3. Pullear la nueva imagen o actualizar `compose.yaml` al nuevo version tag.
4. Levantar el nuevo container con el mismo volumen `/data`.
5. Chequear `/api/v1/health`.
6. Correr `agh config show` y `agh project list`.

Las migraciones de base corren cuando arranca el server.

## Desarrollo local

Para desarrollo sin Docker:

```bash
uv sync
AGH_BOOTSTRAP_OWNER_EMAIL=owner@example.com \
  uv run uvicorn agh.server.app:app --host 0.0.0.0 --port 8912
uv run pytest
```

El desarrollo local escribe datos del server bajo `.agh-data/` por defecto. Los E2E/dev overrides suelen usar archivos ignorados como `.agh-data-dev/` y `.agh-cli-dev.toml`.
