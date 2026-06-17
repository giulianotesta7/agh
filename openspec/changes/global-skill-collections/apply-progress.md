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
