## Verification Report

**Change**: `fix-git-subprocess-timeouts`  
**Version**: N/A  
**Mode**: Standard verification (`strict_tdd: false`)  
**Artifact store**: OpenSpec  
**Verified at**: 2026-06-14

## Completeness

| Metric | Value |
|--------|-------|
| Tasks total | 10 |
| Tasks complete | 10 |
| Tasks incomplete | 0 |
| Proposal/spec/design/tasks present | Yes |
| Specs present | Yes: `workspace-git-subprocess-timeouts` |

## Build & Tests Execution

**Build**: ➖ Not configured for this Python package/OpenSpec change.

**Focused scenario tests**: ✅ Passed

```text
$ uv run pytest tests/test_workspace_sync.py::test_sync_remote_lookup_timeout_fails_clearly tests/test_workspace_sync.py::test_sync_links_default_remote_and_uses_saved_config_auth tests/test_workspace_sync.py::test_sync_supports_non_default_remote tests/test_cli_pull.py::test_pull_vcs_hint_timeout_skips_hint_and_keeps_pull_success tests/test_cli_pull.py::test_pull_vcs_check_ignore_timeout_skips_hint_and_keeps_pull_success tests/test_cli_pull.py::test_pull_success_in_git_repo_prints_vcs_hint_when_cache_not_ignored tests/test_cli_pull.py::test_pull_success_in_git_repo_suppresses_vcs_hint_when_cache_ignored -q
.......                                                                  [100%]
7 passed in 3.78s
```

**Focused workspace sync/pull suite**: ✅ Passed

```text
$ uv run pytest tests/test_workspace_sync.py tests/test_cli_pull.py -q
......................................                                   [100%]
38 passed in 18.53s
```

**Full test suite**: ✅ Passed

```text
$ uv run pytest -q
........................................................................ [ 26%]
........................................................................ [ 53%]
........................................................................ [ 79%]
.......................................................                  [100%]
271 passed, 1 warning in 40.13s
```

Warning observed:

```text
StarletteDeprecationWarning: Using `httpx` with `starlette.testclient` is deprecated; install `httpx2` instead.
```

**Ad-hoc verification probe for `git check-ignore` timeout**: ✅ Passed

```text
$ uv run python - <<'PY'
from pathlib import Path
import subprocess
import tempfile

import agh.cli.workspace_pull as workspace_pull


def fake_run(cmd, **kwargs):
    if cmd[:2] == ["git", "rev-parse"]:
        return subprocess.CompletedProcess(cmd, 0, stdout="true\n", stderr="")
    if cmd[:2] == ["git", "check-ignore"]:
        raise subprocess.TimeoutExpired(cmd=cmd, timeout=5)
    raise AssertionError(f"unexpected command: {cmd!r}")


original_run = workspace_pull.subprocess.run
workspace_pull.subprocess.run = fake_run
try:
    with tempfile.TemporaryDirectory() as workspace:
        hint = workspace_pull._vcs_guidance_hint(Path(workspace))
        assert hint is None, f"expected no VCS hint on check-ignore timeout, got: {hint!r}"
finally:
    workspace_pull.subprocess.run = original_run
PY
Command executed successfully
```

**Lint**: ✅ Passed

```text
$ uv run --with ruff ruff check .
All checks passed!
```

**Format check**: ✅ Passed

```text
$ uv run --with ruff ruff format --check .
52 files already formatted
```

**Type check**: ✅ Passed

```text
$ uv run --with pyright pyright
0 errors, 0 warnings, 0 informations
```

**OpenSpec validation**: ⚠️ Not executed; CLI unavailable in this environment.

```text
$ openspec validate fix-git-subprocess-timeouts --strict
zsh:1: command not found: openspec
```

**Coverage**: ➖ Not configured.

## Spec Compliance Matrix

| Requirement | Scenario | Runtime Evidence | Result |
|-------------|----------|------------------|--------|
| Sync remote lookup timeout | Remote lookup times out during sync | `tests/test_workspace_sync.py::test_sync_remote_lookup_timeout_fails_clearly` passed; asserts exit code `5`, timeout text, no project lookup, and no `.agh/project.toml`. | ✅ COMPLIANT |
| Sync remote lookup timeout | Remote lookup succeeds within the timeout | `tests/test_workspace_sync.py::test_sync_links_default_remote_and_uses_saved_config_auth` and `tests/test_workspace_sync.py::test_sync_supports_non_default_remote` passed in focused scenario tests. | ✅ COMPLIANT |
| Pull hint checks are advisory | Advisory hint check times out during pull | `tests/test_cli_pull.py::test_pull_vcs_hint_timeout_skips_hint_and_keeps_pull_success` and `tests/test_cli_pull.py::test_pull_vcs_check_ignore_timeout_skips_hint_and_keeps_pull_success` passed; the ad-hoc probe also confirmed `git check-ignore` timeout returns no hint. | ✅ COMPLIANT |
| Pull hint checks are advisory | Advisory hint check succeeds during pull | `tests/test_cli_pull.py::test_pull_success_in_git_repo_prints_vcs_hint_when_cache_not_ignored` and `tests/test_cli_pull.py::test_pull_success_in_git_repo_suppresses_vcs_hint_when_cache_ignored` passed. | ✅ COMPLIANT |

**Compliance summary**: 4/4 scenarios compliant.

## Correctness (Static Evidence)

| Requirement | Status | Notes |
|------------|--------|-------|
| Add fixed 5-second timeout to sync remote lookup | ✅ Implemented | `agh/cli/workspace_sync.py` defines `GIT_SUBPROCESS_TIMEOUT_SECONDS = 5` and passes it to `subprocess.run` for `git remote get-url`. |
| Sync timeout must fail clearly with non-zero exit | ✅ Implemented | `subprocess.TimeoutExpired` is converted to `WorkspaceSyncError(..., code=5)` with timeout text. |
| Add fixed 5-second timeout to pull VCS hint checks | ✅ Implemented | `agh/cli/workspace_pull.py` passes `timeout=GIT_SUBPROCESS_TIMEOUT_SECONDS` to both `git rev-parse` and `git check-ignore`. |
| Pull hint timeout must preserve pull success | ✅ Implemented | `git rev-parse` timeout returns no worktree hint path, and `git check-ignore` timeout returns `None`; `_vcs_guidance_hint()` treats both paths as no-hint advisory fallback. |
| Pull hint timeout must omit hint for any advisory hint check timeout | ✅ Implemented | `_is_git_ignored()` returns `None` on `TimeoutExpired`, and `_vcs_guidance_hint()` suppresses the hint when the ignored state is `None` or `True`. |
| Focused pull timeout test coverage | ✅ Implemented | Pull coverage includes both the `git rev-parse` timeout branch and the previous blocker branch where `git rev-parse` succeeds but `git check-ignore` times out. |

## Coherence (Design)

| Design Decision | Followed? | Notes |
|-----------------|-----------|-------|
| Use per-call `subprocess.run(..., timeout=5)` | ✅ Yes | Implemented locally in both modules. |
| Do not extract shared Git helper | ✅ Yes | No shared helper or broader CLI refactor was introduced. |
| Sync remote lookup timeout raises `WorkspaceSyncError` | ✅ Yes | Timeout maps to user-facing error and exit code `5`. |
| Pull hint timeout returns no hint and preserves pull result | ✅ Yes | Both VCS hint timeout paths omit the hint while keeping pull successful. |
| Keep scope to workspace sync/pull and focused tests | ✅ Yes | Runtime code and tests are scope-limited to `workspace_sync.py`, `workspace_pull.py`, and focused tests. |

## Issues Found

### CRITICAL

None.

### WARNING

1. **OpenSpec CLI is not installed in this environment.**  
   `openspec validate fix-git-subprocess-timeouts --strict` could not run because `openspec` was not found.

2. **Existing Starlette deprecation warning remains in the full test suite.**  
   The warning is unrelated to this change and does not affect the verified sync/pull behavior.

### SUGGESTION

None.

## Verdict

**PASS WITH WARNINGS**

The previous CRITICAL blocker is fixed: `git check-ignore` timeout now suppresses the VCS hint and allows `agh pull` to complete. Formatting is fixed, focused and full pytest suites pass, lint passes, and type checking passes; only environment-level OpenSpec CLI availability and an unrelated existing deprecation warning remain.
