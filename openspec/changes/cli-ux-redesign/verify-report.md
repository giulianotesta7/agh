# Verification Report

**Change**: `cli-ux-redesign`
**Slices covered**: Phase 3 / PR3 — User / Project / Collection Vocabulary only
**Mode**: Strict TDD
**Artifact store**: OpenSpec
**Phase 3 verdict**: PASS
**Overall change/archive readiness**: BLOCKED — Phases 4-6 remain intentionally unchecked and unverified.

## Scope Boundary

This report's authoritative verified slice is Phase 3: resource vocabulary for
`user`, `project`, and `collection`; nested `user token rotate`; `project member`
management; `--git-url`; and `USER_REF` / `PROJECT_REF` / `COLLECTION_REF`
wording. Phase 3 carries a full verify ceremony.

Phase 4 (Package Assignment UX), Phase 5 (Skill / Link / Pull Cleanup), and
Phase 6 (Docs / Changelog / Final Validation) remain archive blockers and are
not verified here. The PR3 worktree intentionally keeps the pre-PR4 package
assignment structure (`project package` / `collection package` subgroups) so the
slice is coherent and reviewable on its own.

The shell used for this verification does not have `uv` on `PATH`. All runtime
evidence below uses the explicit working executable
`/tmp/opencode/uvpkg/bin/uv` (`uv 0.11.25`).

## Completeness

| Metric | Value |
|--------|-------|
| Total tasks in change | 25 |
| Completed tasks through Phase 3 | 16/25 |
| Phase 3 tasks complete | 3/3 |
| Remaining archive blockers | 9 unchecked tasks in Phases 4-6 |
| Phase 3 slice readiness | ✅ Ready (verified) |
| Full change archive readiness | ❌ Blocked until Phases 4-6 are implemented and verified |

## Build & Tests Execution

| Command | Result | Evidence |
|---------|--------|----------|
| `/tmp/opencode/uvpkg/bin/uv --version` | ✅ Passed | `uv 0.11.25 (aarch64-unknown-linux-gnu)` |
| `/tmp/opencode/uvpkg/bin/uv run pytest tests/test_cli_admin_commands.py tests/test_cli_help_map.py tests/test_project_routes.py -q` | ✅ Passed | 49 passed in 13.20s |
| `/tmp/opencode/uvpkg/bin/uv run --with ruff ruff check .` | ✅ Passed | All checks passed |
| `/tmp/opencode/uvpkg/bin/uv run --with ruff ruff format --check .` | ✅ Passed | 67 files already formatted |
| `/tmp/opencode/uvpkg/bin/uv run --with pyright pyright agh tests` | ✅ Passed | 0 errors, 0 warnings, 0 informations |
| `/tmp/opencode/uvpkg/bin/uv run towncrier check` | ⚠️ Limited local check | `On origin/main branch, or no diffs, so no newsfragment required.` because the worktree has no committed diffs and the fragment is untracked |
| `git diff --check` | ✅ Passed | No whitespace errors |

## Phase 3 Spec Compliance Matrix

| Requirement / scenario | Covering runtime evidence | Result |
|------------------------|---------------------------|--------|
| Resource verbs use `list`, `describe`, `create`, `update`, `activate`, `deactivate` for user/project/collection resources | Focused 49-test run; `tests/test_cli_help_map.py::test_resource_help_uses_phase3_vocabulary_and_ref_metavars`; `tests/test_cli_admin_commands.py` resource command tests | ✅ COMPLIANT |
| User token rotation is exposed as `user token rotate` | Focused 49-test run; `test_cli_user_token_project_commands_map_to_api_and_mask_stored_token`; `test_cli_user_token_mutations_use_human_output_and_preserve_one_time_tokens`; help-map assertions | ✅ COMPLIANT |
| Project member management is available under `project member` | Focused 49-test run; `test_cli_project_mutation_commands_use_human_output`; `tests/test_project_routes.py::test_member_reads_only_active_developer_projects_and_membership_removal_revokes_access`; admin-only route coverage | ✅ COMPLIANT |
| Reference arguments use honest `USER_REF`, `PROJECT_REF`, and `COLLECTION_REF` wording | Focused 49-test run; `test_resource_help_uses_phase3_vocabulary_and_ref_metavars`; resolver tests in `test_cli_admin_commands.py`; source inspection of `*_refs.py` messages | ✅ COMPLIANT |
| Legacy resource aliases are not part of supported behavior for this slice | Focused 49-test run; `test_legacy_resource_commands_are_not_supported`; resource help assertions omit `show`/`get`/`delete`; top-level `token` is unsupported | ✅ COMPLIANT for Phase 3 scope |
| Package assignment UX | Phase 4 tasks 4.1-4.3 unchecked; pre-PR4 `project package` / `collection package` structure retained | ⏸ BLOCKER for full archive |
| Skill/link/pull cleanup | Phase 5 tasks 5.1-5.3 unchecked | ⏸ BLOCKER for full archive |
| README/README.es final migration prose and final validation | Phase 6 tasks 6.1-6.3 unchecked | ⏸ BLOCKER for full archive |

## TDD Compliance

| Check | Result | Details |
|-------|--------|---------|
| TDD evidence reported | ✅ | `apply-progress.md` contains Phase 3 TDD Cycle Evidence rows for 3.1-3.3 |
| All Phase 3 tasks have tests | ✅ | Tasks 3.1-3.3 map to `tests/test_cli_admin_commands.py`, `tests/test_cli_help_map.py`, and `tests/test_project_routes.py` |
| RED confirmed | ✅ | Apply evidence records 26 failing RED tests after test updates before production changes; historical RED cannot be re-executed from the current green state |
| GREEN confirmed | ✅ | Focused Phase 3 command now passes: 49/49 |
| Triangulation adequate | ✅ | Coverage spans resource verbs, token nesting, member list, refs, human output, server route auth, and unsupported legacy forms |
| Safety net for modified files | ✅ | Apply evidence records 46 passing safety-net tests before RED; current focused validation also passes |
| Refactor validation | ✅ | `*_REF` constants/messages and Typer wiring are exercised by help, resolver, and API tests |

**TDD Compliance**: Phase 3 Strict TDD evidence is sufficient for the implemented slice.

## Test Layer Distribution

| Layer | Tests | Files | Tools |
|-------|-------|-------|-------|
| CLI unit/integration via `CliRunner` | Focused Phase 3 CLI coverage | `tests/test_cli_admin_commands.py`, `tests/test_cli_help_map.py` | pytest + Typer `CliRunner` |
| API integration via `TestClient` | Project member route/admin coverage | `tests/test_project_routes.py` | pytest + FastAPI `TestClient` |
| E2E | 0 | 0 | Not used for Phase 3 |
| **Total focused** | **49 passing tests** | **3 files** | `/tmp/opencode/uvpkg/bin/uv run pytest ...` |

## Changed File Coverage

Coverage analysis skipped — no coverage command/capability was provided for this
verification slice, and coverage is not one of the expected quality gates. This
does not affect the Phase 3 verdict.

## Assertion Quality

Scanned the Phase 3 created/modified test files for tautologies, ghost loops,
smoke-only assertions, orphan empty checks, and type-only assertions used alone.

| File | Result |
|------|--------|
| `tests/test_cli_admin_commands.py` | ✅ Assertions exercise CLI commands/API calls, exit codes, exact output, token redaction, resolver behavior, and request bodies. Empty `calls == []` checks are paired with production CLI invocation and error assertions. |
| `tests/test_cli_help_map.py` | ✅ Loop assertions iterate fixed non-empty command lists and assert help output/exit behavior; no ghost loops or tautologies found. |
| `tests/test_project_routes.py` | ✅ Assertions exercise real TestClient routes, admin/member authorization, response payloads, and status codes; no trivial assertions found. |

**Assertion quality**: 0 CRITICAL, 0 WARNING.

## Design Coherence

| Design decision | Phase 3 evidence | Status |
|-----------------|------------------|--------|
| Keep Typer groups and central command wiring in `agh/cli/main.py` | Resource command rewiring remains in `agh/cli/main.py`; source inspection shows `user`, `project`, `collection`, `user token`, and `project member` Typer groups | ✅ Followed |
| Resource verbs use canonical names | Source inspection and tests show `list/create/describe/update/activate/deactivate` for resources | ✅ Followed |
| User token rotation is nested | `token_rotate` is registered under `user_token_app`; top-level `token` is absent from supported help/tests | ✅ Followed |
| Project member list exists only if required | `GET /projects/{project_id}/members` was added in `agh/server/routes/projects.py` with admin-only access | ✅ Followed |
| Align `*_REF` help/errors | `user_refs.py`, `project_refs.py`, and `collection_refs.py` use `USER_REF`, `PROJECT_REF`, and `COLLECTION_REF` wording | ✅ Followed |
| Keep later package/skill/link/docs changes sliced | `tasks.md` leaves Phases 4-6 unchecked; PR4 package assignment structure is not present in this slice | ✅ Followed |

## Files Changed in Phase 3 Worktree

| Path | Status | Verification note |
|------|--------|-------------------|
| `agh/cli/main.py` | Modified | Resource command wiring, `user token rotate`, `project member`, `--git-url`, help map; pre-PR4 `project package` / `collection package` subgroups retained |
| `agh/server/routes/projects.py` | Modified | Admin-only project member listing route |
| `agh/cli/user_refs.py` | Modified | `USER_REF` resolver wording |
| `agh/cli/project_refs.py` | Modified | `PROJECT_REF` resolver wording |
| `agh/cli/collection_refs.py` | Modified | `COLLECTION_REF` resolver wording |
| `tests/test_cli_admin_commands.py` | Modified | Phase 3 CLI behavior coverage; legacy `collection package` tests retained |
| `tests/test_cli_help_map.py` | Modified | Phase 3 help/root-map/legacy absence coverage; pre-PR4 nested package rows retained |
| `tests/test_project_routes.py` | Modified | Project member route coverage |
| `changelog.d/+cli-resource-vocabulary.breaking.md` | Created / untracked | Per-slice breaking Towncrier fragment |
| `openspec/changes/cli-ux-redesign/tasks.md` | Modified | Phase 3 tasks marked complete; Phases 4-6 left unchecked |
| `openspec/changes/cli-ux-redesign/apply-progress.md` | Modified | Phase 3 apply evidence recorded |
| `openspec/changes/cli-ux-redesign/verify-report.md` | Modified | This Phase 3 verification report |

## Issues Found

**CRITICAL**
- None for Phase 3.

**WARNING**
- Full `cli-ux-redesign` is not archive-ready. Phases 4-6 remain unchecked and unverified.
- `uv` is absent from `PATH` in this shell; verification used the explicit `/tmp/opencode/uvpkg/bin/uv` workaround and reports it openly.
- `towncrier check` reported `On origin/main branch, or no diffs, so no newsfragment required.` because the PR3 worktree has no committed diffs and the fragment is untracked. The fragment `changelog.d/+cli-resource-vocabulary.breaking.md` was confirmed by direct inspection; authoritative Towncrier validation must come from branch CI after the changes are committed.

**SUGGESTION**
- Keep Phase 4 focused on package assignment UX only; do not mix Phase 5 skill/link/pull or Phase 6 docs/changelog into that review slice.

## Final Verdict

**PASS for Phase 3 / PR3 User / Project / Collection Vocabulary.**

The overall `cli-ux-redesign` change remains **BLOCKED for archive** until
Phases 4-6 are implemented, verified, and their task checkboxes are completed.

## Next Recommended

Proceed to Phase 4: Package Assignment UX. Preserve the OpenSpec change as open
and do not archive the full change yet.
