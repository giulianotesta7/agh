# Tasks: CLI UX Redesign

## Review Workload Forecast

| Field | Value |
|-------|-------|
| Estimated changed lines | 900-1,400 total; target 150-300 per slice |
| 400-line budget risk | High |
| Chained PRs recommended | Yes |
| Suggested split | PR1 help/root → PR2 config/auth/target → PR3 resources → PR4 package → PR5 skill/link/pull → PR6 docs/changelog |
| Delivery strategy | ask-always |
| Chain strategy | stacked-to-main |

Decision needed before apply: Resolved
Chained PRs recommended: Yes
Chain strategy: stacked-to-main
Delivery strategy: ask-always (approved chained PRs)
400-line budget risk: High

### Suggested Work Units

| Unit | Goal | Likely PR | Notes |
|------|------|-----------|-------|
| 1 | Help/root infrastructure | PR1 | Rollback `agh/cli/main.py`; verify CLI tests + `uv run agh --help`. |
| 2 | Config/auth + target | PR2 | Depends PR1; rollback config/target files; verify isolated `AGH_CONFIG_FILE`. |
| 3 | User/project/collection vocabulary | PR3 | Depends PR1; rollback resource wiring; verify focused CLI/API tests. |
| 4 | Package assignment UX | PR4 | Depends PR3 refs; rollback package wiring; verify package CLI tests. |
| 5 | Skill + link/pull cleanup | PR5 | Depends PR2 target; rollback skill/link/pull wiring; verify target/help tests. |
| 6 | Docs/changelog final | PR6 | Depends final UX; verify docs tests, Towncrier, diff whitespace. |

## Phase 1: Help / Root Infrastructure

- [x] 1.1 RED: Test `agh --help`, `--version`, subgroup help, unknown exit 2, and absent legacy names.
- [x] 1.2 GREEN: Rewire `agh/cli/main.py` root map and subgroup help without aliases.
- [x] 1.3 REFACTOR: Prevent root-help leakage into empty/nested groups.

## Phase 2: Config / Auth / Target

> Phase 2 is split into three stacked review slices (PR2a config, PR2b auth,
> PR2c target) to stay within the 400-line review budget. Mark only the slice
> you ship.

### 2a — Instance config (PR2a)

- [x] 2a.1 RED: Test `config` shows only instance URL (never auth); `config set`
      normalizes/stores/overwrites; `config clear` clears only instance.
- [x] 2a.2 GREEN: Add instance/corrupt helpers in `agh/cli/config.py`
      (`load/save/clear_instance_url`, `InstanceUpdate`, `ConfigCorruptError`,
      `_read/_write_config_dict`, `_write_or_remove`); wire `config`,
      `config set`, `config clear` in `agh/cli/main.py`.
- [x] 2a.3 RED/GREEN: Trust boundary — changing the instance clears stored
      credentials; same normalized instance preserves them; orphaned creds
      after `config clear` are dropped on the next `config set`.
- [x] 2a.4 RED/GREEN: Corrupt config graceful recovery for `config`,
      `config set`, and `config clear` (no traceback, clear guidance, file
      left intact).

### 2b — Auth (PR2b)

- [x] 2b.1 RED: Test `login` uses configured instance (flags + interactive),
      never prompts URL, fails before prompts when unconfigured; `whoami`;
      `logout` clears only credentials.
- [x] 2b.2 GREEN: Rewrite `login` (no `--url`, `load_instance_url` +
      `save_credentials`); add `whoami`, `logout`; add
      `save_credentials`/`clear_credentials`; drop now-dead `save_config`.
- [x] 2b.3 RED/GREEN: Corrupt config recovery for `logout`, and for
      `whoami`/API-backed commands via `_api_request`
      (`load_config` raises `ConfigCorruptError` → recovery guidance).
      Judgment Day Round 1: extended to `login`, `sync`, and linked `pull`
      (regression tests for each).

### 2c — Target (PR2c)

- [ ] 2c.1 RED: Test `target`/`target set`/`target clear` with `--global`;
      public `agent` removed (exit 2, no alias); output/help uses "target".
- [ ] 2c.2 GREEN: Replace public `agent` with `target` in `agh/cli/main.py`
      (workspace + global); reuse `agent_integrations` storage.
- [ ] 2c.3 RED/GREEN: Update `agh pull` missing-target message to
      `agh target set ...` (direct rename dependency); remove dead
      `format_agent_preference`.

## Phase 3: User / Project / Collection Vocabulary

- [ ] 3.1 RED: Test resource verbs, `user token rotate`, and `project member`.
- [ ] 3.2 GREEN: Rename resource wiring in `agh/cli/main.py`; add `projects.py` member route only if required.
- [ ] 3.3 REFACTOR: Align `*_REF` help/errors in `agh/cli/*_refs.py`.

## Phase 4: Package Assignment UX

- [ ] 4.1 RED: Test exclusive `--project/--collection`, no position/positional target, verbs, and `@latest` SemVer.
- [ ] 4.2 GREEN: Move assignment under `package` in `agh/cli/main.py`; update `package_refs.py` messages.
- [ ] 4.3 REFACTOR: Ensure assignment errors name package ref and target.

## Phase 5: Skill / Link / Pull Cleanup

- [ ] 5.1 RED: Test target resolution, non-interactive error, `link`, absent `sync`, and `pull` help.
- [ ] 5.2 GREEN: Wire supported `skill`, `link`, and `pull` help in `main.py`/`workspace_sync.py`.
- [ ] 5.3 REFACTOR: Remove unsupported `skill installed/remove/agent` exposure.

## Phase 6: Docs / Changelog / Final Validation

- [ ] 6.1 Update `README.md` and `README.es.md` with final CLI map; preserve H2 contract.
- [ ] 6.2 Create `changelog.d/+cli-ux-redesign.breaking.md` summarizing the breaking CLI redesign.
- [ ] 6.3 Verify: `uv run pytest tests/test_docs_guidance.py -q`, `uv run towncrier check`, `uv run pytest -q`, and `git diff --check`.
