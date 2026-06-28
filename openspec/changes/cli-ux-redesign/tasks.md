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

- [ ] 2.1 RED: Test temp `AGH_CONFIG_FILE`, mocked `/me`, token masking, logout, and no URL prompt.
- [ ] 2.2 GREEN: Update `agh/cli/config.py` and `agh/cli/main.py` for config/auth commands.
- [ ] 2.3 RED/GREEN: Test target scope, then add `agent_integrations.py` wrappers and target wiring.

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
