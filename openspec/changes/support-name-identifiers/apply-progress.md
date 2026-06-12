## PR 1 / Slice 1: Project refs only

- Branch: `feat/project-name-refs`
- Chain strategy: `stacked-to-main`
- Target: `main`
- Scope: project identifiers only; user email refs and pack `name@version` refs are intentionally out of scope for PR1.
- Mode: Standard (`strict_tdd: false`); tests were updated alongside behavior.

## Completed

- Added shared `validate_project_name()` validation for required, trimmed, non-digit-only project names.
- Added migration `002_unique_project_names.sql` with global `ux_projects_name` uniqueness.
- Mapped duplicate project names to `409` and digit-only project names to `400` on create/update.
- Added `GET /api/v1/projects/by-name/{name:path}` with exact, active, visibility-scoped single-row lookup.
- Resolved CLI project refs by exact project name through `agh/cli/project_refs.py` for project get/update/delete/member/pack commands while preserving `prj_...` and all-digit passthrough.
- Updated English README/CLI help guidance for project refs.

## Verification

- `uv run pytest tests/test_common_helpers.py tests/test_db_migrations.py tests/test_project_routes.py tests/test_cli_admin_commands.py tests/test_cli_pack_commands.py tests/test_docs_guidance.py` — passed (75 tests, 1 existing Starlette/httpx warning).
- `uv run pytest` — passed (244 tests, 1 existing Starlette/httpx warning).

## PR 2 / Slice 2: User email refs only

- Branch: `feat/user-email-refs`
- Chain strategy: `stacked-to-main`
- Target: `main` directly because PR1 is already merged to `main`.
- Scope: user email identifiers only; pack `name@version` refs remain out of scope for PR2.
- Mode: Standard (`strict_tdd: false`); tests were updated alongside behavior.

## Completed

- Added `GET /api/v1/users/by-email/{email:path}` before dynamic user routes with authentication, exact active-email lookup, invalid-email `400`, unauthorized `401`, non-admin `403`, and missing/inactive `404` behavior.
- Added `GET /api/v1/users/{user_id}` to support `agh user show` while preserving ID-only action routes.
- Added `agh/cli/user_refs.py` to resolve non-`usr_...` refs as exact emails through the API while keeping `usr_...` passthrough.
- Updated `agh user show`, `agh user update`, `agh user delete`, `agh token rotate`, `agh token reset`, and `agh project member add/remove` to accept user IDs or exact emails.
- Updated English README and CLI/help coverage for user refs.

## Verification

- `uv run pytest tests/test_user_routes.py tests/test_cli_admin_commands.py tests/test_docs_guidance.py` — passed (35 tests, 1 existing Starlette/httpx warning).
- `uv run pytest` — passed (248 tests, 1 existing Starlette/httpx warning).
- `uv run --with ruff ruff format --check .` — passed (51 files already formatted).
- `uv run --with ruff ruff check .` — passed.
- `git diff --check` — passed.

## Remaining Future Slices

- PR3 pack version refs: resolver endpoint/parser, CLI pack-ref resolution, and tests.
