# Quickstart

Levantá AGH con Docker, logueate con el primer token owner y aplicá los packs asignados desde un repo.

## 1. Levantar el server

Corré AGH con la imagen publicada y estado persistente bajo `/data`:

```bash
docker compose up -d
```

El compose file usa por defecto la imagen publicada más reciente:

```text
ghcr.io/giulianotesta7/agent-guidance-hub:${AGH_IMAGE_TAG:-latest}
```

Chequeá el server:

```bash
curl http://127.0.0.1:8912/api/v1/health
```

## 2. Leer el primer owner token

AGH escribe el token una sola vez:

```text
/data/secrets/initial_owner_token
```

Leelo desde el volumen Docker:

```bash
docker run --rm -v agh-data:/data busybox \
  cat /data/secrets/initial_owner_token
```

## 3. Instalar el CLI

Desde el paquete publicado:

```bash
uv tool install --force agh
```

Verificalo:

```bash
agh --help
```

## 4. Login

```bash
agh login \
  --url http://127.0.0.1:8912 \
  --email owner@example.com \
  --token "$(docker run --rm -v agh-data:/data busybox cat /data/secrets/initial_owner_token)"
```

Chequeá la config guardada. AGH enmascara el token:

```bash
agh config show
```

## 5. Crear un proyecto

```bash
agh project create \
  --repo-url "<your-git-remote-url>" \
  "<project-name>"
```

## 6. Linkear un repo

Corré esto dentro del repo cuyo remote matchea el proyecto:

```bash
agh sync
```

AGH escribe:

```text
.agh/project.toml
```

## 7. Elegir tu agent local y traer packs

Cada dev elige un target local por workspace. La selección se guarda en `.agh-cache/preferences.toml`, que es estado local de cache y no se commitea.

Definilo explícitamente:

```bash
agh agent select opencode
```

O corré pull en una terminal interactiva y elegí Claude Code, OpenCode o Skip for now cuando pregunte. Primero previsualizá:

```bash
agh pull --dry-run
```

Aplicá los cambios:

```bash
agh pull
```

Chequeá paths locales y la selección actual:

```bash
agh agent
agh agent show
```

## Archivos para commitear

Después de un pull exitoso, commiteá el estado estable:

- `.agh/project.toml`
- `.agh/lock.toml`
- `AGENTS.md` / `CLAUDE.md` cuando existan

Ignorá el cache:

```gitignore
.agh-cache/
```

Los skill targets bajo `.claude/skills/` o `.opencode/skills/` los genera el pull del workspace para el agent local seleccionado. Commitelos solo si tu equipo quiere revisar esos archivos en Git. Si son symlinks, refrescá el workspace después de clonar para reconstruir `.agh-cache/packs/`.
