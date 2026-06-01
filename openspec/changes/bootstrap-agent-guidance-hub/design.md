# Design: Bootstrap Agent Guidance Hub MVP

## Technical Approach

Build one Python distribution with `agh.server`, `agh.cli`, and `agh.common`. Server owns FastAPI `/api/v1`, SQLite metadata, `/data` pack storage, bootstrap, and logging. CLI owns Typer UX plus local workspace writes. `agh.common` owns shared validation: prefixed IDs, email, SemVer, pack slugs, repo URL normalization, manifests, managed-block checksums.

## Architecture Decisions

| Topic | Decision | Alternatives / rationale |
|---|---|---|
| Auth header | `Authorization: Bearer <token>`; inactive users return `403`, invalid/missing token `401`. | Custom headers add no value; Bearer matches spec and HTTP tooling. |
| DB migrations | Lightweight versioned SQL migrations in `agh.server.migrations` with `schema_migrations(version, applied_at)`. | Alembic is stronger long-term but heavy for SQLite MVP/greenfield. |
| Duplicate repo URL | Reject active duplicate normalized URLs with `409 Conflict`; deactivated projects do not reserve URLs. | Ambiguous sync is worse than admin correction. |
| Pack slugs | `domain`/`name`: lowercase ASCII `^[a-z0-9](?:[a-z0-9-]{0,61}[a-z0-9])?$`; no `latest` as domain/name; SemVer exact for publish. | Human-readable, filesystem-safe, free domains without central registry. |
| Managed markers | HTML comments: `<!-- AGH-BEGIN pack="domain/name@version" artifact="instructions/AGENTS.md" checksum="sha256:<hex>" -->` and `<!-- AGH-END pack="..." -->`. Checksum is SHA-256 of normalized managed payload bytes: UTF-8, LF line endings, exactly one trailing newline. | Comments are valid in Markdown; checksum excludes markers so metadata can change. |
| Exit codes | `0` success/no-op/dry-run without conflicts; `1` generic/runtime/API; `2` validation/usage; `3` pull conflict; `4` auth; `5` not linked/no matching project. Dry-run returns `3` if it would conflict. | Stable scripting contract. |
| Skills on Windows | Try relative symlink from agent skill path to `.agh-cache/packs/...`; on failure or Windows without privilege, copy file and record `mode="copy"` in lock. | Preserves Unix cache benefits while working by default on Windows. |
| Pull ordering | Apply project assignments by `position ASC`, then `domain/name ASC`; artifacts apply instructions before skills. | Deterministic and admin-controllable. |

## Data Flow

`agh pull` reads `.agh/project.toml` → GET pull-manifest → downloads/caches artifacts → computes target edits → validates existing checksums → writes managed blocks/skills + `.agh/lock.toml` atomically. `--dry-run` stops before writes; `--force` permits checksum replacement.

## File Changes

| File | Action | Description |
|---|---|---|
| `pyproject.toml`, `Dockerfile` | Create | Package, dependencies, `agh` entrypoint, server image. |
| `agh/common/*` | Create | IDs, validation, TOML models, URL normalization, checksums. |
| `agh/server/*` | Create | FastAPI app, routes, auth, DB, storage, migrations, logging. |
| `agh/cli/*` | Create | Typer commands and workspace applier. |
| `tests/*` | Create | Pytest unit/integration coverage. |
| `openspec/config.yaml` | Modify | Add verified test/lint commands after slice A. |

## Interfaces / Contracts

### Data model

Tables: `users(id,email unique,role,active,created_at,updated_at)`, `tokens(id,user_id,token_hash,created_at,revoked_at)` where `token_hash` stores the hashed API token only, `projects(id,name,repo_url,repo_url_normalized,active)`, `project_members(project_id,user_id)`, `packs(id,domain,name,created_by)`, `pack_versions(id,pack_id,version,manifest_json,storage_path,created_at,checksum)`, `project_packs(id,project_id,pack_id,version_ref,position,active)`.

### API route map

Public: `GET /api/v1/health`. Auth: `GET /api/v1/me`; `GET/POST/PATCH/DELETE /users`; `POST /users/{id}/token:rotate`; `GET/POST/PATCH/DELETE /projects`; `PUT/DELETE /projects/{id}/members/{user_id}`; `GET/POST /projects/{id}/packs`; `PATCH/DELETE /projects/{id}/packs/{assignment_id}`; `GET /projects/{id}/pull-manifest`; `GET/POST /packs`; `GET /packs/{domain}/{name}/versions/{version}/files/{path}`. JSON errors use `{error:{code,message}}`.

Pull-manifest shape: `{project:{id,name,repo_url_normalized}, packs:[{id:"domain/name@resolved", assignment_id, position, manifest, artifacts:[{kind:"instruction|skill", path, target_agent, target_path, checksum, download_url}]}]}`.

### Local formats

`~/.config/agh/config.toml`: `instance_url`, `email`, `token` (0600). `.agh/project.toml`: `instance_url`, `project_id`, `repo_url_normalized`, `synced_at`. `.agh/lock.toml`: `version=1`, `packs[]`, `artifacts[] {target_path, checksum, mode, source}`. `.agh-cache/packs/<domain>/<name>/<version>/...` mirrors pack source layout: `agh.pack.toml`, `instructions/`, `skills/<skill>/SKILL.md`.

### CLI mapping

`login/config` use config + `/me`; `user/token/project/pack` map to API CRUD/publish; `sync` uses git remote + project list/search then writes `.agh/project.toml`; `pull` uses pull-manifest and filesystem applier; `agent` inspects Claude/OpenCode availability and current workspace.

## Testing Strategy

| Layer | What | Approach |
|---|---|---|
| Unit | validators, URL normalization, SemVer/latest, checksums, migration runner | pytest temp dirs/SQLite |
| Integration | bootstrap, auth middleware, role checks, CRUD, pull-manifest | FastAPI TestClient |
| CLI/workspace | login config permissions, sync, dry-run/force/conflicts, symlink-copy fallback | Typer CliRunner + temp git repos |

First slice adds pytest and smoke tests: health endpoint, logging path creation, `agh --help`.

## Migration / Rollout

No existing app data. Migrations run at server startup before bootstrap; each chained slice adds forward SQL only. Implement as stacked review units under 400 changed lines: A scaffold/health/tests; B DB/bootstrap/login; C users/tokens; D projects/sync; E packs/publish; F assignments/manifest; G pull core markers/lock/cache; H agent skills/platform fallback. No unresolved design questions.