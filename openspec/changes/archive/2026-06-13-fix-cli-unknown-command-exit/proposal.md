# Proposal: Fix CLI Unknown Command Exit Status

## Intent

Unknown root commands and nested subcommands currently print helpful AGH usage output and exit `0`, so typos look successful to scripts and CI. Preserve the visual/help-first UX while returning non-zero usage-error behavior, preferably Click/Typer convention `2`.

## Scope

### In Scope
- Unknown root command behavior for `agh <unknown>`.
- Unknown nested command behavior for `config`, `user`, `token`, `project`, `project member`, `project pack`, `pack`, and `agent` groups where applicable.
- Test updates for existing `exit_code == 0` unknown-command assertions plus nested group coverage.

### Out of Scope
- Changing valid command behavior or command-specific `--help` output.
- Redesigning CLI help text, command names, or argument parsing.
- Changing non-command validation failures beyond this unknown-command bug.

## Capabilities

### New Capabilities
- `cli-usage-errors`: Defines CLI usage-error behavior for unknown commands while preserving helpful usage output.

### Modified Capabilities
- None; no existing OpenSpec specs are present.

## Approach

Update custom Typer group unknown-command handling so invalid command tokens still display the current helpful AGH usage output but terminate with usage-error exit status `2`. Keep no-argument and explicit help paths successful. Apply the behavior consistently across root and nested command groups.

## Affected Areas

| Area | Impact | Description |
|------|--------|-------------|
| `agh/cli/main.py` | Modified | Adjust `AghHelpGroup` and `AghSubcommandGroup` unknown-command exits. |
| `tests/test_cli_login.py` | Modified | Change root/config unknown-command expectations from `0` to `2` while preserving usage output assertions. |
| `tests/test_cli_admin_commands.py` | Modified | Add/adjust unknown nested coverage for user/project/member groups. |
| `tests/test_cli_pack_commands.py` | Modified | Add/adjust pack and project pack unknown-command coverage if applicable. |
| `tests/test_agent_command.py` | Modified | Add agent unknown-command coverage if applicable. |

## Risks

| Risk | Likelihood | Mitigation |
|------|------------|------------|
| Accidentally changing explicit help/no-arg success paths | Medium | Keep regression assertions for `[]`, `--help`, group help, and command help. |
| Inconsistent nested group behavior | Medium | Cover root plus config/user/token/project/member/project pack/pack/agent groups. |
| Output moves from stdout to stderr unexpectedly | Low | Assert humans still see the expected helpful usage text. |

## Rollback Plan

Revert the group unknown-command exit handling and associated test expectation changes in this change only.

## Dependencies

- Existing Typer/Click behavior and pytest CLI tests.

## Success Criteria

- [ ] Unknown root commands exit `2` and still show helpful usage output.
- [ ] Unknown nested subcommands exit `2` for applicable command groups.
- [ ] No-argument invocation and explicit `--help` remain exit `0`.
- [ ] Updated CLI tests pass with `uv run pytest`.
