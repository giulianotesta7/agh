# Tasks: Git Subprocess Timeout Safety for Sync and Pull

## Review Workload Forecast

| Field | Value |
|-------|-------|
| Estimated changed lines | 120-180 |
| 400-line budget risk | Low |
| Chained PRs recommended | No |
| Suggested split | Single PR |
| Delivery strategy | ask-always |
| Chain strategy | pending |

Decision needed before apply: No
Chained PRs recommended: No
Chain strategy: pending
400-line budget risk: Low

### Suggested Work Units

| Unit | Goal | Likely PR | Notes |
|------|------|-----------|-------|
| 1 | Add timeout handling to required sync remote lookup | PR 1 | Base on current change branch; includes sync test |
| 2 | Add advisory timeout fallback for pull VCS hints | PR 1 | Same PR; keep behavior isolated to hint helpers and tests |

## Phase 1: Foundation / Timeout Contract

- [x] 1.1 Update `agh/cli/workspace_sync.py` to define the local 5-second subprocess timeout constant used by remote detection.
- [x] 1.2 Update `agh/cli/workspace_pull.py` to define the same local 5-second timeout constant for VCS hint subprocess calls.

## Phase 2: Core Behavior

- [x] 2.1 Wrap `git remote get-url` in `agh/cli/workspace_sync.py` with `timeout=5` and convert `subprocess.TimeoutExpired` into `WorkspaceSyncError` with a clear timeout message and non-zero exit path.
- [x] 2.2 Wrap `git rev-parse` and `git check-ignore` in `agh/cli/workspace_pull.py` with `timeout=5` and treat `TimeoutExpired` as advisory fallback that suppresses the hint.
- [x] 2.3 Keep the timeout handling local to these files; do not extract a shared Git helper or widen the CLI refactor scope.

## Phase 3: Testing / Verification

- [x] 3.1 Add a focused sync test in `tests/test_workspace_sync.py` that monkeypatches `subprocess.run` to raise `TimeoutExpired` and asserts non-zero exit plus clear timeout/error output.
- [x] 3.2 Add focused pull tests in `tests/test_cli_pull.py` that cover both `git rev-parse` timeout and `git check-ignore` timeout, asserting pull still succeeds without printing the hint.
- [x] 3.3 Verify existing success-path tests still pass for sync remote resolution and pull hint generation.

## Phase 4: Cleanup / Scope Guard

- [x] 4.1 Confirm the tasks stay limited to `workspace_sync.py`, `workspace_pull.py`, and their focused tests.
- [x] 4.2 Exclude workspace atomicity, Docker hardening, corrupt pack handling, retries, and broader CLI refactors from this batch.
