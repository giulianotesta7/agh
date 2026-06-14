# Tasks: Workspace Pull Atomicity

## Review Workload Forecast
Estimated changed lines: 300-520
Decision needed before apply: Yes
Chained PRs recommended: Yes
Chain strategy: stacked-to-main
400-line budget risk: High

## Phase 1: Foundation / Staging Helpers
- [x] 1.1 Add cache staging/rollback helpers in `agh/cli/workspace_pull.py`.
- [x] 1.2 Define AGH-owned rollback paths and stale stage cleanup.
- [x] 1.3 Add unit tests in `tests/test_workspace_pull.py` for stage safety.

## Phase 2: Atomic Promotion Flow
- [x] 2.1 Replace sequential local writes with `_commit_pull_writes()`.
- [x] 2.2 Roll back prior cache dirs on later failures; publish lock last.
- [x] 2.3 Preserve dry-run, conflict, symlink, force, and VCS behavior.
- [x] 2.4 Add cache/target/skill/lock failure tests.

## Phase 3: CLI Regression Verification
- [x] 3.1 Add CLI dry-run and success consistency regressions.
- [x] 3.2 Verify managed-block rejection and forced overwrite behavior.
- [x] 3.3 Run changed modules and full verification.

## Phase 4: Final Verification Remediation
- [x] 4.1 Add stale-stage success regression and wire successful pull cleanup.
- [x] 4.2 Move stale-stage cleanup before lock publication and cover cleanup-failure rollback.
