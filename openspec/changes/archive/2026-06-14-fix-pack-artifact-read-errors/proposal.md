# Proposal: Fix Pack Artifact Read Errors v0.3.3

## Intent
Make published pack artifact reads fail predictably: 404 for missing/unsafe expected files, 503 for unreadable/corrupt/I/O failures.

## Scope
- In: direct downloads now; pull-manifest assembly later.
- Out: storage repair, layout changes, client changes, publish validation.

## Approach
Use small route-local classification helpers at read points, keep existing FastAPI `{ "detail": ... }` errors, and preserve path-safety checks.

## Affected Areas
- `agh/server/routes/packs.py` — PR1 direct-download classification.
- `tests/test_pack_routes.py` — PR1 coverage.
- `agh/server/routes/projects.py` — PR2 pull-manifest slice.
- `tests/test_pull_manifest_routes.py` — later regression coverage.

## Risks and Rollback
Avoid turning unsafe paths into storage errors. Roll back by reverting the route/test diff; no data or schema changes.
