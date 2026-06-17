# Tasks: Global Skill Collections

## Review Workload Forecast

| Field | Value |
|-------|-------|
| Estimated changed lines | 500-700 |
| 400-line budget risk | High |
| Chained PRs recommended | Yes |
| Suggested split | PR 1A: collection foundation → PR 1B: collection package assignment + skill discovery → PR 2: CLI global skills |
| Delivery strategy | chained PRs |
| Chain strategy | feature-branch-chain |
| Issue | #97 |
| Tracker branch | `feat/global-skill-collections` |

Decision needed before apply: No — user selected chained PRs with a feature-branch-chain/tracker PR strategy for issue #97, then split the oversized server slice into PR 1A and PR 1B.
Chained PRs recommended: Yes
Chain strategy: feature-branch-chain
400-line budget risk: High

### Suggested Work Units

| Unit | Goal | Likely PR | Notes |
|------|------|-----------|-------|
| 1A | Collection migration/table foundation and collection CRUD routes | PR 1A | Base = tracker branch/PR; includes migration, `col_` ID prefix, router wiring, auth-aware collection CRUD tests |
| 1B | Collection package assignments, skill-only validation, and skill list/resolve endpoints | PR 1B | Base = PR 1A; includes assignment/list/resolve route tests |
| 2 | Global skill install/remove, agent default selection, native path resolver | PR 2 | Base = PR 1B; includes CLI/state tests and rollback |

## Phase 1: Foundation / Data Model

- [x] 1.1 Add `agh/server/migrations/004_collections.sql` for `collections` plus `col_` ID prefix updates.
- [ ] 1.2 Extend `agh/server/db.py` schema helpers and repository types for collection CRUD and assignment records.
- [x] 1.3 Add route/module wiring in `agh/server/app.py` for the new collections router.

## Phase 2: Core Server Behavior

- [x] 2.1A Implement collection CRUD endpoints with owner/admin mutation and member read/list behavior.
- [ ] 2.1B Implement collection package assignment endpoints with owner/admin authorization.
- [ ] 2.2 Add skill-only validation that rejects package artifacts containing `instructions/AGENTS.md` or `instructions/CLAUDE.md`.
- [ ] 2.3 Implement `GET /skills` and `GET /skills:resolve` for collection-backed skill discovery and concrete version resolution.

## Phase 3: CLI Global Skills

- [ ] 3.1 Add `agh/cli/global_skills.py` for resolve/download/cache/target/lock/remove flow under user AGH state.
- [ ] 3.2 Extend `agh/cli/agent_integrations.py` with `global_skill_dir(agent)` and separate global default-agent selection.
- [ ] 3.3 Add CLI commands for `skill list/install/remove` plus global-skill-scoped agent defaults such as `skill agent show/select/clear` in `agh/cli/main.py`.

## Phase 4: Strict TDD Verification

- [x] 4.1A Write focused tests for collection migration, auth, CRUD/list/get/update/delete, and active/inactive behavior in `tests/`.
- [ ] 4.1B Write focused tests for collection package assignment, skill-only rejection, skill list, and resolve scenarios in `tests/`.
- [ ] 4.2 Write failing tests for global install/remove, checksum no-op, AGH-owned update, and untracked target `--force` behavior.
- [ ] 4.3 Verify CLI prompts and default-agent behavior, including `Select the agent for global skills:` wording.

## Phase 5: Cleanup / Documentation

- [ ] 5.1 Update CLI help/docs for global skill commands and agent-default behavior.
- [ ] 5.2 Keep the workspace prompt wording cleanup as a separate follow-up PR; do not include it in core implementation.

## Phase 6: PR 1A.2 Collection CRUD API Hardening

- [x] 6.1 Add bounded collection name and description validation in the API layer (`agh/server/routes/collections.py`).
- [x] 6.2 Expand collection CRUD/update contract tests for admin create, name update, reactivation, invalid update names, duplicate update names, and unauthenticated DELETE.
- [x] 6.3 Add `005_collection_constraints` migration and direct migration/schema tests for collection length constraints.
