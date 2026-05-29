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
- [x] 2.3 (PR2B-2 split) Add `agh/server/auth.py`, bootstrap startup after migrations, hashed Bearer token verification, `/api/v1/me`, and `$AGH_DATA_DIR/secrets/initial_owner_token` with tests for no token logging and no re-bootstrap.

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

## Files Changed (PR2B-2)

| File | Action | Notes |
|------|--------|-------|
| `agh/server/auth.py` | Created | Bootstrap owner creation, SHA-256 token hashing, indexed Bearer token hash lookup with constant-time digest confirmation, inactive-user 403 handling, restrictive initial token file write |
| `agh/server/app.py` | Modified | Runs migrations before bootstrap in `create_app()`, stores DB path on app state, and adds protected `GET /api/v1/me` while leaving health public |
| `agh/server/db.py` | Modified | Moved `get_data_dir()` into DB helper module to avoid app/db import cycle while preserving AGH_DATA_DIR behavior |
| `tests/test_auth_bootstrap.py` | Created | Integration tests for bootstrap secret/hash behavior, concurrent/no re-bootstrap, env-absent no-op, `/me` auth statuses, revoked-token 401, inactive user 403, and public health |
| `openspec/changes/bootstrap-agent-guidance-hub/tasks.md` | Modified | Marked task 2.3 complete for PR2B-2 scope only |
| `openspec/changes/bootstrap-agent-guidance-hub/apply-progress.md` | Modified | Recorded cumulative PR2B-2 progress and validation |

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

uv run pytest tests/test_auth_bootstrap.py -q
# RED before implementation: ModuleNotFoundError: No module named 'agh.server.auth'

uv run pytest tests/test_auth_bootstrap.py -q
# 6 passed, 1 warning in 0.30s

uv run pytest -q
# 35 passed, 1 warning in 0.38s

uv run pytest tests/test_auth_bootstrap.py -q
# 8 passed, 1 warning in 0.31s (after review fixes)

uv run pytest -q
# 37 passed, 1 warning in 0.38s (after review fixes)

uv run pytest tests/test_db_migrations.py -q
# 6 passed in 0.30s (after concurrent migration startup fix)

uv run pytest tests/test_auth_bootstrap.py -q
# 8 passed, 1 warning in 0.37s (after concurrent migration startup fix)

uv run pytest -q
# 38 passed, 1 warning in 0.49s (after concurrent migration startup fix)
```

## TDD Evidence

Strict TDD not active (`openspec/config.yaml: strict_tdd: false`). Tests were written before PR2B-1 production code where practical; the focused RED run failed with `ModuleNotFoundError: No module named 'agh.server.db'` before implementation. PR2B-2 tests were also written before production code where practical; the focused RED run failed with `ModuleNotFoundError: No module named 'agh.server.auth'` before implementation.

## Deviations from Design

None — PR2B-2 keeps auth/bootstrap in stdlib/FastAPI modules, uses SQLite directly, stores only `tokens.token_hash`, runs migrations before bootstrap, and writes the one bootstrap plaintext token under `$AGH_DATA_DIR/secrets/initial_owner_token` so Docker's `AGH_DATA_DIR=/data` yields the specified `/data/secrets/initial_owner_token` path.

## Issues Found / Review Fixes

- Fresh review found ID prefixes did not match the API spec (`proj` vs `prj`, missing `asn`). Fixed allowed prefixes and added parametrized tests.
- Fresh review found malformed TOML escaped as `tomllib.TOMLDecodeError`. Fixed manifest loader to wrap malformed TOML in `PackManifestError`.
- Fresh review noted the packs spec did not explicitly require `description`; updated the spec to match the approved manifest contract and implementation.
- PR2B-1 focused RED test initially failed because `agh.server.db` did not exist; implemented `db.py` and migrations to satisfy it.
- Fresh review found migration application was not atomic because `executescript()` could leave partial schema before recording `schema_migrations`. Fixed migration execution to run statements inside a savepoint and added a failing-migration rollback test.
- User requested explicit DB naming: changed `tokens.token` to `tokens.token_hash` and added schema test coverage.
- PR2B-2 exposed an app/db import cycle when wiring startup migrations; fixed by moving `get_data_dir()` ownership to `agh.server.db` and importing it from `agh.server.app`.
- Fresh security review found bootstrap was not serialized enough for the "exactly one owner" first-start requirement. Fixed with `BEGIN IMMEDIATE`, rechecking user count inside the transaction, and a concurrent bootstrap test.
- Fresh security review found auth lookup scanned all active tokens and overstated constant-time verification. Fixed by querying the unique `token_hash` directly, retaining `hmac.compare_digest` confirmation, and adding revoked-token coverage.
- Fresh final review found concurrent first-start migrations could race before auth bootstrap. Fixed `run_migrations()` to serialize applied-version check/apply/record with `BEGIN IMMEDIATE` and added concurrent migration startup coverage.

## Remaining Tasks

- [ ] 2.2 parent-controlled completion remains open in `tasks.md` after PR2B-1 split note.
- [ ] 2.4 Add `agh/cli/config.py` and login flow
- [ ] 3.1–6.4 unchanged

## Workload / PR Boundary

- **Mode**: stacked PR slice (PR2B-2) targeting current `main` after merged PR #4, per prompt boundary
- **Boundary**: Server auth/bootstrap only: migrations + first-owner bootstrap in app factory, hashed Bearer validation, `/api/v1/me`, and tests. No CLI login/config, user CRUD, token rotate/reset endpoints, project/pack APIs, sync, pull, agent integrations, web UI, OAuth/SSO, or commits.
- **Review impact**: focused server-auth slice with one new auth module and integration test file; intended as one stacked work unit
