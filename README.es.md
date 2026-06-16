<div align="center">

# Agent Guidance Hub (AGH)

<p><strong>Guidance para agentes de código, self-hosted.</strong></p>

<p>
  <a href="https://pypi.org/project/agh/"><img alt="PyPI" src="https://img.shields.io/pypi/v/agh?color=1f6feb"></a>
  <a href="https://github.com/giulianotesta7/AgentGuidanceHub/pkgs/container/agent-guidance-hub"><img alt="GHCR" src="https://img.shields.io/badge/ghcr-agent--guidance--hub-1f6feb"></a>
  <a href="https://github.com/giulianotesta7/AgentGuidanceHub/actions/workflows/ci.yml"><img alt="CI" src="https://github.com/giulianotesta7/AgentGuidanceHub/actions/workflows/ci.yml/badge.svg"></a>
  <a href="https://github.com/giulianotesta7/AgentGuidanceHub/releases"><img alt="Release" src="https://img.shields.io/github/v/release/giulianotesta7/AgentGuidanceHub"></a>
</p>

<p>
  <a href="#instalar">instalar</a> · <a href="#quick-start">quick start</a> · <a href="#como-funciona-agh">cómo funciona</a> · <a href="#operaciones-del-server">operaciones</a> · <a href="#desarrollo">desarrollo</a> · <a href="README.md">english</a>
</p>

</div>

[English](README.md)

---

![Demo de pull de workspace en AGH](assets/agh-workspace-demo.gif)

**AGH le da a un equipo un lugar para publicar, versionar, asignar y pullear instrucciones y skills reutilizables de agentes a sus repos.**

Usalo cuando el guidance de agentes necesita la misma disciplina que la infraestructura: cambios reproducibles, ownership claro y un server propio. AGH está en una etapa temprana, es Docker-first y se publica como paquete PyPI, fórmula Homebrew e imagen server en GHCR.

- **Centralizá el guidance**: publicá `AGENTS.md`, `CLAUDE.md` y archivos de skill compartidos una sola vez.
- **Versioná cada cambio**: los packages son releases SemVer inmutables asignados a proyectos.
- **Mantené repos determinísticos**: cada workspace registra `.agh/lock.toml` y aplica solo el target del agente elegido.
- **Operalo vos**: corré el server con Docker, SQLite y storage persistente en `/data`.

---

## Instalar

Linux / macOS:

```bash
brew install giulianotesta7/tap/agh
```

o agregá el tap una vez:

```bash
brew tap giulianotesta7/tap
brew install agh
```

o instalá con script:

```bash
curl -fsSL https://raw.githubusercontent.com/giulianotesta7/AgentGuidanceHub/main/scripts/install.sh | sh
```

o instalá con uv:

```bash
uv tool install --force agh
```

desde un checkout:

```bash
git clone https://github.com/giulianotesta7/AgentGuidanceHub.git
cd AgentGuidanceHub
uv tool install --force .
```

probá el CLI:

```bash
agh --help
```

Levantá el server con la imagen Docker publicada:

```bash
docker compose up -d
curl http://127.0.0.1:8912/api/v1/health
```

Compose usa esta imagen por defecto:

```text
ghcr.io/giulianotesta7/agent-guidance-hub:${AGH_IMAGE_TAG:-latest}
```

Pinneá deployments de producción con un release tag:

```bash
AGH_IMAGE_TAG=0.2.0 docker compose up -d
```

## Quick start

Leé el primer token owner en el host donde corre AGH:

```bash
docker run --rm -v agh-data:/data busybox \
  cat /data/secrets/initial_owner_token
```

Después logueate desde tu máquina:

```bash
agh login \
  --url <instance-url> \
  --email owner@example.com \
  --token "<initial-owner-token>"
```

Chequeá la config guardada. AGH enmascara el token:

```bash
agh config show
```

Creá un proyecto con la URL que los devs usan en sus remotes de git:

```bash
agh project create "Agent Guidance Hub" \
  --repo-url https://github.com/giulianotesta7/AgentGuidanceHub.git
```

Trabajá desde un repo conectado:

```bash
agh sync
agh agent select opencode # o: agh agent select claude
agh pull --dry-run
agh pull
agh agent
agh agent show
```

<a id="como-funciona-agh"></a>

## Cómo funciona AGH

```text
Package author ── publish ──▶ AGH server ── assign ──▶ Project
                              │                         │
                              │                         ▼
                         SQLite + /data          Repo workspace
                                                       │
                                                       ├─ AGENTS.md + .opencode/skills/
                                                       └─ CLAUDE.md + .claude/skills/
```

| Pieza | Qué hace |
|-------|----------|
| Packages | Instrucciones compartidas, skills o ambas. Las versiones publicadas son inmutables. |
| Proyectos | Un repo git más las versiones de packages que tiene que usar. |
| Workspaces | Un repo local conectado con `agh sync`, un agente elegido y un lockfile commiteado. |

<details>
<summary><strong>Autoría de packages</strong></summary>

Un package arranca con esta forma:

```text
my-package/
├── agh.package.toml
├── instructions/
│   ├── AGENTS.md
│   └── CLAUDE.md
└── skills/
    └── reviewer/
        └── SKILL.md
```

Creá un template:

```bash
agh package init ./my-package --domain acme --name onboarding --version 1.0.0
```

El manifest arranca así:

```toml
domain = "acme"
name = "onboarding"
version = "1.0.0"
description = "TODO"
```

Flags útiles:

- `--with-agents` crea `instructions/AGENTS.md`.
- `--with-claude` crea `instructions/CLAUDE.md`.
- `--with-skill NAME` crea `skills/NAME/SKILL.md`.

Archivos permitidos:

- `agh.package.toml`
- `instructions/AGENTS.md`
- `instructions/CLAUDE.md`
- `skills/<name>/SKILL.md`

Reglas:

- Un package puede contener instrucciones, skills o ambas.
- Tiene que incluir al menos un archivo de instrucciones o una skill.
- `version` tiene que ser SemVer exacto, como `1.0.0`.
- Las versiones publicadas son inmutables. Publicá `1.0.1` para cambios.
- No publiques `latest`. Usá `latest` solo al asignar packages a proyectos.
- Usá archivos UTF-8. No incluyas symlinks.

Publicá y listá packages:

```bash
agh package publish ./my-package
agh package list
```

Salida de publish:

```text
Published acme/onboarding@1.0.0.
Package ID: pkg_...
Checksum: sha256:...
```

</details>

<details>
<summary><strong>Asignación a proyectos</strong></summary>

Un proyecto es un registro de AGH conectado a un repo git.

```bash
agh project create "Agent Guidance Hub" \
  --repo-url https://github.com/giulianotesta7/AgentGuidanceHub.git
agh project list
agh project get prj_...
agh project update prj_... --name "App API"
agh project delete prj_...
```

Asigna packages de forma interactiva o directa:

```bash
agh project package add
agh project package add prj_...
agh project package add prj_... acme/onboarding@latest
agh project package add prj_... onboarding@1.0.0
agh project package list prj_...
agh project package update prj_... asn_... --package-ref acme/onboarding@1.0.0
agh project package remove prj_... asn_...
```

- `agh project package add` guía la selección del proyecto, la selección de un package sin asignar y la confirmación.
- `agh project package add <project>` omite la selección del proyecto, muestra packages sin asignar para ese proyecto y pide confirmación.
- `agh project package add <project> <package-ref>` asigna directamente sin prompts, adecuado para scripts y CI.

`asn_...` identifica la asignación entre proyecto y package. Usa una versión exacta para fijar el proyecto. Usa `latest` cuando el proyecto tenga que resolver la versión publicada más nueva durante el pull.

Durante el pull del workspace, AGH escribe la versión concreta y el checksum en `.agh/lock.toml`.

</details>

<details>
<summary><strong>Pull del workspace y estado en Git</strong></summary>

| Comando | Qué hace |
|---------|----------|
| `agh sync` | Matchea el remote de git con un proyecto AGH y escribe `.agh/project.toml`. |
| `agh agent` / `agh agent show` | Muestra disponibilidad de Claude Code/OpenCode y la selección local actual. |
| `agh agent select claude` | Selecciona Claude Code para este workspace. |
| `agh agent select opencode` | Selecciona OpenCode para este workspace. |
| `agh agent clear` | Borra la selección local del workspace. |
| `agh pull --dry-run` | Pide el plan al server sin escribir archivos del repo. |
| `agh pull` | Aplica instrucciones y skills del agente elegido y escribe `.agh/lock.toml`. |
| `agh pull --force` | Reemplaza bloques AGH o skill targets en conflicto. |

No hay opción `both`. Si no hay agente seleccionado, `agh pull` interactivo pregunta cuál usar. Skip sale con código `2` y no escribe nada.

Los archivos de instrucciones usan bloques administrados:

```md
<!-- AGH-BEGIN package="<package-ref>" artifact="instructions/AGENTS.md" checksum="sha256:..." -->
Las instrucciones del proyecto viven acá.
<!-- AGH-END package="<package-ref>" -->
```

Si editás dentro del bloque, el siguiente `agh pull` sale con código de conflicto `3`. Usá `agh pull --force` cuando AGH tenga que reemplazarlo.

Las skills van donde los agentes ya las buscan:

```text
.claude/skills/<skill>/SKILL.md
.opencode/skills/<skill>/SKILL.md
```

AGH intenta usar un symlink relativo a `.agh-cache/packages/...`. Si el SO rechaza symlinks, copia el archivo. El lockfile registra el modo:

```toml
[[packages]]
package_ref = "acme/onboarding@1.0.0"

[[artifacts]]
package_ref = "acme/onboarding@1.0.0"
path = "skills/reviewer/SKILL.md"
target_path = ".opencode/skills/reviewer/SKILL.md"
mode = "symlink" # o mode = "copy"
source = ".agh-cache/packages/acme/onboarding/1.0.0/skills/reviewer/SKILL.md"
```

Commiteá el estado compartido del workspace:

- `.agh/project.toml`
- `.agh/lock.toml`
- `AGENTS.md` / `CLAUDE.md` generados cuando tu equipo quiera revisarlos
- `.claude/skills/` u `.opencode/skills/` generados cuando tu equipo quiera revisar skills

No commitees estado local de cache:

```gitignore
.agh-cache/
```

AGH descarga packages en `.agh-cache/packages/` y guarda la elección de agente de cada dev en `.agh-cache/preferences.toml`. Si los skill targets son symlinks, un clone nuevo necesita `agh pull` para reconstruir el cache antes de que esos links resuelvan.

Exit codes:

| Código | Significado |
|--------|-------------|
| `0` | Éxito o sin cambios. |
| `1` | Error runtime/API/download. |
| `2` | Validación local, manifest inválido o selección de agente faltante/skipped. |
| `3` | Conflicto. |
| `4` | Error de autenticación/autorización. |
| `5` | Workspace sin link; corré `agh sync`. |

</details>

## Operaciones del server

El primer token owner se escribe una sola vez:

```text
/data/secrets/initial_owner_token
```

Guardalo. AGH no lo vuelve a mostrar. El server guarda hashes de tokens, no tokens en texto plano.

| Rol | Uso |
|-----|-----|
| `owner` | Acceso admin completo, incluyendo ownership inicial. |
| `admin` | Gestiona usuarios, proyectos, packages y asignaciones. |
| `member` | Uso diario desde workspaces. |

Comandos admin:

```bash
agh user list
agh user create user@example.com --role admin
agh user update usr_... --role member
agh user delete usr_...
agh token rotate
agh token reset usr_...
agh config show
```

`agh config show` enmascara el token guardado como `token = ****`.

El estado runtime vive bajo `/data`:

| Path | Uso |
|------|-----|
| `/data/agh.sqlite3` | Base SQLite. |
| `/data/packages/` | Payloads de packages publicados. |
| `/data/logs/agh.log` | Log del server. |
| `/data/secrets/initial_owner_token` | Primer owner token, creado una vez. |

La imagen deja `/data` como `agh:agh` (`10001:10001`) durante el build.
Los named volumes de Docker se inicializan desde ese árbol `/data` ya preparado en la imagen.
Los bind mounts tienen que ser escribibles previamente por UID/GID `10001:10001`; el container no repara ownership del host.

Docker run directo:

```bash
docker run --rm -p 8912:8912 -v agh-data:/data \
  -e AGH_BOOTSTRAP_OWNER_EMAIL=owner@example.com \
  ghcr.io/giulianotesta7/agent-guidance-hub:0.2.0
```

Healthcheck:

```bash
curl http://127.0.0.1:8912/api/v1/health
```

Backup mínimo:

```text
/data/agh.sqlite3
/data/packages/
/data/secrets/
```

Actualizá pinneando el siguiente image tag y reiniciando:

```bash
AGH_IMAGE_TAG=0.2.0 docker compose pull
AGH_IMAGE_TAG=0.2.0 docker compose up -d
```

## Desarrollo

```bash
uv sync
uv run pytest
uv run uvicorn agh.server.app:app --host 0.0.0.0 --port 8912
```

Los datos locales usan `.agh-data/` por defecto.

Contribución y seguridad:

- [Contributing](CONTRIBUTING.md)
- [Security](SECURITY.md)
