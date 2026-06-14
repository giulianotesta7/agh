# Apply Progress: Fix Workspace Pull Atomicity

## PR1 Scope
Stacked-to-main PR1: cache staging + rollback helpers only. Target/skill promotion and lock-last stay in PR2.

## Completed Tasks
- [x] 1.1 Cache staging helpers.
- [x] 1.2 AGH-owned rollback/stale cleanup with cache-boundary proof.
- [x] 1.3 Stage safety tests, including second-write failure and symlink/boundary cleanup.
- [x] 2.1 Replaced sequential `agh pull` local writes with `_commit_pull_writes()`.
- [x] 2.2 Added rollback for promoted cache dirs, instruction targets, and skill targets; lockfile write remains last with order-sensitive test evidence.
- [x] 2.3 Preserved dry-run, conflict, symlink, force, VCS, and public `pull_workspace()` failure safety behavior.
- [x] 2.4 Added PR2 rollback tests for target, partial skill, public lock failure, and lock-last failures; PR1 cache staging coverage remains.

## TDD Cycle Evidence
| Task | Test File | Layer | Safety Net | RED | GREEN | TRIANGULATE | REFACTOR |
|---|---|---|---|---|---|---|---|
| PR1 review fixes | `tests/test_workspace_pull.py` | Unit | ✅ 46/46 | ✅ Boundary misuse test failed before helper signature/code | ✅ 49/49 focused; 290/290 full | ✅ second write failure + symlink cleanup | ✅ ruff format/check |
| 2.1-2.4 PR2 atomic promotion | `tests/test_workspace_pull.py`, `tests/test_cli_pull.py` | Unit/API | ✅ 83/83 focused baseline | ✅ Review-finding tests added before cleanup/code changes | ✅ 84/84 focused; 294/294 full | ✅ target + partial skill + public lock failure + lock-last evidence | ✅ removed dead sequential helpers/unused rollback kind; ruff/pyright |

## Remaining
- [ ] PR3 CLI regressions/proof points.
