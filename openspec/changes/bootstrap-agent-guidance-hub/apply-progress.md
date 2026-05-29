# Apply Progress: bootstrap-agent-guidance-hub

**Change**: bootstrap-agent-guidance-hub  
**Mode**: Standard (strict_tdd: false)  
**Delivery**: auto-chain / stacked-to-main  
**Updated**: 2026-05-29

## Completed Tasks

- [x] 1.1 Create `pyproject.toml`, `agh/__init__.py`, `agh/server/app.py`, `agh/cli/main.py`, and `tests/` with FastAPI, Typer, pytest dependencies and `agh` entrypoint.
- [x] 1.2 Add smoke tests in `tests/test_scaffold.py` for `GET /api/v1/health`, `agh --help`, log file creation, and default port constant `8912`.
- [x] 1.3 Implement health route, Typer help, basic stdout/file logging, `Dockerfile` health check.
- [x] 1.4 Update `openspec/config.yaml` test command/testing runner to `uv run pytest`.
- [x] 2.1 (PR2A split) Add `agh/common/ids.py`, `validation.py`, `repo_url.py`, `pack_manifest.py`, `checksums.py` and unit tests for prefixed IDs, email, slug/SemVer/latest handling, URL normalization, manifest validation, and managed payload hashes.
- [x] PR2B-1 partial of 2.2: Add SQLite connection helper, versioned SQL migration, and migration idempotency/schema constraint tests; PR3A later closed the parent-controlled checkbox once the wording was fully satisfied.
- [x] 2.3 (PR2B-2 split) Add `agh/server/auth.py`, bootstrap startup after migrations, hashed Bearer token verification, `/api/v1/me`, and `$AGH_DATA_DIR/secrets/initial_owner_token` with tests for no token logging and no re-bootstrap.
- [x] 2.4 (PR2B-3 split) Add `agh/cli/config.py`, `agh login`, `agh config show`, validated `/api/v1/me` login, atomic restricted config writes, invalid-login preservation, and polished no-arg/top-level help.
- [x] 2.2 (PR3A administrative closeout) Mark DB/migration task complete because the existing merged schema/migration work covers users, tokens, projects, memberships, packs, versions, assignments, `schema_migrations`, and SQLite idempotency tests.
- [x] 3.1 (PR3A split) Add server user CRUD and token rotate/reset routes with role enforcement and sole-owner protection tests.

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

## Files Changed (PR2B-3)

| File | Action | Notes |
|------|--------|-------|
| `agh/cli/config.py` | Created | Local config path/env override, TOML load/write, URL normalization, `/api/v1/me` validation via stdlib `urllib.request`, token masking, and atomic temp-then-replace writes with `0600` chmod best effort |
| `agh/cli/main.py` | Modified | Added `login`, `config show`, top-level `config` group, and no-arg man-style help while preserving `agh --help` discoverability |
| `tests/test_cli_login.py` | Created | Focused CLI tests for successful login, Authorization header, normalized storage, `0600`, invalid login preservation, email mismatch preservation, masked config output, and help discoverability |
| `openspec/changes/bootstrap-agent-guidance-hub/tasks.md` | Modified | Marked task 2.4 complete only |
| `openspec/changes/bootstrap-agent-guidance-hub/apply-progress.md` | Modified | Recorded cumulative PR2B-3 progress and validation |
| `sdd/apply-pr2b3-result.md` | Created | Standard SDD apply result envelope for PR2B-3 |

## Files Changed (PR3A)

| File | Action | Notes |
|------|--------|-------|
| `agh/server/routes/__init__.py` | Created | Route package marker for server route modules |
| `agh/server/routes/users.py` | Created | Authenticated user list/create/update/deactivate routes plus token rotate/reset, SQLite direct access, role checks, hashed token storage, and sole-owner protection |
| `agh/server/app.py` | Modified | Wires user routes under `/api/v1` |
| `tests/test_user_routes.py` | Created | FastAPI integration tests for owner/admin/member permissions, email validation, no token hash leakage, token revoke/issue lifecycle, inactive/delete behavior, and sole-owner protection |
| `openspec/changes/bootstrap-agent-guidance-hub/tasks.md` | Modified | Marks 3.1 complete and administratively closes 2.2 with rationale |
| `openspec/changes/bootstrap-agent-guidance-hub/apply-progress.md` | Modified | Records cumulative PR3A progress and validation |

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

uv run pytest tests/test_cli_login.py -q
# RED before implementation: 4 failed, 1 passed (login/config commands absent; no-arg help exited 2)

uv run pytest tests/test_cli_login.py -q
# 5 passed in 1.61s

uv run pytest -q
# 43 passed, 1 warning in 1.94s

uv run pytest tests/test_cli_login.py -q
# 8 passed in 2.63s (after redirect/timeout review fixes)

uv run pytest -q
# 46 passed, 1 warning in 3.05s (after redirect/timeout review fixes)

uv run pytest tests/test_cli_login.py -q
# 9 passed in 2.64s (after help behavior review fix)

uv run pytest -q
# 47 passed, 1 warning in 2.95s (after help behavior review fix)

uv run pytest tests/test_user_routes.py -q
# RED before implementation: 7 failed with 404 Not Found for missing `/api/v1/users` routes

uv run pytest tests/test_user_routes.py -q
# 7 passed, 1 warning in 0.40s

uv run pytest -q
# 54 passed, 1 warning in 3.12s

uv run pytest tests/test_user_routes.py -q
# 9 passed, 1 warning in 0.46s (after PR3A review fixes)

uv run pytest -q
# 56 passed, 1 warning in 3.16s (after PR3A review fixes)

uv run pytest tests/test_user_routes.py -q
# 9 passed, 1 warning in 0.45s (after create-user initial token UX change)

uv run pytest -q
# 56 passed, 1 warning in 3.23s (after create-user initial token UX change)
```

## TDD Evidence

Strict TDD not active (`openspec/config.yaml: strict_tdd: false`). Tests were written before PR2B-1 production code where practical; the focused RED run failed with `ModuleNotFoundError: No module named 'agh.server.db'` before implementation. PR2B-2 tests were also written before production code where practical; the focused RED run failed with `ModuleNotFoundError: No module named 'agh.server.auth'` before implementation. PR2B-3 tests were written before production code where practical; the focused RED run failed because `login`/`config show` were not implemented and no-arg help exited 2. PR3A tests were written before production code where practical; the focused RED run failed with 404s for the missing `/api/v1/users` routes before implementation.

## Deviations from Design

None — PR2B-2 keeps auth/bootstrap in stdlib/FastAPI modules, uses SQLite directly, stores only `tokens.token_hash`, runs migrations before bootstrap, and writes the one bootstrap plaintext token under `$AGH_DATA_DIR/secrets/initial_owner_token` so Docker's `AGH_DATA_DIR=/data` yields the specified `/data/secrets/initial_owner_token` path. PR2B-3 uses stdlib `urllib.request` instead of adding an HTTP dependency, stores the default config at `~/.config/agh/config.toml`, supports `AGH_CONFIG_FILE` for test isolation/overrides, and never adds a reveal-secret flag. PR3A returns an initial plaintext token once from `POST /users` for better admin UX while storing only `tokens.token_hash`; `DELETE /users/{id}` deactivates (`active=0`) because the schema has no `deleted_at` column and auth already denies inactive users.

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
- PR2B-3 security review found `urllib` followed redirects with the Bearer token and timeout errors could escape as unhandled exceptions. Fixed login validation with a no-redirect opener, explicit redirect rejection, timeout wrapping, and tests for redirect/token non-forwarding and clean timeout failures.
- PR2B-3 help review found disabling root help broke command-specific `--help`. Fixed the custom Typer group to return the AGH manual for group help/unknown commands while preserving generated help for concrete commands such as `agh login --help` and `agh config show --help`.
- PR3A decision: admin token rotate/reset is treated as user administration, so admins may rotate/reset `member` tokens only; owners may rotate/reset any user token. This matches the prompt's admin-can-manage-members-only constraint.
- PR3A implementation uses simple FastAPI `HTTPException.detail` strings rather than the design's future `{error:{code,message}}` helper because existing auth routes currently use detail strings and the prompt requested simple errors for now.
- PR3A fresh review found unauthorized member target routes leaked user existence, owner-protection checks were not transactionally safe, and email canonicalization was case-sensitive. Fixed by checking admin/owner permission before target lookup, wrapping target read/check/write in `BEGIN IMMEDIATE`, lowercasing stored emails (including bootstrap owner), and adding tests for non-enumeration, case-insensitive duplicates, and concurrent owner demotions.
- User asked whether create-user should return an initial token for better UX. Updated `POST /users` to atomically create the user and initial token hash, returning plaintext `token` once alongside `user`; rotate/reset still revoke previous active tokens and return new plaintext tokens once.

## Remaining Tasks

- [ ] 3.2 Add project CRUD, duplicate normalized URL `409`, developer membership, and access checks in `agh/server/routes/projects.py`; test inactive project denial.
- [ ] 3.3 Add Typer `user`, `token`, and `project` command groups in `agh/cli/main.py` mapping to `/api/v1` and masking secrets in config output.
- [ ] 3.4 Add `agh/cli/workspace_sync.py` for git remote lookup, no `--project`, `.agh/project.toml`, `--remote`, and `--force` link-only behavior; test with temp git repos.
- [ ] 4.1–6.4 unchanged.

## Workload / PR Boundary

- **Mode**: stacked PR slice (PR3A) targeting current `main` after merged PR #6, per prompt boundary
- **Boundary**: Server user administration and token lifecycle routes only: `agh/server/routes/users.py`, app wiring, role/owner-protection tests, and administrative 2.2 closeout. No CLI `agh user`/`agh token`/`agh project`, project APIs, sync, packs, pull, workspace behavior, agent integrations, web UI, OAuth/SSO, or commits.
- **Review impact**: focused server API slice with one route module and one focused test file; intended as one stacked work unit under the resolved auto-chain strategy
