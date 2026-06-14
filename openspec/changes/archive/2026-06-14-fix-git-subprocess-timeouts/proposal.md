# Proposal: Git Subprocess Timeout Safety for Sync and Pull

## Intent

Prevent local Git subprocess calls from hanging `agh sync` or `agh pull`. This is a small v0.3.2 fix: sync must fail clearly when required remote detection times out, while pull must continue when advisory VCS hints time out.

## Proposal Question Round

Assumptions for user review:
- 5 seconds is the fixed timeout for this slice; no config/env override.
- Timeout UX distinguishes required sync remote lookup from advisory pull hints.
- Broader Git hardening remains deferred.

## Scope

### In Scope
- Add a 5-second timeout to `git remote get-url` in `agh/cli/workspace_sync.py`.
- Add a 5-second timeout to `git rev-parse` and `git check-ignore` in `agh/cli/workspace_pull.py`.
- Add focused pytest coverage for sync timeout failure and pull hint timeout fallback.

### Out of Scope
- Workspace atomicity, Docker hardening, corrupt pack file handling.
- Shared Git helper extraction or broader CLI refactors.
- Retries, telemetry, or configurable timeout policy.

## Capabilities

### New Capabilities
- `workspace-git-subprocess-timeouts`: Timeout behavior for local Git subprocess calls used by sync and pull guidance.

### Modified Capabilities
- None — no existing OpenSpec specs found.

## Approach

Use per-call `subprocess.run(..., timeout=5)` handling. In sync, catch `subprocess.TimeoutExpired` and raise `WorkspaceSyncError` with a non-zero user-facing failure because remote detection is required. In pull, catch timeout in VCS hint helpers and skip the hint so the completed pull result is preserved.

## Affected Areas

| Area | Impact | Description |
|------|--------|-------------|
| `agh/cli/workspace_sync.py` | Modified | Required Git remote lookup gains timeout and clear failure. |
| `agh/cli/workspace_pull.py` | Modified | Advisory Git hint checks gain timeout and safe fallback. |
| `tests/test_workspace_sync.py` | Modified | Covers sync timeout as non-zero user-facing error. |
| `tests/test_cli_pull.py` | Modified | Covers pull hint timeout continuing without hint. |

## Risks

| Risk | Likelihood | Mitigation |
|------|------------|------------|
| Slow local Git operation exceeds 5 seconds. | Low | Keep error explicit for sync; pull only skips advisory hint. |
| Timeout behavior diverges between files. | Medium | Use focused tests that encode required vs advisory semantics. |

## Rollback Plan

Revert this change folder and implementation edits to the two workspace modules/tests. Existing subprocess behavior returns to no timeout.

## Dependencies

- None.

## Success Criteria

- [ ] `agh sync` exits non-zero with a clear timeout error when `git remote get-url` exceeds 5 seconds.
- [ ] `agh pull` completes and omits the VCS hint when advisory Git checks exceed 5 seconds.
- [ ] Focused tests pass with `uv run pytest`.
