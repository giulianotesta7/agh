# Verification Report

**Change**: `cli-ux-redesign`
**Slices covered**: Phase 3 / PR3 — User / Project / Collection Vocabulary (verified); Phase 4 / PR4 — Package Assignment UX (implemented + review-fix validated)
**Mode**: Strict TDD
**Artifact store**: OpenSpec
**Phase 3 verdict**: PASS
**Phase 4 verdict**: IMPLEMENTED + REVIEW-FIX VALIDATED (no standalone re-verify ceremony; evidence recorded in `apply-progress.md` and refreshed in the Phase 4 Review-Fix Round below)
**Overall change/archive readiness**: BLOCKED — Phases 5-6 remain intentionally unchecked and unverified.

## Scope Boundary

This report's authoritative verified slice is Phase 3: resource vocabulary for
`user`, `project`, and `collection`; nested `user token rotate`; `project member`
management; `--git-url`; and `USER_REF` / `PROJECT_REF` / `COLLECTION_REF`
wording. Phase 3 carries a full verify ceremony plus a Judgment Day re-validation.

Phase 4 (Package Assignment UX) is implemented and its TDD evidence is recorded in
`apply-progress.md` (Phase 4 section). It did not receive a separate standalone
verify ceremony; instead, a Phase 4 Review-Fix Round (4R findings) re-ran the
focused + full validation after removing a redundant `GET /packages` round-trip
and adding two focused tests. That evidence is recorded in this report's Phase 4
Review-Fix Round section and is sufficient to treat Phase 4 as done-but-not-yet-
re-verified for archive purposes; archive remains blocked by Phases 5-6.

Prior PR1/PR2 artifacts remain part of the cumulative branch history, but this
verification does not re-adjudicate those slices beyond running the full current
test suite. Phase 5 skill/link/pull cleanup and Phase 6 docs/final validation
remain archive blockers.

The shell used for this verification does not have `uv` on `PATH`. All runtime
evidence below uses the explicit working executable
`/tmp/opencode/uvpkg/bin/uv` (`uv 0.11.25`).

## Completeness

| Metric | Value |
|--------|-------|
| Total tasks in change | 25 |
| Completed tasks through Phase 3 | 16/25 |
| Completed tasks through Phase 4 | 19/25 |
| Phase 3 tasks complete | 3/3 |
| Phase 4 tasks complete | 3/3 |
| Remaining archive blockers | 6 unchecked tasks in Phases 5-6 |
| Phase 3 slice readiness | ✅ Ready (verified) |
| Phase 4 slice readiness | ✅ Implemented + review-fix validated |
| Full change archive readiness | ❌ Blocked until Phases 5-6 are implemented and verified |

## Build & Tests Execution

| Command | Result | Evidence |
|---------|--------|----------|
| `/tmp/opencode/uvpkg/bin/uv --version` | ✅ Passed | `uv 0.11.25 (aarch64-unknown-linux-gnu)` |
| `/tmp/opencode/uvpkg/bin/uv run pytest tests/test_cli_admin_commands.py tests/test_cli_help_map.py tests/test_project_routes.py -q` | ✅ Passed | 48 passed in 11.74s |
| `/tmp/opencode/uvpkg/bin/uv run pytest -q` | ✅ Passed | 535 passed in 116.03s |
| `/tmp/opencode/uvpkg/bin/uv run --with ruff ruff check .` | ✅ Passed | All checks passed |
| `/tmp/opencode/uvpkg/bin/uv run --with ruff ruff format --check .` | ✅ Passed | 67 files already formatted |
| `/tmp/opencode/uvpkg/bin/uv run --with pyright pyright agh tests` | ✅ Passed | 0 errors, 0 warnings, 0 informations |
| `/tmp/opencode/uvpkg/bin/uv run towncrier check` | ✅ Passed (limited) | On origin/main branch, or no diffs, so no newsfragment required. See Towncrier evidence limitation below. |
| `git diff --check` | ✅ Passed | No whitespace errors |

### Towncrier evidence limitation

This verification ran on the `main` working tree with the Phase 3 fragment
`changelog.d/+cli-resource-vocabulary.breaking.md` still untracked, so
`towncrier check` saw no branch diff and trivially passed. That evidence is
limited: it does not prove CI will accept the fragment on the actual PR branch.
The fragment follows the documented orphan `+*.breaking.md` contract and
contains a single breaking-change sentence, but branch CI (the
`towncrier check` job on the PR) is the authority that validates it against the
real diff. Mark this evidence as branch-CI-validated once the PR check runs.

### Judgment Day re-validation

After the Phase 3 review-fix round (changelog wording, verify-report counts,
and three coverage additions), the suite was re-run with the same explicit
`/tmp/opencode/uvpkg/bin/uv` because `uv` is still not on PATH:

- Focused: `/tmp/opencode/uvpkg/bin/uv run pytest tests/test_cli_help_map.py tests/test_cli_admin_commands.py tests/test_project_routes.py -q` -> 49 passed.
- Full suite: `/tmp/opencode/uvpkg/bin/uv run pytest -q` -> 536 passed.
- `ruff check .` clean; `ruff format --check .` clean; `pyright agh tests` 0 errors; `git diff --check` clean.

The original Phase 3 Build table above remains the historical record; the
counts above supersede it for the post-fix state.

## Phase 3 Spec Compliance Matrix

| Requirement / scenario | Covering runtime evidence | Result |
|------------------------|---------------------------|--------|
| Resource verbs use `list`, `describe`, `create`, `update`, `activate`, `deactivate` for user/project/collection resources | Focused 49-test run; `tests/test_cli_help_map.py::test_resource_help_uses_phase3_vocabulary_and_ref_metavars`; `tests/test_cli_admin_commands.py` resource command tests | ✅ COMPLIANT |
| User token rotation is exposed as `user token rotate` | Focused 49-test run; `test_cli_user_token_project_commands_map_to_api_and_mask_stored_token`; `test_cli_user_token_mutations_use_human_output_and_preserve_one_time_tokens`; help-map assertions | ✅ COMPLIANT |
| Project member management is available under `project member` | Focused 49-test run; `test_cli_project_mutation_commands_use_human_output`; `tests/test_project_routes.py::test_member_reads_only_active_developer_projects_and_membership_removal_revokes_access`; admin-only route coverage | ✅ COMPLIANT |
| Reference arguments use honest `USER_REF`, `PROJECT_REF`, and `COLLECTION_REF` wording | Focused 49-test run; `test_resource_help_uses_phase3_vocabulary_and_ref_metavars`; resolver tests in `test_cli_admin_commands.py`; source inspection of `*_refs.py` messages | ✅ COMPLIANT |
| Legacy resource aliases are not part of supported behavior for this slice | Focused 49-test run; `test_legacy_resource_commands_are_not_supported`; resource help assertions omit `show`/`get`/`delete`; top-level `token` is unsupported | ✅ COMPLIANT for Phase 3 scope |
| Package assignment UX | Phase 4 tasks 4.1-4.3 complete; `tests/test_cli_package_assignment.py` (46 focused PR4 tests); Phase 4 Review-Fix Round validation below | ✅ COMPLIANT (implemented + review-fix validated) |
| Skill/link/pull cleanup | Phase 5 tasks 5.1-5.3 unchecked | ⏸ BLOCKER for full archive |
| README/README.es final migration prose and final validation | Phase 6 tasks 6.1-6.3 unchecked | ⏸ BLOCKER for full archive |

## TDD Compliance

| Check | Result | Details |
|-------|--------|---------|
| TDD evidence reported | ✅ | `apply-progress.md` contains Phase 3 TDD Cycle Evidence rows for 3.1-3.3 |
| All Phase 3 tasks have tests | ✅ | Tasks 3.1-3.3 map to `tests/test_cli_admin_commands.py`, `tests/test_cli_help_map.py`, and `tests/test_project_routes.py` |
| RED confirmed | ✅ | Apply evidence records 26 failing RED tests after test updates before production changes; historical RED cannot be re-executed from the current green state |
| GREEN confirmed | ✅ | Focused Phase 3 command now passes: 49/49; full suite passes: 536/536 |
| Triangulation adequate | ✅ | Coverage spans resource verbs, token nesting, member list, refs, human output, server route auth, and unsupported legacy forms |
| Safety net for modified files | ✅ | Apply evidence records 46 passing safety-net tests before RED; current focused/full validation also passes |
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
| Keep later package/skill/link/docs changes sliced | Phase 4 implemented + review-fix validated; Phase 5-6 remain sliced and unchecked | ✅ Followed |

## Files Changed in Phase 3 Worktree

| Path | Status | Verification note |
|------|--------|-------------------|
| `agh/cli/main.py` | Modified | Resource command wiring, `user token rotate`, `project member`, `--git-url`, help map |
| `agh/server/routes/projects.py` | Modified | Admin-only project member listing route |
| `agh/cli/user_refs.py` | Modified | `USER_REF` resolver wording |
| `agh/cli/project_refs.py` | Modified | `PROJECT_REF` resolver wording |
| `agh/cli/collection_refs.py` | Modified | `COLLECTION_REF` resolver wording |
| `tests/test_cli_admin_commands.py` | Modified | Phase 3 CLI behavior coverage |
| `tests/test_cli_help_map.py` | Modified | Phase 3 help/root-map/legacy absence coverage |
| `tests/test_project_routes.py` | Modified | Project member route coverage |
| `changelog.d/+cli-resource-vocabulary.breaking.md` | Created / untracked | Per-slice breaking Towncrier fragment |
| `openspec/changes/cli-ux-redesign/tasks.md` | Modified | Phase 3-4 tasks marked complete; Phase 5-6 left unchecked |
| `openspec/changes/cli-ux-redesign/apply-progress.md` | Modified | Phase 3 apply evidence recorded |
| `openspec/changes/cli-ux-redesign/verify-report.md` | Modified | This Phase 3 verification report |
| `.codegraph/` | Untracked | Must not be committed |

## Issues Found

**CRITICAL**
- None for Phase 3.

**WARNING**
- Full `cli-ux-redesign` is not archive-ready. Phases 5-6 remain unchecked and
  unverified; Phase 4 is implemented + review-fix validated but has not had a
  standalone verify ceremony.
- `.codegraph/` is untracked and must not be committed.
- `uv` is absent from `PATH` in this shell; verification used the explicit
  `/tmp/opencode/uvpkg/bin/uv` workaround and reports it openly.

**SUGGESTION**
- Keep Phase 5 focused on skill/link/pull cleanup only; do not mix Phase 6
  docs/changelog into that review slice.

## Phase 4 Review-Fix Round (4R findings)

After Phase 4 implementation, the remaining real 4R findings were addressed on
top of the completed slice. This is a focused fix round, not a standalone Phase 4
verify ceremony; it re-ran the focused + full validation recorded below.

### What shipped

- **Removed redundant `GET /packages` in `package describe @latest`.** The
  describe path previously fetched `/packages` twice: once inside
  `_resolve_describe_package_ref` to resolve `@latest` to the highest SemVer
  version, and again in `package_describe` to look up the resolved package. The
  two steps were collapsed into a single `_find_describe_package` helper that
  resolves and looks up in one fetch. Behavior preserved: SemVer-aware `@latest`
  resolution, exact-version describe, and the `package ... not found` failure
  message are unchanged.
- **Closed a public ref-resolution contract gap.** Added
  `test_package_assign_resolves_exact_project_name_through_real_resolver`, which
  proves an exact project name passed to `package assign --project` resolves
  through the real `/projects/by-name/{name}` resolver end-to-end (no
  `_resolve_project_ref` monkeypatch), exercising public project-ref resolution
  through the new PR4 surface.

### TDD note

- **Double-fetch removal is a genuine RED/GREEN cycle.**
  `test_package_describe_latest_fetches_packages_once` asserts exactly one
  `GET /packages` call for `package describe @latest`. It was written first and
  failed RED on the pre-fix code (`2 == 1`, two fetches recorded), then passed
  GREEN after the refactor. The observable contract is the network round-trip
  count.
- **The ref-resolution test is coverage hardening**, not a RED/GREEN cycle: it
  passes on the pre-fix code as well, because `package assign` already preserved
  public ref resolution. It is recorded honestly as closing a public-contract
  coverage gap, not as a freshly-fixed bug.

### Validation

Run with `/tmp/opencode/uvpkg/bin/uv` (`uv 0.11.25`); `uv` is not on PATH in
this shell.

- Focused: `/tmp/opencode/uvpkg/bin/uv run pytest tests/test_cli_package_assignment.py tests/test_cli_package_commands.py -q` -> 49 passed.
- Package + admin + help focused run
  (`test_cli_package_assignment.py`, `test_cli_admin_commands.py`,
  `test_cli_package_commands.py`, `test_cli_help_map.py`) -> 87 passed.
- Full suite: `/tmp/opencode/uvpkg/bin/uv run pytest -q` -> 544 passed.
- `ruff check .` clean; `ruff format --check .` clean (68 files);
  `pyright agh tests` 0 errors; `git diff --check` clean.

### Files Changed (Phase 4 review-fix round)

| File | Action | What Was Done |
|------|--------|---------------|
| `agh/cli/main.py` | Modified | Replaced `_resolve_describe_package_ref` (returned a ref string, fetched `/packages`) + second `/packages` lookup in `package_describe` with a single-fetch `_find_describe_package` helper that resolves `@latest`/exact/unknown and returns the package record in one fetch. |
| `tests/test_cli_package_assignment.py` | Modified | Added `test_package_describe_latest_fetches_packages_once` (RED/GREEN for the redundant fetch) and `test_package_assign_resolves_exact_project_name_through_real_resolver` (public ref-resolution coverage through `package assign`). |
| `openspec/changes/cli-ux-redesign/verify-report.md` | Modified | Brought the durable story to a coherent Phase 4 state using recorded Phase 4 evidence + this review-fix round. |
| `openspec/changes/cli-ux-redesign/apply-progress.md` | Modified | Recorded this Phase 4 review-fix round. |

## Final Verdict

**PASS for Phase 3 / PR3 User / Project / Collection Vocabulary.**

**Phase 4 / PR4 Package Assignment UX: IMPLEMENTED + REVIEW-FIX VALIDATED.**
Phase 4 is functionally complete (tasks 4.1-4.3 checked) and its review-fix
round (redundant `GET /packages` removal + public ref-resolution coverage)
passes focused + full validation. It has not received a separate standalone
verify ceremony; its evidence lives in `apply-progress.md` (Phase 4 section) and
the Phase 4 Review-Fix Round section above.

The overall `cli-ux-redesign` change remains **BLOCKED for archive** until
Phases 5-6 are implemented, verified, and their task checkboxes are completed.

## Next Recommended

Proceed to Phase 5: Skill / Link / Pull Cleanup. Preserve the OpenSpec change as
open and do not archive the full change yet.
