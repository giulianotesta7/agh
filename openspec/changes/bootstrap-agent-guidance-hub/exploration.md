# Exploration: Bootstrap Agent Guidance Hub MVP

## Current State

`aictx` is harness-only: `openspec/config.yaml` contains approved AGH decisions, `.pi/settings.json` contains SDD model routing, `.atl/skill-registry.md` exists, and `.gitignore` ignores only local Pi/ATL state. There is no FastAPI/Typer application code, tests, CI, or `openspec/specs/` yet. This exploration is therefore spec-driven rather than code archaeology.

## Affected Areas

| Area | Role |
|------|------|
| `agh/server/` | FastAPI app, `/api/v1`, auth middleware, bootstrap, logging |
| `agh/cli/` | Typer CLI: login, config, project, user, token, pack, sync, agent, pull |
| `agh/common/` | Prefixed IDs, pack manifest validation, URL normalization, checksums |
| SQLite + `/data/` | Metadata DB, pack storage, logs, bootstrap secret |
| `openspec/changes/bootstrap-agent-guidance-hub/specs/*` | Capability requirements for the MVP |
| Consumer repos | `.agh/project.toml`, `.agh/lock.toml`, managed blocks, agent skill paths |

## Approaches

| # | Approach | Pros | Cons | Effort |
|---|----------|------|------|--------|
| 1 | One SDD change + chained apply | Coherent MVP planning; keeps decisions together | Large `tasks.md`; implementation must be sliced carefully | Medium planning / High build |
| 2 | Multiple SDD changes (`agh-auth`, `agh-packs`, etc.) | Smaller review units per phase | Integration gaps and duplicated context | High process |
| 3a | Single Python package with server/cli/common modules | Fast bootstrap; shared code for models/validation | Can grow fat if dependencies are not separated carefully | Low |
| 3b | Split packages/wheels (`agh-server`, `agh-cli`) | Cleaner install boundaries | Packaging overhead before MVP value | Medium |
| 4a | Managed marker blocks + checksums | Matches product requirements; protects manual edits | Highest local merge/conflict complexity | High |
| 4b | Full-file replace + skill symlinks | Simpler implementation | Violates approved conflict policy and weakens trust | Medium |
| 5a | Aggregate pull-manifest API | One stable CLI round-trip for pull; simple client orchestration | Requires designing response schema early | Medium |

## Recommendation

1. Use **one SDD change**: `bootstrap-agent-guidance-hub`.
2. Plan implementation as **chained PR/apply slices** because the 400-line review budget risk is high.
3. Use a single Python distribution with internal modules: `agh.server`, `agh.cli`, and `agh.common`.
4. Keep managed marker blocks/checksums and a dedicated pull-manifest endpoint in scope.
5. Create capability specs for: `auth`, `storage`, `api`, `projects`, `packs`, `cli`, and `workspace`.
6. Make the first implementation slice add `pytest` and update `openspec/config.yaml` test commands.

## Suggested Apply Slices

| Slice | Scope | Budget risk |
|-------|-------|-------------|
| A | `pyproject`, Docker, health endpoint on `:8912`, logging, pytest | Low |
| B | DB, bootstrap owner, token hashing, `/me`, `agh login` | Medium |
| C | User roles/CRUD, owner protection, token rotation/reset | Medium |
| D | Projects, URL normalization, membership, CLI project commands | Medium-High |
| E | Packs, `agh.pack.toml`, publish, immutable versions | High |
| F | Project-pack assignment | Medium |
| G | `agh sync`, `.agh/project.toml` | Medium |
| H | `agh pull`, lockfile, cache, markers, agents, conflicts | High; split further |

## Capabilities for Proposal/Spec

| Capability | Domain |
|------------|--------|
| Bootstrap owner + initial token file | `auth` |
| Token hashing, email user id, no auto-expiry | `auth` |
| `owner` / `admin` / `member` roles | `auth` |
| Prefixed IDs | `api` |
| Projects + normalized repo URL | `projects` |
| Role-less project membership | `projects` |
| Pack + immutable versions | `packs` |
| Project-pack assignments with `latest` support | `projects` |
| CLI config + login | `cli` |
| `agh sync`, `agh pull`, lock, cache | `workspace` |
| Claude + OpenCode integrations with availability indicators | `workspace` |
| VCS guidance: commit project+lock; ignore packs cache | `workspace` |
| Container stdout/file logging | `storage` |

## Open Questions

1. Exact managed-block delimiter grammar and checksum algorithm.
2. Auth header format: `Authorization: Bearer` vs custom header.
3. Detailed pack domain/name validation rules.
4. Pull-manifest field list and pack ordering semantics.
5. Alembic vs lightweight manual migrations for SQLite MVP.
6. Conflict exit codes for edited managed blocks and non-managed file collisions.
7. Backend behavior for duplicate normalized repo URLs.
8. Symlink vs copy fallback for skills on Windows.

## Out of Scope for This Change

- Web UI.
- SSO/LDAP.
- Automatic token expiry.
- Pack signing.
- Webhooks.
- HA/S3 storage.
- Public marketplace.
- Cursor/Codex/Pi integrations beyond the initial Claude/OpenCode MVP.
- Manual `agh sync --project` override.
- `default.md` instruction fallback.
- Publish approval workflows.
- Offline-only pack publishing.

## Ready for Proposal

Yes. Proceed to `sdd-proposal` with this exploration as the source for problem statement, scope, capabilities, non-goals, and open decisions.
