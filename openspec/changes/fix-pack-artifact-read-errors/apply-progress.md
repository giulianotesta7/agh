# Apply Progress: Fix Pack Artifact Read Errors v0.3.3

## Scope
Stacked PR chain for pack artifact read errors. PR1 handled direct pack downloads; PR2 handles pull-manifest assembly for current manifests that carry `artifact_paths`.

## Completed Tasks
- [x] 1.1 Missing files -> 404; storage/encoding/path faults -> 503.
- [x] 1.2 `agh/server/routes/projects.py` untouched in PR1.
- [x] 2.1 Direct-pack read helpers implemented and verified.
- [x] 4.1 PR1 route tests added.
- [x] 4.3 Slice validated with `uv run pytest`.
- [x] Fresh-review coverage now proves `Path.read_text()` `OSError` maps to JSON 503.
- [x] Helper renamed to an explicit route-level requirement helper.
- [x] PR2 tasks 2.2, 2.3, 3.1, 4.2: pull-manifest expected reads now 404/503, reject symlink components, and fall back for malformed `artifact_paths`.

## TDD Cycle Evidence
| Task | Test File | Layer | Safety Net | RED | GREEN | TRIANGULATE | REFACTOR |
|------|-----------|-------|------------|-----|-------|-------------|----------|
| 2.2 / 2.3 / 3.1 / 4.2 + risk fixes | `tests/test_pull_manifest_routes.py` | Integration | ✅ 9/9 baseline | ✅ symlink + malformed-list tests failed first | ✅ 11/11 passed | ✅ 404, 503, symlink, malformed-list fallback | ✅ Ruff format applied |

## Validation
- `uv run pytest tests/test_pack_routes.py` -> 23 passed baseline.
- Tests-only RED -> 2 failed, 24 passed.
- After implementation -> 26 passed; after final regression coverage -> 27 passed.
- `uv run ruff check ...` and `uv run ruff format --check ...` passed.
- `uv run pytest` -> 274 passed; later `uv run pytest -q` -> 275 passed.
- PR2 review fix: RED showed 2 failures; GREEN targeted 11 passed; final full suite 282 passed, ruff passed, pyright passed.

## Boundary Note
PR2 intentionally excludes legacy storage-loss checksum detection and any producer-side `artifact_paths` changes in `agh/server/routes/packs.py`; those remain PR3/follow-up scope if needed.
