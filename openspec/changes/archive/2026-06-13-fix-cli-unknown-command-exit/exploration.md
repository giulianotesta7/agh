## Exploration: fix-cli-unknown-command-exit

### Current State
`agh/cli/main.py` overrides Typer/Click command resolution in `AghHelpGroup` and `AghSubcommandGroup`. When the first token is not a known command and does not start with `-`, both groups print `APP_HELP` and raise `typer.Exit(0)`, so invalid commands like `agh wrong-command` and `agh config wrong-command` exit successfully instead of failing as usage errors.

### Affected Areas
- `agh/cli/main.py` — custom `resolve_command()` behavior currently converts unknown commands into successful help output for the root app, `config`, `user`, `token`, `project`, `pack`, and `agent` groups.
- `tests/test_cli_login.py` — currently asserts unknown root and `config` commands exit `0`; this test must change to the new failure contract.
- `tests/test_cli_admin_commands.py` — already covers group-help behavior for `user` and `project`; likely needs added assertions for unknown nested subcommands such as `project member wrong`.
- Potentially other CLI tests (`tests/test_cli_pack_commands.py`, `tests/test_agent_command.py`) if they already encode the same success-on-invalid assumption.

### Approaches
1. **Restore standard Click/Typer usage errors** — unknown commands should fall through to Click’s normal invalid-command handling, which exits non-zero (Click conventionally `2`) and prints usage/error output.
   - Pros: matches standard CLI expectations; one clear behavior across all command groups; fixes the bug at the router layer.
   - Cons: changes current “help-on-typo” UX; may require updating several tests.
   - Effort: Low

2. **Keep help output but exit non-zero** — continue printing `APP_HELP` for unknown commands, but raise `typer.Exit(2)` or a usage-style exception.
   - Pros: preserves the current broad help-first UX while fixing the exit-status bug.
   - Cons: still masks the real error type; less aligned with Click’s built-in invalid-command behavior; harder to distinguish intentional help from usage error.
   - Effort: Low

### Recommendation
Prefer **Approach 1**: let invalid commands behave like standard Click/Typer usage errors. The current custom `resolve_command()` shortcuts are the root cause, and the repo already treats `--help` / empty invocations separately.

### Risks
- Tests may rely on the current help text being emitted for invalid commands; those assertions will need to be updated carefully.
- Nested groups (`project member ...`, `project pack ...`) need explicit coverage so the fix does not only address top-level unknown commands.

### Ready for Proposal
Yes — the current behavior is confirmed, the affected test surface is narrow, and the next step is a small proposal/spec update focused only on CLI invalid-command exit codes.
