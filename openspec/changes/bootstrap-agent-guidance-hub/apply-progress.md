# Apply Progress: bootstrap-agent-guidance-hub

**Change**: bootstrap-agent-guidance-hub  
**Mode**: Standard (strict_tdd: false)  
**Delivery**: auto-chain / stacked-to-main  
**Updated**: 2026-05-28

## Completed Tasks

- [x] 1.1 Create `pyproject.toml`, `agh/__init__.py`, `agh/server/app.py`, `agh/cli/main.py`, and `tests/` with FastAPI, Typer, pytest dependencies and `agh` entrypoint.
- [x] 1.2 Add smoke tests in `tests/test_scaffold.py` for `GET /api/v1/health`, `agh --help`, log file creation, and default port constant `8912`.
- [x] 1.3 Implement health route, Typer help, basic stdout/file logging, `Dockerfile` health check.
- [x] 1.4 Update `openspec/config.yaml` test command/testing runner to `uv run pytest`.
- [x] 2.1 (PR2A split) Add `agh/common/ids.py`, `validation.py`, `repo_url.py`, `pack_manifest.py`, `checksums.py` and unit tests for prefixed IDs, email, slug/SemVer/latest handling, URL normalization, manifest validation, and managed payload hashes.
- [x] PR2B-1 partial of 2.2: Add SQLite connection helper, versioned SQL migration, and migration idempotency/schema constraint tests. The 2.2 checkbox remains open in `tasks.md` per split-slice instruction.

## Files Changed (PR2A)

| File | Action | Notes |
|------|--------|-------|
| `agh/common/__init__.py` | Created | Shared exports for helper layer |
| `agh/common/ids.py` | Created | Prefixed ID generation/validation for `usr/tok/prj/pack/packv/asn` |
| `agh/common/validation.py` | Created | Email/slug/SemVer validation, pack ref parsing, SemVer compare |
| `agh/common/repo_url.py` | Created | GitHub-style SSH/HTTPS normalization with optional `.git` stripping |
| `agh/common/pack_manifest.py` | Created | `agh.pack.toml` loader + validation (required fields, tags) |
| `agh/common/checksums.py` | Created | Managed payload normalization + `sha256:<hex>` digest |
| `tests/test_common_helpers.py` | Created | Focused unit coverage for helper layer |
| `openspec/changes/bootstrap-agent-guidance-hub/specs/packs/spec.md` | Modified | Explicitly requires manifest `description` to match product contract |
| `openspec/changes/bootstrap-agent-guidance-hub/tasks.md` | Modified | Marked task 2.1 complete |

## Files Changed (PR2B-1)

| File | Action | Notes |
|------|--------|-------|
| `agh/server/db.py` | Created | SQLite database path, connection configuration, and idempotent migration runner |
| `agh/server/migrations/__init__.py` | Created | Package marker for migration resources |
| `agh/server/migrations/001_initial_schema.sql` | Created | Initial metadata schema for users, token hashes, projects, memberships, packs, pack versions, assignments |
| `tests/test_db_migrations.py` | Created | Unit tests for data-dir path, schema creation, idempotency, uniqueness, and foreign keys |
| `pyproject.toml` | Modified | Includes SQL migrations as package data for installed distributions |
| `openspec/changes/bootstrap-agent-guidance-hub/tasks.md` | Modified | Added PR2B-1 partial note while leaving 2.2 unchecked |
| `openspec/changes/bootstrap-agent-guidance-hub/apply-progress.md` | Modified | Recorded cumulative PR2B-1 progress and validation |

## Validation

```text
python -m pytest
# failed in system python: missing dependencies / package import during collection

.venv/bin/python -m pytest
# 24 passed in 0.25s

PYTHONDONTWRITEBYTECODE=1 .venv/bin/python -m pytest -q -p no:cacheprovider
# 24 passed in 0.26s

uv run pytest tests/test_db_migrations.py -q
# 4 passed in 0.19s

uv run pytest
# 28 passed, 1 warning in 0.36s

uv run pytest
# 28 passed, 1 warning in 0.30s (after package-data update)

uv run pytest tests/test_db_migrations.py -q
# 5 passed in 0.18s (after atomic migration runner fix)

uv run pytest
# 29 passed, 1 warning in 0.33s (after atomic migration runner fix)
```

## TDD Evidence

Strict TDD not active (`openspec/config.yaml: strict_tdd: false`). Tests were written before PR2B-1 production code where practical; the focused RED run failed with `ModuleNotFoundError: No module named 'agh.server.db'` before implementation.

## Deviations from Design

None — PR2B-1 follows the lightweight SQL migration design using stdlib `sqlite3` and `schema_migrations(version, applied_at)`.

## Issues Found / Review Fixes

- Fresh review found ID prefixes did not match the API spec (`proj` vs `prj`, missing `asn`). Fixed allowed prefixes and added parametrized tests.
- Fresh review found malformed TOML escaped as `tomllib.TOMLDecodeError`. Fixed manifest loader to wrap malformed TOML in `PackManifestError`.
- Fresh review noted the packs spec did not explicitly require `description`; updated the spec to match the approved manifest contract and implementation.
- PR2B-1 focused RED test initially failed because `agh.server.db` did not exist; implemented `db.py` and migrations to satisfy it.
- Fresh review found migration application was not atomic because `executescript()` could leave partial schema before recording `schema_migrations`. Fixed migration execution to run statements inside a savepoint and added a failing-migration rollback test.
- User requested explicit DB naming: changed `tokens.token` to `tokens.token_hash` and added schema test coverage.

## Remaining Tasks

- [ ] 2.2 parent-controlled completion remains open in `tasks.md` after PR2B-1 split note.
- [ ] 2.3 Add `agh/server/auth.py`, bootstrap startup, hashed Bearer tokens, `/api/v1/me`
- [ ] 2.4 Add `agh/cli/config.py` and login flow
- [ ] 3.1–6.4 unchanged

## Workload / PR Boundary

- **Mode**: stacked PR slice (PR2B-1) targeting `main` after PR3 uv-tooling merge, per prompt boundary
- **Boundary**: SQLite DB helper and migrations only; no auth, bootstrap owner, routes, CLI login, users/projects/packs APIs, sync, pull, or agent integrations
- **Review impact**: bounded storage-only slice with focused migration tests, intended as one stacked work unit
