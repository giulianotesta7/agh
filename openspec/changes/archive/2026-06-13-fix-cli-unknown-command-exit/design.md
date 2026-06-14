# Design: Fix CLI Unknown Command Exit Status

## Technical Approach

Keep the existing AGH help-first output path for typoed command names, but change only the exit status used by the custom Typer group resolution in `agh/cli/main.py`. The `cli-usage-errors` spec requires unknown root and nested commands to show the current AGH usage/help output and exit as usage errors, while no-argument and explicit `--help` paths stay successful.

## Architecture Decisions

| Decision | Choice | Alternatives considered | Rationale |
|---|---|---|---|
| Preserve help-first UX | Continue echoing `APP_HELP` for unknown command tokens and raise `typer.Exit(2)` instead of `typer.Exit(0)`. | Let Click/Typer emit native invalid-command errors. | Native errors are more standard but would change visible UX; the proposal and spec explicitly require preserving current help output. |
| Minimal group-level change | Update `AghHelpGroup.resolve_command()` and `AghSubcommandGroup.resolve_command()` only. | Refactor CLI routing or command callbacks. | The root cause is isolated to both custom `resolve_command()` overrides; broader CLI refactor adds risk without changing the contract. |
| Usage-error status | Use Click/Typer convention exit status `2` for unknown command usage failures. | Any non-zero code or existing domain errors (`1`, `4`). | Existing local validation failures already use `2`; scripts need a deterministic usage-error signal. |

## Data Flow

```text
argv tokens ──→ TyperGroup.resolve_command()
       │              │
       │              ├─ known command / option ──→ existing Typer flow
       │              └─ unknown non-option token ──→ echo APP_HELP ──→ Exit(2)
       └─ no args / --help ──→ existing callbacks/help ──→ Exit(0)
```

## File Changes

| File | Action | Description |
|------|--------|-------------|
| `agh/cli/main.py` | Modify | Change unknown non-option command exits in `AghHelpGroup` and `AghSubcommandGroup` from `0` to `2`; optionally introduce a small `USAGE_ERROR_EXIT_CODE = 2` constant near CLI help constants. |
| `tests/test_cli_login.py` | Modify | Update root and `config` typo expectations to exit `2` while preserving stdout equality with no-arg help; keep no-arg and explicit help assertions at `0`. |
| `tests/test_cli_admin_commands.py` | Modify | Add/adjust coverage for `user`, `token`, `project`, and `project member` unknown subcommands exiting `2` with current help-first output. |
| `tests/test_cli_pack_commands.py` | Modify | Add coverage for `pack` and `project pack` unknown subcommands exiting `2` with current help-first output. |
| `tests/test_agent_command.py` | Modify | Add coverage for `agent` unknown subcommands exiting `2` with current help-first output. |

## Interfaces / Contracts

No public API or data model changes. CLI contract changes:

```python
UNKNOWN_COMMAND_EXIT_CODE = 2
UNKNOWN_COMMAND_OUTPUT = APP_HELP  # stdout, unchanged from current visible UX
```

Valid no-argument group invocations and explicit help (`agh`, `agh --help`, `agh config --help`, command-specific help) remain `exit_code == 0`.

## Testing Strategy

| Layer | What to Test | Approach |
|-------|-------------|----------|
| Unit/CLI runner | Root and `config` unknown commands | Update existing `CliRunner` assertions in `tests/test_cli_login.py`: same stdout as root help, exit `2`. |
| Unit/CLI runner | Nested routed groups | Parameterize typo cases for `user`, `token`, `project`, `project member`, `project pack`, `pack`, and `agent`; assert stdout remains `APP_HELP`-equivalent and exit `2`. |
| Regression | Legitimate help/no-arg success | Preserve existing help tests and add assertions where needed that no-arg groups and explicit help stay `0`. |

Run `uv run pytest` after implementation.

## Migration / Rollout

No migration required. This is a CLI behavior correction only.

## Open Questions

None.
