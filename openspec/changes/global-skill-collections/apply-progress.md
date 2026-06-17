## PR 1A Progress
Foundation slice for issue #97 and tracker PR #98. Base: `feat/global-skill-collections`. Scope: collection table, `col_` IDs, router wiring, CRUD routes, and migration/auth/CRUD tests. Excludes package assignments, skill discovery APIs, CLI global skills, and workspace prompt wording.
Completed tasks: 1.1, 1.3, 2.1A, 4.1A.
Review budget: maintainer-approved `size:exception` for PR 1A after formatting pushed the final diff over 400 changed lines.

## TDD Cycle Evidence
| Task | RED | GREEN | TRIANGULATE | SAFETY NET | REFACTOR |
|------|-----|-------|-------------|------------|----------|
| 1.1 Migration and `col_` prefix | ✅ Written: migration/prefix tests failed before schema/prefix support. | ✅ Focused migration/routes tests passed. | ✅ Schema version, columns, FK, and prefix support covered. | ✅ Existing migration/package route tests ran in original server slice. | ✅ Deferred `collection_packages`/`casn_` to PR 1B. |
| 1.3 Router wiring | ✅ Written: collection routes returned 404 before router include. | ✅ Focused route tests passed after `app.py` wiring. | ✅ List/create/get/update/delete exercise the router. | ✅ Full `uv run pytest` passed. | ✅ Reused existing `/api/v1` include pattern. |
| 2.1A CRUD foundation | ✅ Written: owner/admin/member CRUD and active/inactive tests failed before routes. | ✅ Focused route tests and full suite passed after implementation. | ✅ Owner, admin, member, unauthenticated, active, inactive, invalid input, and duplicate-name cases covered. | ✅ Full suite passed after split and cleanup. | ✅ Removed package assignment and skill discovery from PR 1A. |
| 4.1A Coverage cleanup | ✅ Written: review found missing unauthenticated and inactive admin-read coverage. | ✅ `uv run pytest tests/test_collection_routes.py` passed. | ✅ Added auth guard checks and owner/admin inactive direct-read coverage. | ✅ `git diff --check` and full suite passed. | ✅ Test-only cleanup documented role/active contract. |

Verification after split: focused tests → 14 passed; full `uv run pytest` → 360 passed, 1 skipped.
Remaining: PR 1B adds assignments/skill discovery; PR 2 adds CLI/global install.

## PR 1A.2 Progress

Hardening slice for issue #97. Base: `feat/global-skill-collections-server` / PR #99. Scope: collection CRUD API contract hardening only. Excludes collection package assignments, skill discovery APIs, CLI global skills, workspace prompt wording, and DB migration length constraints.

Completed tasks: 6.1, 6.2.
Review budget: within 400-line budget; no `size:exception` required for the API-only slice.

## PR 1A.2 TDD Cycle Evidence

| Task | Test File | Layer | Safety Net | RED | GREEN | TRIANGULATE | REFACTOR |
|------|-----------|-------|------------|-----|-------|-------------|----------|
| 6.1 Bounded collection validation | `tests/test_collection_routes.py` | Integration | ✅ `uv run pytest tests/test_collection_routes.py -q` → passed | ✅ Oversized create/update failed before route validation | ✅ Focused tests passed after `_clean_name` and `_clean_description` | ✅ API create/update paths covered | ✅ `uv run ruff format ...`; focused tests still passed |
| 6.2 Expanded CRUD/update contract | `tests/test_collection_routes.py` | Integration | ✅ Included in focused safety net | ✅ Added admin create/name update/reactivation/invalid update/duplicate update/unauthenticated DELETE assertions before production changes | ✅ Focused tests passed with existing CRUD plus validation changes | ✅ Happy path, auth guard, invalid payload, duplicate, and active-state update paths covered | ✅ Formatted touched Python files; focused tests still passed |

## PR 1A.2 Verification

- `uv run pytest tests/test_collection_routes.py -q` → 10 passed.
- `git diff --check` → passed.
- `uv run pytest -q` → 364 passed, 1 skipped.

Remaining: PR 1A.3 adds migration/schema length constraints; PR 1B adds assignments/skill discovery; PR 2 adds CLI/global install.

## PR 1A.3 Progress

Migration-hardening slice for issue #97. Base: `feat/global-skill-collections-server-hardening` / PR 1A.2. Scope: SQLite `005_collection_constraints` migration, fail-fast diagnostics for legacy over-limit rows, and schema-level length constraint coverage. Excludes collection package assignments, skill discovery APIs, CLI global skills, and workspace prompt wording.

Completed tasks: 6.3.
Review budget: maintainer-approved `size:exception` for PR 1A.3 after migration hardening pushed the diff over 400 changed lines.

## PR 1A.3 TDD Cycle Evidence

| Task | Test File | Layer | Safety Net | RED | GREEN | TRIANGULATE | REFACTOR |
|------|-----------|-------|------------|-----|-------|-------------|----------|
| 6.3 Direct migration/schema coverage | `tests/test_db_migrations.py` | Integration | ✅ `uv run pytest tests/test_db_migrations.py -q` → passed | ✅ Added active default/check, name uniqueness, created_by FK, and length constraint assertions; length checks failed before migration update | ✅ Focused tests passed after migration CHECK constraints and fail-fast diagnostics | ✅ Default, valid insert, invalid active, duplicate name, invalid creator, long name, long description, idempotency, and legacy over-limit failure paths covered | ✅ Formatted touched Python files; focused tests still passed |

## PR 1A.3 Verification

- `uv run pytest tests/test_db_migrations.py -q` → 13 passed.
- `git diff --check` → passed.
- `uv run pytest -q` → 369 passed, 1 skipped.

Remaining: PR 1B adds assignments/skill discovery; PR 2 adds CLI/global install.

## PR 1B.1 Progress

Collection package assignment foundation slice for issue #97. Base: `feat/global-skill-collections` / PR 1A. Scope: `casn_` ID prefix, `006_collection_packages` migration, collection package assignment CRUD/list endpoints under the collections router with owner/admin authorization, assignment response serialization with `@latest` resolution, and focused assignment tests. Excludes skill-only package validation, `GET /api/v1/skills`, `GET /api/v1/skills:resolve`, `@latest` fail-closed skill validation, CLI global skills, and workspace prompt wording. The full PR 1B implementation (including the excluded items) is preserved on branch `preserve/feat/global-skill-collections-skill-api-full` and in `/tmp/feat-global-skill-collections-skill-api-full-*.patch` for PR 1B.2.

Completed tasks: 1.2, 2.1B, 4.1B.
Review budget: target ≤400 changed lines; final diff will be reported after verification.

## PR 1B.1 TDD Cycle Evidence

| Task | Test File | Layer | Safety Net | RED | GREEN | TRIANGULATE | REFACTOR |
|------|-----------|-------|------------|-----|-------|-------------|----------|
| 1.2 `casn_` prefix + collection_packages storage | `tests/test_collection_package_assignments.py` | Integration | ✅ Existing migration/id tests passed | ✅ Prefix and migration-table tests failed before `casn`/`006_collection_packages` | ✅ Prefix/migration tests passed after implementation | ✅ Prefix validation, table columns, and migration version covered | ✅ Used existing migration/id conventions |
| 2.1B Assignment endpoints | `tests/test_collection_package_assignments.py` | Integration | ✅ Existing collection route tests passed | ✅ Auth/validation/CRUD tests failed before endpoints | ✅ Focused assignment tests passed after routes | ✅ Owner/admin create, member rejection, invalid refs, duplicate, reactivation, update, deactivation covered | ✅ Extracted shared helpers (`_assignment_row`, `_collection_package_response`) |

## PR 1B.1 Verification

- `uv run pytest tests/test_collection_package_assignments.py -q` → 5 passed.
- `uv run pytest tests/test_db_migrations.py -q` → 13 passed.
- `uv run pytest tests/test_collection_routes.py -q` → 11 passed.
- `git diff --check` → passed.
- `uv run ruff format agh/server/routes/collections.py tests/test_collection_package_assignments.py tests/test_db_migrations.py agh/common/ids.py` → 1 file reformatted.
- `uv run pytest -q` → 375 passed, 1 skipped.

Review budget: maintainer-approved `size:exception` for PR 1B.1 at 716 changed lines vs `feat/global-skill-collections`; PR 1B.1 remains a focused assignment-foundation slice and is still significantly smaller than the original ~1,184-line PR 1B.

Remaining: PR 1B.2 adds skill-only validation, `/skills`, `/skills:resolve`, and `@latest` fail-closed behavior from the preserved full implementation. PR 2 adds CLI/global install.
