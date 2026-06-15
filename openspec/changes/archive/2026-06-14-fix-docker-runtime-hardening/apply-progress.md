# Apply Progress: Fix Docker Runtime Hardening

Strict TDD (`uv run pytest`). Scope amended on 2026-06-14 to require zero Docker runtime helper scripts. No issue, PR, push, publish, or archive was performed. Delivery remains a single PR candidate under the 400-line review target.

## Previous Apply History Preserved

- [x] Prior pass removed `scripts/docker-runtime-smoke.sh` from CI/release validation and moved Docker hardening checks into pytest/workflows.
- [x] Prior pass added Docker-backed runtime tests and workflow validation.
- [x] Prior pass kept `scripts/install.sh` intact.
- [x] Prior pass used `scripts/docker-entrypoint.py` for runtime `/data` repair; this is now superseded by the amended zero-runtime-scripts contract.

## Current Amendment Completed

- [x] OpenSpec proposal/spec/design/tasks now require zero Docker runtime scripts, named-volume initialization from image-owned `/data`, and bind-mount operator ownership.
- [x] `scripts/docker-entrypoint.py` and `tests/test_docker_entrypoint.py` are absent; `scripts/install.sh` remains intact.
- [x] `Dockerfile` creates `agh:agh` (`10001:10001`), prepares `/data/logs`, `/data/secrets`, `/data/packs`, and `/data/agh.sqlite3`, chowns `/data`, sets `USER 10001:10001`, and keeps the direct exec-form `uvicorn` command.
- [x] `docker-compose.yml` explicitly uses `user: "10001:10001"`, `security_opt: [no-new-privileges:true]`, and `cap_drop: [ALL]`.
- [x] Runtime tests assert image config, non-root PID 1, required path writes, named-volume initialization, pre-owned bind mount behavior, and non-repair of non-runtime-owned bind mounts.
- [x] README docs state named volumes are supported and bind mounts must be pre-owned/writable by UID/GID `10001:10001`.
- [x] Stale verify report was invalidated so archive cannot proceed until a fresh verify pass runs.

## TDD Cycle Evidence

| Task | Test File | Layer | Safety Net | RED | GREEN | TRIANGULATE | REFACTOR |
|------|-----------|-------|------------|-----|-------|-------------|----------|
| 1.1-1.2 Artifact amendment | `openspec/changes/fix-docker-runtime-hardening/*` | Docs/spec | ✅ Read prior artifacts and apply-progress | ✅ Stale scope identified before artifact rewrite | ✅ Artifacts rewritten in English | ✅ Proposal, spec, design, tasks, apply-progress, stale verify guard | ✅ Compact artifacts under SDD budgets |
| 2.1 Dockerfile/Compose/docs contract | `tests/test_docs_guidance.py` | Unit/static contract | ✅ 19/19 targeted baseline before edits | ✅ 3 failing assertions for entrypoint file, missing DB placeholder, missing Compose user/cap_drop | ✅ 3/3 focused tests passed | ✅ Covers script absence, Dockerfile direct runtime, Compose hardening, CI/release script independence, README bind-mount docs | ✅ Ruff format unchanged |
| 2.2 Runtime behavior contract | `tests/test_docker_runtime.py` | Integration | ✅ 19/19 targeted baseline before edits | ✅ Image config test failed while image still used helper entrypoint and no `USER` | ✅ 5 passed, 1 skipped locally after implementation | ✅ Image config, PID UID/GID/groups, named volume, writable paths, bind mount success/failure | ✅ Rootless-Docker bind chown skip documents environment blocker |
| 3.1 Script/test deletion | `tests/test_docs_guidance.py` | Unit/static contract | ✅ Baseline captured before deletion | ✅ Absence assertions failed while `scripts/docker-entrypoint.py` existed | ✅ Absence assertions passed after deletion | ✅ Also asserts no runtime test or Dockerfile reference remains | ✅ Removed obsolete entrypoint unit tests |
| 3.2 Dockerfile implementation | `tests/test_docs_guidance.py`, `tests/test_docker_runtime.py` | Unit + integration | ✅ Existing Docker tests baseline passed before edits | ✅ Dockerfile/image config tests failed on missing `USER`, DB placeholder, and null entrypoint | ✅ Focused docs/runtime tests passed | ✅ Named volume ownership and runtime writes validate real behavior | ✅ No helper script copy/chmod remains |
| 3.3 Compose implementation | `tests/test_docs_guidance.py`, `docker compose config` | Unit/static + config | ✅ Existing compose docs test baseline passed | ✅ Test failed before `user` and `cap_drop` existed | ✅ Focused compose test passed | ✅ `docker compose config` confirmed rendered hardening | ✅ Avoided `read_only`/`tmpfs` overreach |
| 3.4 Docs implementation | `tests/test_docs_guidance.py` | Unit/docs | ✅ Docs test baseline passed | ✅ README expected strings failed before update | ✅ 12/12 docs tests passed | ✅ English and Spanish README coverage for named volumes and bind mounts | ✅ Existing README structure preserved |
| 4.1-4.2 Validation | Full suite and tools | Verification | ✅ Focused tests green before full run | ✅ Docker runtime test exposed rootless bind-mount chown limitation and over-specific empty-file assertion | ✅ Required commands passed | ✅ Full pytest + Docker build/check + Compose config + Ruff + Pyright | ✅ Stale verify report invalidated pending fresh verify |

## Validation Evidence

- ✅ `uv run pytest tests/test_docs_guidance.py::test_docker_runtime_validation_is_pytest_based_not_smoke_script tests/test_docs_guidance.py::test_dockerfile_documents_data_dirs_and_healthcheck tests/test_docs_guidance.py::test_compose_uses_published_ghcr_image_and_data_volume -q` — RED: 3 failed before implementation; GREEN: 3 passed after implementation.
- ✅ `uv run pytest tests/test_docker_runtime.py::test_image_uses_direct_non_root_uvicorn_command -q` — RED: failed before implementation because image had no `USER` and used `docker-entrypoint.py`.
- ✅ `uv run pytest tests/test_docker_runtime.py -q` — 5 passed, 1 skipped. Skip reason: local Docker environment cannot chown bind-mounted host paths from a container; the rootless-environment skip preserves CI coverage where supported.
- ✅ `uv run pytest tests/test_docs_guidance.py -q` — 12 passed.
- ✅ `uv run pytest` — 304 passed, 1 skipped, 1 warning.
- ✅ `uv run --with ruff ruff format --check .` — 53 files already formatted.
- ✅ `uv run --with ruff ruff check .` — all checks passed.
- ✅ `uv run --with pyright pyright agh tests` — 0 errors, 0 warnings.
- ✅ `docker build --check .` — check complete, no warnings found.
- ✅ `docker compose config` — rendered `user: 10001:10001`, `no-new-privileges:true`, and `cap_drop: [ALL]`.
- ✅ `test -f scripts/install.sh && test ! -e scripts/docker-entrypoint.py && test ! -e tests/test_docker_entrypoint.py` — ok.

## Deviations / Issues

- Local Docker appears unable to chown bind-mounted host paths from a container, likely due rootless/userns restrictions. The pre-owned bind-mount test skips only that preparation path; named-volume and non-repair checks still run locally, and CI/rootful Docker should exercise the pre-owned bind-mount path.
- The previous verify report was stale after the scope amendment and has been replaced with a stale marker. A fresh verify pass is required before archive.
