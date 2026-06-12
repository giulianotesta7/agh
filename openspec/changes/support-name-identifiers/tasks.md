## Review Workload Forecast

| Field | Value |
|-------|-------|
| Estimated changed lines | 650-900 across full chain; PR1 is the project-ref slice only |
| 400-line budget risk | High for the full change; managed with chained PRs |
| Chained PRs recommended | Yes |
| Suggested split | PR 1 project refs -> PR 2 user email refs -> PR 3 pack-version refs |
| Delivery strategy | ask-on-risk (ask-always preflight) |
| Chain strategy | stacked-to-main |

Decision needed before apply: Yes
Chained PRs recommended: Yes
Chain strategy: stacked-to-main
400-line budget risk: High

### Suggested Work Units

| Unit | Goal | Likely PR | Notes |
|------|------|-----------|-------|
| 1 | Project lookup, project validation, migration, CLI project refs | PR 1 | Include route, migration, validation, CLI, and docs guidance tests. |
| 2 | User email lookup and CLI user refs | PR 2 | Base after PR 1; include user route and CLI admin tests. |
| 3 | Pack-version resolver endpoint/parser and CLI pack refs | PR 3 | Base after PR 2; include API/unit/CLI pack tests. |

## Phase 1: PR1 Foundation / Project Data Rules

- [x] 1.1 Modify `agh/common/validation.py` with `validate_project_name()`; cover in `tests/test_common_helpers.py`.
- [x] 1.2 Create `agh/server/migrations/002_unique_project_names.sql` adding `ux_projects_name`; cover duplicate-data failure in `tests/test_db_migrations.py`.
- [x] 1.3 Update `agh/server/routes/projects.py` create/update validation and duplicate-name 409 mapping; test in `tests/test_project_routes.py`.

## Phase 2: PR1 Server Project Resolver API

- [x] 2.1 Add `GET /projects/by-name/{name:path}` before dynamic project routes in `agh/server/routes/projects.py`; test exact, scope, and 404 behavior.

## Phase 3: PR1 CLI Project Resolution

- [x] 3.1 Add shared project ref classifier/resolver in `agh/cli/project_refs.py`; malformed local project refs exit 2 and HTTP 401 exits 4 with re-login guidance.
- [x] 3.2 Resolve project refs for get/update/delete/member/pack commands; keep `prj_...` and all-digit passthrough and cover CLI tests.
- [x] 3.3 Update CLI/help/docs guidance for project refs and cover in `tests/test_docs_guidance.py`.

## Phase 4: PR1 Verification

- [x] 4.1 Run targeted `uv run pytest tests/test_common_helpers.py tests/test_db_migrations.py tests/test_project_routes.py tests/test_cli_admin_commands.py tests/test_cli_pack_commands.py tests/test_docs_guidance.py`.
- [x] 4.2 Run full `uv run pytest`; verify existing ID-based scripts remain unchanged.

## Future PR2: User Email Refs

- [x] Add `GET /users/by-email/{email:path}` before `/{user_id}` in `agh/server/routes/users.py`; test exact, active, auth, 400, 404/hidden cases.
- [x] Add `agh user show` and resolve user refs for show/update/delete/token/member commands; keep `usr_...` passthrough and cover in `tests/test_cli_admin_commands.py`.

## Future PR3: Pack Version Refs

- [x] Add pack-version ref parsing helpers; cover in `tests/test_common_helpers.py`.
- [x] Add `GET /packs/versions:resolve` in `agh/server/routes/packs.py`; test canonical `pack_ref`, malformed, missing, and ambiguous no-domain refs.
- [x] Resolve project-pack `pack_ref` inputs through the pack resolver when needed; update CLI help text and `tests/test_docs_guidance.py`.
