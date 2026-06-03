<div align="center">

# Agent Guidance Hub (AGH)

<p><strong>Self-hosted agent instructions and skills, synced per repo.</strong></p>

</div>

---

[Español](README.es.md)

## What AGH is for

AGH gives teams one place to publish the instructions and reusable skills their coding agents use in repos: `AGENTS.md`, `CLAUDE.md`, and skill files placed under agent harness directories.

Without AGH, those files tend to drift from repo to repo. With AGH, you publish a versioned pack, assign it to a project, and apply the assigned files in each repo.

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

Run the published server image with Docker Compose:

```bash
docker compose up -d
```

The default compose file uses the latest published image:

```text
ghcr.io/giulianotesta7/agent-guidance-hub:${AGH_IMAGE_TAG:-latest}
```

To pin a production deployment, set `AGH_IMAGE_TAG` before starting Compose:

```bash
AGH_IMAGE_TAG=0.1.2 docker compose up -d
```

Install the local CLI, then log in with the first owner token:

```bash
uv tool install --force agh

agh login \
  --url http://127.0.0.1:8912 \
  --email owner@example.com \
  --token "$(docker run --rm -v agh-data:/data busybox cat /data/secrets/initial_owner_token)"
```

Then work from a repo:

```bash
agh sync
agh agent select opencode # or: agh agent select claude
agh pull --dry-run
agh pull
agh agent
```

## Docs

| Guide | Use it for |
|-------|------------|
| [Installation](docs/installation.md) | Install the local `agh` CLI and run the Docker server. |
| [Quickstart](docs/quickstart.md) | First Docker run, login, project link, and workspace apply flow. |
| [Packs](docs/packs.md) | Create, publish, and list instruction/skill packs. |
| [Projects](docs/projects.md) | Create projects and assign packs to repos. |
| [Admin](docs/admin.md) | Bootstrap owner, users, roles, tokens, and local config. |
| [Workspace guide](docs/workspace.md) | Repo setup, workspace apply behavior, markers, skills, lockfile, and Git rules. |
| [Operations](docs/operations.md) | Docker runtime layout, `/data`, logs, healthcheck, backup, and upgrades. |
| [Contributing](CONTRIBUTING.md) | Issue-first workflow, PR rules, and validation commands. |
| [Security](SECURITY.md) | Vulnerability reporting and supported security scope. |

## Core Concepts

| Concept | Meaning |
|---------|---------|
| Pack | Versioned set of instruction files and agent skills. |
| Project | AGH record linked to a git repository. |
| Pull manifest | Server plan for the files a repo should download and apply. |
| Lockfile | `.agh/lock.toml`; resolved versions, checksums, sources, and placement mode. |
| Cache | `.agh-cache/packs/`; downloaded pack files that AGH can rebuild. |

## Git Rule

Commit the stable project state:

- `.agh/project.toml`
- `.agh/lock.toml`
- the selected agent target, such as `AGENTS.md` or `CLAUDE.md`

Ignore the cache and each developer's local agent selection:

```gitignore
.agh-cache/
```

Skill targets under `.claude/skills/` or `.opencode/skills/` are generated for the selected local agent. Commit them only if your team wants agent skills reviewed in Git. If they are symlinks, refresh the workspace after clone to rebuild `.agh-cache/packs/`.

## Development

```bash
uv sync
uv run pytest
```

For local server builds and development, see [Operations](docs/operations.md#local-development).
