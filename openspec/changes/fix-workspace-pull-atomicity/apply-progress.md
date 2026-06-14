# Apply Progress: Fix Workspace Pull Atomicity

## PR1 Scope
Stacked-to-main PR1: cache staging + rollback helpers only. Target/skill promotion and lock-last stay in PR2.

## PR2 Scope
Stacked-to-main PR2: runtime promotion/rollback flow. `agh pull` promotes cache, instruction targets, and skill targets before writing `.agh/lock.toml` last; rollback preserves prior public state on promotion failures.

## PR3 Scope
Stacked-to-main PR3: final CLI regression and SDD cleanup only. No runtime code changes were required.

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

## TDD Cycle Evidence
| Task | Test File | Layer | Safety Net | RED | GREEN | TRIANGULATE | REFACTOR |
|---|---|---|---|---|---|---|---|
| PR1 review fixes | `tests/test_workspace_pull.py` | Unit | ✅ 46/46 | ✅ Boundary misuse test failed before helper signature/code | ✅ 49/49 focused; 290/290 full | ✅ second write failure + symlink cleanup | ✅ ruff format/check |
| 2.1-2.4 PR2 atomic promotion | `tests/test_workspace_pull.py`, `tests/test_cli_pull.py` | Unit/API | ✅ 83/83 focused baseline | ✅ Review-finding tests added before cleanup/code changes | ✅ 84/84 focused; 294/294 full | ✅ target + partial skill + public lock failure + lock-last evidence | ✅ removed dead sequential helpers/unused rollback kind; ruff/pyright |
| 3.1-3.2 PR3 final CLI regressions | `tests/test_cli_pull.py` | CLI/API | ✅ 84/84 focused baseline | N/A — characterization regressions were written before runtime changes; PR2 already satisfied them | ✅ 34/34 CLI focused; 86/86 changed modules; 296/296 full | ✅ dry-run prior state + conflict prior state + success no-stage/checksum consistency | ✅ No runtime refactor needed; docs cleanup only |

## Remaining
- [x] None. All implementation tasks are complete and ready for SDD verification/archive.

## Verification
- `uv run pytest tests/test_cli_pull.py` — 34 passed.
- `uv run pytest tests/test_cli_pull.py tests/test_workspace_pull.py` — 86 passed.
- `uv run pytest` — 296 passed, 1 third-party Starlette/httpx deprecation warning.
- `uv run --with ruff ruff check .` — passed.
- `uv run --with ruff ruff format --check .` — 52 files already formatted.
- `uv run --with pyright pyright` — 0 errors, 0 warnings, 0 informations.
- `git diff --check` — passed.

## Final Notes
- PR3 changed only `tests/test_cli_pull.py`, `openspec/changes/fix-workspace-pull-atomicity/tasks.md`, and this apply-progress artifact.
- Runtime files were intentionally untouched because the final regressions passed against the PR2 implementation.
