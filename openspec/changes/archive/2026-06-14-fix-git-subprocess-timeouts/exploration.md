# Exploration: Git subprocess timeout safety for sync/pull hints

### Current State

`agh sync` and `agh pull` both shell out to local `git` without a timeout. In `agh/cli/workspace_sync.py`, `_git_remote_url()` runs `git remote get-url <remote>` and blocks the sync flow before any API work. In `agh/cli/workspace_pull.py`, `_is_git_worktree()` and `_is_git_ignored()` are only used to decide whether to print the VCS guidance hint after a successful pull.

### Affected Areas

- `agh/cli/workspace_sync.py` — `git remote get-url` can hang indefinitely during sync.
- `agh/cli/workspace_pull.py` — advisory `git rev-parse` / `git check-ignore` calls can hang while computing the post-pull hint.
- `tests/test_workspace_sync.py` — needs timeout coverage for sync failure behavior.
- `tests/test_cli_pull.py` — needs timeout coverage for hint fallback behavior.

### Approaches

1. **Per-call timeout with local fallback** — add a short timeout to each `subprocess.run` and handle timeout differently by caller.
   - Pros: smallest change; preserves current structure; lets sync fail clearly while pull hints degrade safely.
   - Cons: duplicated timeout handling unless a helper is introduced.
   - Effort: Low

2. **Shared git subprocess helper** — centralize `subprocess.run(..., timeout=...)` and timeout translation into one helper.
   - Pros: avoids repeated timeout/error wiring; easier to keep consistent.
   - Cons: slightly larger refactor for a very small deferred review item.
   - Effort: Medium

### Recommendation

Use **per-call timeout with local fallback**, keeping scope narrow for the v0.3.2 batch. Sync should treat timeout as a user-facing failure because it cannot proceed without the remote URL. Pull hint checks should treat timeout as advisory-only: skip the VCS hint and continue the pull result so unrelated work is not blocked.

### Risks

- Too-short timeout could misclassify a slow local repo or hung credential helper as failure.
- If timeout handling is inconsistent, sync and pull may surface different UX for similar git failures.

### Ready for Proposal

Yes. The code paths and tests are clear, and the safest next step is a narrowly scoped timeout policy for the advisory git subprocess calls.
