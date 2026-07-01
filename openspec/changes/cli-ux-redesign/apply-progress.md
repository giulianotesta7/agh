# Apply Progress: CLI UX Redesign

Status: PR1 (Help / Root Infrastructure), PR2a (Instance Config), PR2b
(Auth), PR2c (Target), PR3 (User / Project / Collection Vocabulary), and
PR4 (Package Assignment UX) complete. PR1/PR2 were previously verified; PR3
is verified and Judgment-Day approved; PR4 is ready for verify.

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
- [x] Phase 3: User / Project / Collection vocabulary (PR3) — DONE (this batch)
- [x] Phase 4: Package assignment UX (PR4) — DONE (this batch)
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
- Quality gates: `ruff check` clean; `ruff format --check` clean after formatting; `pyright agh tests` 0 errors; `uv run towncrier check` passed.

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

### Review surface accounting

| Surface | Files | Changed lines | vs 800 budget |
|---------|-------|---------------|---------------|
| Runtime code | `agh/cli/main.py`, `agh/server/routes/projects.py`, `agh/cli/*_refs.py` | 217 (152+ / 65−) | under |
| Tests | `test_cli_admin_commands.py`, `test_cli_help_map.py`, `test_project_routes.py` | 333 (245+ / 88−) | under |
| Changelog + OpenSpec governance | Towncrier fragment, `tasks.md`, `apply-progress.md` | additive docs | n/a (governance) |
| **Runtime + test subtotal** | | **550 (397+ / 153−)** | **under 800** |

### Size disposition

Within the user-approved 800-line review budget. This slice is over AGH's older
400-line default but remains focused on one behavior boundary: resource
vocabulary and project member listing. Runtime code stays small; most footprint
is behavior tests.

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
  the untracked orphan fragment on the `main` working tree makes
  `towncrier check` trivially pass, so branch CI is the authority that validates
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

## Phase 4: Package Assignment UX (PR4) — DONE

Stacked-to-main slice. Package assignment is now expressed under `package`
with mutually exclusive `--project`/`--collection` target flags; the nested
`project package` / `collection package` subgroups and the `--position`
option are removed (breaking).

### Provenance and honest TDD note

A prior session had already authored the Phase 4 RED test file
(`tests/test_cli_package_assignment.py`) and implemented the matching GREEN
runtime code in `agh/cli/main.py` (the new `package assign/activate/
deactivate/unassign/list/describe` wiring and helpers), including the removal
of the `collection_package_app` / `project_package_app` subgroups. That work
was present in the uncommitted working tree but was **not finalized**: the
Phase 4 task checkboxes were unchecked, the 5 legacy `collection package`
tests in `tests/test_cli_admin_commands.py` were left **failing** (they still
exercised the removed nested subgroup with `--position`), no Phase 4 progress
or changelog fragment existed, and `agh/cli/main.py` was not ruff-formatted.

This batch finalized that slice honestly:

- Verified the existing Phase 4 tests pass (RED could not be re-demonstrated
  without reverting already-green implementation, so it is recorded as
  coverage hardening of existing green behavior, not freshly faked RED).
- Resolved the genuine RED in the suite: removed the 5 legacy `collection
  package` tests that described the removed breaking behavior.
- Hardened the breaking-removal coverage by extending the legacy-unsupported
  parametrize to the `update`/`remove` forms.
- Formatted the runtime + test files and recorded the slice artifacts.

### What shipped (PR4)

- **Package assignment under `package`.** `package assign|activate|deactivate|
  unassign PACKAGE_REF (--project PROJECT_REF | --collection COLLECTION_REF)`
  with exactly one target flag; both or neither exits 2 with shared guidance
  (`package assignment requires exactly one of --project or --collection`).
- **No positional target / no `--position`.** The target is chosen by flag
  only; assignment ids stay internal and are looked up by package identity
  (domain + name) for activate/deactivate/unassign.
- **Scoped `package list`.** `package list [--project | --collection]` renders
  one assignment table (`PACKAGE_REF / RESOLVED / STATUS`); bare
  `package list` still lists published packages.
- **`@latest` SemVer resolution.** `package describe PACKAGE_REF@latest`
  resolves to the highest SemVer version (SemVer-aware, not string sort:
  `1.10.0` beats `1.2.0`).
- **Assignment errors name the target.** When a package is not assigned,
  activate/deactivate/unassign fail naming the package ref, the scope, the
  scope id, and suggest `agh package list --<scope> <id>`.
- **Breaking removal.** Nested `project package` and `collection package`
  subgroups (list/add/update/remove) and `--position` are gone and exit 2.

### TDD Cycle Evidence

| Task | Test File | Layer | RED | GREEN | TRIANGULATE | REFACTOR |
|------|-----------|-------|-----|-------|-------------|----------|
| 4.1 | `tests/test_cli_package_assignment.py` | Unit (CliRunner) | prior-session RED (tests authored before impl) | 26 passing | exclusive flags x4 verbs, scoped list, `@latest` SemVer, legacy removal (list/add/update/remove), help metavars | n/a |
| 4.2 | `agh/cli/main.py` | Unit | covered by 4.1 | 26 passing | assign to project + collection, activate/deactivate/unassign lookup, describe latest/exact/unknown | `_resolve_package_assignment_target`, `_find_package_assignment_id`, `_find_describe_package` (was `_resolve_describe_package_ref`; collapsed to single-fetch in review-fix round), `_semver_sort_key` |
| 4.3 | `tests/test_cli_package_assignment.py` | Unit | covered by 4.1 (`test_package_activate_names_package_ref_and_target_when_unassigned`) | passing | error names package ref + scope + id + list suggestion | `_find_package_assignment_id` failure message |
| finalize | `tests/test_cli_admin_commands.py` | Unit | 5 legacy `collection package` tests failing (removed behavior) | removed; 0 failures | n/a | n/a |
| harden | `tests/test_cli_package_assignment.py` | Unit | n/a (coverage hardening of already-green breaking removal) | passing | extended legacy-unsupported parametrize to update/remove | n/a |

Test Summary:
- Phase 4 focused run (`test_cli_package_assignment.py` +
  `test_cli_package_commands.py`): 46 passed.
- Package + admin + help focused run
  (`test_cli_package_assignment.py`, `test_cli_admin_commands.py`,
  `test_cli_package_commands.py`, `test_cli_help_map.py`): 84 passed.
- Full suite: `/tmp/opencode/uvpkg/bin/uv run pytest -q` -> 541 passed in 100.76s.
- Validation: `ruff check` clean; `ruff format --check` clean (68 files);
  `pyright agh tests` 0 errors; `git diff --check` clean.
- `uv` is absent from PATH in this shell; all commands used
  `/tmp/opencode/uvpkg/bin/uv` (`uv 0.11.25`).

### Files Changed (PR4)

| File | Action | What Was Done |
|------|--------|---------------|
| `agh/cli/main.py` | Modified (prior session, finalized) | Added `package assign/activate/deactivate/unassign` with mutually exclusive target flags, scoped `package list`, `@latest` describe resolution; removed `collection_package_app`/`project_package_app` and `--position`; ruff-formatted. |
| `tests/test_cli_package_assignment.py` | Created (prior session) / hardened (this batch) | Phase 4 RED/GREEN coverage for exclusive flags, verbs, scoped list, `@latest` SemVer, legacy removal, help metavars, and target-naming errors. Extended legacy-unsupported parametrize to update/remove; ruff-formatted. |
| `tests/test_cli_admin_commands.py` | Modified | Removed 5 legacy `collection package` tests that described the removed nested subgroup (`--position`, positional targets). |
| `changelog.d/+cli-package-assignment.breaking.md` | Created | Towncrier breaking fragment for the package-assignment UX redesign. |
| `openspec/changes/cli-ux-redesign/tasks.md` | Modified | Phase 4 tasks marked complete. |
| `openspec/changes/cli-ux-redesign/apply-progress.md` | Modified | Recorded this PR4 progress and validation evidence. |

### Review surface accounting

| Surface | Files | Changed lines | vs 800 budget |
|---------|-------|---------------|---------------|
| Runtime code | `agh/cli/main.py` (Phase 4 portion only) | additive to the shared working-tree diff | under |
| Tests | `tests/test_cli_package_assignment.py` (created), `tests/test_cli_admin_commands.py` (removed 5 tests) | net additive tests; ~26 new + 5 removed | under |
| Changelog + OpenSpec governance | Towncrier fragment, `tasks.md`, `apply-progress.md` | additive docs | n/a (governance) |

The Phase 4 runtime + test surface stays focused on one behavior boundary
(package assignment UX). Note: the working tree also carries the previously
verified-but-uncommitted PR3 changes, so the raw `git diff --stat` against
`main` mixes PR3 + PR4; the Phase 4 review slice itself is the package
assignment behavior boundary documented here.

### Size disposition

Within the user-approved 800-line review budget for the Phase 4 slice. This
slice is over AGH's older 400-line default but stays focused on the package
assignment behavior boundary. Runtime code is small; most footprint is the
new behavior test file. Rollback stays per-slice (revert this PR only).

### Out of scope (deferred)

- Phase 5 skill/link/pull cleanup.
- Phase 6 README/README.es final migration prose and final full validation.
- `package_refs.py` messages were reviewed and left unchanged: its errors are
  version-resolution messages (canonical ref resolution), not assignment
  target messages, so no `*_REF` wording change was required for this slice.

## Phase 4 Review-Fix Round (4R findings)

Addressed the remaining real Phase 4 4R findings on top of the completed slice.
No user-visible behavior change other than the removed redundant network
round-trip; one genuine RED/GREEN cycle plus one coverage-hardening test.

### What shipped

- **Removed redundant `GET /packages` in `package describe @latest`.** Replaced
  `_resolve_describe_package_ref` (returned a canonical ref string, fetched
  `/packages`) and the second `/packages` lookup in `package_describe` with a
  single `_find_describe_package` helper that resolves `@latest`/exact/unknown
  and returns the package record in one fetch. SemVer-aware `@latest`
  resolution, exact-version describe, and the `package ... not found` failure
  message are preserved.
- **Public ref-resolution contract coverage through `package assign`.** Added
  `test_package_assign_resolves_exact_project_name_through_real_resolver`,
  which exercises the real `/projects/by-name/{name}` resolver end-to-end
  through `package assign --project` (no `_resolve_project_ref` monkeypatch).

### TDD note

- **Genuine RED/GREEN cycle for the round-trip removal.**
  `test_package_describe_latest_fetches_packages_once` was written first and
  failed RED on the pre-fix code (`assert 2 == 1`, two `GET /packages` calls
  recorded for `package describe @latest`), then passed GREEN after the
  single-fetch refactor. The observable contract is the network round-trip
  count, which is user-visible (latency/server load).
- **Coverage hardening (not RED/GREEN)** for the ref-resolution test: it passes
  on the pre-fix code as well, because `package assign` already preserved
  public project-ref resolution. Recorded honestly as a public-contract gap
  closure, not a freshly-fixed bug.

### TDD Cycle Evidence

| Task | Test File | Layer | RED | GREEN | TRIANGULATE | REFACTOR |
|------|-----------|-------|-----|-------|-------------|----------|
| 4R-fetch | `tests/test_cli_package_assignment.py` | Unit (CliRunner) | `test_package_describe_latest_fetches_packages_once` fails: 2 `GET /packages` calls | 1 `GET /packages` call after single-fetch helper | round-trip count contract | `_find_describe_package` collapses resolve + lookup |
| 4R-refgap | `tests/test_cli_package_assignment.py` | Unit (CliRunner) | n/a (coverage hardening of already-green `package assign`) | passing | real `/projects/by-name/{name}` resolution + canonical-id POST target | n/a |

Test Summary:
- Phase 4 focused run (`test_cli_package_assignment.py` +
  `test_cli_package_commands.py`): 49 passed (+1 round-trip test,
  +1 ref-resolution test vs. the 46 recorded at PR4 implementation).
- Package + admin + help focused run: 87 passed.
- Full suite: `/tmp/opencode/uvpkg/bin/uv run pytest -q` -> 544 passed.
- Validation: `ruff check` clean; `ruff format --check .` clean (68 files);
  `pyright agh tests` 0 errors; `git diff --check` clean.
- `uv` is absent from PATH in this shell; all commands used
  `/tmp/opencode/uvpkg/bin/uv` (`uv 0.11.25`).

### Files Changed (Phase 4 review-fix round)

| File | Action | What Was Done |
|------|--------|---------------|
| `agh/cli/main.py` | Modified | Replaced `_resolve_describe_package_ref` + second `/packages` lookup in `package_describe` with single-fetch `_find_describe_package`. |
| `tests/test_cli_package_assignment.py` | Modified | Added round-trip RED/GREEN test and `package assign` real-resolver coverage test. |
| `openspec/changes/cli-ux-redesign/verify-report.md` | Modified | Brought durable story to a coherent Phase 4 state using recorded Phase 4 evidence + this review-fix round. |
| `openspec/changes/cli-ux-redesign/apply-progress.md` | Modified | Recorded this Phase 4 review-fix round; updated helper name in PR4 TDD table. |

### Out of scope (deferred)

- Telemetry/observability architecture (explicitly excluded from this round).
- README/README.es drift (Phase 6).
- Phase 5 skill/link/pull cleanup.

## Phase 5: Skill / Link / Pull Cleanup (PR5) — DONE

Stacked-to-main slice. The public UX now exposes `link` instead of `sync`, `pull`
help points users to `link`, and `skill` only exposes `list` and `install` with
`--target` target resolution.

### What shipped (PR5)

- **`link` command.** `agh link` links the current git repository to its matching
  AGH project, with the same `--remote` and `--force` behavior as the previous
  `sync` command.
- **`sync` removed.** The legacy `sync` command is no longer registered; invoking
  `agh sync` exits 2 as an unknown command and is not retained as a hidden alias.
- **`pull` help aligned.** `agh pull --help` now describes pulling into the
  "linked repository" and mentions `agh link` first, guiding users who have not
  yet linked the workspace.
- **`skill` surface reduced.** Only `skill list` and `skill install` remain public.
  `skill remove`, `skill installed`, and the `skill agent` subgroup (show/select/
  clear) are removed and exit 2 as unsupported.
- **`skill install --target`.** The `--agent` option is replaced by `--target`.
  Target resolution follows the design contract: explicit `--target`, workspace
  target (`.agh-cache/preferences.toml`), global target (`global-skills/defaults.toml`),
  interactive prompt, then non-interactive usage error.
- **Target language everywhere.** Error messages, prompts, and help text use
  "target" instead of "agent" for global skill commands.
- **Changelog fragment.** Added `changelog.d/+cli-skill-link-pull.breaking.md`
  documenting the breaking CLI changes in this slice.

### TDD Cycle Evidence

| Task | Test File | Layer | Safety Net | RED | GREEN | TRIANGULATE | REFACTOR |
|------|-----------|-------|------------|-----|-------|-------------|----------|
| 5.1 | `tests/test_cli_skill_link_pull.py` | Unit (CliRunner) | 138/138 focused | 14 failing | 14 passing | link, sync removal, pull help, target resolution order, non-interactive error, skill cleanup | n/a |
| 5.2 | `agh/cli/main.py`, `agh/cli/workspace_pull.py` | Unit | 138/138 focused | covered by 5.1 | 138 passing | `link` command, `--target` option, pull help | renamed `_resolve_global_skill_agent` → `_resolve_skill_target`, removed dead skill commands |
| 5.3 | `tests/test_cli_help_map.py`, `tests/test_global_skills.py`, `tests/test_workspace_sync.py`, `tests/test_integration_smoke.py` | Unit (CliRunner) | 138/138 focused | existing tests for removed commands fail | updated/removed; 138 passing | root map pins, unsupported command cases | mechanical `sync` → `link` in workspace sync tests |

Test Summary:
- New tests written: 14 in `tests/test_cli_skill_link_pull.py`
- Existing tests updated: `tests/test_cli_help_map.py`, `tests/test_global_skills.py`, `tests/test_workspace_sync.py`, `tests/test_integration_smoke.py`
- Focused run (skill/link/pull + help + workspace sync): 138 passed
- Full suite: `/tmp/opencode/uvpkg/bin/uv run pytest -q` -> 553 passed
- Validation: `ruff check` clean; `ruff format --check` clean (69 files); `pyright agh tests` 0 errors; `git diff --check` clean.
- Towncrier evidence limitation: the new fragment is currently untracked, so any
  local `uv run towncrier check` would be a limited sanity check only; the PR CI
  run is the authority that validates it against the real branch diff.
- `uv` is absent from PATH in this shell; all commands used `/tmp/opencode/uvpkg/bin/uv` (`uv 0.11.25`).

### Files Changed (PR5)

| File | Action | What Was Done |
|------|--------|---------------|
| `agh/cli/main.py` | Modified | Added `link` command; removed `sync`; reduced `skill` to `list`/`install`; added `--target` to `skill install`; removed `skill remove`/`installed`/`agent`; updated `_resolve_skill_target` to check workspace then global target; updated APP_HELP and skill/pull help text. |
| `agh/cli/workspace_pull.py` | Modified | Updated "not linked" guidance from `agh sync` to `agh link`. |
| `tests/test_cli_skill_link_pull.py` | Created | Phase 5 RED/GREEN coverage for `link`, `sync` removal, `pull` help, `skill install --target` target resolution, and removed skill commands. |
| `tests/test_cli_help_map.py` | Modified | Root map pins now expect `link` and no `skill agent`; legacy unsupported cases include `sync` and removed skill commands. |
| `tests/test_global_skills.py` | Modified | Updated skill help/install tests for target vocabulary; removed tests for deleted `skill remove`/`installed`/`agent` commands. |
| `tests/test_workspace_sync.py` | Modified | Mechanical `sync` → `link` rename for CLI invocations and help assertions. |
| `tests/test_integration_smoke.py` | Modified | Smoke flow uses `agh link` instead of `agh sync`. |
| `changelog.d/+cli-skill-link-pull.breaking.md` | Created | Towncrier breaking fragment for the Phase 5 CLI cleanup. |
| `openspec/changes/cli-ux-redesign/tasks.md` | Modified | Phase 5 tasks marked complete. |
| `openspec/changes/cli-ux-redesign/apply-progress.md` | Modified | Recorded this Phase 5 progress and validation evidence. |

### Review surface accounting

| Surface | Files | Changed lines | vs 800 budget |
|---------|-------|---------------|---------------|
| Runtime code | `agh/cli/main.py`, `agh/cli/workspace_pull.py` | 191 (48+ / 143−) | under |
| Tests (tracked modifications) | `test_cli_help_map.py`, `test_cli_pull.py`, `test_global_skills.py`, `test_integration_smoke.py`, `test_workspace_sync.py` | 210 (54+ / 156−) | — |
| New tests | `tests/test_cli_skill_link_pull.py` | 355 (355+ / 0−) | — |
| **Tests total** | | **565** | **over 400 alone** |
| Changelog + OpenSpec governance | `changelog.d/+cli-skill-link-pull.breaking.md`, `tasks.md`, `apply-progress.md` | 132 (132+ / 3−) | n/a (governance) |
| **Runtime + test subtotal** | | **756** | **under 800** |
| **Full PR5 slice total** | | **888** | **over 800 if governance is counted** |

### Size disposition

Runtime + tests (756 changed lines) stay within the user-approved 800-line
behavior-review budget, but the full PR5 slice including governance artifacts is
888 changed lines. The slice exceeds AGH's default 400-line budget on tests
alone; the runtime code surface remains small.

### Deviations / Scope Decisions

- **README/README.es drift remains deferred to Phase 6.** The README still
  references `agh sync`, `agh agent`, and the removed `skill` subcommands. This
  is intentional: Phase 6 is the dedicated docs/changelog final pass, and the
  README already had pre-existing drift from earlier phases (e.g., `--repo-url`
  vs `--git-url`). The Phase 5 slice is reviewable on code + tests; the docs
  follow in the next slice.

### Out of scope (deferred)

- README/README.es comprehensive update and final docs validation (Phase 6).
- Any further Judgment Day or review-fix rounds for earlier phases.

## Phase 5 Cleanup (fresh-audit fix batch)

Addressed two non-blocking warnings from the fresh Phase 5 audit without
broadening scope into Phase 6 docs work.

### What changed

- **`tests/test_cli_pull.py`**: Strengthened the missing-link assertion in
  `test_pull_missing_link_exits_5` from the weak `"not linked" in result.stdout`
  to the exact guidance substring `"workspace is not linked; run `agh link` first"`.
  This proves the CLI points users to `agh link` rather than any generic
  not-linked message.
- **`openspec/changes/cli-ux-redesign/apply-progress.md`**: Removed the
  `tests/test_cli_pull.py` row from the "Files Changed (PR5)" table. That row
  falsely claimed the file was modified during the original PR5 implementation
  slice; it was not (the missing-link test was last touched in PR2b and was
  only updated now in this cleanup).

### TDD Cycle Evidence

| Task | Test File | Layer | Safety Net | RED | GREEN | TRIANGULATE | REFACTOR |
|------|-----------|-------|------------|-----|-------|-------------|----------|
| cleanup-1 | `tests/test_cli_pull.py` | Unit (CliRunner) | 1/1 (`test_pull_missing_link_exits_5`) | n/a (coverage hardening) | 37/37 focused passing | n/a | n/a |
| cleanup-2 | `openspec/changes/cli-ux-redesign/apply-progress.md` | docs | n/a | n/a | n/a | n/a | n/a |

### TDD note

This is coverage-hardening of an already-green assertion, not a fresh
RED/GREEN bug cycle. The production guidance string (`workspace is not linked;
run `agh link` first`) was already in place; the test just did not pin it
strongly enough. The strengthened assertion passes immediately on the existing
implementation.
