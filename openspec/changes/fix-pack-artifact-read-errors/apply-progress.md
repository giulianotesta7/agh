# Apply Progress: Fix Pack Artifact Read Errors v0.3.3

## Scope
PR1 only: direct pack download safety in `agh/server/routes/packs.py` with `tests/test_pack_routes.py`. Pull-manifest work stays in later stacked PRs.

## Completed Tasks
- [x] 1.1 Missing files -> 404; storage/encoding/path faults -> 503.
- [x] 1.2 `agh/server/routes/projects.py` untouched in PR1.
- [x] 2.1 Direct-pack read helpers implemented and verified.
- [x] 4.1 PR1 route tests added.
- [x] 4.3 Slice validated with `uv run pytest`.
- [x] Fresh-review coverage now proves `Path.read_text()` `OSError` maps to JSON 503.
- [x] Helper renamed to an explicit route-level requirement helper.

## Validation
- `uv run pytest tests/test_pack_routes.py` -> 23 passed baseline.
- Tests-only RED -> 2 failed, 24 passed.
- After implementation -> 26 passed; after final regression coverage -> 27 passed.
- `uv run ruff check ...` and `uv run ruff format --check ...` passed.
- `uv run pytest` -> 274 passed; later `uv run pytest -q` -> 275 passed.

## Boundary Note
This file now records only PR1 progress; later pull-manifest work is intentionally excluded.
