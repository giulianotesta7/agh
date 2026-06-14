# Apply Progress: Fix CLI Unknown Command Exit Status

## Mode

Standard (strict TDD inactive; `openspec/config.yaml` sets `strict_tdd: false`).

## Delivery / Review Boundary

- Delivery strategy: ask-always
- Workload forecast: 80-160 changed lines, low 400-line budget risk
- PR mode: single PR
- Actual implementation diff: focused CLI exit-code constant/update plus regression tests; no unrelated CLI refactor

## Completed Tasks

- [x] 1.1 Updated `AghHelpGroup.resolve_command()` to echo `APP_HELP` and exit with status `2` for unknown non-option commands.
- [x] 1.2 Updated `AghSubcommandGroup.resolve_command()` to echo `APP_HELP` and exit with status `2` for unknown non-option nested commands.
- [x] 2.1 Updated `tests/test_cli_login.py` so root and `config` unknown commands exit `2` while no-arg and explicit help remain `0`.
- [x] 2.2 Added admin command typo coverage for `user`, `token`, `project`, and `project member`.
- [x] 2.3 Added pack command typo coverage for `pack` and `project pack`.
- [x] 2.4 Added agent command typo coverage for `agent`.
- [x] 3.1 Ran focused CLI regression tests.
- [x] 3.2 Ran the broader CLI routing pytest subset.
- [x] 4.1 Confirmed the change is limited to custom group resolution and focused test expectations.

## Verification Evidence

| Command | Result |
|---|---|
| `uv run pytest tests/test_cli_login.py tests/test_cli_admin_commands.py tests/test_cli_pack_commands.py tests/test_agent_command.py` | PASS — 54 passed |
| `uv run pytest tests/test_cli_*.py tests/test_agent_command.py` | PASS — 83 passed |

## Deviations from Design

None. The implementation matches the minimal group-level design and preserves help-first stdout while changing unknown-command exit status to `2`.

## Issues Found

- Test assertions comparing directly with `APP_HELP` missed Typer's trailing newline behavior from `typer.echo(APP_HELP)`. Assertions were corrected to compare unknown-command output with the actual root no-argument help output, preserving the visible-output contract.
