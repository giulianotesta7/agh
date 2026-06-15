# Design: Fix Docker Runtime Hardening

## Technical Approach

Move the runtime hardening contract entirely into Dockerfile metadata, Compose configuration, tests, and CI/release workflows. The image owns `/data` at build time, runs directly as `10001:10001`, and relies on Docker named-volume initialization for first-run persistence. Bind mounts are not repaired by the container; operators must pre-own them for UID/GID `10001:10001`.

## Architecture Decisions

| Decision | Choice | Alternatives considered | Rationale |
|---|---|---|---|
| Runtime scripts | Remove `scripts/docker-entrypoint.py`; keep no Docker runtime scripts | Keep a minimal root entrypoint | Zero helper scripts keeps PID 1, ownership, and validation visible in Docker metadata and tests. |
| `/data` ownership | Prepare and chown `/data` plus required subpaths in the image | Repair `/data` at startup | Named volumes are initialized from image contents; bind mounts should not be mutated by application startup. |
| Bind mounts | Document and test pre-owned `10001:10001` requirement | Container-side chown of host paths | Avoids privileged startup and accidental host ownership changes. |
| Compose hardening | `user: "10001:10001"`, `no-new-privileges:true`, `cap_drop: [ALL]` | `read_only`, tmpfs, root entrypoint | Compatible with SQLite/log/pack writes while reducing runtime privileges. |

## Data Flow

```text
Dockerfile build
  ├─ create agh UID/GID 10001
  ├─ create /data required paths and empty DB placeholder
  ├─ chown /data to agh:agh
  └─ USER 10001:10001 + direct uvicorn CMD

Docker named volume ── first mount copies image-owned /data ── AGH writes as 10001
Bind mount ── operator pre-owns/writes host path ────────────── AGH writes as 10001
```

## File Changes

| File | Action | Description |
|---|---|---|
| `Dockerfile` | Modify | Create UID/GID `10001`, prepare `/data` and DB placeholder, set `USER 10001:10001`, remove helper script entrypoint. |
| `docker-compose.yml` | Modify | Run as `10001:10001`; keep `no-new-privileges:true`; add `cap_drop: [ALL]`. |
| `scripts/docker-entrypoint.py` | Delete | Remove runtime ownership repair script. |
| `tests/test_docker_entrypoint.py` | Delete | Remove tests for deleted runtime script behavior. |
| `tests/test_docker_runtime.py` | Modify | Assert image config, non-root PID 1, named volume initialization, pre-owned bind mounts, and root-owned bind mount non-repair. |
| `tests/test_docs_guidance.py` | Modify | Assert no Docker runtime scripts, direct CI validation, Compose hardening, and bind-mount docs. |
| `README.md`, `README.es.md` | Modify | Document named-volume support and bind-mount ownership responsibility. |
| `.github/workflows/ci.yml`, `.github/workflows/release.yml` | Keep/Verify | Continue direct `docker build --check .` and `uv run pytest tests/test_docker_runtime.py -q`. |
| `scripts/install.sh` | Keep | Installer remains untouched. |

## Interfaces / Contracts

- Runtime UID/GID: `10001:10001`.
- Required image-owned paths: `/data`, `/data/logs`, `/data/secrets`, `/data/packs`, `/data/agh.sqlite3`.
- Command: `uvicorn agh.server.app:app --host 0.0.0.0 --port 8912`.
- Named volumes: supported through Docker initialization from image `/data`.
- Bind mounts: must be pre-owned/writable by `10001:10001`.

## Testing Strategy

| Layer | What to Test | Approach |
|---|---|---|
| Unit/docs | Dockerfile, Compose, workflow, docs contracts | `uv run pytest tests/test_docs_guidance.py` |
| Integration | Built image config, health, UID/GID/groups, volume behavior | `uv run pytest tests/test_docker_runtime.py -q` |
| CI/release | Repeat direct checks without scripts | Workflow assertions plus actual validation commands |

## Migration / Rollout

No data migration required for named volumes. Existing bind mounts may need an operator one-time `chown -R 10001:10001 <host-data-dir>` before rollout.

## Open Questions

- [ ] None.
