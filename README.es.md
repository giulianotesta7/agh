<div align="center">

# Agent Guidance Hub (AGH)

<p><strong>Instrucciones y skills para agentes de código, self-hosted y sincronizadas por repo.</strong></p>

</div>

---

[English](README.md)

## Para qué sirve AGH

AGH le da a un equipo un lugar para publicar las instrucciones y skills reutilizables que usan sus agentes de código en los repos: `AGENTS.md`, `CLAUDE.md` y archivos de skill ubicados bajo directorios de cada harness.

Sin AGH, esos archivos terminan copiándose a mano y desalineados entre repos. Con AGH, publicás un pack versionado, lo asignás a un proyecto y aplicás los archivos asignados en cada repo.

```text
AGH Docker service
  ├─ /data/agh.sqlite3
  ├─ /data/packs/
  ├─ /data/logs/agh.log
  └─ /data/secrets/initial_owner_token
        ↓ manifest + pack downloads
repository
  ├─ AGENTS.md / CLAUDE.md
  ├─ .claude/skills/.../SKILL.md
  ├─ .opencode/skills/.../SKILL.md
  └─ .agh/lock.toml
```

## Quick Start

Levantá el server con Docker:

```bash
docker build -t agh .
docker run --rm -p 8912:8912 -v agh-data:/data \
  -e AGH_BOOTSTRAP_OWNER_EMAIL=owner@example.com \
  agh
```

Instalá el CLI local y logueate con el primer token owner:

```bash
uv tool install --force .

agh login \
  --url http://127.0.0.1:8912 \
  --email owner@example.com \
  --token "$(docker run --rm -v agh-data:/data busybox cat /data/secrets/initial_owner_token)"
```

Después trabajá desde un repo:

```bash
agh sync
agh pull --dry-run
agh pull
agh agent
```

## Docs

| Guía | Usala para |
|------|------------|
| [Instalación](docs/es/installation.md) | Instalar el CLI local `agh` y correr el server Docker. |
| [Quickstart](docs/es/quickstart.md) | Primer run con Docker, login, link de proyecto y flujo de aplicación del workspace. |
| [Packs](docs/es/packs.md) | Crear, publicar y listar packs de instrucciones/skills. |
| [Proyectos](docs/es/projects.md) | Crear proyectos y asignar packs a repos. |
| [Admin](docs/es/admin.md) | Bootstrap owner, usuarios, roles, tokens y config local. |
| [Workspace](docs/es/workspace.md) | Setup de repo, aplicación del workspace, markers, skills, lockfile y reglas de Git. |
| [Operaciones](docs/es/operations.md) | Runtime Docker, `/data`, logs, healthcheck, backup y upgrades. |
| [Release checklist](docs/release-checklist.md) | Validación pre-tag de paquete, Docker, CLI, docs y smoke tests. |

## Conceptos

| Concepto | Significado |
|----------|-------------|
| Pack | Conjunto versionado de archivos de instrucciones y agent skills. |
| Project | Registro de AGH asociado a un repositorio git. |
| Pull manifest | Plan del server con los archivos que un repo debe descargar y aplicar. |
| Lockfile | `.agh/lock.toml`; versiones resueltas, checksums, sources y modo de placement. |
| Cache | `.agh-cache/packs/`; archivos descargados que AGH puede reconstruir. |

## Regla con Git

Commiteá el estado estable del proyecto:

- `.agh/project.toml`
- `.agh/lock.toml`
- `AGENTS.md` / `CLAUDE.md`

Ignorá el cache:

```gitignore
.agh-cache/
```

Los skill targets bajo `.claude/skills/` y `.opencode/skills/` los genera el flujo de pull del workspace. Commitelos solo si tu equipo quiere revisar esos archivos en Git. Si son symlinks, refrescá el workspace después de clonar para reconstruir `.agh-cache/packs/`.

## Desarrollo

```bash
uv sync
uv run pytest
```

Para correr el server local sin Docker, mirá [Operaciones](docs/es/operations.md#desarrollo-local).
