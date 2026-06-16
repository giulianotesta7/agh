# Design: Package Nomenclature UX

## Technical Approach

Implement one breaking rename from pack/packs to package/packages across runtime code, tests, docs, API, SQLite schema, server storage, workspace cache, lockfiles, and managed markers. Compatibility code is limited to forward migrations that preserve existing data; no `agh pack`, `agh pkg`, `agh.pack.toml`, or `/api/v1/packs` runtime contract remains.

## Architecture Decisions

| Concern | Options / tradeoff | Decision |
|---|---|---|
| Rename strategy | Aliases reduce breakage but keep dual vocabulary. | Hard rename only; old names are rejected or unknown. |
| Module naming | Keep `pack_*` modules to shrink diff, or rename for clarity. | Rename modules/classes/helpers to package names and delete old imports. |
| DB migration | Edit only initial schema, or add forward migration. | Add `003_rename_packs_to_packages.sql` for deployed DBs; runtime queries use only new tables. |
| Storage migration | SQL-only path rewrite risks missing files. | Run a startup post-migration repair that moves `/data/packs` to `/data/packages` and updates `package_versions.storage_path`. |
| Interactive add | Client-side filtering is simpler but races and duplicates latest logic. | Add a project-scoped available-packages API; POST assignment remains authoritative. |

## Data Flow

```text
startup -> SQL migrations -> package tables/pkg IDs -> storage repair -> FastAPI runtime

agh project package add <project>
  explicit ref -> resolve package version -> POST assignment
  omitted ref  -> GET available latest refs -> prompt -> confirm -> POST assignment

agh project package add
  require TTY -> GET visible projects -> prompt project -> GET available latest refs
  -> prompt package -> confirm -> POST assignment
```

## File Changes

| File | Action | Description |
|---|---|---|
| `agh/cli/main.py` | Modify | Register `package_app` and `project_package_app`; remove `pack` groups; add omitted-ref prompt and exit 130 cancellation. |
| `agh/cli/pack_init.py`, `agh/cli/pack_publish.py`, `agh/cli/pack_refs.py` | Rename | Become `package_init.py`, `package_publish.py`, `package_refs.py`; use `agh.package.toml` and package wording. |
| `agh/common/pack_manifest.py`, `agh/common/validation.py`, `agh/common/ids.py` | Rename/modify | Use `PackageManifest`, `parse_package_ref`, `pkg`/`pkgv` prefixes; keep `asn`. |
| `agh/server/routes/packs.py` | Rename | Become `packages.py` with `/packages`, `/packages/versions:resolve`, file download, and publish storage under `/data/packages`. |
| `agh/server/routes/projects.py` | Modify | Rename project package endpoints, responses, pull-manifest package keys, download URLs, and available-package listing. |
| `agh/server/app.py`, `agh/server/db.py`, `agh/server/migrations/003_rename_packs_to_packages.sql` | Modify/Create | Include packages router, update publish-size middleware path, run DB + filesystem migration. |
| `agh/cli/workspace_pull.py`, `agh/cli/pull_markers.py`, `agh/cli/pull_plan.py` | Modify | Expect manifest `packages`, cache `.agh-cache/packages`, lock `[[packages]]`, artifact `package_ref`, marker `package="..."`. |
| `tests/*`, `README*.md`, `Dockerfile`, `openspec/specs/*` | Modify | Rename expectations, docs, data directory creation, and capability specs. |

## Interfaces / Contracts

- CLI: `agh package list|init|publish`; `agh project package list|add|update|remove`. `agh project package add <project> <ref>` is non-interactive. `agh project package add <project>` requires a TTY for package selection; non-TTY exits 2 before API calls. `agh project package add` requires a TTY, lists visible projects with `GET /projects`, then reuses the selected project's package selector; non-TTY exits 2 before API calls. A single positional argument is always treated as the project ref. Prompt cancellation prints `Cancelled.` and exits 130.
- API: `/api/v1/packages`, `/api/v1/packages/versions:resolve`, `/api/v1/packages/{domain}/{name}/versions/{version}/files/{path}`, `/api/v1/projects/{id}/packages`, `/api/v1/projects/{id}/packages/{asn}`, and `GET /api/v1/projects/{id}/packages:available` returning unassigned latest exact SemVer refs with descriptions.
- JSON keys: `packages`, `project_packages`, `package_id`, `package_ref`, `resolved_ref`; pull-manifest top-level `packages`.
- SQLite: `packages(id pkg_..., domain, name, created_by)`, `package_versions(id pkgv_..., package_id, version, manifest_json, storage_path, checksum)`, `project_packages(id asn_..., project_id, package_id, version_ref, position, active)`.
- Local files: `agh.package.toml`; `.agh-cache/packages/...`; `.agh/lock.toml` uses `[[packages]]` and `package_ref`.

## Testing Strategy

| Layer | What to Test | Approach |
|---|---|---|
| Unit | IDs, ref parsing, manifest loader, marker rendering, lock TOML | Write failing tests first in `tests/test_common_helpers.py`, `test_pull_markers.py`, `test_workspace_pull.py`. |
| Migration | Table rename, ID conversion, relationships, storage path repair, idempotent retry | SQLite temp DB + temp `/data` tests before migration code. |
| API | New package routes, old routes 404, available list, assignment races, pull-manifest schema | FastAPI `TestClient` tests. |
| CLI | Typer command tree, no `pack`/`pkg`, explicit add, one-arg package selection, no-arg project+package selection, confirm/cancel, non-TTY | `CliRunner` and local HTTP test server. |
| Full suite | Regression | `uv run pytest` after each slice and before verify. |

Strict TDD applies: create or update failing tests for each slice before implementation, then refactor after green.

## Migration / Rollout

SQL migration copies/renames `packs`, `pack_versions`, `project_packs` to package tables, rewrites `pack_`/`packv_` IDs to `pkg_`/`pkgv_`, and preserves `asn_` assignment IDs. The filesystem repair creates a backup/sentinel, moves package artifacts to `/data/packages`, updates storage paths, treats already-moved rows as success, and fails closed on conflicting destinations. Rollback is release-level: stop service, restore DB/filesystem backups, and deploy previous code. Main risks are broken automation, partial DB/filesystem migration, stale workspace lock/cache files, and missed terminology in docs/tests.

## Open Questions

None.
