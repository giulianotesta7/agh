# Tasks: Fix Review Findings

## Review Workload Forecast

| Field | Value |
|-------|-------|
| Estimated changed lines | 220-320 |
| 400-line budget risk | Medium |
| Chained PRs recommended | No |
| Suggested split | Single PR |
| Delivery strategy | ask-always |
| Chain strategy | pending |

Decision needed before apply: No
Chained PRs recommended: No
Chain strategy: pending
400-line budget risk: Medium

### Suggested Work Units

| Unit | Goal | Likely PR | Notes |
|------|------|-----------|-------|
| 1 | Stabilize pack publish storage and orphan recovery | PR 1 | Base on current change; include regression tests for startup state and conservative cleanup |
| 2 | Harden request-body validation | PR 1 | Same slice; keep malformed Content-Length 400 JSON and oversized 413 coverage together |

## Phase 1: Foundation / Storage State

- [x] 1.1 Update `agh/server/app.py` to store startup `data_dir` on `app.state` alongside `db_path`.
- [x] 1.2 Add or adjust a small helper contract in `agh/server/routes/packs.py` to read publish storage from `request.app.state.data_dir`, not request-time environment lookups.
- [x] 1.3 Confirm pack publish path composition remains `{data_dir}/packs/{domain}/{name}/{version}` and document the boundary in code comments only if needed.

## Phase 2: Core Implementation

- [x] 2.1 Update `agh/server/routes/packs.py` publish flow to use startup-derived storage consistently for staging/final paths.
- [x] 2.2 Add conservative orphan-final-directory handling: delete/recover only when the DB proves no matching `pack_versions` row and no row references the target storage path.
- [x] 2.3 Keep ambiguous final directories fail-closed; do not delete when orphan status cannot be proven.
- [x] 2.4 Harden `Content-Length` parsing in `agh/server/app.py` so malformed or non-numeric values return JSON `400`, while oversized bodies still map to existing `413`.

## Phase 3: Testing / Verification

- [x] 3.1 Add a regression test showing publish ignores post-startup `AGH_DATA_DIR` drift and writes under the startup root.
- [x] 3.2 Add a regression test for proven orphan final-pack cleanup/recovery, including successful republish after crash-leftover final directories.
- [x] 3.3 Add a regression test that ambiguous/DB-referenced final directories are preserved and publish fails closed.
- [x] 3.4 Add request-body tests for malformed and non-numeric `Content-Length` returning JSON `400`, plus oversized payloads preserving `413`.

## Phase 4: Cleanup / Documentation

- [x] 4.1 Update any nearby comments or test names to reflect startup-derived storage state and conservative cleanup rules.
- [x] 4.2 Add a brief follow-up backlog note only for deferred review findings excluded from this slice.
