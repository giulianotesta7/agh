## Verification Report

**Change**: `fix-cli-unknown-command-exit`
**Version**: N/A
**Mode**: Standard (strict TDD inactive; `openspec/config.yaml` sets `strict_tdd: false`)

### Completeness

| Metric | Value |
|--------|-------|
| Tasks total | 9 |
| Tasks complete | 9 |
| Tasks incomplete | 0 |

### Build & Tests Execution

**Build**: ➖ Not configured

No project build/type-check command is configured in `openspec/config.yaml` for verification. Static sanity check passed:

```text
$ git diff --check
Command executed successfully
```

**Focused CLI tests**: ✅ 54 passed

```text
$ uv run pytest tests/test_cli_login.py tests/test_cli_admin_commands.py tests/test_cli_pack_commands.py tests/test_agent_command.py
collected 54 items
tests/test_cli_login.py .........
tests/test_cli_admin_commands.py ................
tests/test_cli_pack_commands.py ......................
tests/test_agent_command.py .......
============================= 54 passed in 15.22s ==============================
```

**Broader CLI routing tests**: ✅ 83 passed

```text
$ uv run pytest tests/test_cli_*.py tests/test_agent_command.py
collected 83 items
tests/test_cli_admin_commands.py ................
tests/test_cli_login.py .........
tests/test_cli_pack_commands.py ......................
tests/test_cli_pull.py .............................
tests/test_agent_command.py .......
============================= 83 passed in 29.36s ==============================
```

**Full test suite**: ✅ 268 passed, ⚠️ 1 existing warning

```text
$ uv run pytest
collected 268 items
tests/test_agent_command.py .......
tests/test_api_errors.py .....
tests/test_auth_bootstrap.py ........
tests/test_cli_admin_commands.py ................
tests/test_cli_login.py .........
tests/test_cli_pack_commands.py ......................
tests/test_cli_pull.py .............................
tests/test_common_helpers.py .......................
tests/test_db_migrations.py .......
tests/test_docs_guidance.py ...........
tests/test_install_script.py ...
tests/test_integration_smoke.py .
tests/test_pack_routes.py .......................
tests/test_project_pack_assignments.py ....
tests/test_project_routes.py .....
tests/test_pull_manifest_routes.py ....
tests/test_pull_markers.py ...............
tests/test_pull_plan.py ............
tests/test_scaffold.py ....
tests/test_user_routes.py ...........
tests/test_workspace_pull.py ...........................................
tests/test_workspace_sync.py ......
======================= 268 passed, 1 warning in 38.76s ========================
```

Full-suite warning observed:

```text
.venv/lib/python3.14/site-packages/fastapi/testclient.py:1:
StarletteDeprecationWarning: Using `httpx` with `starlette.testclient` is deprecated; install `httpx2` instead.
```

**Coverage**: ➖ Not available / no coverage command configured.

### Spec Compliance Matrix

| Requirement | Scenario | Runtime Test Evidence | Result |
|-------------|----------|------------------------|--------|
| Unknown command exits with usage error | Unknown root command (`agh does-not-exist`) | `tests/test_cli_login.py::test_top_level_help_lists_login_config_flags_and_arguments` in focused, broader, and full pytest runs | ✅ COMPLIANT |
| Unknown command exits with usage error | Unknown nested subcommand (`agh config does-not-exist`) | `tests/test_cli_login.py::test_top_level_help_lists_login_config_flags_and_arguments` in focused, broader, and full pytest runs | ✅ COMPLIANT |
| Applicability covers routed command groups | Nested group typo in project member path | `tests/test_cli_admin_commands.py::test_cli_admin_unknown_subcommands_exit_2_with_help_first_output` in focused, broader, and full pytest runs | ✅ COMPLIANT |
| Applicability covers routed command groups | Nested group typo in agent path | `tests/test_agent_command.py::test_agent_unknown_subcommand_exits_2_with_help_first_output` in focused, broader, and full pytest runs | ✅ COMPLIANT |
| Valid help paths remain successful | Root help succeeds | `tests/test_cli_login.py::test_top_level_help_lists_login_config_flags_and_arguments` in focused, broader, and full pytest runs | ✅ COMPLIANT |
| Valid help paths remain successful | Group help succeeds (`agh config --help`) | `tests/test_cli_login.py::test_top_level_help_lists_login_config_flags_and_arguments` in focused, broader, and full pytest runs | ✅ COMPLIANT |

**Compliance summary**: 6/6 scenarios compliant.

### Correctness (Static Evidence)

| Requirement | Status | Notes |
|------------|--------|-------|
| Unknown command exits with usage error | ✅ Implemented | `agh/cli/main.py` defines `USAGE_ERROR_EXIT_CODE = 2`; `AghHelpGroup.resolve_command()` and `AghSubcommandGroup.resolve_command()` echo `APP_HELP` and raise `typer.Exit(2)` for unknown non-option command tokens. |
| Preserve help-first visible output | ✅ Implemented | Updated tests compare unknown-command stdout with the actual no-argument help output, preserving the visible help-first contract. |
| Applicability covers routed command groups | ✅ Implemented | Root/config use `AghHelpGroup`; user, token, project, project member, project pack, pack, and agent use `AghSubcommandGroup`. Runtime tests cover config, user, token, project, project member, project pack, pack, and agent typo paths. |
| Valid help paths remain successful | ✅ Implemented | No-argument and explicit help assertions remain `exit_code == 0` for root/config and relevant routed groups. |

### Coherence (Design)

| Decision | Followed? | Notes |
|----------|-----------|-------|
| Preserve help-first UX | ✅ Yes | Unknown command paths still emit `APP_HELP`; only the exit status changes to `2`. |
| Minimal group-level change | ✅ Yes | Application code changes are limited to the two custom `resolve_command()` overrides plus a small exit-code constant; no CLI routing refactor was introduced. |
| Usage-error status | ✅ Yes | Unknown root and nested command paths return Click/Typer usage-error status `2`. |

### Issues Found

**CRITICAL**: None.

**WARNING**: None.

**SUGGESTION**:
- The full suite still emits an unrelated `StarletteDeprecationWarning` from `fastapi/testclient.py`; it does not affect this change but should be tracked separately if dependency maintenance is in scope.

### Verdict

PASS

All tasks are complete, all spec scenarios have passing runtime test evidence, the implementation matches the design, and focused plus full verification commands passed.
