# Apply Progress: fix-review-findings

## Mode

Standard — strict TDD is disabled in `openspec/config.yaml` and Engram testing capabilities for `agentguidancehub`.

## Workload / PR Boundary

- Mode: single PR
- Current work unit: pack publish hardening plus invalid `Content-Length` behavior
- Boundary: starts from the existing review findings change and ends after startup-derived storage, conservative orphan cleanup, invalid `Content-Length` JSON 400 handling, and focused regression coverage.
- Estimated review budget impact: 177 changed lines before this artifact, within the 400-line review budget.

## Completed Tasks

- [x] 1.1 Store startup `data_dir` on `app.state` alongside `db_path`.
- [x] 1.2 Read pack publish storage from `request.app.state.data_dir` instead of request-time environment lookups.
- [x] 1.3 Preserve pack path composition as `{data_dir}/packs/{domain}/{name}/{version}`.
- [x] 2.1 Use startup-derived storage consistently for pack publish staging and final paths.
- [x] 2.2 Delete/recover final pack directories only when no DB row references the target storage path.
- [x] 2.3 Fail closed and preserve final directories when DB references make orphan status ambiguous.
- [x] 2.4 Return JSON `400` for invalid `Content-Length` while preserving JSON `413` for oversized payloads.
- [x] 3.1 Add regression coverage for post-startup `AGH_DATA_DIR` drift.
- [x] 3.2 Add regression coverage for proven orphan final-pack cleanup/recovery.
- [x] 3.3 Add regression coverage for DB-referenced ambiguous final directories.
- [x] 3.4 Add request-body coverage for invalid `Content-Length` and existing oversized behavior.
- [x] 4.1 Update test names to reflect startup-derived storage and conservative cleanup rules.
- [x] 4.2 Deferred review findings remain out of scope: unknown CLI command exit 0, corrupt/missing pack files returning 500, git subprocess timeouts, non-atomic workspace pull, duplicate project-name migration startup risk, Docker mutable/root defaults, duplicated CLI HTTP handling, and large modules.

## Verification

- `uv run pytest tests/test_pack_routes.py -q` — passed: 22 tests.
- `uv run pytest tests/test_api_errors.py tests/test_pack_routes.py -q` — passed: 27 tests.

## Files Changed

| File | Action | What Was Done |
|------|--------|---------------|
| `agh/server/app.py` | Modified | Stores resolved startup data root on app state and parses `Content-Length` defensively. |
| `agh/server/routes/packs.py` | Modified | Uses startup data root for publish storage, cleans proven orphan final directories, and preserves ambiguous DB-referenced storage. |
| `tests/test_pack_routes.py` | Modified | Adds focused regression tests for storage root drift, orphan cleanup, ambiguous preservation, invalid `Content-Length`, and oversized `413`. |
| `openspec/changes/fix-review-findings/tasks.md` | Modified | Marks completed apply tasks. |
| `openspec/changes/fix-review-findings/apply-progress.md` | Created | Captures cumulative apply progress and verification evidence. |

## Deviations from Design

None — implementation matches the design.

## Issues Found

- Current `TestClient` can preserve a custom invalid `Content-Length` header when raw `content` is used, enabling route-level regression coverage without lower-level socket tests.
- Pre-existing module import behavior creates the global `app` at import time; this was observed during manual probing but is outside this slice.
