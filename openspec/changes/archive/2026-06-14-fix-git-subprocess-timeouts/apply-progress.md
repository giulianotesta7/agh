# Apply Progress: Git Subprocess Timeout Safety for Sync and Pull

## Mode

Standard apply mode. Strict TDD is disabled in `openspec/config.yaml` and Engram testing capabilities.

## Completed Tasks

- [x] 1.1 Update `agh/cli/workspace_sync.py` to define the local 5-second subprocess timeout constant used by remote detection.
- [x] 1.2 Update `agh/cli/workspace_pull.py` to define the same local 5-second timeout constant for VCS hint subprocess calls.
- [x] 2.1 Wrap `git remote get-url` in `agh/cli/workspace_sync.py` with `timeout=5` and convert `subprocess.TimeoutExpired` into `WorkspaceSyncError` with a clear timeout message and non-zero exit path.
- [x] 2.2 Wrap `git rev-parse` and `git check-ignore` in `agh/cli/workspace_pull.py` with `timeout=5` and treat `TimeoutExpired` as advisory fallback that suppresses the hint, including the `check-ignore` branch.
- [x] 2.3 Keep the timeout handling local to these files; do not extract a shared Git helper or widen the CLI refactor scope.
- [x] 3.1 Add a focused sync test in `tests/test_workspace_sync.py` that monkeypatches `subprocess.run` to raise `TimeoutExpired` and asserts non-zero exit plus clear timeout/error output.
- [x] 3.2 Add focused pull coverage for VCS hint timeout fallback; implemented in `tests/test_cli_pull.py` beside existing VCS hint CLI coverage, with explicit regression coverage for `git check-ignore` timing out after `git rev-parse` succeeds.
- [x] 3.3 Verify existing success-path tests still pass for sync remote resolution and pull hint generation.
- [x] 4.1 Confirm the tasks stay limited to `workspace_sync.py`, `workspace_pull.py`, and their focused tests.
- [x] 4.2 Exclude workspace atomicity, Docker hardening, corrupt pack handling, retries, and broader CLI refactors from this batch.

## Files Changed

| File | Action | What Was Done |
|------|--------|---------------|
| `agh/cli/workspace_sync.py` | Modified | Added `GIT_SUBPROCESS_TIMEOUT_SECONDS = 5`, passed it to `git remote get-url`, and converted `TimeoutExpired` into `WorkspaceSyncError(code=5)` with a clear message. |
| `agh/cli/workspace_pull.py` | Modified | Added `GIT_SUBPROCESS_TIMEOUT_SECONDS = 5`, passed it to `git rev-parse` and `git check-ignore`, and suppresses the advisory hint when `check-ignore` times out. |
| `tests/test_workspace_sync.py` | Modified | Added CLI-level sync timeout coverage that asserts exit code 5, timeout text, no project lookup, and no `.agh/project.toml`. |
| `tests/test_cli_pull.py` | Modified | Added CLI-level pull timeout coverage that asserts pull succeeds, writes expected results, and omits the VCS hint for both `rev-parse` and `check-ignore` timeout paths. |
| `openspec/changes/fix-git-subprocess-timeouts/tasks.md` | Modified | Marked all implementation, test, and scope-guard tasks complete. |

## Verification

| Command | Result |
|---------|--------|
| `uv run pytest tests/test_workspace_sync.py tests/test_cli_pull.py -q` | Passed: 38 tests. |
| `uv run --with ruff ruff format --check .` | Passed: 52 files already formatted. |

## Deviations / Notes

- Earlier planning used a stale pull test filename, but `design.md` named `tests/test_cli_pull.py` and existing VCS hint CLI tests are located there. The implemented test is placed beside those existing CLI hint tests to keep the behavior coverage cohesive.
- No shared Git helper was extracted; timeout handling remains local to the two affected modules.
- Verify blocker remediation updated `_is_git_ignored()` to distinguish a timeout from a normal “not ignored” result so `_vcs_guidance_hint()` can omit the hint when `git check-ignore` times out.

## Workload / PR Boundary

- Mode: single PR.
- Current work unit: sync and pull Git subprocess timeout behavior.
- Boundary: starts from the existing OpenSpec change and ends with local timeout handling plus focused tests only.
- Estimated review budget impact: 62 changed implementation/test lines before OpenSpec artifact updates; remains below the 400-line review budget.
