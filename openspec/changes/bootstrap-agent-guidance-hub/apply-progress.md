# Apply Progress: bootstrap-agent-guidance-hub

**Change**: bootstrap-agent-guidance-hub  
**Mode**: Standard (strict_tdd: false)  
**Delivery**: auto-chain / stacked-to-main  
**Updated**: 2026-05-28

## Completed Tasks

- [x] 1.1 Create `pyproject.toml`, `agh/__init__.py`, `agh/server/app.py`, `agh/cli/main.py`, and `tests/` with FastAPI, Typer, pytest dependencies and `agh` entrypoint.
- [x] 1.2 Add smoke tests in `tests/test_scaffold.py` for `GET /api/v1/health`, `agh --help`, log file creation, and default port constant `8912`.
- [x] 1.3 Implement health route, Typer help, basic stdout/file logging, `Dockerfile` health check.
- [x] 1.4 Update `openspec/config.yaml` test command/testing runner to `python -m pytest`.
- [x] 2.1 (PR2A split) Add `agh/common/ids.py`, `validation.py`, `repo_url.py`, `pack_manifest.py`, `checksums.py` and unit tests for prefixed IDs, email, slug/SemVer/latest handling, URL normalization, manifest validation, and managed payload hashes.

## Files Changed (PR2A)

| File | Action | Notes |
|------|--------|-------|
| `agh/common/__init__.py` | Created | Shared exports for helper layer |
| `agh/common/ids.py` | Created | Prefixed ID generation/validation for `usr/tok/prj/pack/packv/asn` |
| `agh/common/validation.py` | Created | Email/slug/SemVer validation, pack ref parsing, SemVer compare |
| `agh/common/repo_url.py` | Created | GitHub-style SSH/HTTPS normalization with optional `.git` stripping |
| `agh/common/pack_manifest.py` | Created | `agh.pack.toml` loader + validation (required fields, tags) |
| `agh/common/checksums.py` | Created | Managed payload normalization + `sha256:<hex>` digest |
| `tests/test_common_helpers.py` | Created | Focused unit coverage for helper layer |
| `openspec/changes/bootstrap-agent-guidance-hub/specs/packs/spec.md` | Modified | Explicitly requires manifest `description` to match product contract |
| `openspec/changes/bootstrap-agent-guidance-hub/tasks.md` | Modified | Marked task 2.1 complete |

## Validation

```text
python -m pytest
# failed in system python: missing dependencies / package import during collection

.venv/bin/python -m pytest
# 24 passed in 0.25s

PYTHONDONTWRITEBYTECODE=1 .venv/bin/python -m pytest -q -p no:cacheprovider
# 24 passed in 0.26s
```

## TDD Evidence

Strict TDD not active (`openspec/config.yaml: strict_tdd: false`).

## Deviations from Design

None — helper behavior matches Phase 2.1 design/spec scope after review fixes.

## Issues Found / Review Fixes

- Fresh review found ID prefixes did not match the API spec (`proj` vs `prj`, missing `asn`). Fixed allowed prefixes and added parametrized tests.
- Fresh review found malformed TOML escaped as `tomllib.TOMLDecodeError`. Fixed manifest loader to wrap malformed TOML in `PackManifestError`.
- Fresh review noted the packs spec did not explicitly require `description`; updated the spec to match the approved manifest contract and implementation.

## Remaining Tasks

- [ ] 2.2 Add `agh/server/db.py` and migrations
- [ ] 2.3 Add `agh/server/auth.py`, bootstrap startup, hashed Bearer tokens, `/api/v1/me`
- [ ] 2.4 Add `agh/cli/config.py` and login flow
- [ ] 3.1–6.4 unchanged

## Workload / PR Boundary

- **Mode**: stacked PR slice (PR2A) targeting `main` after PR1 merge
- **Boundary**: common pure helper layer only (no DB/auth/routes/CLI login)
- **Review impact**: bounded helper+tests slice within PR2 split strategy
