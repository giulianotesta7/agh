# Proposal: Package Nomenclature UX

## Intent

AGH exposes reusable guidance artifacts as `pack` across CLI, API, DB, storage, lockfiles, docs, tests, and errors. Rename the product language to `package` / `packages` and preserve existing DB rows and filesystem artifacts.

## Scope

### In Scope
- Rename every `pack` / `packs` surface to `package` / `packages`.
- Break old CLI/API contracts: only `agh package ...`, `/api/v1/packages`, `/api/v1/projects/{id}/packages`.
- Migrate persistence to `packages`, `package_versions`, `project_packages`, `/data/packages`, `.agh-cache/packages`, `[[packages]]`, `package_ref`.
- Keep IDs as `pkg_...` / `pkgv_...`; keep assignments as `asn_...`.
- Add interactive discovery when `agh project package add <project>` omits ref.

### Out of Scope
- No `agh pkg`, `agh pack`, `agh.pack.toml`, old API/storage compatibility.
- No authoring wizard/composer; authoring stays folder-based with `agh.package.toml`.
- No model change.

## Capabilities

### New Capabilities
- `guidance-packages`: Package lifecycle, terminology, routes, persistence names, lock/cache names, and assignment UX.

### Modified Capabilities
- `cli-usage-errors`: command groups become package/project package.
- `pack-artifact-read-errors`: package artifact wording and migrated paths.
- `workspace-pull-atomicity`: package cache/lock entries remain atomic.
- `docker-runtime-hardening`: image-owned data tree uses `/data/packages`.

## User-visible Behavior Changes

- `agh pack ...` fails as unknown; `agh package ...` is canonical.
- Local authoring uses `agh.package.toml` only.
- Explicit refs remain direct for CI/advanced use.
- Without ref, show only unassigned latest-stable `domain/name@version` choices, then confirm.
- If none are assignable, suggest `list` / `update`.
- Cancelled confirmation prints `Cancelled.` and exits 130.

## Approach

Implement one hard rename with backup-first migrations and no legacy runtime support. Split specs by package contract, CLI UX, API/DB/storage, and pull/cache/lock behavior for reviewable slices under 400 lines.

## Affected Areas

| Area | Impact | Description |
|------|--------|-------------|
| `agh/cli/*`, `tests/*` | Modified | CLI, help, errors, interactive add |
| `agh/server/routes/*` | Modified | package APIs and assignments |
| `agh/server/migrations/*`, `/data/*` | Modified | DB/filesystem migration |
| `agh/common/*`, `.agh/lock.toml` | Modified | IDs, manifest, validation, lock/cache |
| `README*.md`, `openspec/specs/*` | Modified | docs/spec terminology |

## Risks and Rollout

| Risk | Likelihood | Mitigation |
|------|------------|------------|
| Data loss during migration | Med | Backup-first migration tests |
| Broken automation | High | Document breaking CLI/API policy |
| Incomplete rename | Med | Tests plus grep for forbidden old surfaces |

## Rollback Plan

Revert code/spec changes and restore DB/filesystem backups. Rollback is release-level, not dual-mode fallback.

## Dependencies

- Existing publish/version resolution.
- Migration design.

## Success Criteria

- [ ] No-legacy breaking-change policy and data preservation are explicit.
- [ ] Spec-phase capabilities are named.
- [ ] Interactive add UX and cancellation behavior are covered.
