# Quickstart

Levantá AGH con Docker, logueate con el primer token owner y aplicá los packs asignados desde un repo.

## 1. Levantar el server

Buildeá la imagen:

```bash
docker build -t agh .
```

Corré AGH con estado persistente bajo `/data`:

```bash
docker run --rm -p 8912:8912 -v agh-data:/data \
  -e AGH_BOOTSTRAP_OWNER_EMAIL=owner@example.com \
  agh
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

Desde el checkout de AGH:

```bash
uv tool install --force .
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

## 7. Traer los packs asignados

Primero previsualizá:

```bash
agh pull --dry-run
```

Aplicá los cambios:

```bash
agh pull
```

Chequeá paths locales de agents:

```bash
agh agent
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

Los skill targets bajo `.claude/skills/` y `.opencode/skills/` los genera el pull del workspace. Commitelos solo si tu equipo quiere revisar esos archivos en Git. Si son symlinks, refrescá el workspace después de clonar para reconstruir `.agh-cache/packs/`.
