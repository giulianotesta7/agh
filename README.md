<div align="center">

# Agent Guidance Hub (AGH)

<p><strong>Self-hosted guidance distribution for coding agents.</strong></p>

<p>
  <a href="https://pypi.org/project/agh/"><img alt="PyPI" src="https://img.shields.io/pypi/v/agh?color=1f6feb"></a>
  <a href="https://github.com/giulianotesta7/AgentGuidanceHub/pkgs/container/agent-guidance-hub"><img alt="GHCR" src="https://img.shields.io/badge/ghcr-agent--guidance--hub-1f6feb"></a>
  <a href="https://github.com/giulianotesta7/AgentGuidanceHub/actions/workflows/ci.yml"><img alt="CI" src="https://github.com/giulianotesta7/AgentGuidanceHub/actions/workflows/ci.yml/badge.svg"></a>
  <a href="https://github.com/giulianotesta7/AgentGuidanceHub/releases"><img alt="Release" src="https://img.shields.io/github/v/release/giulianotesta7/AgentGuidanceHub"></a>
</p>

</div>

[Español](README.es.md)

AGH gives teams one place to publish, version, assign, and pull reusable agent instructions and skills into their repos.

Use it when agent guidance needs the same discipline as infrastructure: reproducible changes, clear ownership, and self-hosted runtime.

## Why AGH

- **Centralize guidance** — publish shared `AGENTS.md`, `CLAUDE.md`, and skill files once.
- **Version every change** — packs are immutable SemVer releases assigned to projects.
- **Keep repos deterministic** — each workspace pulls a manifest, records `.agh/lock.toml`, and applies only the chosen agent.
- **Run it yourself** — host the server with Docker, SQLite, and persistent `/data` storage.

## How it works

```text
Pack author ── publish ──▶ AGH server ── assign ──▶ Project
                              │                         │
                              │                         ▼
                         SQLite + /data          Repo workspace
                                                       │
                                                       ├─ AGENTS.md + .opencode/skills/
                                                       └─ CLAUDE.md + .claude/skills/
```

Each developer chooses one agent for a workspace:

```bash
agh agent select opencode # or: agh agent select claude
```

AGH stores that choice in `.agh-cache/preferences.toml`; you do not commit it.

![AGH workspace pull demo](docs/assets/agh-workspace-demo.gif)

Demo source: [`docs/assets/agh-workspace-demo.tape`](docs/assets/agh-workspace-demo.tape).

## Quick start

Run the server with the published Docker image:

```bash
docker compose up -d
curl http://127.0.0.1:8912/api/v1/health
```

Install the CLI:

```bash
curl -fsSL https://raw.githubusercontent.com/giulianotesta7/AgentGuidanceHub/main/scripts/install.sh | sh
```

Or use uv directly:

```bash
uv tool install --force agh
```

Log in with the first owner token:

```bash
agh login \
  --url http://127.0.0.1:8912 \
  --email owner@example.com \
  --token "$(docker run --rm -v agh-data:/data busybox cat /data/secrets/initial_owner_token)"
```

Then work from a linked repo:

```bash
agh sync
agh agent select opencode # or: agh agent select claude
agh pull --dry-run
agh pull
agh agent
```

The default Compose image is:

```text
ghcr.io/giulianotesta7/agent-guidance-hub:${AGH_IMAGE_TAG:-latest}
```

Pin production deployments with a release tag:

```bash
AGH_IMAGE_TAG=0.2.0 docker compose up -d
```

## What gets committed

Commit the shared workspace state:

- `.agh/project.toml`
- `.agh/lock.toml`
- the generated target your team wants reviewed, such as `AGENTS.md` or `CLAUDE.md`

Do not commit local cache state:

```gitignore
.agh-cache/
```

AGH downloads packs to `.agh-cache/packs/` and stores each developer's agent choice in `.agh-cache/preferences.toml`.

AGH generates skill targets under `.claude/skills/` or `.opencode/skills/` for the selected agent. Commit them only if your team wants agent skills reviewed in Git.

## Docs

| Guide | Use it for |
|-------|------------|
| [Quickstart](docs/quickstart.md) | First Docker run, login, project link, and workspace apply flow. |
| [Installation](docs/installation.md) | CLI installer, checkout install, PATH troubleshooting, and uninstall. |
| [Packs](docs/packs.md) | Create, publish, and list instruction/skill packs. |
| [Projects](docs/projects.md) | Create projects and assign packs to repos. |
| [Admin](docs/admin.md) | Bootstrap owner, users, roles, tokens, and local config. |
| [Workspace guide](docs/workspace.md) | Repo setup, workspace apply behavior, markers, skills, lockfile, and Git rules. |
| [Operations](docs/operations.md) | Docker runtime layout, `/data`, logs, healthcheck, backup, and upgrades. |
| [Contributing](CONTRIBUTING.md) | Issue-first workflow, PR rules, and validation commands. |
| [Security](SECURITY.md) | Vulnerability reporting and supported security scope. |

## Status

AGH is an early self-hosted release for teams that want to own their agent guidance. It ships as a PyPI package and a GHCR server image.

## Development

```bash
uv sync
uv run pytest
```

For local server builds and development, see [Operations](docs/operations.md#local-development).
