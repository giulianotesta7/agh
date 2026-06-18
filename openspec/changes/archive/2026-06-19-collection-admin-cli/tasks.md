# Tasks: Collection Admin CLI

## Review Workload Forecast

| Field | Value |
|-------|-------|
| Estimated changed lines | 650-900 across tests, CLI, route, docs |
| 400-line budget risk | High |
| Chained PRs recommended | Yes |
| Suggested split | PR 1 backend by-name → PR 2 CLI CRUD → PR 3 CLI packages/docs |
| Delivery strategy | ask-on-risk |
| Chain strategy | stacked-to-main |

Decision needed before apply: No
Chained PRs recommended: Yes
Chain strategy: stacked-to-main
400-line budget risk: High

### Suggested Work Units

| Unit | Goal | Likely PR | Notes |
|------|------|-----------|-------|
| 1 | Add collection by-name backend support | PR 1 | Isolate `agh/server/routes/collections.py` + route tests. |
| 2 | Add `agh collection` CRUD CLI | PR 2 | Depends on PR 1 for name refs; include CLI tests. |
| 3 | Add collection package CLI and docs | PR 3 | Depends on PR 2; include package tests and README updates. |

## Phase 1: Backend By-Name Resolver (PR 1)

- [x] 1.1 Add failing tests in `tests/test_collection_routes.py` for authenticated exact-name lookup, inactive 404, case mismatch 404, and visibility scope.
- [x] 1.2 Add `GET /collections/by-name/{name:path}` in `agh/server/routes/collections.py`, returning only exact active visible `{id, name}` matches.
- [x] 1.3 Run `uv run pytest tests/test_collection_routes.py` and keep existing collection CRUD/package behavior passing.

## Phase 2: Collection Ref Foundation and CRUD CLI (PR 2)

- [x] 2.1 Add failing HTTP-stub tests in `tests/test_cli_admin_commands.py` for `agh collection` registration and CRUD path/body mapping.
- [x] 2.2 Add failing CLI tests for `col_...` pass-through and exact-name resolver calls before targeted operations.
- [x] 2.3 Create `agh/cli/collection_refs.py` to pass through `col_...`, quote name refs, and validate resolver payloads.
- [x] 2.4 Update `agh/cli/main.py` with `collection_app`, list/create/show/update/delete commands, and project-style active=false delete output.
- [x] 2.5 Run `uv run pytest tests/test_cli_admin_commands.py tests/test_collection_routes.py`.

## Phase 3: Collection Package CLI (PR 3)

- [x] 3.1 Add failing HTTP-stub tests in `tests/test_cli_admin_commands.py` for `collection package list/add/update/remove` paths, bodies, and `casn_...` targets.
- [x] 3.2 Add failing tests proving package commands resolve collection names, skip resolver for `col_...`, and surface server skill-only rejection.
- [x] 3.3 Update `agh/cli/main.py` with nested `collection package` commands mirroring project package assignment, using skill-only server validation.
- [x] 3.4 Run `uv run pytest tests/test_cli_admin_commands.py tests/test_collection_package_assignments.py`.

## Phase 4: Documentation and Final Verification (PR 3)

- [x] 4.1 Update `README.md` with admin `agh collection` CRUD/package examples, login reuse, and `casn_...` assignment IDs.
- [x] 4.2 Update `README.es.md` with equivalent collection admin CLI documentation.
- [x] 4.3 Run full verification: `uv run pytest`.
