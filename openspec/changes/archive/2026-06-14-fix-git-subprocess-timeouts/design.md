# Design: Git Subprocess Timeout Safety for Sync and Pull

## Technical Approach

Add a narrow, fixed 5-second timeout to the three local Git subprocess calls identified by the proposal and the `workspace-git-subprocess-timeouts` spec. Keep the existing module boundaries: `agh sync` still resolves its required remote URL in `agh/cli/workspace_sync.py`, while `agh pull` still computes the post-success VCS hint in `agh/cli/workspace_pull.py`. Timeout behavior differs by business need: sync converts timeout into a `WorkspaceSyncError`; pull treats hint timeouts as advisory and omits the hint.

## Architecture Decisions

| Option | Tradeoff | Decision |
|--------|----------|----------|
| Per-call `subprocess.run(..., timeout=5)` | Smallest diff and follows current direct subprocess style, but duplicates the literal unless centralized locally. | Use per-call timeout for this slice. |
| Shared Git helper | Reduces duplication, but widens scope into a CLI refactor explicitly deferred by the proposal. | Reject for now. |
| Sync timeout raises `WorkspaceSyncError` | Blocks sync when remote detection hangs, but gives a deterministic non-zero failure. | Required remote lookup must fail clearly. |
| Pull hint timeout returns no hint | Can omit helpful `.gitignore` guidance, but preserves successful pull results. | Advisory hint checks must not fail pull. |

## Data Flow

`agh sync` required path:

    main.sync ──→ sync_workspace ──→ _git_remote_url
                                      │
                                      ├─ success <5s ──→ normalize/fetch/match/write
                                      └─ TimeoutExpired ──→ WorkspaceSyncError(code=5)

`agh pull` advisory hint path:

    pull_workspace ──→ apply/cache/lock ──→ _vcs_guidance_hint
                                               │
                                               ├─ git checks succeed ──→ hint or None
                                               └─ TimeoutExpired ──→ None, result preserved

## File Changes

| File | Action | Description |
|------|--------|-------------|
| `agh/cli/workspace_sync.py` | Modify | Add local `GIT_SUBPROCESS_TIMEOUT_SECONDS = 5`; pass `timeout` to `git remote get-url`; catch `subprocess.TimeoutExpired` and raise `WorkspaceSyncError` with a clear message and code `5`. |
| `agh/cli/workspace_pull.py` | Modify | Add the same local timeout constant; pass `timeout` to `git rev-parse` and `git check-ignore`; catch `subprocess.TimeoutExpired` with advisory fallback behavior (`None`/no hint). |
| `tests/test_workspace_sync.py` | Modify | Add CLI-level coverage that monkeypatches `agh.cli.workspace_sync.subprocess.run` to raise `TimeoutExpired` for remote lookup and asserts non-zero exit plus timeout text and no project link. |
| `tests/test_cli_pull.py` | Modify | Add pull coverage near existing VCS hint tests; monkeypatch `agh.cli.workspace_pull.subprocess.run` timeout and assert pull exits `0`, writes expected results, and omits the hint. |

## Interfaces / Contracts

No public API, CLI flag, config, or environment variable is added.

Internal contract:

```python
GIT_SUBPROCESS_TIMEOUT_SECONDS = 5
```

`_git_remote_url()` continues returning `str` or raising `WorkspaceSyncError`. `_is_git_worktree()` continues returning `bool`. `_is_git_ignored()` returns `True`, `False`, or `None`; `None` means the advisory Git check timed out or was unavailable, so `_vcs_guidance_hint()` suppresses the hint without failing pull.

## Testing Strategy

| Layer | What to Test | Approach |
|-------|-------------|----------|
| Unit/CLI | `agh sync` remote timeout is user-facing and non-zero. | Monkeypatch module-local `subprocess.run` to raise `subprocess.TimeoutExpired`; invoke Typer CLI; assert exit code `5`, clear timeout message, and no `.agh/project.toml`. |
| Unit/CLI | `agh pull` VCS hint timeout is advisory. | Use existing pull server/helpers; monkeypatch only Git hint subprocess calls to timeout; assert exit `0`, normal pull output/lockfile, and no VCS hint. |
| Regression | Existing success and hint behavior remains unchanged. | Run `uv run pytest tests/test_workspace_sync.py tests/test_cli_pull.py`, then `uv run pytest` in verify. |

## Migration / Rollout

No migration required. Roll out as a patch-level CLI behavior change.

## Open Questions

None.
