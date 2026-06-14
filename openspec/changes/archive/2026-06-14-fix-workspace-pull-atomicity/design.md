# Design: Fix Workspace Pull Atomicity

Replace sequential local writes in `pull_workspace()` with staged helpers in `agh/cli/workspace_pull.py`.

## Decisions
- Stage cache under `.agh-cache/packs/<domain>/<name>/.agh-pull-stage-*`.
- Promote: cache, instruction targets, skill targets, `.agh/lock.toml`.
- Roll back only AGH-owned paths; validate cleanup against `.agh-cache/packs`.
- Never follow symlink stage directories during cleanup.

Files: `agh/cli/workspace_pull.py`, `tests/test_workspace_pull.py`, `tests/test_cli_pull.py`.
