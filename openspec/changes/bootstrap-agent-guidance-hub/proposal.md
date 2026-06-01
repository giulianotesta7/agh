# Proposal: Bootstrap Agent Guidance Hub MVP

## Intent

Teams lack a single place to publish, version, and distribute agent guidance (instructions, rules, skills) into developer repositories. The `aictx` repository is harness-only today—no FastAPI service, no `agh` CLI, no specs, and no tests. This change bootstraps **Agent Guidance Hub (AGH)**: a self-hosted control plane plus local CLI so owners/admins can manage packs and developers can `sync` and `pull` guidance into repos with checksum-backed managed blocks.

## Scope

### In Scope

- Single Python distribution with `agh.server`, `agh.cli`, `agh.common`; separate server (Docker) and CLI install artifacts
- FastAPI `/api/v1` on port **8912**; SQLite metadata + filesystem pack storage under `/data/`
- Bootstrap owner from `AGH_BOOTSTRAP_OWNER_EMAIL`; initial token file at `/data/secrets/initial_owner_token` (path logged only)
- Auth: email user IDs, hashed API tokens (no auto-expiry), roles `owner` / `admin` / `member`, owner protection
- Projects linked to normalized git remote URLs; role-less developer membership; project–pack assignments (`latest` supported)
- Packs `<domain>/<name>@<version>` with required `agh.pack.toml`, instructions (`AGENTS.md` / `CLAUDE.md`), optional skills
- CLI: `login`, config, project/user/token/pack commands, `agh sync` (git remote match only), `agh pull` (managed blocks, lockfile, cache, conflicts), `agh agent` (Claude + OpenCode availability)
- Aggregate pull-manifest API; container logging to stdout/stderr and `/data/logs/agh.log`
- Capability specs under `openspec/specs/{auth,storage,api,projects,packs,cli,workspace}/`
- First apply slice: `pytest`, `pyproject`, Docker health check, update `openspec/config.yaml` test commands

### Out of Scope

- Web UI, SSO/LDAP, automatic token expiry, pack signing, webhooks, HA/S3, public marketplace
- Cursor/Codex/Pi integrations beyond Claude/OpenCode MVP
- Manual `agh sync --project` override; `default.md` instruction fallback; publish approval; offline-only publish

## Capabilities

> Contract for `sdd-spec`. Greenfield—no existing `openspec/specs/` to modify.

### New Capabilities

| Capability | Covers |
|------------|--------|
| `auth` | Bootstrap owner + secret file; token hashing; email identity; `owner`/`admin`/`member`; admin/member CRUD; owner protection; token rotate/reset |
| `storage` | SQLite schema; pack blobs on disk; `/data/` layout (secrets, logs, packs); bootstrap secret path policy |
| `api` | `/api/v1` routing; prefixed IDs; auth middleware; health; pull-manifest response schema |
| `projects` | Project CRUD; normalized repo URL; duplicate-URL policy; role-less membership; project–pack assignment |
| `packs` | Pack ID format; `agh.pack.toml` validation; immutable SemVer publish; `latest` resolution for assignment/consumption |
| `cli` | Typer `agh` binary; `~/.config/agh/config.toml` permissions; login validation via `/api/v1/me`; admin/dev commands |
| `workspace` | `agh sync` (remote URL match, `--force` link-only); `agh pull` (managed markers, checksums, `.agh/lock.toml`, `.agh-cache/packs` cache, `--dry-run`/`--force`); Claude/OpenCode paths; VCS guidance (commit project+lock, ignore cache) |

### Modified Capabilities

None.

## Approach

1. **One SDD change, chained apply** — keep planning unified; implement in review-safe slices (see forecast).
2. **Monorepo modules** — one distribution, internal `server` / `cli` / `common`; defer split wheels until post-MVP.
3. **Server-first contracts** — define pull-manifest and auth header in `api` spec before `cli`/`workspace` apply slices.
4. **Managed blocks (4a)** — marker delimiters + checksums; never full-file blind replace.
5. **Resolve open design in spec/design** — block grammar, Bearer vs custom header, domain/name rules, migration strategy, conflict exit codes, duplicate repo URLs, Windows symlink fallback.

## Affected Areas

| Area | Impact | Description |
|------|--------|-------------|
| `agh/server/` | New | FastAPI app, middleware, bootstrap, `/api/v1` |
| `agh/cli/` | New | Typer commands: login, project, user, token, pack, sync, pull, agent |
| `agh/common/` | New | IDs, URL normalization, manifest validation, checksums |
| `pyproject.toml`, `Dockerfile` | New | Packaging, `:8912`, `/data` volumes |
| `openspec/specs/*` | New | Seven capability specs |
| `openspec/config.yaml` | Modified | Test/lint commands after slice A |
| Consumer repos | New behavior | `.agh/project.toml`, `.agh/lock.toml`, managed files, agent skill paths |

## Risks

| Risk | Likelihood | Mitigation |
|------|------------|------------|
| `agh pull` complexity (markers, conflicts, cache) | High | Spec block grammar + exit codes early; split apply slice H into H1/H2 |
| Review budget exceeded on monolithic PR | High | Mandatory chained slices; no slice >400 lines without exception |
| Git URL normalization edge cases | Med | Shared `agh.common` normalizer; spec duplicate-URL behavior |
| Greenfield—no test anchors | Med | Slice A adds pytest + smoke tests per slice |
| Windows symlink limitations | Med | Spec copy fallback for skills; test on non-Unix in verify |
| Open API/auth choices block CLI | Med | Lock in `api`/`auth` specs before workspace apply |

## Rollback / Recovery

- **Per slice**: revert PR; redeploy previous Docker tag; CLI remains backward-compatible if API unchanged.
- **Database**: SQLite file on volume—restore snapshot from before migration; document manual downgrade steps in slice PRs.
- **Bootstrap secret**: rotating bootstrap file does not re-issue owner; recovery via existing owner token or volume restore.
- **Consumer repos**: `agh pull --dry-run` before apply; users can `--force` managed blocks or restore from git; lockfile pins known-good state.
- **Full MVP rollback**: stop container, restore `/data` volume + DB backup, pin CLI to prior release; consumer `.agh/*` is git-revertible.

## Dependencies

- Python 3.11+, FastAPI, Typer, SQLite
- Docker for self-hosted server deployment
- Git available locally for `agh sync`

## Success Criteria

- [ ] Docker image serves health on `:8912`; logs to stdout and `/data/logs/agh.log`
- [ ] First start creates owner; token written only to `/data/secrets/initial_owner_token`
- [ ] `agh login` persists config and passes `/api/v1/me`
- [ ] Admins manage members; owners create admins; owners cannot be demoted/deleted
- [ ] Projects match normalized git URLs; `agh sync` links repo without manual project override
- [ ] Packs publish with immutable versions; assignments resolve `latest`
- [ ] `agh pull` updates managed blocks, lockfile, cache; detects conflicts; supports `--dry-run` and `--force`
- [ ] Claude and OpenCode integrations show availability; skills land in documented paths
- [ ] `pytest` runs via `openspec/config.yaml` commands; each apply slice has verification steps

## Review Workload Forecast

| Guard | Value |
|-------|-------|
| Decision needed before apply | **Yes** |
| Chained PRs recommended | **Yes** (`chained_pr_strategy: auto-forecast`) |
| 400-line budget risk | **High** |

| Slice | Scope | Est. risk |
|-------|-------|-----------|
| A | `pyproject`, Docker, health `:8912`, logging, pytest | Low |
| B | DB, bootstrap owner, token hash, `/me`, `agh login` | Medium |
| C | User roles/CRUD, owner protection, token rotate/reset | Medium |
| D | Projects, URL normalization, membership, CLI project cmds | Med–High |
| E | Packs, `agh.pack.toml`, publish, immutable versions | High |
| F | Project–pack assignment | Medium |
| G | `agh sync`, `.agh/project.toml` | Medium |
| H | `agh pull`, lockfile, cache, markers, agents, conflicts | High — **split H1/H2** |

Total MVP implementation will exceed a single 400-line PR; treat slices as stacked PRs with autonomous verify/rollback per slice.
