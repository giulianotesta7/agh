# Apply Progress: Fix Workspace Pull Atomicity

## PR1 Scope
Stacked-to-main PR1: cache staging + rollback helpers only. Target/skill promotion and lock-last stay in PR2.

## PR2 Scope
Stacked-to-main PR2: runtime promotion/rollback flow. `agh pull` promotes cache, instruction targets, and skill targets before writing `.agh/lock.toml` last; rollback preserves prior public state on promotion failures.

## PR3 Scope
Stacked-to-main PR3: final CLI regression and SDD cleanup only. No runtime code changes were required.

## Remediation Scope
Stacked-to-main remediation PR: final verify failure fix plus review-critical ordering fix only. Add committed regressions for successful stale `.agh-pull-stage-*` cleanup and stale-cleanup failure rollback, then minimally run stale cleanup before `.agh/lock.toml` publication.

## Completed Tasks
- [x] 1.1 Cache staging helpers.
- [x] 1.2 AGH-owned rollback/stale cleanup with cache-boundary proof.
- [x] 1.3 Stage safety tests, including second-write failure and symlink/boundary cleanup.
- [x] 2.1 Replaced sequential `agh pull` local writes with `_commit_pull_writes()`.
- [x] 2.2 Added rollback for promoted cache dirs, instruction targets, and skill targets; lockfile write remains last with order-sensitive test evidence.
- [x] 2.3 Preserved dry-run, conflict, symlink, force, VCS, and public `pull_workspace()` failure safety behavior.
- [x] 2.4 Added PR2 rollback tests for target, partial skill, public lock failure, and lock-last failures; PR1 cache staging coverage remains.
- [x] 3.1 Added CLI dry-run prior-state preservation and success consistency regressions.
- [x] 3.2 Verified managed-block conflict rejection preserves previous target/cache/lock and existing force overwrite coverage remains green.
- [x] 3.3 Ran changed-module tests, full pytest, Ruff lint/format, Pyright, and diff hygiene checks.
- [x] 4.1 Added stale-stage success regression and wired successful pull cleanup.
- [x] 4.2 Added stale-cleanup failure regression and moved stale cleanup before lock publication so cleanup failure rolls back cache/targets/skills without publishing a new lock.

## TDD Cycle Evidence
| Task | Test File | Layer | Safety Net | RED | GREEN | TRIANGULATE | REFACTOR |
|---|---|---|---|---|---|---|---|
| PR1 review fixes | `tests/test_workspace_pull.py` | Unit | ✅ 46/46 | ✅ Boundary misuse test failed before helper signature/code | ✅ 49/49 focused; 290/290 full | ✅ second write failure + symlink cleanup | ✅ ruff format/check |
| 2.1-2.4 PR2 atomic promotion | `tests/test_workspace_pull.py`, `tests/test_cli_pull.py` | Unit/API | ✅ 83/83 focused baseline | ✅ Review-finding tests added before cleanup/code changes | ✅ 84/84 focused; 294/294 full | ✅ target + partial skill + public lock failure + lock-last evidence | ✅ removed dead sequential helpers/unused rollback kind; ruff/pyright |
| 3.1-3.2 PR3 final CLI regressions | `tests/test_cli_pull.py` | CLI/API | ✅ 84/84 focused baseline | N/A — characterization regressions were written before runtime changes; PR2 already satisfied them | ✅ 34/34 CLI focused; 86/86 changed modules; 296/296 full | ✅ dry-run prior state + conflict prior state + success no-stage/checksum consistency | ✅ No runtime refactor needed; docs cleanup only |
| 4.1 final stale-stage remediation | `tests/test_cli_pull.py` | CLI/API | ✅ 86/86 focused baseline | ✅ New CLI regression failed because pre-existing `.agh-pull-stage-*` survived success | ✅ Targeted regression passed after one-line `_commit_pull_writes()` cleanup wiring | ✅ Existing cleanup tests prove unrelated dirs, committed cache siblings, and symlink targets are preserved | ✅ No refactor; minimal runtime wiring only |
| 4.2 stale-cleanup failure ordering | `tests/test_cli_pull.py` | CLI/API | ✅ 87/87 focused baseline | ✅ New regression failed because cleanup failure left a newly written `.agh/lock.toml` | ✅ Targeted regression passed after moving cleanup before lock publication | ✅ Stale success + cleanup-failure + helper safety cases passed together | ✅ Minimal ordering change only |

## Remaining
- [x] None. All implementation tasks are complete and ready for SDD re-verification. Do not archive until `sdd-verify` records a PASS verdict.

## Verification
- `uv run pytest tests/test_cli_pull.py` — 34 passed.
- `uv run pytest tests/test_cli_pull.py tests/test_workspace_pull.py` — 86 passed.
- `uv run pytest` — 296 passed, 1 third-party Starlette/httpx deprecation warning.
- `uv run --with ruff ruff check .` — passed.
- `uv run --with ruff ruff format --check .` — 52 files already formatted.
- `uv run --with pyright pyright` — 0 errors, 0 warnings, 0 informations.
- `git diff --check` — passed.
- Remediation safety net: `uv run pytest tests/test_cli_pull.py tests/test_workspace_pull.py` — 86 passed before code changes.
- Remediation RED: `uv run pytest tests/test_cli_pull.py::test_successful_pull_removes_pre_existing_stale_cache_stages` — failed because the stale stage remained after success.
- Remediation GREEN: `uv run pytest tests/test_cli_pull.py::test_successful_pull_removes_pre_existing_stale_cache_stages` — passed after cleanup wiring.
- Remediation triangulation: `uv run pytest tests/test_cli_pull.py::test_successful_pull_removes_pre_existing_stale_cache_stages tests/test_workspace_pull.py::test_cleanup_stale_cache_staging_dirs_removes_only_agh_stage_siblings tests/test_workspace_pull.py::test_cleanup_stale_cache_staging_dirs_unlinks_stage_symlink_without_target_delete` — 3 passed.
- Remediation changed modules: `uv run pytest tests/test_cli_pull.py tests/test_workspace_pull.py` — 87 passed.
- Remediation full suite: `uv run pytest` — 297 passed, 1 third-party Starlette/httpx deprecation warning.
- Remediation Ruff: `uv run --with ruff ruff check .` and `uv run --with ruff ruff format --check .` — passed.
- Remediation Pyright: `uv run --with pyright pyright agh tests` — 0 errors, 0 warnings, 0 informations.
- Remediation Docker check: `docker build --check .` — passed.
- Remediation stale-stage probe: previous verify probe now prints `remaining_stage_dirs= []`, target content, and `lock_exists= True`.
- Review-critical RED: `uv run pytest tests/test_cli_pull.py::test_pull_workspace_stale_cleanup_failure_preserves_previous_public_state` — failed because cleanup failure left the new lockfile behind.
- Review-critical GREEN: `uv run pytest tests/test_cli_pull.py::test_pull_workspace_stale_cleanup_failure_preserves_previous_public_state` — passed after moving stale cleanup before lock publication.
- Review-critical triangulation: `uv run pytest tests/test_cli_pull.py::test_successful_pull_removes_pre_existing_stale_cache_stages tests/test_cli_pull.py::test_pull_workspace_stale_cleanup_failure_preserves_previous_public_state tests/test_workspace_pull.py::test_cleanup_stale_cache_staging_dirs_removes_only_agh_stage_siblings tests/test_workspace_pull.py::test_cleanup_stale_cache_staging_dirs_unlinks_stage_symlink_without_target_delete` — 4 passed.
- Review-critical changed modules: `uv run pytest tests/test_cli_pull.py tests/test_workspace_pull.py` — 88 passed.
- Review-critical full suite: `uv run pytest` — 298 passed, 1 third-party Starlette/httpx deprecation warning.
- Review-critical Ruff: `uv run --with ruff ruff check .` and `uv run --with ruff ruff format --check .` — passed.
- Review-critical Pyright: `uv run --with pyright pyright agh tests` — 0 errors, 0 warnings, 0 informations.
- Review-critical Docker check: `docker build --check .` — passed.
- Review-critical diff hygiene: `git diff --check` — passed.

## Final Notes
- PR3 changed only `tests/test_cli_pull.py`, `openspec/changes/fix-workspace-pull-atomicity/tasks.md`, and this apply-progress artifact.
- Runtime files were intentionally untouched because the final regressions passed against the PR2 implementation.
- Remediation changes `agh/cli/workspace_pull.py`, `tests/test_cli_pull.py`, `tasks.md`, and this apply-progress artifact. The stale failed `verify-report.md` was removed from the worktree so it is not accidentally included in this remediation PR.
