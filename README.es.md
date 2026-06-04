<div align="center">

# Agent Guidance Hub (AGH)

<p><strong>Guidance para agentes de código, self-hosted.</strong></p>

<p>
  <a href="https://pypi.org/project/agh/"><img alt="PyPI" src="https://img.shields.io/pypi/v/agh?color=1f6feb"></a>
  <a href="https://github.com/giulianotesta7/AgentGuidanceHub/pkgs/container/agent-guidance-hub"><img alt="GHCR" src="https://img.shields.io/badge/ghcr-agent--guidance--hub-1f6feb"></a>
  <a href="https://github.com/giulianotesta7/AgentGuidanceHub/actions/workflows/ci.yml"><img alt="CI" src="https://github.com/giulianotesta7/AgentGuidanceHub/actions/workflows/ci.yml/badge.svg"></a>
  <a href="https://github.com/giulianotesta7/AgentGuidanceHub/releases"><img alt="Release" src="https://img.shields.io/github/v/release/giulianotesta7/AgentGuidanceHub"></a>
</p>

</div>

[English](README.md)

AGH le da a un equipo un lugar para publicar, versionar, asignar y traer instrucciones y skills reutilizables de agentes a sus repos.

Usalo cuando el guidance de agentes necesita la misma disciplina que la infraestructura: cambios reproducibles, ownership claro y un server propio.

## Por qué AGH

- **Centralizá el guidance** — publicá `AGENTS.md`, `CLAUDE.md` y archivos de skill compartidos una sola vez.
- **Versioná cada cambio** — los packs son releases SemVer inmutables asignados a proyectos.
- **Mantené repos determinísticos** — cada workspace trae un manifest, registra `.agh/lock.toml` y aplica solo el target del agente elegido.
- **Operalo vos** — corré el server con Docker, SQLite y storage persistente en `/data`.

## Cómo funciona

```text
Pack author ── publish ──▶ AGH server ── assign ──▶ Project
                              │                         │
                              │                         ▼
                         SQLite + /data          Repo workspace
                                                       │
                                                       ├─ AGENTS.md + .opencode/skills/
                                                       └─ CLAUDE.md + .claude/skills/
```

Cada dev elige un agente por workspace:

```bash
agh agent select opencode # o: agh agent select claude
```

AGH guarda esa elección en `.agh-cache/preferences.toml`; no la commiteás.

![Demo de pull de workspace en AGH](docs/assets/agh-workspace-demo.gif)

Fuente del demo: [`docs/assets/agh-workspace-demo.tape`](docs/assets/agh-workspace-demo.tape).

## Quick start

Levantá el server con la imagen Docker publicada:

```bash
docker compose up -d
curl http://127.0.0.1:8912/api/v1/health
```

Instalá el CLI:

```bash
curl -fsSL https://raw.githubusercontent.com/giulianotesta7/AgentGuidanceHub/main/scripts/install.sh | sh
```

O usá uv directo:

```bash
uv tool install --force agh
```

Logueate con el primer token owner:

```bash
agh login \
  --url http://127.0.0.1:8912 \
  --email owner@example.com \
  --token "$(docker run --rm -v agh-data:/data busybox cat /data/secrets/initial_owner_token)"
```

Después trabajá desde un repo conectado:

```bash
agh sync
agh agent select opencode # o: agh agent select claude
agh pull --dry-run
agh pull
agh agent
```

Compose usa esta imagen por defecto:

```text
ghcr.io/giulianotesta7/agent-guidance-hub:${AGH_IMAGE_TAG:-latest}
```

Pinneá deployments de producción con un release tag:

```bash
AGH_IMAGE_TAG=0.2.0 docker compose up -d
```

## Qué se commitea

Commiteá el estado compartido del workspace:

- `.agh/project.toml`
- `.agh/lock.toml`
- el target generado que tu equipo quiera revisar, como `AGENTS.md` o `CLAUDE.md`

No commitees estado local de cache:

```gitignore
.agh-cache/
```

AGH descarga packs en `.agh-cache/packs/` y guarda la elección de agente de cada dev en `.agh-cache/preferences.toml`.

AGH genera skill targets bajo `.claude/skills/` u `.opencode/skills/` para el agente elegido. Commitelos solo si tu equipo quiere revisar esos archivos en Git.

## Docs

| Guía | Usala para |
|------|------------|
| [Quickstart](docs/es/quickstart.md) | Primer run con Docker, login, link de proyecto y flujo de aplicación del workspace. |
| [Instalación](docs/es/installation.md) | Instalador del CLI, instalación desde checkout, PATH y desinstalación. |
| [Packs](docs/es/packs.md) | Crear, publicar y listar packs de instrucciones/skills. |
| [Proyectos](docs/es/projects.md) | Crear proyectos y asignar packs a repos. |
| [Admin](docs/es/admin.md) | Bootstrap owner, usuarios, roles, tokens y config local. |
| [Workspace](docs/es/workspace.md) | Setup de repo, aplicación del workspace, markers, skills, lockfile y reglas de Git. |
| [Operaciones](docs/es/operations.md) | Runtime Docker, `/data`, logs, healthcheck, backup y upgrades. |
| [Contribuir](CONTRIBUTING.md) | Flujo issue-first, reglas de PR y comandos de validación. |
| [Seguridad](SECURITY.md) | Reporte de vulnerabilidades y alcance de seguridad soportado. |

## Estado

AGH está en una etapa temprana y apunta a equipos que quieren controlar su guidance de agentes. Se publica como paquete PyPI e imagen server en GHCR.

## Desarrollo

```bash
uv sync
uv run pytest
```

Para builds locales del server y desarrollo, mirá [Operaciones](docs/es/operations.md#desarrollo-local).
