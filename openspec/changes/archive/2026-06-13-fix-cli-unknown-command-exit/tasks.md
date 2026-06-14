# Tasks: Fix CLI Unknown Command Exit Status

## Review Workload Forecast

| Field | Value |
|-------|-------|
| Estimated changed lines | Runtime/test diff: 80-160; SDD/OpenSpec artifact payload: ~429; total PR payload: ~509-589 |
| Runtime/test 400-line budget risk | Low |
| Total PR payload 400-line budget risk | High due to traceability artifacts |
| Chained PRs recommended | No for the runtime/test work; SDD artifact overhead is accepted as traceability and excluded from the runtime review budget |
| Suggested split | Single PR |
| Delivery strategy | exception-ok for SDD traceability overhead |
| Chain strategy | size-exception |

Decision needed before apply: No
Chained PRs recommended: No
Chain strategy: size-exception
400-line budget risk: Low
Budget basis: Runtime/test diff only. The ~429 lines of SDD/OpenSpec artifacts are accepted as traceability overhead for this change and should be excluded from the runtime implementation review budget unless reviewer policy requires artifact-only handling.

### Suggested Work Units

| Unit | Goal | Likely PR | Notes |
|------|------|-----------|-------|
| 1 | Change CLI exit status handling for unknown commands | PR 1 | `agh/cli/main.py` plus focused CLI tests |
| 2 | Regenerate nested typo coverage across routed groups | PR 1 | Keep test updates with the behavior change |

## Phase 1: CLI Exit-Code Contract

- [x] 1.1 Update `agh/cli/main.py` so `AghHelpGroup.resolve_command()` raises `typer.Exit(2)` for unknown non-option root commands after echoing `APP_HELP`.
- [x] 1.2 Update `agh/cli/main.py` so `AghSubcommandGroup.resolve_command()` raises `typer.Exit(2)` for unknown non-option nested commands after echoing `APP_HELP`.

## Phase 2: Regression Test Updates

- [x] 2.1 Update `tests/test_cli_login.py` to assert `wrong-command` and `config wrong-command` exit `2` while keeping no-arg and `--help` exit `0`.
- [x] 2.2 Add coverage in `tests/test_cli_admin_commands.py` for typoed `user`, `token`, `project`, and `project member` invocations returning exit `2` and the existing help-first output.
- [x] 2.3 Add coverage in `tests/test_cli_pack_commands.py` for typoed `pack` and `project pack` invocations returning exit `2` and the existing help-first output.
- [x] 2.4 Add coverage in `tests/test_agent_command.py` for an unknown `agent` subcommand returning exit `2` without changing valid help behavior.

## Phase 3: Verification

- [x] 3.1 Run the focused CLI test files to confirm the new exit-code contract and help-first output remain stable.
- [x] 3.2 Run the full CLI pytest subset that exercises `agh/cli/main.py` routing to catch any accidental help regressions.

## Phase 4: Cleanup

- [x] 4.1 Keep changes limited to the custom group resolution path and test expectations; do not introduce unrelated CLI refactors.
