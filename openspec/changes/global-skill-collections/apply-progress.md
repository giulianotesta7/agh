# Apply Progress: Global Skill Collections — PR 1A

## PR 1A Progress

Foundation slice for issue #97 and tracker PR #98. Base branch: `feat/global-skill-collections`. Scope includes collection table, `col_` IDs, router wiring, CRUD routes, and focused migration/auth/CRUD tests. It excludes package assignments, skill-only validation, `/skills`, `/skills:resolve`, CLI global skills, and workspace prompt wording.

Completed tasks: 1.1, 1.3, 2.1A, and 4.1A.

Strict TDD evidence was produced during the original oversized server slice, then split to this PR 1A boundary. Verification after split:

- `uv run pytest tests/test_db_migrations.py tests/test_collection_routes.py` → 12 passed.
- `uv run pytest` → 358 passed, 1 skipped.

Changed areas: `agh/common/ids.py`, `agh/server/migrations/004_collections.sql`, `agh/server/routes/collections.py`, `agh/server/app.py`, collection route/migration tests, and PR 1A task checkboxes.

Remaining: PR 1B must add `collection_packages`, `casn_` IDs, package assignment endpoints, skill-only validation, skill list/resolve APIs, and related tests. PR 2 remains the CLI/global install slice.
