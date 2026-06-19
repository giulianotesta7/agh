# Proposal: Collection Admin CLI

## Intent

Admins can manage collections only through the API today. Add `agh collection ...` so owners/admins can manage collections and skill-only package assignments using the configured AGH server and existing `agh login`. Collection targets must support exact-name references, matching project by-name behavior.

## Scope

### In Scope
- Add admin-only `agh collection` CRUD commands.
- Add `agh collection package` assignment commands for skill-only packages.
- Add collection by-name resolution for active collections.
- Reuse existing auth, output style, and CLI HTTP test patterns.
- Document the admin CLI surface.

### Out of Scope
- Consumer global-skill UX changes under `agh skill ...`.
- Parallel auth, collection-specific server flags, or bypassing `agh login`.
- Server-side business-rule changes beyond by-name resolution.

## Capabilities

### New Capabilities
- None.

### Modified Capabilities
- `global-skill-collections`: Add admin CLI requirements for collection CRUD, ID/name target resolution, and package assignments while keeping consumer `agh skill ...` separate.

## Approach

Implement a thin Typer wrapper over `/api/v1/collections` and `/api/v1/collections/{collection_id}/packages`. Add `GET /api/v1/collections/by-name/{name:path}` analogous to projects; resolve non-`col_...` CLI refs through it. Follow existing `project` shape, `_api_request`, formatting, and HTTP-stub tests. Deactivation uses project-style active=false semantics. Package assignment mirrors projects, with server-enforced skill-only packages.

## Affected Areas

| Area | Impact | Description |
|------|--------|-------------|
| `agh/cli/main.py` | Modified | Register `collection` admin commands. |
| `tests/test_cli_admin_commands.py` | Modified | Cover CRUD, ref resolution, and package assignment. |
| `README.md`, `README.es.md` | Modified | Document admin collection commands. |
| `agh/server/routes/collections.py` | Modified | Add authenticated exact-name resolver for active collections. |
| `tests/test_collection_routes.py` | Modified | Cover by-name auth, exact match, visibility, and inactive behavior. |

## Risks

| Risk | Likelihood | Mitigation |
|------|------------|------------|
| CLI surface exceeds review budget. | Med | Split into PR slices under 400 changed lines. |
| Admin and consumer flows blur. | Med | Keep `agh collection ...` separate from `agh skill ...`. |
| CLI masks auth/server errors. | Low | Reuse `_api_request` handling and test 401/403 paths. |

## Rollback Plan

Remove `collection` CLI registration, the by-name route, related tests/docs, and CLI-only helpers. Existing consumer `agh skill ...` behavior remains unchanged.

## Dependencies

- Existing collection CRUD/package endpoints.
- New collection by-name resolver.
- Existing `agh login` config/token handling.

## Success Criteria

- [ ] Owners/admins can manage collections and package assignments from the CLI.
- [ ] Collection-targeted CLI commands accept `col_...` IDs or exact active collection names.
- [ ] Members cannot mutate collections and receive clear authorization failures.
- [ ] Collection package assignment accepts skill-only targets and surfaces server validation failures.
- [ ] `agh skill ...`, `agh login`, and server selection behavior remain unchanged.
