# Tasks: Package Nomenclature UX

## Review Workload Forecast

| Field | Value |
|-------|-------|
| Estimated changed lines | 900-1400 |
| 400-line budget risk | High |
| Chained PRs recommended | Yes |
| Suggested split | PR 1 IDs/DB/storage, PR 2 CLI/API, PR 3 workspace/docs/tests |
| Delivery strategy | exception-ok (`size:exception`) |
| Chain strategy | N/A — approved single large PR exception |

Decision needed before apply: No
Chained PRs recommended: Yes
Chain strategy: N/A — approved single large PR exception
400-line budget risk: High

### Suggested Work Units

| Unit | Goal | Likely PR | Notes |
|------|------|-----------|-------|
| 1 | Core migration substrate | PR 1 | Base: main; IDs, schema/data, storage repair, manifest model |
| 2 | Public surface rename | PR 2 | Base: PR 1; CLI, API, interactive add, package routes |
| 3 | Workspace/docs enforcement | PR 3 | Base: PR 2; pull/cache/lock, docs, grep tests |

## Phase 1: Foundation / Migration

- [x] 1.1 Add failing tests for package terminology, no legacy `pack`/`packs` commands/routes, and canonical `pkg`/`pkgv` IDs in `tests/`.
- [x] 1.2 Add DB migration test for `packs`/`pack_versions`/`project_packs` -> `packages`/`package_versions`/`project_packages`, preserving `asn_` links.
- [x] 1.3 Add filesystem migration test for `/data/packs` -> `/data/packages` and `package_versions.storage_path` rewrite.

## Phase 2: Core Implementation

- [x] 2.1 Rename ID/ref/manifest helpers in `agh/common/ids.py`, `agh/common/validation.py`, and `agh/common/pack_manifest.py` to `pkg`/`pkgv`, `PackageManifest`, and `agh.package.toml`.
- [x] 2.2 Implement `003_rename_packs_to_packages.sql` and startup storage repair in `agh/server/db.py` or migration bootstrap.
- [x] 2.3 Rename server routes from `agh/server/routes/packs.py` to `agh/server/routes/packages.py` and update project package endpoints in `agh/server/routes/projects.py`.

## Phase 3: CLI / Workspace Wiring

- [x] 3.1 Replace `agh pack` / `agh project pack` with `agh package` / `agh project package` in `agh/cli/main.py`; delete legacy command registration.
- [x] 3.2 Rename `agh/cli/pack_init.py`, `pack_publish.py`, and `pack_refs.py` to package modules; update authoring/publish flow to `agh.package.toml`.
- [x] 3.3 Update `agh/cli/workspace_pull.py`, `pull_plan.py`, and `pull_markers.py` to `packages`, `package_ref`, and `[[packages]]`.
- [x] 3.4 Implement omitted-ref interactive add flow: show unassigned latest-stable package refs, confirm selection, cancel with `Cancelled.` and exit 130.
- [x] 3.5 Amend `agh project package add` with no arguments to select a visible project first, then reuse package selection.

## Phase 4: Testing / Enforcement

- [x] 4.1 Add or update API/CLI tests for `agh package` success, `agh pack` rejection, new `/packages` routes, and project package add behaviors.
- [x] 4.2 Add doc/README/README.es updates plus doc tests for package terminology, `agh.package.toml`, and `package_ref`.
- [x] 4.3 Add final grep enforcement tests to fail on remaining public `pack` terminology, except justified migration internals.

## Phase 5: Cleanup / Verification

- [x] 5.1 Remove obsolete `pack` imports, filenames, and route registrations after green tests.
- [x] 5.2 Run full suite plus terminology grep sweep to confirm only approved historical migration internals remain.
