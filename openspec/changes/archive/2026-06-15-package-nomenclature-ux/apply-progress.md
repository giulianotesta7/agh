# Apply Progress: Package Nomenclature UX

## Status

- Mode: Strict TDD
- Delivery: single large PR approved with `size:exception`
- Completed tasks: 16/16
- Final validation: `uv run pytest` → 353 passed, 1 skipped

## Completed Tasks

- [x] 1.1 Add failing tests for package terminology, no legacy `pack`/`packs` commands/routes, and canonical `pkg`/`pkgv` IDs in `tests/`.
- [x] 1.2 Add DB migration test for `packs`/`pack_versions`/`project_packs` -> `packages`/`package_versions`/`project_packages`, preserving `asn_` links.
- [x] 1.3 Add filesystem migration test for `/data/packs` -> `/data/packages` and `package_versions.storage_path` rewrite.
- [x] 2.1 Rename ID/ref/manifest helpers in `agh/common/ids.py`, `agh/common/validation.py`, and `agh/common/pack_manifest.py` to `pkg`/`pkgv`, `PackageManifest`, and `agh.package.toml`.
- [x] 2.2 Implement `003_rename_packs_to_packages.sql` and startup storage repair in `agh/server/db.py` or migration bootstrap.
- [x] 2.3 Rename server routes from `agh/server/routes/packs.py` to `agh/server/routes/packages.py` and update project package endpoints in `agh/server/routes/projects.py`.
- [x] 3.1 Replace `agh pack` / `agh project pack` with `agh package` / `agh project package` in `agh/cli/main.py`; delete legacy command registration.
- [x] 3.2 Rename `agh/cli/pack_init.py`, `pack_publish.py`, and `pack_refs.py` to package modules; update authoring/publish flow to `agh.package.toml`.
- [x] 3.3 Update `agh/cli/workspace_pull.py`, `pull_plan.py`, and `pull_markers.py` to `packages`, `package_ref`, and `[[packages]]`.
- [x] 3.4 Implement omitted-ref interactive add flow: show unassigned latest-stable package refs, confirm selection, cancel with `Cancelled.` and exit 130.
- [x] 3.5 Amend `agh project package add` with no arguments to select a visible project first, then reuse package selection.
- [x] 4.1 Add or update API/CLI tests for `agh package` success, `agh pack` rejection, new `/packages` routes, and project package add behaviors.
- [x] 4.2 Add doc/README/README.es updates plus doc tests for package terminology, `agh.package.toml`, and `package_ref`.
- [x] 4.3 Add final grep enforcement tests to fail on remaining public `pack` terminology, except justified migration internals.
- [x] 5.1 Remove obsolete `pack` imports, filenames, and route registrations after green tests.
- [x] 5.2 Run full suite plus terminology grep sweep to confirm only approved historical migration internals remain.

## TDD Cycle Evidence

| Task | Test File | Layer | Safety Net | RED | GREEN | TRIANGULATE | REFACTOR |
|------|-----------|-------|------------|-----|-------|-------------|----------|
| 1.1 | `tests/test_package_nomenclature.py` | Unit/API/CLI | ✅ `uv run pytest` baseline: 306 passed, 1 skipped | ✅ New package nomenclature tests failed on missing modules/routes/IDs | ✅ Focused tests passed | ✅ IDs, manifest, CLI, API cases | ✅ Public grep enforcement added |
| 1.2 | `tests/test_package_migration.py` | Migration | ✅ baseline captured before edits | ✅ Legacy table migration test failed before 003 hook | ✅ Focused migration tests passed | ✅ Table, ID rewrite, `asn_` relationship assertions | ✅ Migration SQL delegated to Python hook to stay conditional/idempotent |
| 1.3 | `tests/test_package_migration.py` | Migration/filesystem | ✅ baseline captured before edits | ✅ Storage repair test failed before move/rewrite logic | ✅ Focused migration tests passed | ✅ DB path rewrite plus filesystem move assertions | ✅ Conflict-safe move logic added |
| 2.1 | `tests/test_common_helpers.py`, `tests/test_package_nomenclature.py` | Unit | ✅ existing helper tests passing before edits | ✅ Tests expected `pkg`/`pkgv`, `PackageManifest`, `agh.package.toml` | ✅ Helper tests passed | ✅ ID, canonical ref, id ref, legacy manifest rejection | ✅ Old helper module renamed |
| 2.2 | `tests/test_db_migrations.py`, `tests/test_package_migration.py` | Migration | ✅ migration tests covered existing schema | ✅ 003 migration/version/storage tests failed before implementation | ✅ Migration tests passed | ✅ Fresh DB, legacy DB, concurrent startup, idempotency | ✅ Conditional 003 hook avoids fresh-schema failure |
| 2.3 | `tests/test_package_routes.py`, `tests/test_project_package_assignments.py` | API | ✅ route tests passing before edits | ✅ `/packages` and project package tests failed before route rename | ✅ API tests passed | ✅ list/publish/download/assign/update/remove/available cases | ✅ Renamed router and removed old `/packs` registration |
| 3.1 | `tests/test_cli_package_commands.py`, `tests/test_package_nomenclature.py` | CLI | ✅ CLI tests passing before edits | ✅ `agh package`/`agh pack` command tests failed before registration change | ✅ CLI tests passed | ✅ root package, nested project package, unknown old aliases | ✅ Old command registration removed |
| 3.2 | `tests/test_cli_package_commands.py`, `tests/test_common_helpers.py` | CLI/unit | ✅ publish/init tests covered existing behavior | ✅ `agh.package.toml` expectations failed before module/manifest rename | ✅ Focused and full tests passed | ✅ init, publish, symlink, oversized, malformed manifest cases | ✅ Package module names replace old pack files |
| 3.3 | `tests/test_workspace_pull.py`, `tests/test_pull_markers.py`, `tests/test_integration_smoke.py` | Unit/integration | ✅ workspace pull tests passing before edits | ✅ Lockfile `package_ref` tests failed before lock writer change | ✅ Workspace/integration tests passed | ✅ marker package attribute, cache packages path, TOML lock package_ref | ✅ Workspace helper names cleaned |
| 3.4 | `tests/test_cli_package_commands.py`, `tests/test_project_package_assignments.py` | CLI/API | ✅ CLI/API baseline available | ✅ Omitted-ref prompt and available API tests failed before implementation | ✅ Focused tests passed | ✅ confirm, cancel 130, all-assigned message, unassigned latest-stable API | ✅ Selector kept explicit ref non-interactive |
| 4.1 | `tests/test_cli_package_commands.py`, `tests/test_package_routes.py`, `tests/test_project_package_assignments.py` | CLI/API | ✅ baseline captured | ✅ Package-surface tests failed during migration | ✅ Full suite passed | ✅ Success/rejection/routes/add behaviors | ✅ Tests renamed to package files |
| 4.2 | `tests/test_docs_guidance.py`, README checks | Docs | ✅ docs tests existed before docs edits | ✅ Documentation expectations updated for package terminology | ✅ Docs tests passed in full suite | ✅ README, README.es, Dockerfile, OpenSpec spec docs | ✅ Added lockfile `package_ref` example |
| 4.3 | `tests/test_package_nomenclature.py` | Unit/static | ✅ full suite green before enforcement | ✅ Enforcement test added for public legacy terms | ✅ Enforcement test passed | ✅ Allows only migration internals while scanning public code/docs/specs | ✅ Spec directory renamed to package artifact errors |
| 5.1 | Full suite + grep | Cleanup | ✅ full suite green before cleanup sweep | ✅ Obsolete import/file/route checks failed via grep before cleanup | ✅ Full suite passed | ✅ Module filenames, route registrations, public terms | ✅ Internal helper names cleaned where practical |
| 5.2 | Full suite + grep | Regression | ✅ all focused suites green | ✅ Final suite catches regressions | ✅ `uv run pytest`: 318 passed, 1 skipped | ✅ Grep sweep shows only migration/test legacy fixtures | ✅ No further refactor needed |

## Test Summary

- Total tests written/updated: package nomenclature, migration, CLI/API interactive add, available packages API, lockfile `package_ref`, public grep enforcement, docs expectations.
- Total tests passing: 331 passed, 1 skipped.
- Layers used: Unit, migration, API, CLI integration, workspace integration.
- Approval tests: Existing behavior tests updated across CLI/API/workspace/docs while preserving current non-renamed behavior semantics.
- Pure functions created: none; changes were route/CLI/migration/workspace contract focused.

## Deviations

None requiring spec changes. The SQL migration file is a hook marker; the conditional legacy table/storage migration is implemented in `agh/server/db.py` because SQLite SQL cannot safely branch on deployed legacy-vs-fresh schemas inside the generic migration runner.

## Risks / Follow-up

- This is a large `size:exception` diff by explicit approval.
- Migration internals intentionally retain old table/path names (`packs`, `pack_versions`, `/packs`) so existing data can be preserved and moved forward.

## Verify Warning Remediation

### Root Cause Summary

- Formatter warning: the implementation changed source and test files without applying `ruff format`; `uv run ruff format --check` reproduced the 14-file formatting drift.
- Non-TTY omitted-ref warning: `_select_available_package_ref()` listed available packages and called `typer.prompt()` unconditionally. In a non-interactive stdin context, the prompt raised EOF and Typer exited `1` instead of the design-required usage error exit `2`.
- Pyright warning: `pyright` is not available/configured in this worktree; no remediation was attempted because the verify report treats it as an environmental suggestion.

### Remediation Evidence

| Warning | Action | Evidence |
|---------|--------|----------|
| Ruff format drift | Ran `uv run ruff format` to apply canonical formatting. | Follow-up `uv run ruff format --check` reported `55 files already formatted`. |
| Omitted-ref non-TTY exit code | Added an explicit stdin interactivity guard before prompting when assignable packages exist; non-interactive omitted-ref add now fails through `_fail(..., code=2)` and does not POST an assignment. | Added `tests/test_cli_package_commands.py::test_cli_project_package_add_without_ref_non_tty_exits_2`; focused and full pytest runs pass. |

### TDD Cycle Evidence — Remediation

| Task | Test File | Layer | Safety Net | RED | GREEN | TRIANGULATE | REFACTOR |
|------|-----------|-------|------------|-----|-------|-------------|----------|
| Verify warning: non-TTY omitted-ref exit code | `tests/test_cli_package_commands.py` | CLI | ✅ Existing omitted-ref tests: `4 passed` before production edits | ✅ New non-TTY regression failed with exit `1` before implementation | ✅ Focused omitted-ref tests passed after guard: `4 passed` | ✅ Existing prompt confirm, cancel 130, all-assigned, and explicit-ref tests cover alternate paths | ✅ Extracted `_stdin_is_interactive()` seam and kept assignment flow unchanged |
| Verify warning: Ruff formatting | N/A | Formatting | ✅ `uv run ruff format --check` reproduced 14 unformatted files | ➖ Formatter remediation, no behavior test required | ✅ `uv run ruff format --check`: `55 files already formatted` | ➖ Structural formatting only | ✅ No code behavior changed by formatter |

### Verification Commands

```text
uv run pytest tests/test_cli_package_commands.py -k 'without_ref or project_package_commands_resolve'
Result: 4 passed, 21 deselected

uv run pytest tests/test_cli_package_commands.py -k 'non_tty or without_ref'
RED before fix: 1 failed, 3 passed, 22 deselected; new non-TTY test observed exit 1 instead of 2
GREEN after fix: 4 passed, 22 deselected

uv run ruff format
Result: 14 files reformatted, 41 files left unchanged

uv run pytest
Result: 319 passed, 1 skipped

uv run ruff check
Result: All checks passed!

uv run ruff format --check
Result: 55 files already formatted
```

### Remaining Warnings

- `pyright` remains unavailable/not configured in this worktree. Treat type-checking as an environmental/tooling follow-up if the project wants it in the verify gate.

## Fresh Review Blocker Remediation

### Root Cause Summary

- DB/filesystem migration safety blocker: `agh/server/db.py` rewrote DB rows inside a SQLite savepoint but moved `/data/packs` children to `/data/packages` directly. A filesystem failure after one child move could roll back the DB while leaving moved files behind, making retry unsafe.
- Silent legacy row loss blocker: the legacy table copy used `INSERT OR IGNORE` and then dropped `packs`, `pack_versions`, and `project_packs`; mapped key collisions could be ignored without surfacing data loss.
- Legacy workspace marker blocker: workspace pull markers only accepted `package="..."`; existing AGH-managed blocks rendered with legacy marker metadata could fail parsing instead of being normalized during the next pull.
- Adjacent warning: omitted-ref `agh project package add <project>` fetched available packages before checking TTY status, so non-interactive invocations could still make an API call before failing.

### Remediation Evidence

| Blocker | Action | Evidence |
|---------|--------|----------|
| Transactional/idempotent DB/filesystem migration | Added storage preflight before DB mutation and rollback-safe child moves that restore already-moved children on failure; retry then succeeds. Added migration start/success/failure logging with recovery context. | `tests/test_package_migration.py::test_storage_repair_rolls_back_partial_move_failure_for_retry` failed RED on partial move residue, then passed after rollback-safe moves. |
| `INSERT OR IGNORE` data loss | Replaced ignoring SQL copy with explicit mapped-key conflict detection, plain inserts, row-count validation, and migrated-key validation before dropping legacy tables. | `tests/test_package_migration.py::test_package_table_id_collision_fails_closed_and_preserves_legacy_data` failed RED because legacy tables were dropped, then passed after fail-closed migration validation. |
| Legacy workspace metadata | Added legacy marker parsing for existing managed blocks, then normalized output back to canonical `package="..."`; cache/lock pull behavior writes package paths and `package_ref`. | `tests/test_pull_markers.py::test_plan_managed_update_normalizes_legacy_pack_marker_metadata` and `tests/test_workspace_pull.py::test_populate_cache_and_write_lock_replaces_legacy_pack_cache_metadata` pass. |
| Non-TTY before remote fetch | Moved the TTY guard before the available-packages API request and introduced `COMMAND_CANCELLED_EXIT_CODE = 130`. | `tests/test_cli_package_commands.py::test_cli_project_package_add_without_ref_non_tty_exits_2` now asserts no API calls happen in non-TTY mode. |

### TDD Cycle Evidence — Fresh Review Remediation

| Task | Test File | Layer | Safety Net | RED | GREEN | TRIANGULATE | REFACTOR |
|------|-----------|-------|------------|-----|-------|-------------|----------|
| Safe DB/filesystem migration retry | `tests/test_package_migration.py` | Migration/filesystem | ✅ Existing migration tests read before edits | ✅ Focused run failed with partial moved children and legacy tables at risk | ✅ Focused blocker tests passed: `7 passed` | ✅ Failure rollback plus successful retry path | ✅ Storage preflight and rollback helper extracted |
| Fail-closed legacy table migration | `tests/test_package_migration.py` | Migration | ✅ Existing migration preservation test covered happy path | ✅ Collision test failed because no error was raised | ✅ Focused migration tests passed | ✅ ID collision preservation plus existing happy-path migration | ✅ Explicit plan/validation helpers replace `INSERT OR IGNORE` |
| Legacy marker/cache/lock migration | `tests/test_pull_markers.py`, `tests/test_workspace_pull.py` | Unit/integration | ✅ Existing pull marker/workspace tests passing after remediation | ✅ Legacy marker parse failed with `AGH-BEGIN requires package...` | ✅ Focused marker/cache tests passed | ✅ Marker normalization plus lock/cache package output | ✅ Legacy marker handling isolated to parsing only; renderer remains canonical |
| Non-TTY omitted-ref fetch guard | `tests/test_cli_package_commands.py` | CLI | ✅ Existing omitted-ref tests covered prompt/cancel/all-assigned paths | ✅ Non-TTY no-fetch assertion failed because GET occurred first | ✅ Focused CLI tests passed | ✅ Non-TTY failure plus interactive all-assigned path | ✅ Added named exit constant for cancellation |

### Verification Commands

```text
uv run pytest tests/test_package_migration.py tests/test_pull_markers.py::test_plan_managed_update_normalizes_legacy_pack_marker_metadata tests/test_workspace_pull.py::test_populate_cache_and_write_lock_replaces_legacy_pack_cache_metadata tests/test_cli_package_commands.py::test_cli_project_package_add_without_ref_non_tty_exits_2
RED before fix: 4 failed, 3 passed; failures covered partial filesystem residue, ignored DB collision, legacy marker parse, and non-TTY API call.
GREEN after fix: 7 passed.

uv run pytest tests/test_db_migrations.py tests/test_package_migration.py tests/test_pull_markers.py tests/test_workspace_pull.py tests/test_cli_package_commands.py -k 'without_ref or migration or managed_update or cache_and_write_lock or lock or pack_cache'
Result: 40 passed, 66 deselected.

uv run pytest
Result: 323 passed, 1 skipped.

uv run ruff check
Result: All checks passed!

uv run ruff format --check
Result: 55 files already formatted.

git diff --check
Result: passed.
```

### Remaining Risks

- Legacy handling remains intentionally scoped to data/workspace migration and preservation only. Old `agh pack`, `agh pkg`, `/api/v1/packs`, and `agh.pack.toml` remain unsupported.
- This remains a large approved `size:exception` change.

## Focused Re-review Blocker Remediation

### Root Cause Summary

- Filesystem migration rollback blocker: `_move_legacy_package_storage()` rolled back child moves only around the move loop. A final `old_root.rmdir()` failure happened outside that rollback scope, so SQLite could roll back while children stayed under `/data/packages`. Also, a failed cross-device `shutil.move()` could leave a partial target before the move was recorded for rollback.
- Non-TTY omitted-ref blocker: `project_package_add()` resolved project names before checking whether omitted-ref mode had an interactive terminal, so `agh project package add Docs` could call `/projects/by-name/Docs` before failing locally.

### Remediation Evidence

| Blocker | Action | Evidence |
|---------|--------|----------|
| Legacy root removal failure after moves | Moved `old_root.rmdir()` inside the rollback-protected operation and records each planned target before attempting the move. On failure, completed moves are restored to the legacy root. | Added `tests/test_package_migration.py::test_storage_repair_rolls_back_when_legacy_root_removal_fails`; RED failed with missing legacy artifact, GREEN passes. |
| Partial target after failed copy/move | Rollback now handles a staged move whose target exists while the original still exists by deleting the partial target; if the original is gone, it moves the target back. | Added `tests/test_package_migration.py::test_storage_repair_removes_partial_target_when_move_fails_before_recorded`; RED left `/packages/acme`, GREEN removes it. |
| Project-name omitted-ref non-TTY API call | Added an early omitted-ref TTY guard before project ref resolution; kept the prompt-level guard as a defensive seam. | Added `tests/test_cli_package_commands.py::test_cli_project_package_add_without_ref_project_name_non_tty_exits_before_api`; RED hit `/projects/by-name/Docs`, GREEN exits 2 with no calls. |
| Low-risk naming cleanup | Renamed confusing non-legacy package command/routes test names that still said `pack`. | Focused package command/routes tests pass after rename-only cleanup. |

### TDD Cycle Evidence — Focused Re-review Remediation

| Task | Test File | Layer | Safety Net | RED | GREEN | TRIANGULATE | REFACTOR |
|------|-----------|-------|------------|-----|-------|-------------|----------|
| Roll back legacy root removal failure | `tests/test_package_migration.py` | Migration/filesystem | ✅ Existing migration file baseline: `4 passed` | ✅ New rmdir-failure test failed because moved child stayed under `packages` | ✅ Focused migration tests: `3 passed`; full migration file: `6 passed` | ✅ Existing partial move retry plus new rmdir failure cover different rollback paths | ✅ Extracted rollback/removal helpers |
| Remove partial target after failed move/copy | `tests/test_package_migration.py` | Migration/filesystem | ✅ Existing migration file baseline: `4 passed` | ✅ New partial-target test failed because `/packages/acme` remained | ✅ Focused migration tests: `3 passed`; full migration file: `6 passed` | ✅ Source-preserved partial target and successful retry paths both covered | ✅ Rollback distinguishes partial target vs completed move |
| Fail omitted-ref non-TTY before project-name lookup | `tests/test_cli_package_commands.py` | CLI | ✅ Existing omitted-ref baseline: `4 passed` | ✅ New project-name test failed with API call to `/projects/by-name/Docs` and exit `1` | ✅ Focused CLI tests: `3 passed`; combined focused command/migration run: `14 passed` | ✅ Covers canonical project id no-call path, project-name no-call path, and interactive prompt path | ✅ Shared `_fail_omitted_package_ref_requires_tty()` guard |
| Rename confusing non-legacy test names | `tests/test_cli_package_commands.py`, `tests/test_package_routes.py` | Test cleanup | ✅ Focused command/routes tests passed before rename cleanup | ➖ Rename-only cleanup; no behavior change intended | ✅ Focused package command/routes tests passed | ➖ Existing behavior tests unchanged | ✅ Test names now use package terminology except intentional legacy migration contexts |

### Verification Commands

```text
uv run pytest tests/test_package_migration.py
Baseline before edits: 4 passed

uv run pytest tests/test_cli_package_commands.py -k 'without_ref'
Baseline before edits: 4 passed, 22 deselected

uv run pytest tests/test_package_migration.py::test_storage_repair_rolls_back_when_legacy_root_removal_fails tests/test_package_migration.py::test_storage_repair_removes_partial_target_when_move_fails_before_recorded
RED before fix: 2 failed

uv run pytest tests/test_cli_package_commands.py::test_cli_project_package_add_without_ref_project_name_non_tty_exits_before_api
RED before fix: 1 failed

uv run pytest tests/test_package_migration.py::test_storage_repair_rolls_back_when_legacy_root_removal_fails tests/test_package_migration.py::test_storage_repair_removes_partial_target_when_move_fails_before_recorded tests/test_package_migration.py::test_storage_repair_rolls_back_partial_move_failure_for_retry
GREEN after fix: 3 passed

uv run pytest tests/test_cli_package_commands.py::test_cli_project_package_add_without_ref_project_name_non_tty_exits_before_api tests/test_cli_package_commands.py::test_cli_project_package_add_without_ref_non_tty_exits_2 tests/test_cli_package_commands.py::test_cli_project_package_add_without_ref_prompts_and_confirms
GREEN after fix: 3 passed

uv run pytest tests/test_package_migration.py tests/test_cli_package_commands.py -k 'without_ref or migration or storage_repair or unknown_subcommands or read_commands'
Result: 14 passed, 19 deselected

uv run pytest tests/test_package_routes.py -k 'skill_only_package or skill_directory or routes_require_auth'
Result: 3 passed, 24 deselected

uv run pytest
Result: 326 passed, 1 skipped

uv run ruff check
Result: All checks passed!

uv run ruff format --check
Result: 55 files already formatted

git diff --check
Result: passed
```

### Remaining Risks

- Filesystem rollback is best-effort because the operating system can still fail rollback moves/removals; the migration now avoids the reviewed DB/filesystem split-brain paths and leaves the migration unrecorded for retry.
- Legacy `pack` names remain only where they describe existing deployed legacy schema/storage inputs or explicit legacy rejection tests.

## Final Readability Warning Cleanup

### Root Cause Summary

- Some non-legacy package CLI test function names still used `pack`, which looked like old product terminology even though the tests target canonical `package` behavior.
- Fresh package-table fixtures in route/schema tests used legacy-looking `pack_` / `packv_` IDs outside migration-compatibility contexts.
- One migration test name said `moves_packages_to_packages`, obscuring that it verifies legacy `/packs` storage migration into `/packages`.

### Remediation Evidence

| Warning | Action | Evidence |
|---------|--------|----------|
| CLI test names used non-legacy `pack` wording | Renamed the skill-only and symlink-path package publish tests to use package terminology. | Focused CLI publish tests passed. |
| Non-legacy package-table fixtures used legacy-looking IDs | Renamed fresh package route/schema fixture IDs to `pkg_*` / `pkgv_*`; left explicit legacy migration fixtures unchanged. | Focused package route and DB migration tests passed. |
| Ambiguous storage repair test name | Renamed the test to `test_storage_repair_moves_legacy_packs_to_packages_and_rewrites_storage_paths`. | Focused migration test passed. |

### TDD Cycle Evidence — Final Readability Cleanup

| Task | Test File | Layer | Safety Net | RED | GREEN | TRIANGULATE | REFACTOR |
|------|-----------|-------|------------|-----|-------|-------------|----------|
| Rename non-legacy CLI test names | `tests/test_cli_package_commands.py` | Test readability | ✅ Changed-file baseline: `67 passed` before edits | ➖ Rename-only cleanup; no product behavior change intended | ✅ Focused publish tests and full changed-file suite passed | ➖ Existing behavior assertions unchanged | ✅ Test names now use package terminology |
| Rename non-legacy package-table fixtures | `tests/test_package_routes.py`, `tests/test_db_migrations.py` | Test readability/schema | ✅ Changed-file baseline: `67 passed` before edits | ➖ Fixture-name cleanup; no product behavior change intended | ✅ Focused route/schema tests and full changed-file suite passed | ➖ Existing DB/storage assertions unchanged | ✅ Fresh package-table fixtures now use `pkg`/`pkgv`; legacy fixtures remain scoped to migration tests |
| Clarify legacy storage repair test name | `tests/test_package_migration.py` | Test readability/migration | ✅ Changed-file baseline: `67 passed` before edits | ➖ Rename-only cleanup; no product behavior change intended | ✅ Focused migration test and full changed-file suite passed | ➖ Existing migration assertions unchanged | ✅ Test name now states legacy packs -> packages |

### Verification Commands

```text
uv run pytest tests/test_cli_package_commands.py tests/test_package_routes.py tests/test_db_migrations.py tests/test_package_migration.py
Baseline before edits: 67 passed

uv run pytest tests/test_cli_package_commands.py::test_cli_package_publish_accepts_skill_only_package tests/test_cli_package_commands.py::test_cli_package_publish_refuses_symlinked_package_paths tests/test_package_routes.py::test_package_publish_preserves_db_referenced_final_directory tests/test_db_migrations.py::test_schema_enforces_core_uniqueness_and_foreign_keys tests/test_package_migration.py::test_storage_repair_moves_legacy_packs_to_packages_and_rewrites_storage_paths
Result: 5 passed

uv run ruff format --check tests/test_cli_package_commands.py tests/test_package_routes.py tests/test_db_migrations.py tests/test_package_migration.py && uv run ruff check tests/test_cli_package_commands.py tests/test_package_routes.py tests/test_db_migrations.py tests/test_package_migration.py
Result: 4 files already formatted; All checks passed!

uv run pytest tests/test_cli_package_commands.py tests/test_package_routes.py tests/test_db_migrations.py tests/test_package_migration.py
Result: 67 passed
```

### Remaining Warnings

None from this cleanup. Legacy `pack`/`packv` fixture names remain only where tests explicitly exercise deployed legacy schema/storage or public legacy rejection behavior.

## Final Review Warning Cleanup — Auth Intent, Legacy Marker Auditability, Migration Readability

### Root Cause Summary

- Risk review warning: package listing, resolving, and artifact download endpoints required authentication but did not document that they are intentionally a global authenticated package registry rather than project-membership-scoped reads.
- Readability warning: legacy managed-block marker parsing hid the old metadata key through string joining, making the migration-only exception harder to audit.
- Readability warning: package migration conflict detection represented target keys as implicit tuples and branched on tuple length, obscuring which conflict shape was being checked.

### Remediation Evidence

| Warning | Action | Evidence |
|---------|--------|----------|
| Global authenticated package registry intent | Added explicit SDD spec language and a route comment documenting that authenticated users may list/resolve/download packages globally; project membership still gates assignments and pull-manifest access. Added a regression showing an authenticated member with no project membership can list and download a package. | `tests/test_package_routes.py::test_authenticated_member_without_project_membership_can_list_and_download_packages` passes. |
| Hidden legacy marker key | Replaced the string-joined key with explicit `LEGACY_MARKER_PACKAGE_KEY = "pack"`, documented it as legacy marker normalization, and narrowed static grep enforcement to that audited exception only. | `tests/test_package_nomenclature.py::test_legacy_marker_key_exception_is_explicit_and_not_hidden` and public-surface grep enforcement pass. |
| Implicit migration conflict tuple shapes | Introduced `PackageConflictKey` and `PackageTableMigrationPlan` typed structures; conflict checks now build WHERE clauses from explicit key objects instead of `len(key)` branching. | `tests/test_package_nomenclature.py::test_package_migration_conflict_checks_use_typed_key_structures` and migration collision preservation test pass. |

### TDD Cycle Evidence — Final Review Warning Cleanup

| Task | Test File | Layer | Safety Net | RED | GREEN | TRIANGULATE | REFACTOR |
|------|-----------|-------|------------|-----|-------|-------------|----------|
| Document global authenticated registry intent | `tests/test_package_routes.py`, `tests/test_package_nomenclature.py` | API/static docs | ✅ Changed-file baseline: `51 passed` before edits | ✅ Static documentation test failed until spec and route comment named the intent; behavior approval test passed and locked existing behavior | ✅ Focused tests passed: `6 passed`; changed-file suite: `62 passed` | ✅ Auth-required behavior remains covered by existing 401 tests; new member/no-membership path covers global authenticated reads | ✅ No authorization model change |
| Make legacy marker exception auditable | `tests/test_package_nomenclature.py`, `tests/test_pull_markers.py` | Static/unit | ✅ Existing marker tests included legacy normalization before edits | ✅ Static test failed while the key was hidden via string join | ✅ Focused tests passed: `6 passed`; changed-file suite: `62 passed` | ✅ Existing legacy marker parse/normalization test plus public grep enforcement cover allowed and forbidden surfaces | ✅ Exception isolated to `LEGACY_MARKER_PACKAGE_KEY = "pack"` |
| Clarify package migration conflict checks | `tests/test_package_nomenclature.py`, `tests/test_package_migration.py` | Static/migration | ✅ Existing migration conflict test preserved behavior before refactor | ✅ Static test failed while conflict checks used implicit tuple shapes and `len(key)` branching | ✅ Focused tests passed: `6 passed`; changed-file suite: `62 passed` | ✅ Existing collision test verifies fail-closed preservation; typed key test verifies readability guard | ✅ Added `PackageConflictKey` and `PackageTableMigrationPlan` |

### Verification Commands

```text
uv run pytest tests/test_package_routes.py tests/test_pull_markers.py tests/test_package_migration.py
Baseline before edits: 51 passed

uv run pytest tests/test_package_routes.py::test_authenticated_member_without_project_membership_can_list_and_download_packages tests/test_package_nomenclature.py::test_global_authenticated_package_registry_access_is_explicitly_documented tests/test_package_nomenclature.py::test_legacy_marker_key_exception_is_explicit_and_not_hidden tests/test_package_nomenclature.py::test_package_migration_conflict_checks_use_typed_key_structures
RED before fix: 3 failed, 1 passed

uv run pytest tests/test_package_routes.py::test_authenticated_member_without_project_membership_can_list_and_download_packages tests/test_package_nomenclature.py::test_global_authenticated_package_registry_access_is_explicitly_documented tests/test_package_nomenclature.py::test_legacy_marker_key_exception_is_explicit_and_not_hidden tests/test_package_nomenclature.py::test_package_migration_conflict_checks_use_typed_key_structures tests/test_package_migration.py::test_package_table_id_collision_fails_closed_and_preserves_legacy_data tests/test_pull_markers.py::test_plan_managed_update_normalizes_legacy_pack_marker_metadata
GREEN after fix: 6 passed

uv run pytest tests/test_package_nomenclature.py tests/test_package_routes.py tests/test_pull_markers.py tests/test_package_migration.py
Result: 62 passed

uv run ruff check agh/cli/pull_markers.py agh/server/db.py agh/server/routes/packages.py tests/test_package_nomenclature.py tests/test_package_routes.py && uv run ruff format --check agh/cli/pull_markers.py agh/server/db.py agh/server/routes/packages.py tests/test_package_nomenclature.py tests/test_package_routes.py
Result: All checks passed; 5 files already formatted
```

### Remaining Warnings

None from this cleanup. Product behavior is unchanged: global package registry reads require authentication only; project-scoped authorization remains on project package and pull-manifest endpoints.


## No-argument Project Selector Amendment

### Root Cause Summary

- The approved package selector only handled `agh project package add <project>`; Typer still required the project positional argument, so `agh project package add` failed with generic usage output before AGH could provide the requested interactive project selection.
- Non-TTY safety needed to happen before `GET /projects` so CI/non-interactive invocations fail locally with exit 2 and make no API calls.

### Remediation Evidence

| Requirement | Action | Evidence |
|-------------|--------|----------|
| No-arg interactive project + package selection | Made the project argument optional, added a visible-project selector backed by `GET /projects`, and then reused the existing available-package selector/confirmation flow for the selected project. | `tests/test_cli_package_commands.py::test_cli_project_package_add_without_args_selects_project_then_package` failed RED with Typer usage exit 2, then passed after implementation. |
| Non-TTY no-arg safety | Reused the omitted-ref TTY guard before project listing, preserving the no-API-call local failure contract. | `tests/test_cli_package_commands.py::test_cli_project_package_add_without_args_non_tty_exits_2_without_api` failed RED on generic usage output, then passed with exit 2 and zero calls. |
| Empty project list | Chose the existing project-list empty UX: print `No projects found.` and exit successfully without prompting for package selection. | `tests/test_cli_package_commands.py::test_cli_project_package_add_without_args_reports_no_visible_projects` passed after implementation. |
| Invalid project selection | Treats out-of-range project selection as usage exit 2, matching package selector behavior. | `tests/test_cli_package_commands.py::test_cli_project_package_add_without_args_invalid_project_selection_exits_2` passed after implementation. |
| Single positional remains project | Kept one positional bound as `project_id`; even package-looking values resolve through project-name lookup and do not call package-version resolution. | `tests/test_cli_package_commands.py::test_cli_project_package_add_one_positional_is_project_even_if_package_like` passed. |

### TDD Cycle Evidence — No-argument Project Selector Amendment

| Task | Test File | Layer | Safety Net | RED | GREEN | TRIANGULATE | REFACTOR |
|------|-----------|-------|------------|-----|-------|-------------|----------|
| No-arg project then package selector | `tests/test_cli_package_commands.py` | CLI | ✅ Existing related CLI baseline: `8 passed` | ✅ New no-arg tests failed with Typer usage exit 2/generic output before implementation | ✅ Focused selector tests passed: `10 passed` | ✅ Happy path, non-TTY no API, empty projects, invalid selection, and one-positional-as-project cases | ✅ Extracted `_select_visible_project_id()` and reused existing package selector/cancel behavior |

### Verification Commands

```text
uv run pytest tests/test_cli_package_commands.py -k 'without_ref or project_package_commands_resolve or read_commands'
Baseline before edits: 8 passed, 19 deselected

uv run pytest tests/test_cli_package_commands.py -k 'without_args or one_positional_is_project'
RED before implementation: 4 failed, 1 passed, 27 deselected

uv run pytest tests/test_cli_package_commands.py -k 'without_args or one_positional_is_project or without_ref'
GREEN after implementation: 10 passed, 22 deselected

uv run pytest tests/test_cli_package_commands.py
Result: 32 passed

uv run pytest
Result: 331 passed, 1 skipped

uv run ruff check
Result: All checks passed!

uv run ruff format --check
Result: 55 files already formatted

git diff --check
Result: passed
```

### Remaining Risks

- No new API was added; the no-arg flow depends on existing `GET /projects` visibility semantics and the existing project-scoped available-package endpoint.
- Cancellation semantics are inherited from the existing package confirmation prompt (`Cancelled.` exit 130).

## No-argument Selector Review Warning Cleanup

### Root Cause Summary

- Invalid project/package selections still used `typer.prompt(..., type=int)`, which converted bad or exhausted input into Typer's prompt loop/abort path and exited `1` instead of AGH's usage error `2`.
- The package selector already rejected out-of-range choices but lacked a regression proving invalid input after `/packages:available` does not POST an assignment.
- A few active runtime identifiers still used legacy-looking `pack` names outside migration/legacy-normalization contexts.

### Remediation Evidence

| Warning | Action | Evidence |
|---------|--------|----------|
| Invalid package selection after available choices | Added deterministic package-selector tests for non-integer and exhausted input; selector now exits `2` before POSTing. | `tests/test_cli_package_commands.py::test_cli_project_package_add_without_ref_invalid_package_selection_exits_2` and `::test_cli_project_package_add_without_ref_exhausted_package_input_exits_2` failed RED with exit `1`, then passed. |
| Invalid project selection input | Added a no-arg project-selector non-integer regression; selector now exits `2` with a clear message. | `tests/test_cli_package_commands.py::test_cli_project_package_add_without_args_invalid_project_input_exits_2` failed RED with exit `1`, then passed. |
| Active runtime `pack` helper/local names | Renamed `_pull_manifest_pack` to `_pull_manifest_package` and `staged_by_pack` to `staged_by_package`; added a static guard for exact legacy helper/local names. | `tests/test_package_nomenclature.py::test_active_runtime_helpers_use_package_terminology` failed RED, then passed after renames. |

### TDD Cycle Evidence — Review Warning Cleanup

| Task | Test File | Layer | Safety Net | RED | GREEN | TRIANGULATE | REFACTOR |
|------|-----------|-------|------------|-----|-------|-------------|----------|
| Deterministic package selector failures | `tests/test_cli_package_commands.py` | CLI | ✅ Related selector baseline: `11 passed`; full pull-manifest/workspace baseline: `66 passed` | ✅ New invalid/exhausted package input tests failed with exit `1` before implementation | ✅ Focused selector tests passed: `12 passed` | ✅ Non-integer input, exhausted input, existing out-of-range, confirm, cancel, and happy paths | ✅ Extracted `_prompt_selection_index()` single-read parser |
| Deterministic project selector failures | `tests/test_cli_package_commands.py` | CLI | ✅ Existing no-arg selector tests passed before edits | ✅ New non-integer project input test failed with exit `1` before implementation | ✅ Focused no-arg selector tests passed | ✅ Non-integer, out-of-range, empty list, non-TTY, and happy path cases | ✅ Project/package selectors share parser |
| Runtime package naming cleanup | `tests/test_package_nomenclature.py`, `tests/test_pull_manifest_routes.py`, `tests/test_workspace_pull.py` | Static/unit/integration | ✅ `tests/test_pull_manifest_routes.py tests/test_workspace_pull.py`: `66 passed` before edits | ✅ Static naming test failed on `_pull_manifest_pack` and `staged_by_pack` | ✅ Naming guard plus pull-manifest/workspace tests passed: `67 passed` | ✅ Static exact-name guard plus behavior suites for affected runtime paths | ✅ Renamed active helper/local names only; legacy migration contexts unchanged |

### Verification Commands

```text
uv run pytest tests/test_cli_package_commands.py -k 'without_args or without_ref or one_positional_is_project or project_package_commands_resolve' tests/test_project_package_assignments.py tests/test_workspace_pull.py tests/test_pull_manifest_routes.py
Baseline before edits: 11 passed, 92 deselected

uv run pytest tests/test_pull_manifest_routes.py tests/test_workspace_pull.py -q
Baseline before edits: 66 passed

uv run pytest tests/test_cli_package_commands.py -k 'invalid_package_selection or exhausted_package_input or invalid_project_input' tests/test_package_nomenclature.py::test_active_runtime_helpers_use_package_terminology -q
RED before fix: 3 failed for selector exit `1`; static naming guard failed separately on `_pull_manifest_pack` and `staged_by_pack`

uv run pytest tests/test_cli_package_commands.py -k 'invalid_package_selection or exhausted_package_input or invalid_project_input or without_ref or without_args' tests/test_package_nomenclature.py::test_active_runtime_helpers_use_package_terminology -q
GREEN after fix: 12 passed, 24 deselected

uv run pytest tests/test_cli_package_commands.py tests/test_package_nomenclature.py tests/test_pull_manifest_routes.py tests/test_workspace_pull.py -q
Result: 108 passed

uv run pytest
Result: 335 passed, 1 skipped

uv run ruff check
Result: All checks passed!

uv run ruff format --check
Result: 55 files already formatted

git diff --check
Result: passed
```

### Remaining Risks

- Confirmation still uses Typer confirmation semantics so existing `n` cancellation remains `Cancelled.` with exit `130`; this cleanup intentionally changed only project/package numeric selection failure handling.
- Legacy `pack` names remain intentionally scoped to migration, legacy marker normalization, and explicit legacy rejection tests.

## Final Resilience Blocker and Reliability Warning Remediation

### Root Cause Summary

- Crash/retry storage blocker: `_preflight_package_storage()` treated any existing `/data/packages/<child>` as a hard conflict. After a crash or restart between a filesystem move and DB migration completion, `/data/packages/<child>` could already contain the moved artifact while `/data/packs/<child>` was gone or only left empty directory residue, making retries fail permanently even though the target was the preserved data.
- True-conflict safety requirement: retry reconciliation still needed to fail closed when source and target both contain data, rather than deleting or overwriting either side.
- Reliability warning: no-argument project selection already handled EOF through the shared selector parser, but there was no direct regression proving visible projects plus exhausted input exits `2` without package selection or POST calls.

### Remediation Evidence

| Finding | Action | Evidence |
|---------|--------|----------|
| Crash-interrupted partial storage move retry failed on existing target | Reconciled existing target children only when the legacy source child is an empty directory tree residue; migration then removes `/data/packs`, keeps the moved target artifact, moves any remaining legacy children, and rewrites DB storage paths. | Added `tests/test_package_migration.py::test_storage_repair_reconciles_crash_interrupted_partial_move_on_retry`; RED failed in `_preflight_package_storage()`, GREEN passes. |
| True source/target content conflict must fail closed | Kept non-empty source plus existing target as a hard error and added symlink checks for source/target children. | Added `tests/test_package_migration.py::test_storage_repair_fails_closed_on_different_source_and_target_content`; preserves both sides and leaves migration unrecorded. |
| No-argument project selector EOF needed direct coverage | Added a no-arg selector regression where `/projects` returns visible projects but stdin is exhausted. | Added `tests/test_cli_package_commands.py::test_cli_project_package_add_without_args_exhausted_project_input_exits_2`; exits `2`, performs only `GET /projects`, and makes no package/POST calls. |

### TDD Cycle Evidence — Final Remediation

| Task | Test File | Layer | Safety Net | RED | GREEN | TRIANGULATE | REFACTOR |
|------|-----------|-------|------------|-----|-------|-------------|----------|
| Crash/retry-safe package storage migration | `tests/test_package_migration.py` | Migration/filesystem | ✅ Baseline focused migration/selector suite: `11 passed` | ✅ New interrupted partial move retry test failed on `package storage target already exists` | ✅ New focused tests passed: `3 passed`; full changed-file tests passed: `44 passed` | ✅ Retry reconciliation plus true source/target conflict preservation | ✅ Extracted empty-residue reconciliation helpers and deterministic preflight ordering |
| EOF no-arg project selector coverage | `tests/test_cli_package_commands.py` | CLI | ✅ Baseline no-arg selector suite: included in `11 passed` | ➖ Coverage-only warning; shared selector already had the correct EOF behavior | ✅ New focused CLI test passed and full changed-file tests passed | ✅ Exhausted input complements non-integer, out-of-range, empty-list, non-TTY, and happy-path project selector tests | ➖ No production change needed |

### Verification Commands

```text
uv run pytest tests/test_package_migration.py tests/test_cli_package_commands.py -k 'without_args or migration or storage_repair'
Baseline before edits: 11 passed, 30 deselected

uv run pytest tests/test_package_migration.py::test_storage_repair_reconciles_crash_interrupted_partial_move_on_retry tests/test_package_migration.py::test_storage_repair_fails_closed_on_different_source_and_target_content tests/test_cli_package_commands.py::test_cli_project_package_add_without_args_exhausted_project_input_exits_2 -q
RED before fix: 1 failed, 2 passed; partial move retry failed in `_preflight_package_storage()`
GREEN after fix: 3 passed

uv run pytest tests/test_package_migration.py tests/test_cli_package_commands.py -q
Result: 44 passed

uv run pytest
Result: 338 passed, 1 skipped

uv run ruff check
Result: All checks passed!

uv run ruff format --check
Result: 55 files already formatted

git diff --check
Result: passed
```

### Remaining Risks

- Reconciliation is intentionally narrow: only empty legacy source directory residue is removed when the package target already exists. Non-empty source plus existing target remains fail-closed to preserve data for operator inspection.
- Filesystem rollback/reconciliation remains best-effort at the OS boundary; unsafe roots/children and symlinked targets are rejected rather than followed.

## Final Minor Review Warning Cleanup

### Root Cause Summary

- `tests/test_package_nomenclature.py` had static tests that asserted internal implementation details such as migration dataclass names, private helper/local names, and exact source substrings. Those checks could fail safe refactors even though behavior-focused tests already cover migration safety, marker normalization, routes, CLI, and workspace behavior.
- `agh/server/db.py` rewrote legacy package IDs and storage paths with hard-coded slice offsets (`5`, `6`, `6`) and SQL substring offset (`7`), making the migration code harder to audit.

### Remediation Evidence

| Warning | Action | Evidence |
|---------|--------|----------|
| Implementation-centric nomenclature tests | Removed private-name/source-shape assertions. Kept behavior-oriented checks and softened the public legacy-term sweep so audited legacy exceptions are recognized by context instead of exact constant names. | `tests/test_package_nomenclature.py` still verifies public package terminology, canonical commands/routes, manifest naming, spec wording, and forbidden public legacy terms. |
| Magic slice lengths in DB migration rewrite helpers | Added named legacy/canonical prefix constants and rewrote ID/storage transformations with `removeprefix`; parameterized the SQL storage-path rewrite with named constants, including the SQLite suffix start offset. | Migration behavior remains covered by package migration and DB migration tests. |

### TDD Cycle Evidence — Final Minor Cleanup

| Task | Test File | Layer | Safety Net | RED | GREEN | TRIANGULATE | REFACTOR |
|------|-----------|-------|------------|-----|-------|-------------|----------|
| Remove brittle implementation-centric static assertions | `tests/test_package_nomenclature.py` | Static/public contract | ✅ Baseline focused suite: `29 passed` before edits | ➖ Test cleanup; removed brittle assertions rather than adding behavior | ✅ Focused suite after cleanup: `26 passed` | ➖ Behavioral coverage preserved by existing migration/API/CLI/workspace tests | ✅ Public legacy-term sweep now allows audited exceptions by context, not private constant names |
| Replace magic migration rewrite slices | `tests/test_package_migration.py`, `tests/test_db_migrations.py` | Migration/refactor | ✅ Baseline focused suite: `29 passed` before edits | ➖ Refactor under approval tests; behavior should not change | ✅ Focused migration/nomenclature/DB suite: `26 passed`; full suite passed | ✅ Existing ID rewrite, storage path rewrite, retry, and conflict tests cover alternate paths | ✅ Introduced named prefix/storage constants and shared prefix rewrite helper |

### Verification Commands

```text
uv run pytest tests/test_package_nomenclature.py tests/test_package_migration.py tests/test_db_migrations.py -q
Baseline before edits: 29 passed
Result after edits: 26 passed

uv run ruff check agh/server/db.py tests/test_package_nomenclature.py && uv run ruff format --check agh/server/db.py tests/test_package_nomenclature.py
Result: All checks passed; 2 files already formatted

uv run pytest
Result: 350 passed, 1 skipped

uv run ruff check && uv run ruff format --check && git diff --check
Result: All checks passed; 55 files already formatted; git diff check passed
```

### Remaining Risks

- Static public terminology enforcement remains intentionally limited to public surface files plus audited legacy migration/cache/marker contexts; behavior tests remain the primary migration-safety gate.

## Ultimate Review Blocker and Warning Remediation

### Root Cause Summary

- Crash/retry reconciliation only removed empty legacy source residue when `/data/packages/<child>` already existed. That left two unsafe retry states unresolved: an empty target blocking a still-populated legacy source move, and identical non-empty source/target content after a completed copy but failed source cleanup.
- The previous rollback helper could delete a non-empty partial target while the legacy source still existed, even when the target had not been proven equivalent to the source.
- `PackageTableMigrationPlan` still carried package, package-version, and project-package rows as plain tuples, so validation depended on positional indexes like `row[0]`, `row[1]`, and `row[2]`.

### Remediation Evidence

| Finding | Action | Evidence |
|---------|--------|----------|
| Empty target with populated legacy source wedged retry | Reconciliation now removes only an empty target and then retries the source move. | Added `tests/test_package_migration.py::test_storage_repair_removes_empty_target_and_retries_legacy_source_move`; RED failed on `package storage target already exists`, GREEN passes. |
| Identical non-empty source/target residue wedged retry | Reconciliation now compares safe filesystem signatures and removes the legacy source only when source and target are identical. | Added `tests/test_package_migration.py::test_storage_repair_removes_identical_non_empty_legacy_source_residue`; RED failed on existing target, GREEN passes. |
| Different source/target content must preserve both | Existing fail-closed conflict test remains green; rollback now also preserves a non-empty partial target unless it is empty or proven equivalent. | Updated `tests/test_package_migration.py::test_storage_repair_preserves_different_partial_target_when_move_fails`; different content is preserved with the legacy source. |
| Tuple-shaped migration plan hurt maintainability | Added named dataclasses for package, package-version, and project-package migration rows with explicit key/value accessors; validation no longer indexes row tuples. | Strengthened `tests/test_package_nomenclature.py::test_package_migration_conflict_checks_use_typed_key_structures` to reject tuple row storage and `row[0]`/`row[1]`/`row[2]`. |

### Reconciliation Design

- If target exists and source is empty legacy residue: remove the empty source and continue.
- If target exists empty and source contains data: remove the empty target, then move the source to the canonical package location.
- If target and source both exist with identical non-empty content: remove the legacy source residue and continue; the canonical target is retained.
- If target and source both exist with different content: raise a migration conflict, preserve both paths, leave the migration unrecorded, and require operator inspection.
- Symlinked source/target paths are rejected; comparison walks only regular files/directories and refuses symlink traversal.

### TDD Cycle Evidence — Ultimate Remediation

| Task | Test File | Layer | Safety Net | RED | GREEN | TRIANGULATE | REFACTOR |
|------|-----------|-------|------------|-----|-------|-------------|----------|
| Crash/retry reconciliation cases | `tests/test_package_migration.py` | Migration/filesystem | ✅ Existing focused migration/readability baseline: `9 passed` | ✅ New empty-target and identical-content tests failed; different-content preservation stayed green | ✅ Focused reconciliation tests passed: `5 passed`; migration file passed: `10 passed` | ✅ Empty target, identical non-empty content, different content, and partial-target rollback paths | ✅ Extracted safe signature comparison and retry-safe residue helpers |
| Named migration row records | `tests/test_package_nomenclature.py`, `agh/server/db.py` | Static/readability | ✅ Existing typed-key guard passed before edits | ✅ Strengthened guard failed while rows were `list[tuple]` and validation used positional indexes | ✅ Guard passed after dataclasses and explicit accessors | ✅ Static guard plus full migration tests cover maintainability and behavior | ✅ Added `PackageMigrationPackageRow`, `PackageMigrationVersionRow`, and `ProjectPackageMigrationRow` |

### Verification Commands

```text
uv run pytest tests/test_package_migration.py tests/test_package_nomenclature.py::test_package_migration_conflict_checks_use_typed_key_structures
Baseline before edits: 9 passed

uv run pytest tests/test_package_migration.py::test_storage_repair_removes_empty_target_and_retries_legacy_source_move tests/test_package_migration.py::test_storage_repair_removes_identical_non_empty_legacy_source_residue tests/test_package_migration.py::test_storage_repair_fails_closed_on_different_source_and_target_content tests/test_package_nomenclature.py::test_package_migration_conflict_checks_use_typed_key_structures
RED before fix: 3 failed, 1 passed

uv run pytest tests/test_package_migration.py::test_storage_repair_removes_empty_target_and_retries_legacy_source_move tests/test_package_migration.py::test_storage_repair_removes_identical_non_empty_legacy_source_residue tests/test_package_migration.py::test_storage_repair_fails_closed_on_different_source_and_target_content tests/test_package_migration.py::test_storage_repair_preserves_different_partial_target_when_move_fails tests/test_package_nomenclature.py::test_package_migration_conflict_checks_use_typed_key_structures
GREEN after fix: 5 passed

uv run ruff format agh/server/db.py tests/test_package_migration.py tests/test_package_nomenclature.py && uv run ruff check agh/server/db.py tests/test_package_migration.py tests/test_package_nomenclature.py
Result: 1 file reformatted, 2 files left unchanged; All checks passed!

uv run pytest tests/test_package_migration.py tests/test_package_nomenclature.py::test_package_migration_conflict_checks_use_typed_key_structures
Result: 11 passed

uv run pytest
Result: 344 passed, 1 skipped

uv run ruff check
Result: All checks passed!

uv run ruff format --check
Result: 55 files already formatted

git diff --check
Result: passed
```

### Remaining Risks

- Filesystem migration remains best-effort at the OS boundary; unsafe roots, symlinked children, and true source/target content conflicts fail closed rather than guessing.
- Non-empty target/source deletion is only allowed after explicit equivalence verification; otherwise both paths are preserved for operator inspection.

## Final Reliability Blocker and Readability Warning Remediation

### Root Cause Summary

- Workspace skill symlink ownership detection still looked at the old pre-release `.agh/packages` cache but did not recognize deployed legacy `.agh-cache/packs` skill symlinks. During package nomenclature upgrade, an existing AGH-owned skill link into `.agh-cache/packs/.../skills/<name>/SKILL.md` could be treated as a user-owned symlink conflict instead of being replaced with the canonical `.agh-cache/packages/...` link.
- Managed block parsing accepted mixed legacy/current marker pairs because `_END_RE` captured the marker key but parsing compared only the package value. That made legacy normalization harder to audit and allowed corrupt `AGH-BEGIN pack` / `AGH-END package` combinations.
- `agh/server/routes/projects.py` duplicated exact/latest package-version row lookup and empty handling between `_resolve_package_version()` and `_resolved_package_version_row()`.

### Remediation Evidence

| Finding | Action | Evidence |
|---------|--------|----------|
| Legacy `.agh-cache/packs` skill symlinks blocked pulls | Added focused workspace tests for planning and commit paths, then expanded AGH-owned legacy symlink detection to include `.agh-cache/packs` while preserving the existing `.agh/packages` pre-release path. | `tests/test_workspace_pull.py::test_plan_skill_placement_updates_legacy_pack_cache_symlink`, `::test_commit_pull_writes_replaces_legacy_pack_cache_skill_symlink`, and existing `tests/test_cli_pull.py::test_pull_replaces_old_pre_release_skill_cache_symlink` pass. |
| Marker key handling was implicit | Added a mixed-key regression and changed parser state to retain the begin marker key, reject mixed legacy/current marker pairs, and normalize valid legacy blocks back to canonical `package` output. | `tests/test_pull_markers.py::test_parse_managed_blocks_rejects_mixed_legacy_and_current_marker_keys` and existing legacy normalization tests pass. |
| Duplicate version lookup logic | Extracted `_package_version_row_or_404()` and `_raise_package_version_not_found()` so string resolution and manifest-row resolution share exact/latest lookup, 404 behavior, and SemVer max selection. | Project package assignment, available packages, pull-manifest, and package route suites pass. |

### TDD Cycle Evidence — Final Reliability Remediation

| Task | Test File | Layer | Safety Net | RED | GREEN | TRIANGULATE | REFACTOR |
|------|-----------|-------|------------|-----|-------|-------------|----------|
| Legacy `.agh-cache/packs` skill symlink migration | `tests/test_workspace_pull.py`, `tests/test_cli_pull.py` | Workspace/CLI integration | ✅ Baseline changed-file suite: `102 passed` before edits | ✅ New planning test failed with `conflict` for a legacy `.agh-cache/packs` symlink | ✅ Focused symlink tests passed; full suite passed | ✅ Covers legacy `.agh-cache/packs`, canonical replacement, and existing pre-release `.agh/packages` path | ✅ Detection uses explicit `LEGACY_PACK_CACHE_DIR` legacy exception |
| Explicit marker key handling | `tests/test_pull_markers.py` | Unit | ✅ Existing marker/workspace suite: `73 passed` after first green | ✅ Mixed legacy/current marker tests failed because parser ignored `end.group("key")` | ✅ Focused marker tests passed; full marker suite passed | ✅ Valid legacy normalization and invalid mixed key pairs both covered | ✅ Parser uses `_BeginMetadata` instead of loose dict state |
| Shared package-version lookup helper | `tests/test_project_package_assignments.py`, `tests/test_pull_manifest_routes.py`, `tests/test_package_routes.py` | API/refactor approval | ✅ Relevant API approval suite: `46 passed` before refactor | ➖ Approval-test refactor; no behavior change intended | ✅ Relevant API suite passed; full suite passed | ✅ Exact assignment, latest resolution, available latest refs, and pull-manifest latest paths covered | ✅ Duplicate latest/404/SemVer selection removed |

### Verification Commands

```text
uv run pytest tests/test_workspace_pull.py::test_plan_skill_placement_updates_legacy_pack_cache_symlink tests/test_workspace_pull.py::test_commit_pull_writes_replaces_legacy_pack_cache_skill_symlink tests/test_pull_markers.py::test_parse_managed_blocks_rejects_mixed_legacy_and_current_marker_keys -q
RED before fix: 3 failed, 1 passed; failures covered `.agh-cache/packs` symlink conflict and mixed marker acceptance.
GREEN after fix: 4 passed.

uv run pytest tests/test_workspace_pull.py tests/test_pull_markers.py -q
Result: 73 passed.

uv run pytest tests/test_project_package_assignments.py tests/test_pull_manifest_routes.py tests/test_package_routes.py -q
Result: 46 passed.

uv run pytest tests/test_cli_pull.py::test_pull_replaces_old_pre_release_skill_cache_symlink tests/test_package_nomenclature.py::test_public_surfaces_do_not_expose_legacy_pack_terms tests/test_workspace_pull.py::test_plan_skill_placement_updates_legacy_pack_cache_symlink -q
Result: 3 passed.

uv run pytest
Result: 348 passed, 1 skipped.

uv run ruff check
Result: All checks passed!

uv run ruff format --check
Result: 55 files already formatted.

git diff --check
Result: passed.
```

### Remaining Risks

- Legacy handling remains intentionally narrow: `.agh-cache/packs` and pre-release `.agh/packages` are recognized only as AGH-owned skill symlink sources during migration to canonical `.agh-cache/packages` links.
- Mixed marker pairs now fail closed; valid legacy managed blocks still normalize to canonical `package` markers on update.

## Final Reliability Blocker and README Warning Remediation — Legacy `.agh/packs` Symlinks

### Root Cause Summary

- Workspace skill symlink migration recognized canonical `.agh-cache/packages`, pre-release `.agh/packages`, and deployed legacy `.agh-cache/packs` roots, but missed older pre-cache `.agh/packs` roots. An existing AGH-owned skill symlink into `.agh/packs/.../skills/<name>/SKILL.md` could therefore be classified as a user-owned symlink conflict instead of being replaced by the canonical `.agh-cache/packages` symlink during pull.
- README lockfile snippets showed `mode = "symlink"` beside `[[packages]]`, but the actual lock writer emits `mode` under each `[[artifacts]]` entry.

### Remediation Evidence

| Finding | Action | Evidence |
|---------|--------|----------|
| Legacy `.agh/packs` skill symlinks blocked pull migration | Added direct planning and commit tests for skill symlinks pointing into `.agh/packs`, then included that root in migration-only AGH-owned legacy cache detection. The comment documents that these paths are only accepted for replacement with canonical `.agh-cache/packages` links. | `tests/test_workspace_pull.py::test_plan_skill_placement_updates_legacy_agh_pack_symlink` and `::test_commit_pull_writes_replaces_legacy_agh_pack_skill_symlink` pass. |
| README lockfile shape was misleading | Added docs guidance coverage proving `mode` appears under `[[artifacts]]`, then corrected both English and Spanish snippets to match `_lockfile_toml()`. | `tests/test_docs_guidance.py::test_readme_lockfile_snippets_put_mode_under_artifacts` passes. |

### TDD Cycle Evidence — Final Blocker Cleanup

| Task | Test File | Layer | Safety Net | RED | GREEN | TRIANGULATE | REFACTOR |
|------|-----------|-------|------------|-----|-------|-------------|----------|
| Legacy `.agh/packs` skill symlink migration | `tests/test_workspace_pull.py` | Workspace/unit | ✅ Existing relevant baseline: `14 passed` (`workspace_pull` legacy symlink tests + docs guidance) | ✅ New planning test failed with `conflict` for `.agh/packs` symlink before production change | ✅ New focused symlink tests passed; focused workspace/docs suite passed: `71 passed` | ✅ Planning path plus commit replacement path; existing `.agh-cache/packs` and `.agh/packages` tests stayed green | ✅ Legacy root handling is documented as migration-only and no writes target legacy paths |
| README lockfile snippet shape | `tests/test_docs_guidance.py` | Docs/static | ✅ Existing docs guidance baseline included in `14 passed` | ✅ New docs test failed because `[[artifacts]]` was absent and `mode` was top-level beside `[[packages]]` | ✅ Focused docs test passed; full docs suite included in `71 passed` | ✅ English and Spanish README snippets are both checked | ✅ Snippets now mirror actual `[[packages]]` + `[[artifacts]]` writer shape |

### Verification Commands

```text
uv run pytest tests/test_workspace_pull.py::test_plan_skill_placement_updates_legacy_pack_cache_symlink tests/test_workspace_pull.py::test_commit_pull_writes_replaces_legacy_pack_cache_skill_symlink tests/test_docs_guidance.py -q
Baseline before edits: 14 passed

uv run pytest tests/test_workspace_pull.py::test_plan_skill_placement_updates_legacy_agh_pack_symlink tests/test_workspace_pull.py::test_commit_pull_writes_replaces_legacy_agh_pack_skill_symlink tests/test_docs_guidance.py::test_readme_lockfile_snippets_put_mode_under_artifacts -q
RED before fix: 2 failed, 1 passed; planning failed as `conflict`, README shape lacked `[[artifacts]]`.
GREEN after fix: 3 passed.

uv run pytest tests/test_workspace_pull.py tests/test_cli_pull.py::test_pull_replaces_old_pre_release_skill_cache_symlink tests/test_docs_guidance.py -q
Result: 71 passed.

uv run pytest
Result: 351 passed, 1 skipped.

uv run ruff check
Result: All checks passed!

uv run ruff format --check
Result: 55 files already formatted.

git diff --check
Result: passed.
```

### Remaining Risks

- Legacy handling remains narrow and migration-only: `.agh/packs`, `.agh/packages`, and `.agh-cache/packs` are recognized only as AGH-owned existing skill symlink sources so pull can replace them with canonical `.agh-cache/packages` links.

## Critical Reliability Blocker Remediation — DB Validation Before Storage Mutation

### Root Cause Summary

- `_apply_package_rename_migration()` ran package storage preflight before package table migration validation.
- The storage preflight reused reconciliation logic, so retry-safe cleanup could delete legacy `/packs/...` residue before DB conflict validation discovered a target package-table collision.
- If DB validation then failed, SQLite rolled back but the already-mutated filesystem could leave legacy DB rows pointing at removed legacy storage.
- `tests/test_workspace_pull.py` duplicated legacy skill symlink setup for `.agh-cache/packs` and `.agh/packs`, making the migration-only cases noisier to review.

### Remediation Evidence

| Finding | Action | Evidence |
|---------|--------|----------|
| Filesystem mutation happened before DB conflict validation | Built and validated the package table migration plan before storage preflight. `_migrate_package_tables()` now consumes the prevalidated plan instead of validating after storage checks. | New collision tests keep legacy `/packs/acme` intact when DB target rows collide. |
| Storage preflight was mutating | Split preflight into non-mutating `_validate_package_storage_preflight()` plus `_validate_existing_package_storage_target()`. Mutating reconciliation remains inside `_move_legacy_package_storage()` on the successful/no-conflict path. | Existing crash/retry reconciliation tests still pass, including empty target, identical residue, and different-content fail-closed cases. |
| Legacy symlink tests duplicated setup | Added `_create_legacy_skill_symlink()` and parametrized `.agh-cache/packs` plus `.agh/packs` planning/commit tests. | `tests/test_workspace_pull.py` passes with the same coverage and less duplicated fixture setup. |

### TDD Cycle Evidence — Critical Reliability Blocker

| Task | Test File | Layer | Safety Net | RED | GREEN | TRIANGULATE | REFACTOR |
|------|-----------|-------|------------|-----|-------|-------------|----------|
| DB conflict before storage mutation | `tests/test_package_migration.py` | Migration/filesystem | ✅ Baseline migration/workspace suite: `67 passed` | ✅ New identical source/target + DB collision test failed because `/packs/acme` was deleted before DB validation aborted | ✅ Focused collision tests passed: `2 passed`; full migration file passed: `12 passed` | ✅ Added empty-target retry-state collision case; existing success/no-conflict reconciliation cases stayed green | ✅ Split non-mutating validation from mutating reconciliation and reused prevalidated DB migration plan |
| Deduplicate legacy symlink setup | `tests/test_workspace_pull.py` | Test readability/refactor | ✅ Baseline workspace suite included in `67 passed` | ➖ Refactor-only cleanup; behavior already covered | ✅ Workspace suite passed: `57 passed` | ✅ Parametrized `.agh-cache/packs` and `.agh/packs` roots for both plan and commit paths | ✅ Extracted `_create_legacy_skill_symlink()` helper |

### Verification Commands

```text
uv run pytest tests/test_package_migration.py tests/test_workspace_pull.py -q
Baseline before edits: 67 passed

uv run pytest tests/test_package_migration.py::test_package_table_collision_preserves_identical_legacy_storage_residue -q
RED before fix: 1 failed; legacy `/packs/acme` residue was removed before DB conflict abort.
GREEN after fix: 1 passed.

uv run pytest tests/test_package_migration.py::test_package_table_collision_preserves_identical_legacy_storage_residue tests/test_package_migration.py::test_package_table_collision_preserves_empty_target_retry_state -q
Result: 2 passed.

uv run pytest tests/test_package_migration.py -q
Result: 12 passed.

uv run pytest tests/test_workspace_pull.py -q
Result: 57 passed.

uv run pytest tests/test_package_migration.py tests/test_workspace_pull.py -q
Result: 69 passed.

uv run ruff format agh/server/db.py tests/test_package_migration.py tests/test_workspace_pull.py
Result: 1 file reformatted, 2 files left unchanged.

uv run ruff check agh/server/db.py tests/test_package_migration.py tests/test_workspace_pull.py
Result: All checks passed!

uv run pytest
Result: 353 passed, 1 skipped.

uv run ruff check
Result: All checks passed!

uv run ruff format --check
Result: 55 files already formatted.

git diff --check
Result: passed.
```

### Remaining Risks

- Filesystem reconciliation remains intentionally narrow and only mutates after DB conflicts have been validated. Unsafe symlinks and true source/target content conflicts still fail closed.
- Legacy `pack` storage names remain only in migration/retry scenarios and explicit legacy rejection coverage.

## Strict TDD Verification Failure Remediation — No-op Migration Tests

### Root Cause Summary

- Two DB-collision regression tests in `tests/test_package_migration.py` only built fixtures and closed the database connection.
- The intended behavior checks had drifted into `test_package_table_collision_preserves_empty_target_retry_state`, leaving `test_package_table_id_collision_fails_closed_and_preserves_legacy_data` and `test_package_table_collision_preserves_identical_legacy_storage_residue` with no assertions, no `run_migrations()`, and no `pytest.raises()`.
- This weakened the Strict TDD evidence for the DB collision + legacy storage preservation safety behavior.

### Remediation Evidence

| Finding | Action | Evidence |
|---------|--------|----------|
| DB id collision test was no-op | Added the missing `run_migrations()` failure assertion and verified the migration fails closed: legacy tables remain, legacy `pack_*` row remains, the pre-existing conflicting `pkg_*` row remains, and migration `003_rename_packs_to_packages` is not recorded. | `uv run pytest tests/test_package_migration.py -q` passes with 12 real migration tests. |
| Identical storage residue collision test was no-op | Added source/target identical legacy storage fixtures, asserted DB conflict aborts migration, and proved both legacy and canonical storage residues remain untouched. | Focused package migration suite passes; static no-op scan reports no empty tests. |
| Empty-target retry-state test carried unrelated checks | Removed duplicated DB-collision and identical-residue assertions from the empty-target test so each regression has one focused behavior. | `uv run pytest` passes with `353 passed, 1 skipped`. |

### TDD Cycle Evidence — No-op Test Remediation

| Task | Test File | Layer | Safety Net | RED | GREEN | TRIANGULATE | REFACTOR |
|------|-----------|-------|------------|-----|-------|-------------|----------|
| Convert no-op DB collision tests into behavior tests | `tests/test_package_migration.py` | Migration/test quality | ✅ Existing verification failure identified two no-op tests around lines 530 and 548 | ✅ Static inspection found tests with no assertion, no `run_migrations()`, and no `pytest.raises()` | ✅ Focused package migration tests pass: `12 passed`; full suite passes: `353 passed, 1 skipped` | ✅ Separate coverage now proves bare DB collision preservation, identical storage residue preservation, and empty target retry-state preservation | ✅ Split accidental merged assertions into focused tests; no production code changed |

### Verification Commands

```text
uv run pytest tests/test_package_migration.py -q
Result: 12 passed

python - <<'PY'
import ast
from pathlib import Path
path = Path('tests/test_package_migration.py')
mod = ast.parse(path.read_text())
for node in mod.body:
    if isinstance(node, ast.FunctionDef) and node.name.startswith('test_'):
        has_assert = any(isinstance(n, ast.Assert) for n in ast.walk(node))
        has_raises = any(
            isinstance(n, ast.Call)
            and isinstance(n.func, ast.Attribute)
            and n.func.attr == 'raises'
            for n in ast.walk(node)
        )
        has_run = any(
            isinstance(n, ast.Call)
            and isinstance(n.func, ast.Name)
            and n.func.id == 'run_migrations'
            for n in ast.walk(node)
        )
        if not (has_assert or has_raises or has_run):
            print(f'NOOP {node.name}:{node.lineno}')
PY
Result: no output; no no-op tests found

uv run ruff format tests/test_package_migration.py
Result: 1 file left unchanged

uv run ruff check
Result: All checks passed!

uv run pytest
Result: 353 passed, 1 skipped

uv run ruff format --check
Result: 55 files already formatted

git diff --check
Result: passed
```

### Remaining Risks

None from this remediation. The change is test-only and keeps DB/storage migration safety coverage focused on fail-closed preservation behavior.

## Final Readability Warning Cleanup — Shared Package Publish Limits

### Root Cause Summary

- `agh/cli/package_publish.py` and `agh/server/routes/packages.py` both declared the same package publish business limits for file count, path length, per-file bytes, and total bytes.
- Duplicated limit declarations made CLI preflight validation and server-side enforcement easy to drift, even though they are meant to enforce the same package publishing contract.

### Remediation Evidence

| Warning | Action | Evidence |
|---------|--------|----------|
| Duplicated package publish limits | Added `agh/common/package_limits.py` and moved the shared package publish constants there. CLI publish validation and server route validation now import the same constants. | `tests/test_package_nomenclature.py::test_package_publish_limits_are_shared_between_cli_and_server` passes. |
| Future drift risk | Updated package publish/route tests to import limits from the common module and added a static guard that fails if CLI/server publisher modules redeclare the shared business constants. | `tests/test_package_nomenclature.py::test_package_publish_limits_are_not_redeclared_in_publishers` passes. |
| Behavior preservation | Kept existing limit values and error messages unchanged; only the constant definitions moved. | Focused CLI package publish, package routes, and full pytest suites pass. |

### TDD Cycle Evidence — Shared Limits Cleanup

| Task | Test File | Layer | Safety Net | RED | GREEN | TRIANGULATE | REFACTOR |
|------|-----------|-------|------------|-----|-------|-------------|----------|
| Centralize package publish limits | `tests/test_package_nomenclature.py`, `tests/test_cli_package_commands.py`, `tests/test_package_routes.py` | Static/unit/API/CLI | ✅ Previous full suite was green before this cleanup in prior verification; focused package publish/routes were read before edits | ✅ New common-limit imports failed with `ModuleNotFoundError: No module named 'agh.common.package_limits'` before implementation | ✅ Focused shared-limit and publish/route tests passed: `4 passed`, then package-focused suite `73 passed` | ✅ Added source-level no-redeclaration guard plus existing CLI/server oversized payload/file cases | ✅ Constants now live in `agh/common/package_limits.py`; CLI and server import them without behavior or message changes |

### Verification Commands

```text
uv run pytest tests/test_package_nomenclature.py::test_package_publish_limits_are_shared_between_cli_and_server tests/test_cli_package_commands.py::test_cli_package_publish_refuses_oversized_manifest_before_parsing tests/test_cli_package_commands.py::test_cli_package_publish_refuses_binary_manifest_and_oversized_files tests/test_package_routes.py::test_package_publish_rejects_oversized_payload_before_filesystem_writes -q
RED before fix: collection failed with ModuleNotFoundError for agh.common.package_limits
GREEN after fix: 4 passed

uv run pytest tests/test_package_nomenclature.py::test_package_publish_limits_are_shared_between_cli_and_server tests/test_package_nomenclature.py::test_package_publish_limits_are_not_redeclared_in_publishers -q
Result: 2 passed

uv run pytest tests/test_cli_package_commands.py tests/test_package_routes.py tests/test_package_nomenclature.py -q
Result: 73 passed

uv run pytest
Result: 352 passed, 1 skipped

uv run ruff format
Result: 1 file reformatted, 55 files left unchanged

uv run pytest tests/test_cli_package_commands.py tests/test_package_routes.py tests/test_package_nomenclature.py -q
Result: 73 passed

uv run pytest
Result: 352 passed, 1 skipped

uv run ruff check && uv run ruff format --check && git diff --check
Result: All checks passed; 56 files already formatted; git diff check passed
```

### Remaining Risks

None from this cleanup. Package publish limit values remain unchanged and are now defined once for both local CLI validation and server enforcement.

## Final Blocker Remediation — Package Publish JSON Body Cap

### Root Cause Summary

- `MAX_PACKAGE_PUBLISH_BODY_BYTES` used `MAX_PACKAGE_TOTAL_BYTES + (MAX_PACKAGE_FILES * 128)`, which bounded raw content bytes plus a small unexplained per-file allowance.
- The server enforces this cap before JSON parsing/validation, so a package that satisfies per-file and total content limits can still exceed the wire-body cap when JSON escaping expands control characters, quotes, backslashes, or UTF-8 scalar values.
- The formula did not account for worst-case JSON string escaping of file contents, worst-case escaped path keys, or the JSON object syntax around each file entry.

### Remediation Evidence

| Finding | Action | Evidence |
|---------|--------|----------|
| Valid max-content package rejected before validation | Added a regression that posts a package whose decoded file content totals exactly `MAX_PACKAGE_TOTAL_BYTES` while JSON control-character escaping expands the request body well beyond raw content size. | `tests/test_package_routes.py::test_package_publish_body_cap_allows_max_content_with_json_escaping` failed RED with `413`, then passed with `201`. |
| Magic body-cap overhead | Replaced the `* 128` allowance with named constants for JSON control escaping, path surrogate escaping, envelope syntax, and per-file entry syntax. | `agh/common/package_limits.py` now documents the cap as worst-case escaped content + worst-case escaped paths + JSON syntax overhead. |
| Oversized request protection must remain meaningful | Kept middleware and streamed-body checks against `MAX_PACKAGE_PUBLISH_BODY_BYTES`; oversized bodies still return `413` before filesystem writes. | `tests/test_package_routes.py::test_package_publish_rejects_streamed_body_over_body_cap` passes. |
| Server import clarity | The FastAPI middleware now imports the shared body cap directly from `agh.common.package_limits` instead of through the packages route module. | Focused package route tests and full suite pass. |

### TDD Cycle Evidence — JSON Body Cap Remediation

| Task | Test File | Layer | Safety Net | RED | GREEN | TRIANGULATE | REFACTOR |
|------|-----------|-------|------------|-----|-------|-------------|----------|
| Permit valid max-content escaped JSON package bodies | `tests/test_package_routes.py` | API/middleware | ✅ Existing body-cap package route baseline: `3 passed` | ✅ New escaped-content max-boundary test failed with middleware `413` before implementation | ✅ Focused body-cap tests passed: `2 passed`; package routes/nomenclature passed: `38 passed`; full suite passed | ✅ Existing streamed oversized-body test proves the cap still rejects bodies over the new bound | ✅ Extracted named JSON escape/path/syntax constants and imported shared cap directly in app middleware |

### Verification Commands

```text
uv run pytest tests/test_package_routes.py -k 'package_publish_rejects_streamed_body_over_body_cap or package_publish_rejects_oversized_payload_before_filesystem_writes or package_publish_validation_and_immutability'
Baseline before edits: 3 passed, 25 deselected

uv run pytest tests/test_package_routes.py::test_package_publish_body_cap_allows_max_content_with_json_escaping
RED before fix: 1 failed; response was 413 `package publish payload is too large`

uv run pytest tests/test_package_routes.py::test_package_publish_body_cap_allows_max_content_with_json_escaping tests/test_package_routes.py::test_package_publish_rejects_streamed_body_over_body_cap
GREEN after fix: 2 passed

uv run pytest tests/test_package_routes.py -q
Result: 29 passed

uv run pytest tests/test_cli_package_commands.py -k 'publish or package_commands' -q
Result: 36 passed

uv run pytest tests/test_package_routes.py tests/test_package_nomenclature.py -q
Result: 38 passed

uv run pytest
Result: 353 passed, 1 skipped

uv run ruff check
Result: All checks passed!

uv run ruff format --check
Result: 56 files already formatted

git diff --check
Result: passed
```

### Remaining Risks

- The body cap deliberately bounds compact JSON plus worst-case string escaping. It does not attempt to allow arbitrary extra whitespace or unrelated JSON fields, because those are not needed for a package that passes content limits and would weaken request-size protection.
