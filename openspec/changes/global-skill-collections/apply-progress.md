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

## PR 1B.2 Progress

Skill-only validation and skill discovery slice for issue #97. Base: PR 1B.1 / `feat/global-skill-collections-skill-api`. Scope: reject instruction-bearing collection packages, add `GET /api/v1/skills`, add `GET /api/v1/skills:resolve`, resolve concrete package versions, and fail closed when `@latest` resolves to instruction-bearing content. Excludes CLI global skills and workspace prompt wording.

Completed tasks: 2.2, 2.3, 4.1B discovery coverage.
Review budget: maintainer-approved `size:exception` for PR 1B.2 after validation/discovery plus review fixes pushed the diff over 400 changed lines.

## PR 1B.2 TDD Cycle Evidence

| Task | Test File | Layer | Safety Net | RED | GREEN | TRIANGULATE | REFACTOR |
|------|-----------|-------|------------|-----|-------|-------------|----------|
| 2.2 Skill-only validation | `tests/test_collection_package_assignments.py` | Integration | ✅ Assignment tests green | ✅ Instruction-bearing package tests failed before validation | ✅ Rejection tests passed after validation helper | ✅ AGENTS.md, CLAUDE.md, latest-resolving-to-instruction, and skill-only acceptance covered | ✅ Validation reused stored package artifacts |
| 2.3 Skill list/resolve | `tests/test_collection_package_assignments.py` | Integration | ✅ Assignment tests green | ✅ List/resolve tests failed before endpoints | ✅ Discovery tests passed after `/skills` and `/skills:resolve` | ✅ Active/inactive filtering, latest resolution, fail-closed latest, collection filter, and download URL covered | ✅ Reused package artifact URL helper |

## PR 1B.2 Verification

- `uv run pytest tests/test_collection_package_assignments.py -q` → 14 passed.
- `uv run ruff format --check agh/server/routes/collections.py tests/test_collection_package_assignments.py` → passed.
- `uv run ruff check agh/server/routes/collections.py tests/test_collection_package_assignments.py` → passed.
- `git diff --check feat/global-skill-collections...HEAD` → passed.
- `uv run pytest -q` → 384 passed, 1 skipped.

Remaining: PR 2 adds CLI global skills install/remove, agent default selection, and native path resolver.

## PR 1B.2 Post-Verify Review Fixes

Reliability blocker and contract warning fixes applied after formal verify passed.

### Fixes Applied

- `update_collection_package()` now revalidates the effective package/version for skill-only compliance whenever the assignment will remain/become active, even when `package_ref` is not supplied in the PATCH payload. This prevents a stored `@latest` assignment from being successfully patched (e.g., `position` or `active: true`) after `latest` drifts to an instruction-bearing package.
- `GET /skills:resolve` now accepts either the stored requested ref (e.g., `acme/tool@latest`) or the concrete resolved ref returned by `GET /skills` (e.g., `acme/tool@1.2.0`), while still requiring the resolved package to be collection-authorized and skill-only.
- `_validate_skill_only_package()` accepts an optional pre-resolved `version_row` to avoid redundant version resolution in `list_skills()` and `resolve_skill()`.

### Tests Added

- `test_patch_rejects_active_assignment_when_latest_resolves_to_instruction_package`
- `test_skills_resolve_accepts_concrete_ref_from_skills_list`

### Verification After Fixes

- `uv run pytest tests/test_collection_package_assignments.py -q` → 16 passed.
- `uv run pytest -q` → 386 passed, 1 skipped.
- `uv run ruff format agh/server/routes/collections.py tests/test_collection_package_assignments.py` → 2 files reformatted.
- `uv run ruff check agh/server/routes/collections.py tests/test_collection_package_assignments.py` → All checks passed.

## PR 1B.2 Final Review Fixes

- Added warning-level logging when `GET /skills` suppresses an active assignment because the resolved package is no longer skill-only.
- Hardened collection filter assertions to prove non-empty/cardinality behavior.
- Added an isolated inactive-collection resolve test where the assignment remains active.
- Removed dead parsing variables from the package publishing test helper.

### Final Verification

- `uv run pytest tests/test_collection_package_assignments.py -q` → 18 passed.
- `uv run pytest -q` → 388 passed, 1 skipped.
- `uv run ruff format agh/server/routes/collections.py tests/test_collection_package_assignments.py` → clean.
- `uv run ruff check agh/server/routes/collections.py tests/test_collection_package_assignments.py` → clean.

## PR 2A.1a Progress

Core global-skill module slice for issue #97. Base: PR 1B.2 / `feat/global-skill-collections`. Scope: `agh/cli/global_skills.py`, the `global_skill_dir(agent)` path helper in `agh/cli/agent_integrations.py`, and focused core tests in `tests/test_global_skills.py`. Excludes default-agent read/write/clear helpers (PR 2A.1b) and CLI commands in `agh/cli/main.py` (PR 2A.2).

Completed tasks: 3.1, 3.2a (`global_skill_dir`), 4.2.
Review budget: `size:exception` required; the core module plus its tests exceed the 400-line review budget.

### TDD Cycle Evidence

| Task | Test File | Layer | Safety Net | RED | GREEN | TRIANGULATE | REFACTOR |
|------|-----------|-------|------------|-----|-------|-------------|----------|
| 3.1 `agh/cli/global_skills.py` | `tests/test_global_skills.py` | Unit/Integration | ✅ Existing CLI tests passed before modifying CLI files | ✅ Core install/remove/lock/cache/resolve/download tests failed before `global_skills.py` | ✅ Focused core tests passed after implementing `global_skills.py` | ✅ Covered XDG/fallback paths, resolve URL, download auth, install target/lock/cache, same-checksum no-op, AGH-owned update, untracked + force, cross-package conflict, remove cleanup, list filtering | ✅ Extracted helpers (`_target_path`, `_cache_path`, `_find_entry`, `_write_lock`) |
| 3.2a `agent_integrations.py` `global_skill_dir` | `tests/test_global_skills.py` | Unit | ✅ Included in CLI safety net above | ✅ Wrote failing tests for `global_skill_dir` paths and invalid-agent rejection before implementation | ✅ Focused tests passed after adding helper | ✅ Covered opencode/claude paths and invalid agent rejection | ✅ Reused existing `SUPPORTED_AGENT_TARGETS` constant |
| 4.2 Install/remove/conflict tests | `tests/test_global_skills.py` | Unit/Integration | ✅ Existing global-skills core tests green before adding edge cases | ✅ Added failing conflict/untracked-force/remove-missing tests before production fixes | ✅ All edge-case tests passed | ✅ Added different-package-same-skill conflict and untracked-with-force tests | ✅ Cleaned assertions to verify real behavior |

### Verification

- `uv run pytest tests/test_global_skills.py -q` → 15 passed.
- `uv run pytest tests/test_agent_command.py tests/test_cli_package_commands.py -q` → 43 passed.
- `uv run ruff format agh/cli/global_skills.py agh/cli/agent_integrations.py tests/test_global_skills.py` → clean.
- `uv run ruff check agh/cli/global_skills.py agh/cli/agent_integrations.py tests/test_global_skills.py` → clean.
- `uv run pytest -q` → 407 passed, 1 skipped.
- `git diff --check feat/global-skill-collections` → passed.

### Preservation

- The full PR 2A.1 work (core module + agent-integration helpers) before this split is preserved as tag `backup/pr2a1-full-6d3736c` and branch `preserve/feat/global-skill-collections-cli-2a1b` at commit `6d3736c`.
- The full original PR 2A work (including CLI commands and CLI tests) remains on branch `preserve/feat/global-skill-collections-cli-full` at commit `3b5594e08cc61ddbf9f455b7782447cdc99c4e51`.

Remaining: PR 2A.1b adds default-agent read/write/clear helpers and their tests; PR 2A.2 adds CLI commands in `agh/cli/main.py` and CLI command tests.

## PR 2A.1b Progress

Default global-skill agent helper slice for issue #97. Base: PR 2A.1a / `feat/global-skill-collections`. Scope: default agent read/write/clear helpers in `agh/cli/agent_integrations.py` and focused tests in `tests/test_global_skills.py`. Excludes CLI commands in `agh/cli/main.py` (PR 2A.2).

Completed tasks: 3.2b.
Review budget: within the 400-line budget; no `size:exception` required.

### TDD Cycle Evidence

| Task | Test File | Layer | Safety Net | RED | GREEN | TRIANGULATE | REFACTOR |
|------|-----------|-------|------------|-----|-------|-------------|----------|
| 3.2b Default-agent helpers | `tests/test_global_skills.py` | Unit | ✅ Existing global-skills tests remained green before this slice; post-review focused/full suites pass | ✅ Added default-agent roundtrip/idempotent/corrupt tests before helper implementation; review fixes added failing non-directory-parent and invalid UTF-8 tests before code changes | ✅ Focused tests passed after adding read/write/clear helpers and after post-review hardening | ✅ Covered no default, write/read, clear, idempotent clear, invalid agent write, corrupt TOML, invalid UTF-8, non-directory parent for read/clear, and symlinked defaults/parent for read/clear | ✅ Removed unused `monkeypatch` fixture from roundtrip test and kept helper changes minimal |

### Post-Review Fixes

- `read_global_skill_default_agent()` now rejects a non-directory `XDG_STATE_HOME/agh/global-skills` parent instead of treating the default as absent.
- `clear_global_skill_default_agent()` now rejects the same non-directory parent instead of returning `False`.
- Invalid UTF-8 while reading `defaults.toml` is wrapped in `AgentPreferenceError`.
- Added behavior tests for non-directory parents, invalid UTF-8, symlinked defaults files, and symlinked defaults parents.

### Verification

- `uv run pytest tests/test_global_skills.py -q` → 41 passed.
- `uv run pytest -q` → 433 passed, 1 skipped.
- `uv run ruff check tests/test_global_skills.py agh/cli/agent_integrations.py` → All checks passed.
- `uv run ruff format --check tests/test_global_skills.py agh/cli/agent_integrations.py` → 2 files already formatted.
- `uv run --with pyright pyright agh tests` → 0 errors, 0 warnings, 0 informations.
- `git diff --check feat/global-skill-collections...HEAD` → passed after final amend.

Remaining: PR 2A.2 adds CLI commands in `agh/cli/main.py` and CLI command tests.

## PR 2A.1c Progress
Focused remove/lock resilience hardening slice for issue #97. Completed tasks: 3.2c, 4.2c. Scope stays `agh/cli/global_skills.py`, `tests/test_global_skills.py`, and SDD artifacts; PR 2A.2 CLI commands remain out of scope.
Evidence: native install/remove plus AGH state lock/cache writes/deletes reject symlinked existing ancestors (`~/.config/opencode`, `$XDG_STATE_HOME/agh`); failed updates restore previous target/cache content, and failed rollback now raises `GlobalSkillError` with restore failure plus manual recovery context. Tests cover both blockers and prior tampered-target/malformed-lock recovery.
Verification is recorded in `verify-report-2A.1c.md`: diff 5 files, 363 insertions/37 deletions; focused tests 49 passed; full suite 441 passed, 1 skipped; ruff, format, pyright, and diff checks passed. Remaining: PR 2A.2 CLI commands.

## PR 2A.2 Progress

CLI command wiring slice for issue #97. Base: PR 2A.1c / `feat/global-skill-collections`. Scope: `agh skill list`, `agh skill install`, `agh skill remove`, `agh skill installed`, and global-skill-scoped `agh skill agent show/select/clear` in `agh/cli/main.py`, plus focused CLI tests in `tests/test_global_skills.py`. Excludes full CLI docs/help documentation beyond command registration/help text.

Completed tasks: 3.3, 4.3.
Review budget: within the 400-line target at implementation time; no `size:exception` required.
### TDD Cycle Evidence

| Task | Test File | Layer | Safety Net | RED | GREEN | TRIANGULATE | REFACTOR |
|------|-----------|-------|------------|-----|-------|-------------|----------|
| 3.3 CLI skill commands | `tests/test_global_skills.py` | CLI/Integration | ✅ `uv run pytest tests/test_global_skills.py tests/test_agent_command.py tests/test_cli_package_commands.py -q` → 84 passed before modifying command wiring | ✅ Added failing tests for `skill list`, `skill install --agent --force`, `skill remove`, `skill installed`, and `skill agent show/select/clear` before commands existed | ✅ Focused tests passed after adding `skill_app`, `skill_agent_app`, API requester binding, and command handlers | ✅ Covered available-skill listing, install wiring, remove with default agent, installed lock output, default-agent roundtrip, prompt save path, and non-TTY failure | ✅ Reused existing `_echo_table`, `_fail`, `_prompt_selection_index`, and default-agent helpers; formatted and linted touched files |
| 4.3 Prompt/default-agent CLI behavior | `tests/test_global_skills.py` | CLI/Integration | ✅ Included in CLI safety net above | ✅ Prompt wording/default-save/non-TTY tests failed before `_resolve_global_skill_agent()` and `_prompt_global_skill_agent()` existed | ✅ `uv run pytest tests/test_global_skills.py -q` → 56 passed after rebase onto PR 2A.1c | ✅ Covered exact `Select the agent for global skills:` wording, save-default confirmation, saved default usage for remove, and non-interactive failure | ✅ Kept prompt logic isolated in small helper functions |
### Verification

- `git diff --check feat/global-skill-collections...HEAD` → passed after rebase.
- `uv run pytest tests/test_global_skills.py -q` → 56 passed after rebase onto PR 2A.1c.
- `uv run pytest tests/test_global_skills.py tests/test_agent_command.py tests/test_cli_package_commands.py -q` → 99 passed after rebase onto PR 2A.1c.
- `uv run pytest -q` → 448 passed, 1 skipped.
- `uv run ruff check agh tests` → passed.
- `uv run ruff format --check agh tests` → 61 files already formatted.
- `uv run --with pyright pyright agh tests` → 0 errors, 0 warnings, 0 informations.
