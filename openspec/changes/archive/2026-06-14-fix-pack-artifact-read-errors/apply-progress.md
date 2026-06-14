# Apply Progress: Fix Pack Artifact Read Errors v0.3.3

## Scope
Stacked PR chain for pack artifact read errors. PR1 handled direct pack downloads; PR2 handles pull-manifest assembly for manifests that carry `artifact_paths`; PR3 adds final pull-manifest regression coverage and documents the conservative legacy fallback boundary.

## Completed Tasks
- [x] 1.1 Missing files -> 404; storage/encoding/path faults -> 503.
- [x] 1.2 `agh/server/routes/projects.py` untouched in PR1.
- [x] 2.1 Direct-pack read helpers implemented and verified.
- [x] 4.1 PR1 route tests added.
- [x] 4.3 Slice validated with `uv run pytest`.
- [x] Fresh-review coverage now proves `Path.read_text()` `OSError` maps to JSON 503.
- [x] Helper renamed to an explicit route-level requirement helper.
- [x] PR2 tasks 2.2, 2.3, 3.1, 4.2: pull-manifest expected reads now 404/503, reject symlink components, and fall back for malformed `artifact_paths`.
- [x] 3.2 PR3 stayed focused on `tests/test_pull_manifest_routes.py`: optional legacy instruction loss is skipped through discovery fallback, while expected/current instruction read `OSError` returns JSON 503.
- [x] 5.1 Removed temporary slice assumptions by documenting the final PR3 boundary as tests/spec cleanup with no runtime changes.
- [x] 5.2 Updated final change notes to make legacy no-inventory storage-loss detection intentionally deferred rather than silently implied.

## TDD Cycle Evidence
| Task | Test File | Layer | Safety Net | RED | GREEN | TRIANGULATE | REFACTOR |
|------|-----------|-------|------------|-----|-------|-------------|----------|
| 2.2 / 2.3 / 3.1 / 4.2 + risk fixes | `tests/test_pull_manifest_routes.py` | Integration | ✅ 9/9 baseline | ✅ symlink + malformed-list tests failed first | ✅ 11/11 passed | ✅ 404, 503, symlink, malformed-list fallback | ✅ Ruff format applied |
| 3.2 | `tests/test_pull_manifest_routes.py` | Integration | ✅ 11/11 baseline | ⚠️ Regression tests written first; behavior already passed on PR2 runtime, so no production RED was available | ✅ 13/13 passed with no runtime changes | ✅ legacy optional instruction fallback + expected instruction `OSError` 503 | ➖ None needed |
| 5.1 / 5.2 | `openspec/changes/fix-pack-artifact-read-errors/specs/pack-artifact-read-errors/spec.md`, `tasks.md`, `apply-progress.md` | Documentation | N/A (artifacts only) | ➖ Structural cleanup/change notes | ✅ Artifact updates applied | ➖ Single documentation outcome | ✅ Spec now matches documented deferred legacy boundary |

## Validation
- `uv run pytest tests/test_pack_routes.py` -> 23 passed baseline.
- Tests-only RED -> 2 failed, 24 passed.
- After implementation -> 26 passed; after final regression coverage -> 27 passed.
- `uv run ruff check ...` and `uv run ruff format --check ...` passed.
- `uv run pytest` -> 274 passed; later `uv run pytest -q` -> 275 passed.
- PR2 review fix: RED showed 2 failures; GREEN targeted 11 passed; final full suite 282 passed, ruff passed, pyright passed.
- PR3 safety net: `uv run pytest tests/test_pull_manifest_routes.py -q` -> 11 passed, 1 warning.
- PR3 targeted: `uv run pytest tests/test_pull_manifest_routes.py -q` -> 13 passed, 1 warning.
- PR3 full suite: `uv run pytest -q` -> 284 passed, 1 warning.
- PR3 quality: `uv run ruff check .` -> passed; `uv run ruff format --check .` -> 52 files already formatted.
- PR3 typecheck: `uv run pyright` unavailable in the local environment (`Failed to spawn: pyright`).

## Boundary Note
Final PR3 intentionally does not add runtime logic or producer-side `artifact_paths` changes in `agh/server/routes/packs.py`. Expected/current artifacts identified by `artifact_paths` now have explicit regression coverage for 404/503 behavior. Legacy manifests without artifact inventory remain conservative discovery fallback: missing optional instruction/skill files may be skipped, and full historical storage-loss detection is deferred until a future design can distinguish intentionally absent optional files from lost stored files.
