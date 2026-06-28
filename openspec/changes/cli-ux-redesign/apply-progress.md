# Apply Progress: CLI UX Redesign

Status: PR1 (Help / Root Infrastructure) complete. Ready for verify.

## Delivery

- Delivery strategy: ask-always with approved chained PRs
- Chain strategy: stacked-to-main

### Review surface accounting (corrected)

PR1 is an **SDD planning + help/root slice**. Its review footprint must be
split into two surfaces, because the untracked OpenSpec governance artifacts
travel with the change but are not runtime code:

| Surface | Files | Changed lines | vs 400 budget |
|---------|-------|---------------|---------------|
| Runtime code | `agh/cli/main.py` | 117 (78+ / 39-) | under |
| Tests | 4 modified test files + new `tests/test_cli_help_map.py` | 353 (320+ / 33-) | — |
| **Runtime + test subtotal** | | **470** | **slightly over** |
| OpenSpec planning artifacts | proposal, spec, design, tasks, apply-progress, exploration | 531 (additive docs) | n/a (governance) |
| **Full PR review footprint** | | **1,169** | **over** |

The earlier "369 changed lines, within budget" claim counted only runtime+test
at apply time and **undercounted** the OpenSpec artifacts. The full PR1 review
footprint (1,169 changed lines) **exceeds the 400-line budget** and must not be claimed
under-budget.

- The runtime code change (`agh/cli/main.py`, 117 lines) is small and within
  budget.
- Runtime + test (~470) drifts slightly over 400 only because this review-fix
  batch hardened the help-map tests (+~112 lines of assertions) as required by
  the 4R findings.
- The OpenSpec artifacts (~531 lines) are additive SDD governance/spec
  documentation with no runtime impact and low cognitive review risk.

### Size disposition

Accepted as `size:exception` for the SDD planning envelope, on a stacked-to-main
chain. Recommended split consideration if the reviewer wants the runtime+test
commit strictly under 400: land the OpenSpec planning artifacts as a separate
`docs(spec): cli-ux-redesign planning` commit ahead of the runtime+test commit,
so the runtime+test commit stays self-contained and the governance docs are
reviewed as the change spec rather than as runtime review load. Rollback stays
per-slice (revert the active PR only).

## TDD Cycle Evidence

| Task | Test File | Layer | Safety Net | RED | GREEN | TRIANGULATE | REFACTOR |
|------|-----------|-------|------------|-----|-------|-------------|----------|
| 1.1 | `tests/test_cli_help_map.py` (+ 4 updated files) | Unit (CliRunner) | 84/84 | 9 failing | 92 passing | 8 cases | n/a |
| 1.2 | `agh/cli/main.py` | Unit | 84/84 | 9 failing | 92 passing | covered by 1.1 | intrinsic |
| 1.3 | `agh/cli/main.py` | Unit | 84/84 | covered by 1.1 | 501/501 full | covered | `_show_local_help` helper + `group.get_help(ctx)` |
| review-fix | `tests/test_cli_help_map.py` | Unit (CliRunner) | 93/93 (5 files) | n/a (hardening) | 12/12 in file | 3 cases | exact-row parser + constants |

Test Summary:
- Total tests written: 12 (new `test_cli_help_map.py`: 9 original + 3 4R
  review-fix assertions)
- Total tests updated (approval-test changes for spec-driven behavior fix): 5
  across `test_cli_admin_commands.py`, `test_cli_package_commands.py`,
  `test_agent_command.py`, `test_cli_login.py`
- Layers used: Unit (CliRunner) 12
- Focused run (5 CLI test files): 93 passed, no regressions
- Validation: `ruff check` clean, `ruff format --check` clean

## Phase 1: Help / Root Infrastructure — DONE

- [x] 1.1 RED: tests for root map + --version, subgroup local help, unknown
  exit 2, and honest (no phantom alias) help.
- [x] 1.2 GREEN: rewired root map (`APP_HELP`) to a full command tree with
  nested subcommands and `--version`; subgroups render local help.
- [x] 1.3 REFACTOR: `_show_local_help(ctx)` helper + `group.get_help(ctx)` in
  `_exit_on_unknown_command` prevent root-help leakage into empty/nested
  groups; `config_app` moved from `AghHelpGroup` to `AghSubcommandGroup`.

## Files Changed (PR1)

| File | Action | What Was Done |
|------|--------|---------------|
| `agh/cli/main.py` | Modified | Rewrote `APP_HELP` (nested tree + `--version`); `_exit_on_unknown_command` now echoes `group.get_help(ctx)`; added `_show_local_help`; all callbacks use it; `config_app` → `AghSubcommandGroup`; group docstrings clarified. |
| `tests/test_cli_help_map.py` | Created | PR1 help-map, local-help, version, and unknown-command coverage. |
| `tests/test_cli_admin_commands.py` | Modified | Updated leakage tests to assert LOCAL group help on no-arg/unknown. |
| `tests/test_cli_package_commands.py` | Modified | Package/project-package unknown → LOCAL help. |
| `tests/test_agent_command.py` | Modified | Agent unknown → LOCAL help. |
| `tests/test_cli_login.py` | Modified | `config` no-arg/--help/unknown now LOCAL config help; root invocations still share root map. |

## Deviations / Scope Decisions

- **"Absent legacy names" is progressive, not fully done in PR1.** The
  orchestrator scope explicitly forbids renaming `agent`→`target`, `sync`→
  `link`, config/auth, resource verbs, package assignment, and skills in PR1.
  Those commands stay functional and therefore remain honestly listed in the
  root command map. PR1 interprets "absent legacy names" as: no phantom aliases
  are invented and no not-yet-implemented names (`target`/`link`/`whoami`/
  `logout`) are advertised. Legacy names are removed from the map in their own
  later slices as each command is rewired.
- **`*_REF` metavar naming** already exists for collection/project/user/
  package refs; full `*_REF` help/error alignment lives in slice 3
  (`*_refs.py`), out of PR1 scope.

## Review-Fix Batch (4R findings)

Addressed small confirmed review findings without touching runtime behavior or
later slices:

- **Root-map markers strengthened.** Replaced the weak `assert "member" in
  help_output` with a `_root_command_rows()` parser that pins exact top-level
  and nested rows (`test_root_map_pins_intended_current_command_rows`).
- **Phantom future names covered.** Added a negative test asserting `target`,
  `link`, `whoami`, `logout` are not advertised command rows
  (`test_root_help_does_not_advertise_not_yet_implemented_commands`). Checks
  parsed rows, so `sync`'s "Link this git repository..." prose cannot false-
  match `link`.
- **Nested leaf help wording.** Added `config show --help` and
  `project member add --help` assertions for "Show this help page." and the
  absence of "and exit" (`test_nested_leaf_help_uses_concise_wording`).
- **Review-surface accounting corrected** (see Delivery): runtime code 117
  lines, runtime+test ~470, full PR footprint 1,169 changed lines incl. OpenSpec artifacts;
  recorded as a size:exception SDD planning+PR1 slice with a split option.

## Follow-ups

- **Dynamic root-map parity / golden test.** PR1 pins the intended-current
  root map via exact-row parsing, which is the strongest practical pin within
  scope. A full golden snapshot of the entire `agh --help` output (including
  descriptions) is intentionally deferred: it would couple this slice to every
  later command rename (`agent`→`target`, `sync`→`link`, verb renames) and
  churn on every subsequent slice. Track a golden test once the command tree
  stabilizes in/after PR5.
- Move the `member` / nested-row assertions fully onto the parser once a golden
  harness exists.

## Remaining Phases

- [ ] Phase 2: Config / Auth / Target (PR2)
- [ ] Phase 3: User / Project / Collection vocabulary (PR3)
- [ ] Phase 4: Package assignment UX (PR4)
- [ ] Phase 5: Skill / Link / Pull cleanup (PR5)
- [ ] Phase 6: Docs / Changelog / Final validation (PR6)
