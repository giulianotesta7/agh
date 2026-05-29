# Tasks: Bootstrap Agent Guidance Hub MVP

Model note: task plan prepared on `openai-codex/gpt-5.5`.

## Review Workload Forecast

| Field | Value |
|-------|-------|
| Estimated changed lines | 3,000-5,000 |
| 400-line budget risk | High |
| Chained PRs recommended | Yes |
| Suggested split | PR 1 scaffold → PR 2 auth/storage → PR 3 users/projects/sync → PR 4 packs/assignments → PR 5 pull core → PR 6 agents/Docker/docs |
| Delivery strategy | ask-on-risk |
| Chain strategy | stacked-to-main |

Decision needed before apply: No
Chained PRs recommended: Yes
Chain strategy: stacked-to-main
400-line budget risk: High

### Suggested Work Units

| Unit | Goal | Likely PR | Notes |
|------|------|-----------|-------|
| 1 | Scaffold, pytest, health, logging | PR 1 | Starts from greenfield; finish with `pytest` and Docker health. |
| 2 | SQLite migrations, bootstrap, auth, login | PR 2 | Depends PR 1; rollback removes DB/bootstrap slice. |
| 3 | User/project APIs and `agh sync` | PR 3 | Depends PR 2; verifies URL matching and membership. |
| 4 | Pack publish, storage, assignment, manifest | PR 4 | Depends PR 3; verifies immutable SemVer/latest. |
| 5 | Pull markers, dry-run/conflicts, lock/cache | PR 5 | Depends PR 4; high-risk pull behavior isolated. |
| 6 | Agent skills fallback, Docker polish, docs/tests | PR 6 | Depends PR 5; verifies Claude/OpenCode paths. |

## Phase 1: Scaffold and Test Runner

- [x] 1.1 Create `pyproject.toml`, `agh/__init__.py`, `agh/server/app.py`, `agh/cli/main.py`, and `tests/` with FastAPI, Typer, pytest dependencies and `agh` entrypoint.
- [x] 1.2 Add RED smoke tests in `tests/test_scaffold.py` for `GET /api/v1/health`, `agh --help`, `$AGH_DATA_DIR/logs/agh.log` creation, and default port constant `8912`.
- [x] 1.3 Implement health route, Typer help, basic stdout/file logging, `Dockerfile` health check, then run `uv run pytest`.
- [x] 1.4 Update `openspec/config.yaml` `apply.test_command`, `verify.test_command`, and testing runner fields to the verified `uv run pytest` command.

## Phase 2: Common Validation, Storage, Auth Bootstrap

- [x] 2.1 Add `agh/common/ids.py`, `validation.py`, `repo_url.py`, `pack_manifest.py`, `checksums.py` with unit tests for prefixed IDs, email, slug/SemVer/latest, URL normalization, and managed payload hashes.
- [ ] 2.2 Add `agh/server/db.py` and `agh/server/migrations/*.sql` for users, tokens, projects, memberships, packs, versions, assignments, and `schema_migrations`; test migration idempotency on SQLite.
  - PR2B-1 partial: SQLite connection helper, initial migration, and idempotency/schema tests implemented; checkbox remains open for parent-controlled Phase 2 completion.
- [x] 2.3 Add `agh/server/auth.py`, bootstrap startup, hashed Bearer tokens, `/api/v1/me`, and secret write to `/data/secrets/initial_owner_token`; test no token logging and no re-bootstrap.
- [ ] 2.4 Add `agh/cli/config.py` and `login` command storing `~/.config/agh/config.toml` mode `0600` after validating `/api/v1/me`; test invalid login preserves prior config.

## Phase 3: Users, Projects, and Sync

- [ ] 3.1 Add user CRUD/token rotate/reset routes in `agh/server/routes/users.py` plus role/owner-protection tests.
- [ ] 3.2 Add project CRUD, duplicate normalized URL `409`, developer membership, and access checks in `agh/server/routes/projects.py`; test inactive project denial.
- [ ] 3.3 Add Typer `user`, `token`, and `project` command groups in `agh/cli/main.py` mapping to `/api/v1` and masking secrets in config output.
- [ ] 3.4 Add `agh/cli/workspace_sync.py` for git remote lookup, no `--project`, `.agh/project.toml`, `--remote`, and `--force` link-only behavior; test with temp git repos.

## Phase 4: Packs, Assignments, and Pull Manifest

- [ ] 4.1 Add filesystem pack storage under `/data/packs/` and pack publish/list/file routes in `agh/server/routes/packs.py`; test required `agh.pack.toml`, instruction sources, skills, immutability, and no `latest` publish.
- [ ] 4.2 Add project-pack assignment routes and `latest` resolution by highest SemVer; test ordering by `position ASC`, then `domain/name ASC`.
- [ ] 4.3 Add pull-manifest schema and file download URLs in `agh/server/routes/projects.py`; test project developer authorization and resolved concrete versions.
- [ ] 4.4 Add CLI `pack publish/list` and project assignment commands with manifest validation errors surfaced as exit code `2`.

## Phase 5: Pull Core

- [ ] 5.1 Add `agh/cli/pull_markers.py` for AGH BEGIN/END parsing, normalized payload checksums, insert/update without replacing unmanaged content; test mismatch detection.
- [ ] 5.2 Add `agh/cli/pull_plan.py` for dry-run/conflict planning and exit codes `0/1/2/3/4/5`; test dry-run writes nothing and conflicts return `3`.
- [ ] 5.3 Add `.agh/packs/` cache downloads and `.agh/lock.toml` atomic writes in `agh/cli/workspace_pull.py`; test cache population and lock contents.
- [ ] 5.4 Wire `agh pull --dry-run/--force` to pull-manifest, marker planning, cache, and lock updates; test force overwrites checksum conflicts only in managed blocks.

## Phase 6: Agents, Docker, Verification

- [ ] 6.1 Add Claude/OpenCode instruction targets and skill placement in `agh/cli/agent_integrations.py`, trying relative symlink then copy fallback with lock `mode`; test fallback paths.
- [ ] 6.2 Add `agh agent` advisory output with Claude/OpenCode ✓/✗ detection; test absent agents do not fail.
- [ ] 6.3 Finalize `Dockerfile`, `/data` directory creation, log file append behavior, and health probe docs/comments; verify container serves `:8912`.
- [ ] 6.4 Expand integration tests across auth, API JSON errors, projects, packs, sync, pull, and VCS hints to commit `.agh/project.toml`/`.agh/lock.toml` and ignore `.agh/packs/`.
