# Design: Fix Review Findings First Slice

## Technical Approach

Implement only the first remediation slice: pack publish hardening and request body validation. The server will capture the startup data directory in `FastAPI.state`, pack routes will derive publish storage from that state instead of request-time environment reads, and publish recovery will clean only final pack directories that are safely under the pack root and proven to have no database row. The `Content-Length` middleware will parse defensively so malformed values return JSON `400` while body-size violations keep the existing JSON `413` behavior.

## Architecture Decisions

| Decision | Choice | Alternatives considered | Rationale |
|---|---|---|---|
| Startup storage state | Store `application.state.data_dir = data_dir.resolve()` in `agh/server/app.py`; `packs.py` reads it via a small helper. | Continue calling `get_data_dir()` inside routes; introduce a settings object. | Fixes drift with minimal surface area and follows the existing app-state pattern already used for `db_path`. A settings object is broader than this slice needs. |
| Orphan recovery | Remove an existing final storage directory only after confirming no canonical `pack_versions` row and no row referencing that storage path. | Reorder DB/file writes; reuse existing files; delete any existing target. | Conservative cleanup addresses crash leftovers without broad transactional refactoring. Reusing files is harder to validate; unconditional deletion risks valid data. |
| Request-size validation | Add a tiny parser/helper around `Content-Length`; invalid, empty, signed, or negative values return `400`; values over `MAX_PACK_PUBLISH_BODY_BYTES` return `413`. | Let Starlette/FastAPI handle it; catch `ValueError` generically. | Keeps the route-specific JSON contract explicit and prevents uncontrolled middleware exceptions. |

## Data Flow

```text
create_app()
  ├─ resolve startup data_dir ──→ app.state.data_dir
  └─ derive db_path ────────────→ app.state.db_path

POST /api/v1/packs
  ├─ validate Content-Length: invalid → 400, oversized → 413
  ├─ stage payload under state.data_dir/packs/.staging
  ├─ validate manifest and checksum staged files
  ├─ BEGIN IMMEDIATE
  ├─ reject existing DB version → 409
  ├─ if final dir exists: prove orphan → clean; ambiguous → fail closed
  ├─ copy staged files to final dir
  └─ insert pack_versions row and commit
```

## File Changes

| File | Action | Description |
|------|--------|-------------|
| `agh/server/app.py` | Modify | Resolve/store startup `data_dir`; replace raw `int(content_length)` with safe parser and JSON `400` response. |
| `agh/server/routes/packs.py` | Modify | Use `request.app.state.data_dir`; add focused helpers for storage-path safety, DB-reference checks, and proven-orphan cleanup. |
| `tests/test_pack_routes.py` | Modify | Add regression tests for request-time `AGH_DATA_DIR` drift, proven orphan cleanup, and ambiguous storage preservation. |
| `tests/test_api_errors.py` or `tests/test_pack_routes.py` | Modify | Add invalid `Content-Length` JSON `400` tests and preserve oversized `413` coverage. |

## Interfaces / Contracts

- `application.state.data_dir: Path` is the startup-derived storage root for filesystem-backed server state.
- `application.state.db_path: Path` remains the startup-derived SQLite database path.
- Publish storage path remains `{data_dir}/packs/{domain}/{name}/{version}`.
- Invalid `Content-Length` response: `HTTP 400` with JSON `{"detail": "invalid content-length header"}`.
- Oversized publish response remains: `HTTP 413` with JSON `{"detail": "pack publish payload is too large"}`.

## Testing Strategy

| Layer | What to Test | Approach |
|-------|-------------|----------|
| Unit | `Content-Length` parsing boundaries and orphan-reference checks. | Small helper-level tests if helpers are public enough; otherwise route-level regression tests. |
| Integration | Publish uses startup data dir despite environment mutation. | Start app with one `AGH_DATA_DIR`, mutate env, publish, assert files and DB row point to startup root. |
| Integration | Proven orphan final directory is cleaned and republish succeeds. | Create final directory without DB row, publish same version, assert success and replacement content. |
| Integration | Ambiguous storage is preserved. | Create DB row referencing target storage path or symlinked/unsafe target, publish, assert failure and no deletion. |
| E2E | Not required for this slice. | Existing API tests cover server behavior. |

## Migration / Rollout

No data migration required. Roll out as a narrow first PR; if changed lines exceed the 400-line review budget, split tests and implementation into a chained slice before apply.

## Deferred Follow-up Changes

- Unknown CLI command exit-code policy.
- Missing/corrupt pack files returning `500`.
- Git subprocess timeout handling.
- Non-atomic workspace pull behavior.
- Duplicate project-name migration startup risk.
- Docker mutable tag/root-default hardening.
- Broad CLI HTTP handling and large-module refactors.

## Open Questions

None.
