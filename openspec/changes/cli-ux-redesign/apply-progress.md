# Apply Progress: CLI UX Redesign

Status: PR1 (Help / Root Infrastructure), PR2a (Instance Config), PR2b
(Auth), PR2c (Target), and PR3 (User / Project / Collection Vocabulary)
complete. PR1/PR2 were previously verified; PR3 is verified and its Judgment
Day review findings are addressed in the "Judgment Day Fix Round (Phase 3 /
PR3)" section below (specifically: changelog fragment wording, verify-report
task counts and Towncrier evidence limitation, and regression coverage for
removed `user token reset`, deactivated project members, and empty-state
`project member list` output). Later phases (PR4 Package Assignment UX, PR5
Skill / Link / Pull, PR6 Docs / Changelog) remain pending on their own slices.

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

- [x] Phase 2: Config / Auth / Target — split into stacked slices:
  - [x] 2a instance config (PR2a)
  - [x] 2b auth (PR2b)
  - [x] 2c target (PR2c) — DONE (this branch)
- [x] Phase 3: User / Project / Collection vocabulary (PR3) — DONE (this branch)
- [ ] Phase 4: Package assignment UX (PR4)
- [ ] Phase 5: Skill / Link / Pull cleanup (PR5)
- [ ] Phase 6: Docs / Changelog / Final validation (PR6)

## Phase 2a: Instance Config (PR2a) — DONE

PR2 was originally planned as one slice. To respect the 400-line review budget
it is split into three stacked-to-main slices while PR1 is open:
PR2a (instance config) → PR2b (auth) → PR2c (target). Each branch stacks on the
previous slice branch until PR1 merges.

### What shipped (PR2a)

- **Instance-only config.** `agh config` shows only the configured instance
  URL ("Instance URL: …" / "Instance URL: not set"). `agh config set
  INSTANCE_URL` normalizes and stores the instance URL. `agh config clear`
  removes only the instance URL, preserving credentials. `config show` is
  removed; `config` no-args replaces it (exit 2 as unknown subgroup command).
- **Storage split.** `agh/cli/config.py` gains instance/credential-independent
  helpers (`load/save/clear_instance_url`, `InstanceUpdate`,
  `ConfigCorruptError`, `_read/_write_config_dict`, `_write_or_remove`,
  `_format_partial_config`) over the same flat TOML shape. `save_config` /
  `_format_config` are retained because `login` is unchanged in this slice.
- **Trust boundary (4R blocker carried into the slice).** `save_instance_url`
  drops stored email/token when the normalized instance differs (or when
  credentials are orphaned with no current instance); the same normalized
  instance preserves them. `config set` reports the clearance + login guidance.
- **Corrupt-config recovery (4R blocker).** `config`, `config set`, and
  `config clear` catch `ConfigCorruptError`, print the offending path +
  `config set` recovery guidance, exit non-zero with no traceback, and leave
  the corrupt file intact.
- **`login` is intentionally unchanged** in this slice (still takes `--url` and
  writes via `save_config`). It is rewritten in PR2b, so its tests are kept
  here and updated there.

### TDD Cycle Evidence

| Task | Test File | Layer | RED | GREEN | REFACTOR |
|------|-----------|-------|-----|-------|----------|
| 2a.1 | `tests/test_cli_login.py` (config tests) | Unit (CliRunner) | new failing | passing | `_set_instance` helper |
| 2a.2 | `agh/cli/config.py`, `agh/cli/main.py` | Unit | covered | 30 focused passing | dict read/write helpers |
| 2a.3 | `tests/test_cli_login.py` (trust boundary) | Unit | 3 failing | 3 passing | `InstanceUpdate` contract |
| 2a.4 | `tests/test_cli_login.py` (corrupt) | Unit | 2 failing | 2 passing | `ConfigCorruptError` + `_fail_corrupt_config` |

Test Summary:
- Focused run (`test_cli_login.py` + `test_cli_help_map.py`): 30 passed.
- Full suite: 508 passed, 1 skipped.
- Validation: `ruff check` clean, `ruff format --check` clean, `pyright` on
  touched files 0 errors, `git diff --check` clean.

### Files Changed (PR2a)

| File | Action | What Was Done |
|------|--------|---------------|
| `agh/cli/config.py` | Modified | Added instance split + corrupt handling: `_CONFIG_KEYS`, `INSTANCE_MISSING_MESSAGE`, `corrupt_config_recovery_message`, `ConfigCorruptError`, `InstanceUpdate`, `load/save/clear_instance_url`, `_read/_write_config_dict`, `_write_or_remove`, `_format_partial_config`. Kept `save_config`/`_format_config` for unchanged `login`. |
| `agh/cli/main.py` | Modified | `config` shows instance; added `config set`/`config clear`; removed `config show`; added `_fail_corrupt_config`; `config_app` help updated; `APP_HELP` config block + config-first ordering. |
| `tests/test_cli_login.py` | Modified | Added config/trust-boundary/corrupt tests + `_set_instance`/`_write_corrupt_config`; removed `config show` tests; kept unchanged `login` tests. |
| `tests/test_cli_help_map.py` | Modified | Root map pins updated to PR2a tree (`config set`/`config clear`; config-first order; removed config local-help no-args case; `config set --help` leaf check). |
| `openspec/changes/cli-ux-redesign/tasks.md` | Modified | Phase 2 restructured into 2a/2b/2c sub-tasks; 2a marked done. |

### Review surface accounting

| Surface | Files | Changed lines | vs 400 budget |
|---------|-------|---------------|---------------|
| Runtime code | `agh/cli/config.py`, `agh/cli/main.py` | 217 (200+ / 17−) | under |
| Tests | `test_cli_login.py`, `test_cli_help_map.py` | 356 (284+ / 72−) | over alone |
| OpenSpec governance | `tasks.md`, `apply-progress.md` | 129 (125+ / 4−) | n/a (governance) |
| **Full PR2a slice total** | | **702 (609+ / 93−)** | **over** |

### Size disposition

`size:exception` required. The full PR2a slice is **702 changed lines** vs its
parent (`feat/cli-ux-help-root`), exceeding the 400-line budget. Splitting
Phase 2 into config/auth/target reduced each slice's conceptual scope, but
mandatory config, trust-boundary, and corrupt-config coverage plus the additive
OpenSpec governance artifacts keep this slice over 400. Runtime code alone
stays within budget; the overage is tests plus governance docs, not logic
complexity. Rollback stays per-slice (revert this PR only).

### Out of scope (deferred)

- `login`/`whoami`/`logout` behavior (PR2b).
- `agent` → `target` rename and `agh pull` message (PR2c).
- README/changelog (PR6).

## Phase 2b: Auth (PR2b) — DONE

Stacked on PR2a. The auth commands now use the instance/credential split.

### What shipped (PR2b)

- **`login` rewritten.** Takes `--email`/`--token` (or prompts interactively)
  and authenticates against the configured instance via `load_instance_url`.
  It never prompts for a URL and fails with `agh config set INSTANCE_URL`
  guidance before any prompt when no instance is configured. Credentials are
  persisted with `save_credentials` (instance preserved); on validation
  failure existing credentials are left untouched.
- **`whoami` / `logout`.** `whoami` shows the authenticated user via
  `GET /me`; `logout` clears only credentials (instance preserved) and is a
  no-op when none are stored.
- **Judgment Day fix (confirmed).** `load_config` now raises
  `ConfigCorruptError` (carrying the path) on invalid TOML, and `_api_request`
  catches it → `_fail_corrupt_config`, so `whoami` and every API-backed command
  surface recovery guidance ("Fix or remove … run: agh config set
  INSTANCE_URL") instead of a raw error/traceback. The corrupt file is left
  intact. (`logout` already recovered via `clear_credentials`.)
- **Judgment Day Round 1 fix (extended recovery).** The same corrupt-config
  recovery was missing from `login`, `sync`, and linked `pull`: each surfaced
  raw invalid-config text instead of the shared guidance. `login` now catches
  `ConfigCorruptError` before prompting (fails before any credential prompt);
  `sync`/`pull` let `ConfigCorruptError` propagate from `_load_config_or_error`
  and route it through `_fail_corrupt_config`. Regression tests cover corrupt
  config on `login`, `sync`, and linked `pull --dry-run`.
- **Dead code removed.** `save_config`/`_format_config` (no callers after the
  login rewrite) dropped from `config.py`. `AghConfig`/`normalize_instance_url`
  stay (used by `load_config`/`save_instance_url`, workspace pull/sync, tests).

### TDD Cycle Evidence

| Task | Test File | Layer | RED | GREEN | REFACTOR |
|------|-----------|-------|-----|-------|----------|
| 2b.1 | `tests/test_cli_login.py` (login/whoami/logout) | Unit + local HTTP | login tests rewritten | passing | instance-check-before-prompt |
| 2b.2 | `agh/cli/config.py`, `agh/cli/main.py` | Unit | covered | 39 focused passing | save/clear_credentials |
| 2b.3 | `tests/test_cli_login.py` (corrupt) | Unit | whoami/logout corrupt failing | passing | `load_config`→`ConfigCorruptError` |

Test Summary:
- Focused run (`test_cli_login.py` + `test_cli_help_map.py` +
  `test_workspace_sync.py` + `test_cli_pull.py`): 85 passed.
- Validation: `ruff check` clean, `ruff format --check` clean, `pyright` on
  touched files 0 errors, `git diff --check` clean.

### Files Changed (PR2b)

| File | Action | What Was Done |
|------|--------|---------------|
| `agh/cli/config.py` | Modified | `load_config` raises `ConfigCorruptError` on bad TOML; added `save_credentials`/`clear_credentials`; removed dead `save_config`/`_format_config`. |
| `agh/cli/main.py` | Modified | Rewrote `login` (no `--url`); added `whoami`, `logout`; `_api_request` surfaces corrupt-config recovery; `login`/`sync`/`pull` route corrupt config to `_fail_corrupt_config`; APP_HELP adds whoami/logout; imports trimmed. |
| `agh/cli/workspace_sync.py` | Modified | `_load_config_or_error` lets `ConfigCorruptError` propagate for recovery guidance. |
| `agh/cli/workspace_pull.py` | Modified | `_load_config_or_error` lets `ConfigCorruptError` propagate for recovery guidance. |
| `tests/test_cli_login.py` | Modified | Rewrote login tests; added whoami/logout, trust-boundary-whoami, logout-corrupt, whoami-corrupt, and login-corrupt (JD fix) tests + login-help test. |
| `tests/test_cli_help_map.py` | Modified | Root map adds whoami/logout; `NOT_YET_IMPLEMENTED_COMMANDS` reduced to [target, link]. |
| `tests/test_workspace_sync.py` | Modified | Added sync corrupt-config recovery regression test. |
| `tests/test_cli_pull.py` | Modified | Added linked `pull --dry-run` corrupt-config recovery regression test. |
| `openspec/changes/cli-ux-redesign/tasks.md` | Modified | 2b sub-tasks marked done; corrupt-config recovery scope extended to login/sync/pull. |

### Review surface accounting

| Surface | Files | Changed lines | vs 400 budget |
|---------|-------|---------------|---------------|
| Runtime code | `agh/cli/config.py`, `agh/cli/main.py`, `agh/cli/workspace_sync.py`, `agh/cli/workspace_pull.py` | 145 (84+ / 61−) | under |
| Tests | `test_cli_login.py`, `test_cli_help_map.py`, `test_workspace_sync.py`, `test_cli_pull.py` | 496 (370+ / 126−) | over alone |
| OpenSpec governance | `tasks.md`, `apply-progress.md` | 99 (93+ / 6−) | n/a (governance) |
| **Full PR2b slice total** | | **740 (547+ / 193−)** | **over** |

### Size disposition

`size:exception` required. The full PR2b slice is **740 changed lines** vs its
parent (`feat/cli-ux-config-instance`), exceeding the 400-line budget (it was
611 before the Judgment Day Round 1 corrupt-config extension added runtime
recovery + 3 regression tests). Splitting Phase 2 into config/auth/target
reduced each slice's conceptual scope, but the login rewrite, whoami/logout,
trust-boundary, and corrupt-config coverage plus the additive OpenSpec
governance artifacts keep this slice over 400. Runtime code alone stays within
budget; the overage is tests plus governance docs, not logic complexity.

### Out of scope (deferred)

- README/changelog (PR6).

## Phase 2c: Target (PR2c) — DONE

Stacked on PR2b. The public local selection UX is now `target`.

### What shipped (PR2c)

- **`agent` removed as public command.** The root command map advertises
  `target`; `agh agent` exits 2 as an unknown command and is not retained as a
  hidden alias.
- **Workspace target UX.** `agh target`, `agh target set TARGET`, and
  `agh target clear` manage `.agh-cache/preferences.toml` while reusing the
  existing `[agents] target` state shape.
- **Global target UX.** `agh target --global`, `agh target set TARGET --global`,
  and `agh target clear --global` manage the existing global-skill defaults
  file without changing its path or TOML keys.
- **Pull guidance aligned.** Missing-target guidance now tells users to run
  `agh target set claude` or `agh target set opencode`; dead
  `format_agent_preference` was removed.

### TDD Cycle Evidence

| Task | Test File | Layer | RED | GREEN | REFACTOR |
|------|-----------|-------|-----|-------|----------|
| 2c.1 | `tests/test_target_command.py`, `tests/test_cli_help_map.py` | Unit (CliRunner) | target/root-map tests fail before command rename | passing | row parser retained |
| 2c.2 | `agh/cli/main.py` | Unit | covered by 2c.1 | passing | target show helper split |
| 2c.3 | `tests/test_cli_pull.py` | Unit (CliRunner) | pull guidance expected removed `agent select` | passing | shared guidance string updated |

Test Summary:
- Focused run (`tests/test_target_command.py`, `tests/test_cli_pull.py`,
  `tests/test_cli_help_map.py`, `tests/test_integration_smoke.py`): 63 passed.
- Full suite: 528 passed, 1 skipped.
- Validation: `git diff --check` clean; `ruff check` clean;
  `ruff format --check` clean; `pyright agh tests` 0 errors.

### Files Changed (PR2c)

| File | Action | What Was Done |
|------|--------|---------------|
| `agh/cli/main.py` | Modified | Replaced public `agent` command with `target`; added workspace/global target show, set, and clear behavior; updated APP_HELP. |
| `agh/cli/agent_integrations.py` | Modified | Removed dead `format_agent_preference` helper. |
| `agh/cli/workspace_pull.py` | Modified | Updated missing-target guidance and prompt/error wording to `target`. |
| `tests/test_agent_command.py` | Deleted | Replaced legacy public `agent` command tests. |
| `tests/test_target_command.py` | Created | Covers target help, workspace/global set/show/clear, removal of `agent`, and detection behavior. |
| `tests/test_cli_help_map.py` | Modified | Root-map pins updated from PR2b `agent` to PR2c `target`; `link` remains not-yet-implemented. |
| `tests/test_cli_pull.py` | Modified | Missing-target guidance now asserts `agh target set ...`. |
| `tests/test_integration_smoke.py` | Modified | Smoke flow uses `agh target set opencode` before pull. |
| `openspec/changes/cli-ux-redesign/tasks.md` | Modified | PR2c sub-tasks marked done. |
| `openspec/changes/cli-ux-redesign/apply-progress.md` | Modified | Recorded PR2c implementation progress, validation evidence, and Judgment Day fixes. |

### Review surface accounting

| Surface | Files | Changed lines | vs 400 budget |
|---------|-------|---------------|---------------|
| Runtime code | `agh/cli/agent_integrations.py`, `agh/cli/main.py`, `agh/cli/workspace_pull.py` | 158 (104+ / 54−) | under |
| Tests | `test_agent_command.py`, `test_target_command.py`, `test_cli_help_map.py`, `test_cli_pull.py`, `test_integration_smoke.py` | 393 (260+ / 133−) | over alone |
| OpenSpec governance | `tasks.md`, `apply-progress.md` | 88 (80+ / 8−) | n/a (governance) |
| **Full PR2c slice total** | | **639 (444+ / 195−)** | **over** |

### Size disposition

`size:exception` required. The full PR2c slice is **639 changed lines** vs its
parent (`feat/cli-ux-auth`), exceeding the 400-line budget. Splitting Phase 2
into config/auth/target reduced each slice's conceptual scope, but the
`agent`→`target` rename, workspace/global target UX, pull-guidance alignment,
and the replacement test suite plus additive OpenSpec governance artifacts
keep this slice over 400. Runtime code alone stays within budget; the overage
is tests plus governance docs, not logic complexity.

### Out of scope (deferred)

- README/changelog (PR6).

## Phase 3: User / Project / Collection Vocabulary (PR3) — DONE

Stacked-to-main slice on current `main` after PR1/PR2 and the changelog skill
guidance slice were squash-merged. The public resource vocabulary now matches
the SDD command contract for user, project, and collection resources.

### What shipped (PR3)

- **Resource verbs renamed.** `user`, `project`, and `collection` now expose
  `list/create/describe/update/activate/deactivate`; legacy `show`, `get`, and
  `delete` forms are not registered as aliases.
- **Token rotation nested under users.** Removed the public top-level `token`
  group and exposed rotation as `agh user token rotate USER_REF`; legacy token
  reset remains unsupported in the new public contract.
- **Project member list.** Added `agh project member list PROJECT_REF`, backed by
  `GET /api/v1/projects/{project_id}/members`, with admin-only route access and
  human CLI table output.
- **Project URL flag aligned.** Project create/update now use `--git-url` while
  still sending `repo_url` to the existing API payload.
- **Reference wording aligned.** User, project, and collection reference help and
  resolver errors use `USER_REF`, `PROJECT_REF`, and `COLLECTION_REF` wording.

### TDD Cycle Evidence

| Task | Test File | Layer | RED | GREEN | TRIANGULATE | REFACTOR |
|------|-----------|-------|-----|-------|-------------|----------|
| 3.1 | `tests/test_cli_admin_commands.py`, `tests/test_cli_help_map.py`, `tests/test_project_routes.py` | Unit/API via CliRunner + TestClient | 26 failing after RED tests | 48 focused passing | resource verbs, nested token, project member list, legacy unsupported cases | n/a |
| 3.2 | `agh/cli/main.py`, `agh/server/routes/projects.py` | Unit/API via CliRunner + TestClient | covered by 3.1 | 48 focused passing | activation/deactivation, describe, member list, route auth | command wiring kept in Typer groups |
| 3.3 | `agh/cli/user_refs.py`, `agh/cli/project_refs.py`, `agh/cli/collection_refs.py` | Unit (CliRunner) | USER_REF/COLLECTION_REF expectations fail before wording change | 48 focused passing | help metavar + resolver error assertions | constants and resolver messages aligned |

Test Summary:
- Safety net before RED: `uv run pytest tests/test_cli_admin_commands.py tests/test_cli_help_map.py tests/test_project_routes.py -q` → 46 passed.
- RED run: same focused command → 26 failed, 22 passed after tests were updated before production changes.
- Focused GREEN: same focused command → 48 passed.
- Full suite: `uv run pytest -q` → 535 passed.
- Quality gates: `ruff check` clean; `ruff format --check` clean after formatting; `pyright agh tests` 0 errors; `uv run towncrier check` printed `On origin/main branch, or no diffs, so no newsfragment required.` because the PR3 worktree has no committed diffs and the fragment is untracked — this is a limited local check, not authoritative branch CI evidence.

### Files Changed (PR3)

| File | Action | What Was Done |
|------|--------|---------------|
| `agh/cli/main.py` | Modified | Rewired resource verbs; nested user token rotation; removed top-level token registration; added project member list; switched project URL option to `--git-url`; updated APP_HELP. |
| `agh/server/routes/projects.py` | Modified | Added admin-only `GET /projects/{project_id}/members` route. |
| `agh/cli/user_refs.py` | Modified | Aligned user resolver errors with `USER_REF`. |
| `agh/cli/project_refs.py` | Modified | Aligned project resolver errors with `PROJECT_REF`. |
| `agh/cli/collection_refs.py` | Modified | Aligned collection resolver errors with `COLLECTION_REF`. |
| `tests/test_cli_admin_commands.py` | Modified | RED/GREEN coverage for resource verbs, nested token rotate, project member list, refs, and human output. |
| `tests/test_cli_help_map.py` | Modified | Root-map/resource-help pins and legacy resource command absence. |
| `tests/test_project_routes.py` | Modified | API coverage for project member list and admin-only access. |
| `changelog.d/+cli-resource-vocabulary.breaking.md` | Created | Towncrier breaking fragment for user-facing CLI vocabulary changes. |
| `openspec/changes/cli-ux-redesign/tasks.md` | Modified | Marked Phase 3 tasks complete. |
| `openspec/changes/cli-ux-redesign/apply-progress.md` | Modified | Recorded this PR3 progress and validation evidence. |

### Review surface accounting (corrected)

| Surface | Files | Changed lines | vs 800 budget |
|---------|-------|---------------|---------------|
| Runtime code | `agh/cli/main.py`, `agh/server/routes/projects.py`, `agh/cli/*_refs.py` | 217 (152+ / 65−) | under |
| Tests | `test_cli_admin_commands.py`, `test_cli_help_map.py`, `test_project_routes.py` | 337 (248+ / 89−) | over 400 alone |
| OpenSpec governance + changelog | `tasks.md`, `apply-progress.md`, `verify-report.md`, `changelog.d/+cli-resource-vocabulary.breaking.md` | 394 (278+ / 116−, incl. 1 untracked fragment line) | n/a (docs/fragment) |
| **Runtime + test subtotal** | | **554 (400+ / 154−)** | **under 800** |
| **Full PR3 review footprint (tracked + untracked fragment)** | | **~948 (678+ / 270−)** | **over 800** |

### Size disposition

The runtime + test subtotal (~554 changed lines) is the smallest reviewable
surface and would be under an 800-line ceiling, but that ceiling did not
account for the OpenSpec governance artifacts and the Towncrier fragment.
The **full PR3 review footprint is ~948 changed lines** (947 tracked plus the
one-line untracked `changelog.d/+cli-resource-vocabulary.breaking.md` fragment),
which **exceeds the user-approved 800-line budget**.

The prior "within the user-approved 800-line review budget" claim in this
artifact was therefore misleading: it counted only runtime + tests and treated
the governance docs/fragment as outside the budget. For a real PR reviewer the
whole diff matters, so this corrected accounting records PR3 as a
`size:exception` slice for the full review surface. Runtime code remains the
smallest part of the diff; most of the footprint is behavior tests and additive
SDD governance documentation.

### Out of scope (deferred)

- Phase 4 package assignment UX.
- Phase 5 skill/link/pull cleanup.
- Phase 6 README/README.es final migration prose beyond the required per-slice
  Towncrier fragment.

## Judgment Day Fix Round (Phase 3 / PR3)

Addressed confirmed Phase 3 review findings on top of the completed slice. No
runtime behavior change; docs, changelog wording, and test coverage only.

### What shipped

- **Changelog fragment made explicit.** `changelog.d/+cli-resource-vocabulary.breaking.md`
  now states that the legacy `token reset` command was removed and that the
  project create/update option was renamed `--repo-url` -> `--git-url`, in
  addition to the resource verbs, nested token rotation, and member listing.
- **Verify-report counts corrected.** `verify-report.md` now reports 25 total
  tasks, 16 completed through Phase 3, and 9 remaining archive blockers in
  Phases 4-6 (was 22 / 16/22 / 6).
- **Verify-report tooling honesty.** Added a Towncrier evidence limitation note:
  because the PR3 worktree has no committed diffs and the fragment is untracked,
  `towncrier check` only reports `On origin/main branch, or no diffs, so no
  newsfragment required.` Branch CI after commit is the authority that validates
  the fragment against the real diff.
- **Regression coverage for removed `user token reset`.** Added
  `["user", "token", "reset", "usr_2"]` to
  `test_legacy_resource_commands_are_not_supported` so the removed legacy token
  reset CLI path is pinned as exit-2 unsupported.
- **Coverage for deactivated project members.** New
  `test_deactivated_member_user_still_listed_with_inactive_status` in
  `tests/test_project_routes.py` verifies that a member whose user account is
  deactivated still appears in `GET /projects/{id}/members` with `active: false`
  (the membership row is retained; the listing reflects the user status).
- **CLI empty-state coverage for `project member list`.** Extended
  `test_cli_read_commands_show_empty_messages` to assert the
  `No project members found.` empty-state output.

### TDD note

Fixes 4-6 add regression/coverage tests for ALREADY-SHIPPED green behavior
(legacy command removal, deactivated-member listing, empty-state message). They
pass immediately because the production code already implements the behavior;
they cannot be meaningfully RED without breaking already-merged code. This is
coverage hardening, not new-feature TDD, and is recorded honestly as such.

### Validation

- Focused: `/tmp/opencode/uvpkg/bin/uv run pytest tests/test_cli_help_map.py tests/test_cli_admin_commands.py tests/test_project_routes.py -q` -> 49 passed.
- Full suite: `/tmp/opencode/uvpkg/bin/uv run pytest -q` -> 536 passed.
- `ruff check .` clean; `ruff format --check .` clean (67 files); `pyright agh tests` 0 errors; `git diff --check` clean.
- `uv` is absent from PATH in this shell; all commands used `/tmp/opencode/uvpkg/bin/uv` (`uv 0.11.25`).

### Files Changed (Judgment Day fix round)

| File | Action | What Was Done |
|------|--------|---------------|
| `changelog.d/+cli-resource-vocabulary.breaking.md` | Modified | Added explicit `token reset` removal and `--repo-url` -> `--git-url` rename. |
| `openspec/changes/cli-ux-redesign/verify-report.md` | Modified | Corrected task counts (25/16/9); added Towncrier evidence limitation note. |
| `tests/test_cli_help_map.py` | Modified | Added `user token reset` to legacy-unsupported regression cases. |
| `tests/test_cli_admin_commands.py` | Modified | Added `project member list` empty-state coverage. |
| `tests/test_project_routes.py` | Modified | Added deactivated-member-still-listed-with-inactive-status route test. |
| `openspec/changes/cli-ux-redesign/apply-progress.md` | Modified | Recorded this Judgment Day fix round. |

## PR3-Only Worktree Cleanup

This worktree was prepared as the clean PR3 slice for the stacked-to-main chain.
The source reference tree contained combined PR3+PR4 uncommitted changes; this
slice keeps only the PR3 surface:

- Retained pre-PR4 `project package` / `collection package` subgroups in `agh/cli/main.py`.
- Retained legacy `collection package` test coverage in `tests/test_cli_admin_commands.py`.
- Retained pre-PR4 package help text (`Create, publish, and list guidance packages.`) in `tests/test_cli_help_map.py`.
- Excluded PR4-only files (`tests/test_cli_package_assignment.py`, `changelog.d/+cli-package-assignment.breaking.md`).
- Refreshed `verify-report.md` to describe PR3 only and removed PR4 verification content.

### Validation (this batch)

- Focused: `/tmp/opencode/uvpkg/bin/uv run pytest tests/test_cli_admin_commands.py tests/test_cli_help_map.py tests/test_project_routes.py -q` -> 49 passed.
- `/tmp/opencode/uvpkg/bin/uv run --with ruff ruff check .` -> All checks passed.
- `/tmp/opencode/uvpkg/bin/uv run --with ruff ruff format --check .` -> 67 files already formatted.
- `/tmp/opencode/uvpkg/bin/uv run --with pyright pyright agh tests` -> 0 errors, 0 warnings, 0 informations.
- `git diff --check` -> clean.
