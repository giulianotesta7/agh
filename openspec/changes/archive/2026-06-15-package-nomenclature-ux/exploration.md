## Exploration: package nomenclature UX

### Current State
AGH still models the feature as `pack` end-to-end in the CLI, server routes, schema, storage paths, lockfile, and docs. The current flow is:
- CLI: `agh pack ...` and `agh project pack ...` in `agh/cli/main.py`
- Manifest: local authoring requires `agh.pack.toml` via `agh/common/pack_manifest.py`, `agh/cli/pack_init.py`, and `agh/cli/pack_publish.py`
- API: server routes are `/api/v1/packs` and `/api/v1/projects/.../packs`
- DB: tables are `packs`, `pack_versions`, `project_packs`
- Storage/cache/lock: `/data/packs`, `.agh-cache/packs`, `.agh/lock.toml` entries like `[[packs]]` and `pack_ref`
- Managed blocks: pull markers still render `AGH-BEGIN pack=...`

The good news: CLI and server already have version-ref resolution plumbing (`packv_...`, domain/name@version, name@version) that can be reused during the rename.

### Affected Areas
- `agh/cli/main.py` — primary CLI command surface; needs `package`/`pkg` aliases and interactive add flow.
- `agh/cli/pack_init.py`, `agh/cli/pack_publish.py`, `agh/common/pack_manifest.py` — local authoring manifest rename to `agh.package.toml`.
- `agh/server/routes/packs.py`, `agh/server/routes/projects.py` — API route rename from packs to packages and project package assignment endpoints.
- `agh/server/migrations/001_initial_schema.sql` — schema/table naming migration for `packs`-family storage.
- `agh/common/ids.py`, `agh/common/validation.py` — ID prefix support already includes `pack`/`packv`; needs migration to `pkg`/`pkgv` while preserving `asn`.
- `agh/cli/workspace_pull.py`, `agh/cli/pull_markers.py` — lockfile and managed-block vocabulary/format.
- `README.md`, `README.es.md`, `tests/*`, `openspec/specs/*` — docs and test expectations currently hard-coded to pack terminology.
- storage paths and runtime defaults (`/data/packs`, `.agh-cache/packs`) — rename blast radius for filesystem conventions.

### Approaches
1. **Hard rename everywhere with compatibility removed** — convert all user-facing and internal `pack` terminology to `package`/`pkg` in one migration.
   - Pros: clean final state; avoids dual vocabulary; matches approved decision to eliminate legacy `pack`.
   - Cons: widest blast radius; breaks CLI/API/DB/storage contracts in one pass; biggest test and migration burden.
   - Effort: High

2. **Layered rename by surface, same release** — keep behavior stable within the release, but rename each surface consistently: CLI `package`/`pkg`, manifest `agh.package.toml`, API `/packages`, IDs `pkg_`/`pkgv_`, and storage/docs/tests follow.
   - Pros: clearer spec boundaries; easier to reason about rename groups; still ends with no legacy pack terms.
   - Cons: still a large coordinated migration; many touching points must stay in sync.
   - Effort: High

### Recommendation
Use a single, explicitly planned rename with no legacy compatibility, but split proposal/spec/design by surface so the implementation can be reviewed in slices. Keep the product term as **guidance package** in docs, use `package` for full names, and `pkg` only where short forms already fit AGH conventions (CLI shorthand and IDs). Maintain `asn_...` for assignments.

### Risks
- Breaking existing CLI scripts and automation that still call `agh pack ...` or read `agh.pack.toml`.
- DB/storage migrations are broad: table names, API routes, cache paths, lockfile keys, and managed-block markers all need coordinated updates.
- Search-and-replace is not enough; some places encode semantics (`pack_ref`, `packv_...`, `/api/v1/packs`) and require parser/validator changes.
- Tests and docs are tightly coupled to current terminology, so the rename will produce a large but expected test diff.
- Interactive `agh project package add` must avoid weakening CI usage; it should only prompt when the package ref is omitted.

### Ready for Proposal
Yes. Next phase should define the exact rename matrix (CLI/API/DB/storage/docs/tests), the migration strategy for data and file paths, and the interactive add-flow UX contract for omitted package refs.
