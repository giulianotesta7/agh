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
- [x] 3.2 (PR3B split) Add server project CRUD, duplicate active normalized URL `409`, developer membership add/remove routes, admin/member project access checks, and inactive project denial tests.
- [x] 3.3 (PR3C split) Add Typer `user`, `token`, and `project` command groups mapping to `/api/v1`, using saved config credentials and masking stored secrets in command output.
- [x] 3.4 (PR3D split) Add `agh sync` workspace linking via git remote lookup, `.agh/project.toml`, `--remote`, `--force`, and no manual `--project` override.
- [x] 4.1 (PR4A split) Add filesystem pack storage plus server pack publish/list/file routes with manifest, instruction source, skill layout, immutability, auth, and path safety tests.
- [x] 4.2 (PR4B split) Add server project-pack assignment routes with concrete/latest version refs, highest-SemVer latest resolution, ordering, soft deactivation, and access-control tests.
- [x] 4.3 (PR4C split) Add project pull-manifest route with active assignment ordering, latest resolution, artifact metadata, download URLs, checksums, and access-control tests.
- [x] 4.4 (PR4D split) Add CLI pack publish/list and project pack assignment commands, with local manifest validation errors exiting `2`.

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

## Files Changed (PR3B)

| File | Action | Notes |
|------|--------|-------|
| `agh/server/routes/projects.py` | Created | Authenticated project CRUD, active duplicate repo conflict handling, admin/member read policies, developer membership add/remove routes, and inactive project denial behavior using direct SQLite access |
| `agh/server/app.py` | Modified | Wires project routes under `/api/v1` |
| `tests/test_project_routes.py` | Created | FastAPI integration coverage for project CRUD, duplicate conflicts, developer membership access gain/loss, inactive denial, Bearer auth, and admin-only mutations |
| `openspec/changes/bootstrap-agent-guidance-hub/tasks.md` | Modified | Marks task 3.2 complete only |
| `openspec/changes/bootstrap-agent-guidance-hub/apply-progress.md` | Modified | Records cumulative PR3B progress and validation |
| `sdd/apply-pr3b-result.md` | Created | Standard SDD apply result envelope for PR3B |

## Files Changed (PR3C)

| File | Action | Notes |
|------|--------|-------|
| `agh/cli/main.py` | Modified | Adds plain Typer `user`, `token`, and `project` groups; maps user CRUD, token rotate/reset, project CRUD, and project membership add/remove to existing `/api/v1` routes via saved config Bearer auth; rejects redirects and masks token-like fields except newly issued tokens. |
| `tests/test_cli_admin_commands.py` | Created | Focused CLI tests for API method/path/body mapping, stored token non-disclosure, newly issued token display, auth error exit code, and command/group help behavior. |
| `openspec/changes/bootstrap-agent-guidance-hub/tasks.md` | Modified | Marks task 3.3 complete only. |
| `openspec/changes/bootstrap-agent-guidance-hub/apply-progress.md` | Modified | Records cumulative PR3C progress and validation. |
| `sdd/apply-pr3c-result.md` | Generated local artifact | Standard SDD apply result envelope for PR3C; intentionally ignored by `.gitignore` under `sdd/`. |

## Files Changed (PR3D)

| File | Action | Notes |
|------|--------|-------|
| `agh/cli/workspace_sync.py` | Created | Implements `agh sync` workspace linking: reads selected git remote, normalizes repo URL, fetches accessible `/api/v1/projects` using saved config Bearer auth, matches active project, and writes `.agh/project.toml` atomically. |
| `agh/cli/main.py` | Modified | Adds top-level `agh sync` command with `--remote` and `--force`; no manual `--project` override. |
| `tests/test_workspace_sync.py` | Created | Temp-git-repo CLI coverage for default remote, non-default `--remote`, saved config auth, no `--project`, existing-link refusal, `--force` link-only replacement preserving `.agh/lock.toml`, missing remote, and no matching project. |
| `openspec/changes/bootstrap-agent-guidance-hub/tasks.md` | Modified | Marks task 3.4 complete only. |
| `openspec/changes/bootstrap-agent-guidance-hub/apply-progress.md` | Modified | Records cumulative PR3D progress and validation. |
| `sdd/apply-pr3d-result.md` | Generated local artifact | Standard SDD apply result envelope for PR3D; intentionally ignored by `.gitignore` under `sdd/`. |

## Files Changed (PR4A)

| File | Action | Notes |
|------|--------|-------|
| `agh/server/routes/packs.py` | Created | Adds authenticated `GET/POST /api/v1/packs` and `GET /api/v1/packs/{domain}/{name}/versions/{version}/files/{path}` routes, JSON pack publish payload validation, filesystem storage under `$AGH_DATA_DIR/packs/`, DB metadata writes, immutable version conflicts, checksum calculation, and path/symlink safety checks. |
| `agh/server/app.py` | Modified | Wires pack routes under `/api/v1`. |
| `tests/test_pack_routes.py` | Created | FastAPI integration coverage for publish success, list/download, missing/invalid manifest fields, missing instruction source, `latest` rejection, republish conflict/no overwrite, optional skill layout, auth/role requirements, traversal rejection, symlinked storage rejection, and symlink read rejection. |
| `openspec/changes/bootstrap-agent-guidance-hub/tasks.md` | Modified | Marks task 4.1 complete only. |
| `openspec/changes/bootstrap-agent-guidance-hub/apply-progress.md` | Modified | Records cumulative PR4A progress and validation. |
| `sdd/apply-pr4a-result.md` | Generated local artifact | Standard SDD apply result envelope for PR4A; intentionally ignored by `.gitignore` under `sdd/`. |

## Files Changed (PR4B)

| File | Action | Notes |
|------|--------|-------|
| `agh/server/routes/projects.py` | Modified | Adds `GET/POST/PATCH/DELETE /api/v1/projects/{project_id}/packs` assignment routes; supports `domain/name@version` and `@latest`, resolves latest by highest SemVer in responses, orders by `position ASC, domain/name ASC`, enforces admin mutations, project developer active listing, inactive project mutation denial, and soft-delete assignment deactivation. |
| `tests/test_project_pack_assignments.py` | Created | FastAPI integration coverage for concrete and latest assignment, latest resolution, ordering tie-break, project developer listing, update position/version ref, deactivate/reactivate, missing pack/version rejection, member mutation denial, duplicate active assignment conflict, and inactive project denial. |
| `openspec/changes/bootstrap-agent-guidance-hub/tasks.md` | Modified | Marks task 4.2 complete only. |
| `openspec/changes/bootstrap-agent-guidance-hub/apply-progress.md` | Modified | Records cumulative PR4B progress and validation. |
| `sdd/apply-pr4b-result.md` | Generated local artifact | Standard SDD apply result envelope for PR4B; intentionally ignored by `.gitignore` under `sdd/`. |

## Files Changed (PR4C)

| File | Action | Notes |
|------|--------|-------|
| `agh/server/routes/projects.py` | Modified | Adds `GET /api/v1/projects/{project_id}/pull-manifest`; active project authorization, active assignment ordering, `latest` resolution, pack manifest metadata, instruction/skill artifacts, managed payload checksums, and existing pack file download URLs. |
| `tests/test_pull_manifest_routes.py` | Created | FastAPI integration coverage for owner/admin pull-manifest generation, developer access, non-member 404, inactive project denial, latest resolution, assignment ordering, inactive assignment omission, artifact shape/download URLs, and checksum normalization. |
| `openspec/changes/bootstrap-agent-guidance-hub/tasks.md` | Modified | Marks task 4.3 complete only. |
| `openspec/changes/bootstrap-agent-guidance-hub/apply-progress.md` | Modified | Records cumulative PR4C progress and validation. |
| `sdd/apply-pr4c-result.md` | Generated local artifact | Standard SDD apply result envelope for PR4C; intentionally ignored by `.gitignore` under `sdd/`. |

## Files Changed (PR4D)

| File | Action | Notes |
|------|--------|-------|
| `agh/cli/pack_publish.py` | Created | Validates local pack directories and builds the JSON file-map publish payload while refusing missing manifest/instructions, invalid skills, non-text files, and symlinked paths. |
| `agh/cli/main.py` | Modified | Adds `agh pack list`, `agh pack publish PATH`, and `agh project pack list/add/update/remove` commands mapped to existing pack and project assignment APIs. |
| `tests/test_cli_pack_commands.py` | Created | Focused CLI tests for pack publish/list mapping, local validation exit `2`, symlink refusal, project assignment command mapping, help discoverability, and secret non-disclosure. |
| `openspec/changes/bootstrap-agent-guidance-hub/tasks.md` | Modified | Marks task 4.4 complete only. |
| `openspec/changes/bootstrap-agent-guidance-hub/apply-progress.md` | Modified | Records cumulative PR4D progress and validation. |
| `sdd/apply-pr4d-result.md` | Generated local artifact | Standard SDD apply result envelope for PR4D; intentionally ignored by `.gitignore` under `sdd/`. |

## Files Changed (PR5A)

| File | Action | Notes |
|------|--------|-------|
| `agh/cli/pull_markers.py` | Created | Adds pure marker parsing/rendering/planning helpers for AGH-managed blocks, checksum conflict detection, delimiter injection rejection, checksum metadata validation, and unmanaged-content-preserving updates. |
| `tests/test_pull_markers.py` | Created | Focused coverage for render/checksum normalization, insert/update/noop/conflict planning, corrupt markers, duplicate blocks, CRLF unmanaged preservation, checksum format rejection, and marker delimiter payload rejection. |
| `openspec/changes/bootstrap-agent-guidance-hub/tasks.md` | Modified | Marks task 5.1 complete only. |
| `openspec/changes/bootstrap-agent-guidance-hub/apply-progress.md` | Modified | Records cumulative PR5A progress, validation, and review fixes. |

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

uv run pytest tests/test_project_routes.py -q
# RED before implementation: 4 failed with 404 Not Found for missing `/api/v1/projects` routes

uv run pytest tests/test_project_routes.py -q
# 4 passed, 1 warning in 0.43s

uv run pytest -q
# 60 passed, 1 warning in 3.49s

uv run pytest tests/test_common_helpers.py tests/test_project_routes.py -q
# 24 passed, 1 warning in 0.44s (after PR3B repo URL case-normalization fix)

uv run pytest -q
# 60 passed, 1 warning in 3.51s (after PR3B repo URL case-normalization fix)

uv run pytest tests/test_common_helpers.py tests/test_project_routes.py -q
# 24 passed, 1 warning in 0.46s (after uppercase .GIT suffix fix)

uv run pytest -q
# 60 passed, 1 warning in 3.52s (after uppercase .GIT suffix fix)

uv run pytest tests/test_common_helpers.py tests/test_project_routes.py -q
# 24 passed, 1 warning in 0.49s (after trailing-dot host fix)

uv run pytest -q
# 60 passed, 1 warning in 3.54s (after trailing-dot host fix)

uv run pytest tests/test_common_helpers.py tests/test_project_routes.py -q
# 24 passed, 1 warning in 0.45s (after percent-encoded path fix)

uv run pytest -q
# 60 passed, 1 warning in 3.52s (after percent-encoded path fix)

uv run pytest tests/test_common_helpers.py tests/test_project_routes.py -q
# 24 passed, 1 warning in 0.47s (after dot-segment/trailing encoded slash fix)

uv run pytest -q
# 60 passed, 1 warning in 3.55s (after dot-segment/trailing encoded slash fix)

uv run pytest tests/test_common_helpers.py tests/test_project_routes.py -q
# 24 passed, 1 warning in 0.48s (after percent-encoded host fix)

uv run pytest -q
# 60 passed, 1 warning in 3.61s (after percent-encoded host fix)

uv run pytest tests/test_cli_admin_commands.py -q
# 2 passed, 1 failed (auth-failure test expected 403 but fake handler returned 404 for DELETE /forbidden)

uv run pytest tests/test_cli_admin_commands.py tests/test_cli_login.py -q
# 12 passed in 3.87s

uv run pytest -q
# 63 passed, 1 warning in 4.79s

uv run pytest tests/test_cli_admin_commands.py -q
# 4 passed in 1.79s (after PR3C review fixes)

uv run pytest -q
# 64 passed, 1 warning in 5.34s (after PR3C review fixes)

git diff --check
# passed

uv run pytest tests/test_workspace_sync.py -q
# 5 passed in 2.15s

uv run pytest -q
# 69 passed, 1 warning in 7.48s

uv run pytest tests/test_workspace_sync.py -q
# 6 passed in 2.68s (after symlinked .agh directory safety fix)

uv run pytest -q
# 70 passed, 1 warning in 7.97s (after symlinked .agh directory safety fix)

git diff --check
# passed

uv run pytest tests/test_pack_routes.py -q
# 6 passed, 1 warning in 0.51s

uv run pytest -q
# 76 passed, 1 warning in 8.59s

python -m compileall -q agh/server/routes/packs.py tests/test_pack_routes.py
# passed

git diff --check
# passed

uv run pytest tests/test_pack_routes.py -q
# 7 passed, 1 warning in 0.60s (after PR4A review fixes)

uv run pytest -q
# 77 passed, 1 warning in 8.80s (after PR4A review fixes)

git diff --check
# passed

uv run pytest tests/test_pack_routes.py -q
# 9 passed, 1 warning in 0.64s (after PR4A second review fixes)

uv run pytest -q
# 79 passed, 1 warning in 8.86s (after PR4A second review fixes)

git diff --check
# passed

uv run pytest tests/test_pack_routes.py -q
# 9 passed, 1 warning in 0.66s (after streamed chunk pre-extend cap fix)

uv run pytest -q
# 79 passed, 1 warning in 8.84s (after streamed chunk pre-extend cap fix)

git diff --check
# passed

uv run pytest tests/test_project_pack_assignments.py -q
# 4 passed, 1 warning in 0.58s

uv run pytest -q
# 83 passed, 1 warning in 9.13s

uv run pytest tests/test_pull_manifest_routes.py -q
# RED before implementation: 3 failed with 404 Not Found for missing `/api/v1/projects/{project_id}/pull-manifest`

uv run pytest tests/test_pull_manifest_routes.py -q
# 3 passed, 1 warning in 0.49s

uv run pytest -q
# 86 passed, 1 warning in 9.30s

git diff --check
# passed

uv run pytest tests/test_cli_pack_commands.py -q
# 4 passed in 1.72s

uv run pytest tests/test_cli_pack_commands.py tests/test_cli_admin_commands.py -q
# 8 passed in 3.63s

uv run pytest -q
# 90 passed, 1 warning in 11.31s

git diff --check
# passed

uv run pytest tests/test_cli_pack_commands.py -q
# 8 passed in 3.75s (after PR4D review fixes)

uv run pytest -q
# 94 passed, 1 warning in 13.52s (after PR4D review fixes)

git diff --check
# passed

uv run pytest tests/test_cli_pack_commands.py -q
# 10 passed in 4.72s (after PR4D second review fixes)

uv run pytest -q
# 96 passed, 1 warning in 14.22s (after PR4D second review fixes)

git diff --check
# passed

uv run pytest tests/test_cli_pack_commands.py -q
# 7 passed in 3.25s (after PR4D review fixes)

uv run pytest -q
# 93 passed, 1 warning in 13.19s (after PR4D review fixes)

git diff --check
# passed

uv run pytest tests/test_cli_pack_commands.py -q
# 10 passed in 4.71s (after PR4D second review fixes)

uv run pytest -q
# 96 passed, 1 warning in 14.05s (after PR4D second review fixes)

git diff --check
# passed

uv run pytest tests/test_cli_pack_commands.py -q
# 11 passed in 5.21s (after PR4D third review fixes)

uv run pytest -q
# 97 passed, 1 warning in 14.28s (after PR4D third review fixes)

git diff --check
# passed

uv run pytest tests/test_pull_markers.py -q
# 15 passed in 0.02s (after PR5A review fixes)

uv run pytest -q
# 112 passed, 1 warning in 14.30s (after PR5A review fixes)

git diff --check
# passed

uv run --with pyright pyright tests/test_pull_markers.py agh/cli/pull_markers.py
# 0 errors, 0 warnings, 0 informations

uv run pytest tests/test_pull_markers.py -q
# 12 passed in 0.02s

uv run pytest -q
# 109 passed, 1 warning in 14.30s

git diff --check
# passed

uv run pytest tests/test_pull_markers.py -q
# 15 passed in 0.02s (after PR5A review fixes)

uv run pytest -q
# 112 passed, 1 warning in 14.31s (after PR5A review fixes)

git diff --check
# passed
```

## TDD Evidence

Strict TDD not active (`openspec/config.yaml: strict_tdd: false`). Tests were written before PR2B-1 production code where practical; the focused RED run failed with `ModuleNotFoundError: No module named 'agh.server.db'` before implementation. PR2B-2 tests were also written before production code where practical; the focused RED run failed with `ModuleNotFoundError: No module named 'agh.server.auth'` before implementation. PR2B-3 tests were written before production code where practical; the focused RED run failed because `login`/`config show` were not implemented and no-arg help exited 2. PR3A tests were written before production code where practical; the focused RED run failed with 404s for the missing `/api/v1/users` routes before implementation. PR3B tests were written before production code where practical; the focused RED run failed with 404s for the missing `/api/v1/projects` routes before implementation. PR3C standard-mode tests were added with implementation; a focused test initially exposed a fake-handler route mismatch before passing. PR3D standard-mode tests were added with implementation and passed focused temp-git-repo coverage. PR4A standard-mode tests were added with implementation and passed focused FastAPI pack-route coverage. PR4B standard-mode tests were added with implementation and passed focused FastAPI project-pack assignment coverage. PR4C tests were written before production code; the focused RED run failed with 404s for the missing pull-manifest route before implementation. PR5A marker tests were written alongside the pure marker module and cover rendering, parsing, insert/update/noop, checksum conflicts, corrupt markers, duplicate blocks, and CRLF/trailing-newline normalization.

## Deviations from Design

None — PR2B-2 keeps auth/bootstrap in stdlib/FastAPI modules, uses SQLite directly, stores only `tokens.token_hash`, runs migrations before bootstrap, and writes the one bootstrap plaintext token under `$AGH_DATA_DIR/secrets/initial_owner_token` so Docker's `AGH_DATA_DIR=/data` yields the specified `/data/secrets/initial_owner_token` path. PR2B-3 uses stdlib `urllib.request` instead of adding an HTTP dependency, stores the default config at `~/.config/agh/config.toml`, supports `AGH_CONFIG_FILE` for test isolation/overrides, and never adds a reveal-secret flag. PR3A returns an initial plaintext token once from `POST /users` for better admin UX while storing only `tokens.token_hash`; `DELETE /users/{id}` deactivates (`active=0`) because the schema has no `deleted_at` column and auth already denies inactive users. PR3B keeps project errors as simple `HTTPException.detail` strings and uses `404` for member direct reads of missing/non-member/inactive projects to avoid practical project-existence leakage; owner/admin may inspect inactive projects while members list/read active developer projects only. PR3C keeps CLI output as plain JSON rather than rich tables, uses stdlib `urllib.request` to avoid a new HTTP dependency, and treats create/rotate/reset `token` values as the only permitted plaintext secret outputs because the server returns them once at issuance. PR3D also uses stdlib `urllib.request` and the existing project-list API rather than adding a server lookup endpoint; an existing `.agh/project.toml` requires `--force` before replacement to avoid accidental relinking, and `--force` replaces only `.agh/project.toml` while preserving `.agh/lock.toml`/other `.agh` artifacts. PR4A uses a JSON text-file map for `POST /packs` rather than multipart/archive upload to avoid adding dependencies in the server slice; CLI archive/directory packaging remains deferred to task 4.4. PR4B implements assignment removal as soft deactivation (`active=0`) because the schema has no `deleted_at`, preserves `version_ref=latest` in storage while returning `resolved_version`/`resolved_ref`, and allows owner/admin inspection of inactive assignments while project developers list active assignments only for active accessible projects. PR4C emits relative same-API download URLs rather than absolute URLs so manifests remain stable across proxies/base URLs, and emits both Claude and OpenCode skill artifacts for each stored `skills/<skill>/SKILL.md` because final agent placement happens later in the pull/agent integration slices.

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
- PR3B policy decision: member direct reads use `404 Not Found` for missing, non-member, and inactive projects; owner/admin list/read can include inactive projects for inspection. Membership add/remove reject inactive or missing projects with `404`.
- PR3B security review found active normalized repo uniqueness could be bypassed with GitHub path case variants because `normalize_repo_url()` only lowercased host. Fixed common repo URL normalization to lowercase path components and added duplicate create/update tests for mixed-case owner/repo variants.
- PR3B re-review found uppercase `.GIT` suffix variants still bypassed uniqueness because suffix stripping happened before lowercasing. Fixed normalization to lowercase path before stripping `.git`, with tests for `Org/App.GIT` variants.
- PR3B second re-review found DNS trailing-dot host variants (`github.com.`) still bypassed repo uniqueness. Fixed host canonicalization to strip trailing dots for HTTPS, `ssh://`, and scp-like SSH forms, with duplicate tests for all supported forms.
- PR3B adversarial review found percent-encoded path variants (`app%2Egit`, encoded slashes) still bypassed repo uniqueness. Fixed normalization to percent-decode path before lowercasing and `.git` stripping, with helper and duplicate create tests.
- PR3B final adversarial review found encoded trailing slashes and dot-segment variants (`./`, `%2e`, `../`, `.git/.`) still bypassed uniqueness. Fixed repo URL normalization to resolve dot segments after percent-decoding and before `.git` stripping, with helper and API duplicate tests.
- PR3B adversarial review found percent-encoded hosts (`github%2ecom`) still bypassed uniqueness. Fixed host canonicalization to percent-decode before lowercasing/trailing-dot stripping, with helper and API duplicate tests.
- PR3C fresh review found subgroup `--help` output showed only the root manual, making `agh user --help`, `agh project --help`, and `agh project member --help` non-discoverable. Fixed CLI subgroups to preserve generated subgroup help while unknown subgroup commands still show the main manual.
- PR3C security review found API error payloads could echo token-like fields and `token_hash` normal output used partial masking. Fixed structured error redaction and made `token_hash` always fully redacted as `****`, with tests.
- PR3C review noted `sdd/apply-pr3c-result.md` is an ignored local artifact, not a committed PR file; corrected the progress table wording.
- PR3D security review found `agh sync` would follow a symlinked `.agh` directory and write `.agh/project.toml` outside the repository. Fixed sync to reject symlinked `.agh` directories before writing and added regression coverage.
- PR4A review found pack publish failed under the default relative `.agh-data` root because storage safety compared relative and resolved paths. Fixed pack storage paths to use an absolute data dir/resolved storage target and added relative-data-dir publish coverage.
- PR4A security review found unbounded JSON pack publish payloads could cause memory/disk/CPU DoS. Added content-length middleware for `POST /api/v1/packs` plus pack-level file count, path length, per-file byte, and total byte caps before writing/checksum, with regression coverage.
- PR4A re-review found pack limits still ran after creating the packs root and chunked/no-Content-Length bodies could be parsed before caps. Moved payload validation before filesystem setup and changed `POST /packs` to stream/read the request body with a hard byte cap before JSON/Pydantic parsing; added regression tests for no-filesystem-write and streamed oversized body.
- PR4A second re-review found the streamed body cap extended the bytearray before checking chunk size, allowing an oversized single chunk allocation. Fixed the stream loop to check `len(body) + len(chunk)` before `extend()` and changed the regression to send one oversized chunk.
- PR4B fresh review found the approved route contract in `design.md` still described an older `PUT/DELETE /projects/{id}/packs/{assignment_id}` shape while implementation uses collection create/list (`GET/POST /projects/{id}/packs`) plus item update/delete (`PATCH/DELETE /projects/{id}/packs/{assignment_id}`). Updated the design route map to match the implemented and tested API shape because assignment creation does not know `assignment_id` ahead of time and partial updates are modeled as `PATCH`.
- PR4D fresh/security review found local pack publish validation read symlinked `agh.pack.toml` before rejection, allowed symlinked instruction directories to pass local validation, let binary manifests escape without exit code 2, lacked local file-count/path/size caps, and included unexpected hidden files like `.env`. Fixed validation to reject all symlinks before manifest reads, require real instruction/skill files, wrap Unicode errors, enforce local caps before reading/posting, and allow only `agh.pack.toml`, instruction files, and `skills/<slug>/SKILL.md`; added regression tests.
- PR4D second security review found `agh.pack.toml` was still parsed before size caps and symlinked parent path components could be resolved before validation. Fixed pack root resolution to reject symlinks in any path component, moved file reading/cap enforcement before manifest parsing, and added oversized-manifest and symlinked-parent regressions.
- PR4D third security review found symlink rejection and file collection still used unbounded recursive tree walks before caps. Replaced recursive `rglob()` traversal with bounded, schema-aware streaming collection over only `agh.pack.toml`, `instructions/{AGENTS.md,CLAUDE.md}`, and `skills/<slug>/SKILL.md`; added too-many-files regression coverage.
- PR5A fresh/security review found marker planning normalized whole-file text and mutated unmanaged CRLF content, accepted non-hex checksum metadata, and allowed payload marker delimiter injection to escape the managed block envelope. Fixed parsing/planning to preserve original text outside managed blocks, require `sha256:<64 lowercase hex>`, validate marker metadata values, reject AGH marker delimiter lines in payloads before rendering, and added regressions.
- PR5A fresh/security review found marker planning normalized whole files to LF, mutating unmanaged CRLF content, accepted malformed `sha256:nothex` checksum metadata, and allowed payload marker delimiter injection. Fixed parser/planner to preserve original text outside managed ranges, validate `sha256:<64 lowercase hex>`, and reject AGH marker delimiter lines inside payloads; added regression tests.

## Remaining Tasks

- [x] 3.3 Add Typer `user`, `token`, and `project` command groups in `agh/cli/main.py` mapping to `/api/v1` and masking secrets in config output.
- [x] 3.4 Add `agh/cli/workspace_sync.py` for git remote lookup, no `--project`, `.agh/project.toml`, `--remote`, and `--force` link-only behavior; test with temp git repos.
- [x] 4.1 Add filesystem pack storage under `/data/packs/` and pack publish/list/file routes in `agh/server/routes/packs.py`; test required `agh.pack.toml`, instruction sources, skills, immutability, and no `latest` publish.
- [x] 4.2 Add project-pack assignment routes and `latest` resolution by highest SemVer; test ordering by `position ASC`, then `domain/name ASC`.
- [x] 4.3 Add pull-manifest schema and file download URLs in `agh/server/routes/projects.py`; test project developer authorization and resolved concrete versions.
- [x] 4.4 Add CLI `pack publish/list` and project assignment commands with manifest validation errors surfaced as exit code `2`.
- [x] 5.1 Add `agh/cli/pull_markers.py` for AGH BEGIN/END parsing, normalized payload checksums, insert/update without replacing unmanaged content; test mismatch detection.
- [ ] 5.2–6.4 unchanged.

## Workload / PR Boundary

- **Mode**: stacked PR slice (PR5A) targeting current `main` after PR4D readiness, per prompt boundary
- **Boundary**: Pull marker parsing/rendering/planning only. No `agh pull` command wiring, pull-manifest fetching, cache, `.agh/lock.toml`, filesystem writes, agent integrations, server API changes, web UI, OAuth/SSO, or PR/merge actions.
- **Review impact**: focused pull-core foundation with one helper module, one focused test file, and OpenSpec progress/task updates.
