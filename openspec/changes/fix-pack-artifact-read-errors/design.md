# Design: Fix Pack Artifact Read Errors v0.3.3

## Technical Approach
Add route-local helpers for published artifact reads. Missing/unsafe expected artifacts return 404; read/decode/permission/path-resolution `OSError` failures return 503. Success paths and schemas stay unchanged.

## Decisions
- Keep helpers in the route layer for the smallest safe diff.
- Preserve FastAPI `HTTPException` `{ "detail": ... }` shape.
- Check path safety before file reads.
- Split pull-manifest work into later PRs to protect the budget.

## PR1 Data Flow
`GET /packs/{domain}/{name}/versions/{version}/files/{path}` → validate path → resolve storage target → reject unsafe/missing files with 404 → map read/decode/OSError to 503 → return text/plain on success.

## File Plan
- `agh/server/routes/packs.py` — PR1 direct-download helper/classification.
- `tests/test_pack_routes.py` — PR1 missing 404, unreadable 503, path-resolution 503.
- `agh/server/routes/projects.py` — PR2 pull-manifest classification.
- `tests/test_pull_manifest_routes.py` — PR2/PR3 regression coverage.

## Testing
Use focused pytest cycles for the slice, then run the full suite after PR1.
