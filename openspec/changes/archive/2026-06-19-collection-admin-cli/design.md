# Design: Collection Admin CLI

## Technical Approach

Add a thin Typer facade in `agh/cli/main.py` for admin-only `agh collection ...` commands. Add an authenticated `GET /api/v1/collections/by-name/{name:path}` route analogous to project by-name lookup, then resolve non-`col_...` CLI collection refs before calling ID-based collection/package endpoints. `_api_request` continues to provide configured server, saved `agh login` credentials, redirect refusal, token redaction, and 401/403 exit code behavior. No collection-specific auth, server flags, or `agh skill ...` consumer changes are introduced.

## Architecture Decisions

| Decision | Choice | Alternatives considered | Rationale |
|---|---|---|---|
| CLI shape | Add `collection_app` plus nested `collection_package_app` in `agh/cli/main.py`. | Extend `agh skill ...` or add a new module now. | Existing admin CLI commands live in `main.py`; keeping `collection` separate preserves the admin/consumer split. |
| API usage | Map commands 1:1 to existing collection endpoints via `_api_request`. | Add client orchestration or new server behavior. | Server already owns auth, active/inactive visibility, skill-only validation, duplicate handling, and `casn_` assignment IDs. |
| Collection targeting | Accept `col_...` IDs or exact active collection names by adding `/collections/by-name/{name:path}` and a CLI resolver. | Keep explicit IDs only. | Project CLI already supports by-name refs; collection admin UX should be consistent while server-side exact/active lookup avoids client list filtering. |
| Package assignment UX | Mirror project package commands for list/add/update/remove, requiring an explicit package ref on add. | Reuse project interactive available-package picker. | There is no collection `packages:available` endpoint, and only the server can safely validate skill-only packages. |

## Data Flow

```text
agh collection package add "Team Skills" acme/reviewer@latest
  -> resolve_collection_ref("Team Skills") via GET /collections/by-name/Team%20Skills
  -> _resolve_package_version_ref(...) when needed
  -> _api_request("POST", "/collections/col_123/packages", body)
  -> server validates owner/admin, active collection, and skill-only package
  -> CLI prints human output using existing table/detail conventions
```

Canonical `col_...` refs bypass name resolution. Collection deactivation uses `DELETE /collections/{collection_id}`, which already delegates to `active=false`, matching project deactivation semantics.

## File Changes

| File | Action | Description |
|---|---|---|
| `agh/server/routes/collections.py` | Modify | Add `GET /collections/by-name/{name:path}` returning `{id, name}` for exact, active, visible collections. |
| `agh/cli/collection_refs.py` | Create | Mirror `project_refs.py`: pass through `col_...`, quote name refs, validate resolver payload. |
| `agh/cli/main.py` | Modify | Register `agh collection`, add output helpers, CRUD commands, and nested `package` assignment commands. |
| `tests/test_collection_routes.py` | Modify | Cover resolver auth, exact matching, active-only behavior, and visibility. |
| `tests/test_cli_admin_commands.py` | Modify | Add HTTP-stub tests for command registration, collection ref resolution, request paths/bodies, output, auth exit code, and token redaction. |
| `README.md` | Modify | Document admin collection commands and `casn_` package assignment IDs. |
| `README.es.md` | Modify | Mirror the admin collection command documentation in Spanish. |
| `agh/cli/global_skills.py` | No change | Consumer global-skill behavior stays under `agh skill ...`. |

## Interfaces / Contracts

```http
GET /api/v1/collections/by-name/{name:path}
200 {"id": "col_...", "name": "Team Skills"}
404 when the name is not an exact active visible collection
```

```text
agh collection list
agh collection create NAME [--description TEXT]
agh collection get COLLECTION_REF
agh collection update COLLECTION_REF [--name TEXT] [--description TEXT] [--active/--inactive]
agh collection delete COLLECTION_REF
agh collection package list COLLECTION_REF
agh collection package add COLLECTION_REF PACKAGE_REF [--position N]
agh collection package update COLLECTION_REF casn_... [--package-ref PACKAGE_REF] [--position N] [--active/--inactive]
agh collection package remove COLLECTION_REF casn_...
```

`COLLECTION_REF` is a canonical `col_...` ID or exact active collection name.

CLI response helpers should follow existing admin output style: tables for list commands, concise detail lines for mutations, no raw JSON for successful admin flows, and no plaintext saved-token leakage.

## Testing Strategy

| Layer | What to Test | Approach |
|---|---|---|
| Unit/CLI | Typer command registration, ref resolution, request mapping, bodies, output, and exit codes. | Add failing tests first in `tests/test_cli_admin_commands.py` using existing HTTP stubs. |
| Integration | Collection by-name route auth/exact/active behavior plus existing `casn_` and skill-only rejection. | Add focused route tests in `tests/test_collection_routes.py`; rely on existing package assignment tests. |
| E2E | Whole project behavior after CLI/docs changes. | Run `uv run pytest` after focused CLI tests pass. |

## Migration / Rollout

No migration required. Deliver implementation in PR slices under the 400-line review budget, likely CLI/tests first and documentation separately if needed.

## Open Questions

None.
