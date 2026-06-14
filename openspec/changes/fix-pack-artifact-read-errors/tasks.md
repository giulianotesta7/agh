# Tasks: Fix Pack Artifact Read Errors v0.3.3

## Review Workload Forecast
| Field | Value |
|---|---|
| Estimated changed lines | ~570 total; ~180-220 per slice |
| 400-line budget risk | High |
| Chained PRs recommended | Yes |
| Suggested split | PR 1 → PR 2 → PR 3 |
| Delivery strategy | ask-always |
| Chain strategy | stacked-to-main |

Decision needed before apply: Yes
Chained PRs recommended: Yes
Chain strategy: stacked-to-main
400-line budget risk: High

### Suggested Work Units
| Unit | Goal | Likely PR | Notes |
|---|---|---|---|
| 1 | Harden direct pack reads | PR 1 | `agh/server/routes/packs.py` + `tests/test_pack_routes.py` |
| 2 | Legacy-safe pull-manifest shaping | PR 2 | `agh/server/routes/projects.py` |
| 3 | Pull-manifest regression coverage | PR 3 | `tests/test_pull_manifest_routes.py` |

## Phase 1: Slice Boundaries
- [x] 1.1 Keep PR 1 limited to direct-download 404/503 classification in `agh/server/routes/packs.py`.
- [x] 1.2 Leave `agh/server/routes/projects.py` for later slices.

## Phase 2: Core Implementation
- [x] 2.1 Implement and verify safe path resolution, symlink rejection, and unreadable-file mapping in `agh/server/routes/packs.py`.
- [x] 2.2 Update `agh/server/routes/projects.py` to use `artifact_paths` when present and tolerate legacy manifests when absent.
- [x] 2.3 Preserve mixed instruction+skill packs when `skills/` exists; fail 404 only for genuine missing storage.

## Phase 3: Integration / Wiring
- [x] 3.1 Wire PR 2 manifest output to the new artifact-path behavior without touching PR 1 semantics.
- [ ] 3.2 Keep PR 3 focused on `tests/test_pull_manifest_routes.py` for optional instruction reads and legacy fallback.

## Phase 4: Testing / Verification
- [x] 4.1 Add PR 1 tests in `tests/test_pack_routes.py` for missing 404, unreadable 503, and path-resolution 503.
- [x] 4.2 Add PR 2 tests in `tests/test_pull_manifest_routes.py` for missing `artifact_paths` and missing `skills/` storage.
- [x] 4.3 Run `uv run pytest` after each slice.

## Phase 5: Cleanup / Documentation
- [ ] 5.1 Remove temporary slice assumptions once the chain is stable.
- [ ] 5.2 Update change notes only after the final slice lands.
