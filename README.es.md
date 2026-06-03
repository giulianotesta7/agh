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

Levantá la imagen publicada del server con Docker Compose:

```bash
docker compose up -d
```

El compose file usa por defecto la imagen publicada más reciente:

```text
ghcr.io/giulianotesta7/agent-guidance-hub:${AGH_IMAGE_TAG:-latest}
```

Para pinnear un deployment de producción, definí `AGH_IMAGE_TAG` antes de levantar Compose:

```bash
AGH_IMAGE_TAG=0.1.2 docker compose up -d
```

Instalá el CLI local y logueate con el primer token owner:

```bash
uv tool install --force agh

agh login \
  --url http://127.0.0.1:8912 \
  --email owner@example.com \
  --token "$(docker run --rm -v agh-data:/data busybox cat /data/secrets/initial_owner_token)"
```

Después trabajá desde un repo:

```bash
agh sync
agh agent select opencode # o: agh agent select claude
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
| [Contribuir](CONTRIBUTING.md) | Flujo issue-first, reglas de PR y comandos de validación. |
| [Seguridad](SECURITY.md) | Reporte de vulnerabilidades y alcance de seguridad soportado. |

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
- el target del agente seleccionado, como `AGENTS.md` o `CLAUDE.md`

Ignorá el cache y la selección local de agente de cada dev:

```gitignore
.agh-cache/
```

Los skill targets bajo `.claude/skills/` u `.opencode/skills/` los genera el flujo de pull para el agente local seleccionado. Commitelos solo si tu equipo quiere revisar esos archivos en Git. Si son symlinks, refrescá el workspace después de clonar para reconstruir `.agh-cache/packs/`.

## Desarrollo

```bash
uv sync
uv run pytest
```

Para builds locales del server y desarrollo, mirá [Operaciones](docs/es/operations.md#desarrollo-local).
