## Verification Report

**Change**: fix-docker-runtime-hardening  
**Version**: N/A  
**Mode**: Strict TDD (`uv run pytest`)  
**Date**: 2026-06-14

### Completeness

| Metric | Value |
|--------|-------|
| Tasks total | 10 |
| Tasks complete | 10 |
| Tasks incomplete | 0 |
| Apply-progress TDD rows | 8 |
| Stale verify evidence | Replaced with this current report |

### TDD Compliance

| Check | Result | Details |
|-------|--------|---------|
| TDD Evidence reported | ✅ | `apply-progress.md` contains a TDD Cycle Evidence table for the amendment. |
| All implementation tasks have tests | ✅ | Docker/static docs contracts use `tests/test_docs_guidance.py`; runtime behavior uses `tests/test_docker_runtime.py`. |
| RED confirmed | ✅ | Apply-progress records RED failures before implementation; referenced test files/artifacts exist. |
| GREEN confirmed | ✅ | `TMPDIR=<container_file_t> uv run pytest` passed 305/305; Docker runtime tests passed 6/6. |
| Triangulation adequate | ✅ | Coverage includes image config, source absence, named volume, writable runtime paths, pre-owned bind mount, root-owned bind mount non-repair, Compose, docs, and CI/release paths. |
| Safety Net for modified files | ✅ | Apply-progress records targeted baselines before edits and full validation after edits. |

**TDD Compliance**: 6/6 checks passed.

### Test Layer Distribution

| Layer | Tests | Files | Tools |
|-------|-------|-------|-------|
| Unit/static contract | 5 change-focused tests | `tests/test_docs_guidance.py` | pytest |
| Integration/Docker runtime | 6 tests | `tests/test_docker_runtime.py` | pytest + Docker |
| E2E | 0 | — | Not used |
| **Total change-focused** | **11** | **2** | |

`tests/test_docs_guidance.py` contains 12 total docs/workflow tests; the 5 listed above are the Docker hardening-focused scenarios.

### Changed File Coverage

Coverage analysis skipped — no coverage tool or pytest-cov configuration was detected in `pyproject.toml`, `uv.lock`, or validation workflows.

### Assertion Quality

**Assertion quality**: ✅ All reviewed assertions verify real static or runtime behavior.

Reviewed files:
- `tests/test_docs_guidance.py` — static contract assertions over Dockerfile, Compose, CI/release workflows, docs, and script absence.
- `tests/test_docker_runtime.py` — Docker image inspection, PID 1 UID/GID/groups, volume ownership, runtime writes, health readiness, and root-owned bind-mount non-repair.

No tautologies, ghost loops, orphan empty assertions, type-only-only assertions, or mock-heavy tests were found.

### Quality Metrics

**Ruff format**: ✅ `uv run --with ruff ruff format --check .` — 53 files already formatted.  
**Ruff lint**: ✅ `uv run --with ruff ruff check .` — all checks passed.  
**Type Checker**: ✅ `uv run --with pyright pyright agh tests` — 0 errors, 0 warnings, 0 informations.

### Build & Tests Execution

**Tests**: ✅ Passed

```text
uv run pytest
304 passed, 1 skipped, 1 warning in 56.23s

Skip details from focused default runtime run:
SKIPPED [1] tests/test_docker_runtime.py:193: Docker environment cannot chown bind-mounted host paths from a container:
mkdir: cannot create directory ‘/data/logs’: Permission denied
mkdir: cannot create directory ‘/data/secrets’: Permission denied
mkdir: cannot create directory ‘/data/packs’: Permission denied
```

The skip is local-environment specific: this host's default pytest temp paths are SELinux-labeled `user_tmp_t`, which blocks container writes to bind mounts. Verification reran the same tests with a Docker-writable temp root labeled `container_file_t`:

```text
TMPDIR=<container_file_t tempdir> uv run pytest
305 passed, 1 warning in 58.37s

TMPDIR=<container_file_t tempdir> uv run pytest tests/test_docker_runtime.py -q -rs
6 passed in 15.54s
```

**Focused Docker/static tests**: ✅ Passed

```text
uv run pytest tests/test_docs_guidance.py::test_docker_runtime_validation_is_pytest_based_not_smoke_script \
  tests/test_docs_guidance.py::test_dockerfile_documents_data_dirs_and_healthcheck \
  tests/test_docs_guidance.py::test_compose_uses_published_ghcr_image_and_data_volume \
  tests/test_docs_guidance.py::test_ci_workflow_runs_release_validation_commands \
  tests/test_docs_guidance.py::test_tag_release_workflow_publishes_package_image_and_release -q
5 passed in 0.01s
```

**Docker build check**: ✅ Passed

```text
docker build --check .
Check complete, no warnings found.
```

**Docker Compose render**: ✅ Passed

```text
docker compose config
services.agh.user: 10001:10001
services.agh.security_opt: [no-new-privileges:true]
services.agh.cap_drop: [ALL]
services.agh.volumes: agh-data:/data
```

**Image config and data-tree inspection**: ✅ Passed

```text
docker image inspect --format 'User={{.Config.User}} Entrypoint={{json .Config.Entrypoint}} Cmd={{json .Config.Cmd}}' agh-runtime-pytest:local
User=10001:10001 Entrypoint=null Cmd=["uvicorn","agh.server.app:app","--host","0.0.0.0","--port","8912"]

docker run --rm --entrypoint sh agh-runtime-pytest:local -c "stat -c '%u:%g %F' /data /data/logs /data/secrets /data/packs /data/agh.sqlite3"
10001:10001 directory
10001:10001 directory
10001:10001 directory
10001:10001 directory
10001:10001 regular empty file
```

**Script absence / install script integrity**: ✅ Passed

```text
test -f scripts/install.sh && test ! -e scripts/docker-entrypoint.py && test ! -e scripts/docker-runtime-smoke.sh && test ! -e tests/test_docker_entrypoint.py
script/file absence contract ok

git diff -- scripts/install.sh --exit-code
scripts/install.sh unchanged in working tree

rg -n "docker-entrypoint|docker-runtime-smoke" Dockerfile docker-compose.yml .github/workflows/ci.yml .github/workflows/release.yml
(no matches)
```

### Spec Compliance Matrix

| Requirement | Scenario | Test / Evidence | Result |
|-------------|----------|-----------------|--------|
| Zero Docker runtime scripts | Image command review | `tests/test_docker_runtime.py::test_image_uses_direct_non_root_uvicorn_command`; `docker image inspect` | ✅ COMPLIANT |
| Zero Docker runtime scripts | Source tree review | `tests/test_docs_guidance.py::test_docker_runtime_validation_is_pytest_based_not_smoke_script`; shell absence check | ✅ COMPLIANT |
| Image-owned data tree | Named volume initialization | `tests/test_docker_runtime.py::test_named_volume_is_initialized_from_image_owned_data_tree`; image data-tree stat | ✅ COMPLIANT |
| Bind mount ownership contract | Pre-owned bind mount | `tests/test_docker_runtime.py::test_pre_owned_bind_mount_is_operator_responsibility` passed with SELinux-compatible `TMPDIR`; default `/tmp` blocker documented above | ✅ COMPLIANT |
| Bind mount ownership contract | Root-owned bind mount | `tests/test_docker_runtime.py::test_root_owned_bind_mount_is_not_repaired_by_container` | ✅ COMPLIANT |
| Compose and CI hardening | Validation path | `tests/test_docs_guidance.py` workflow tests; `docker build --check .`; `docker compose config`; grep confirms no helper-script references | ✅ COMPLIANT |

**Compliance summary**: 6/6 scenarios compliant.

### Correctness (Static Evidence)

| Requirement | Status | Notes |
|------------|--------|-------|
| Zero Docker runtime scripts | ✅ Implemented | `scripts/docker-entrypoint.py`, `scripts/docker-runtime-smoke.sh`, and `tests/test_docker_entrypoint.py` are absent. Dockerfile/Compose/CI/release do not reference them. |
| Keep installer intact | ✅ Implemented | `scripts/install.sh` exists and has no working-tree diff. |
| Dockerfile runtime user and data tree | ✅ Implemented | Dockerfile creates `agh:agh` with UID/GID `10001`, prepares `/data/logs`, `/data/secrets`, `/data/packs`, `/data/agh.sqlite3`, chowns `/data`, and sets `USER 10001:10001`. |
| Direct command, no helper entrypoint | ✅ Implemented | Docker image config has `Entrypoint=null` and exec-form `Cmd=["uvicorn", ...]`; Dockerfile has no `ENTRYPOINT`. |
| Compose hardening | ✅ Implemented | Compose renders `user: 10001:10001`, `security_opt: no-new-privileges:true`, and `cap_drop: [ALL]`. |
| Named volume runtime | ✅ Implemented | Docker runtime tests prove named-volume initialization and writeability as `10001:10001`. |
| Bind mount ownership contract | ✅ Implemented with environment note | Runtime tests prove pre-owned bind mounts work when the host path is container-writable and root-owned paths are not repaired. Local SELinux `user_tmp_t` tempdirs block unlabelled bind-mount preparation. |
| Stale verify evidence | ✅ Replaced | Previous stale marker was overwritten by this current report with fresh command evidence. |

### Coherence (Design)

| Decision | Followed? | Notes |
|----------|-----------|-------|
| Remove Docker runtime scripts | ✅ Yes | No runtime helper script exists or is referenced by runtime/config/workflows. |
| Prepare `/data` at image build time | ✅ Yes | Image contains required paths owned by `10001:10001`. |
| Treat bind mounts as operator-owned storage | ✅ Yes | Container does not repair root-owned bind mounts; pre-owned path succeeds under a Docker-writable host label. |
| Compose hardening with non-root user, no-new-privileges, cap drop | ✅ Yes | Rendered Compose config confirms all three settings. |
| Avoid `read_only`/`tmpfs` overreach | ✅ Yes | Compose keeps writable `/data` volume and does not add deferred hardening that would break SQLite/log/pack writes. |

### Issues Found

**CRITICAL**: None.

**WARNING**:
- Local default pytest temp directories are SELinux-labeled `user_tmp_t`; Docker containers cannot write/chown those unlabelled bind mounts, causing the default runtime suite to skip the pre-owned bind-mount test. Re-running with a `container_file_t` temp root produced 6/6 Docker runtime passes and 305/305 full test passes.
- Full pytest emits an existing `StarletteDeprecationWarning` from `fastapi.testclient`; it is unrelated to the Docker hardening change.

**SUGGESTION**:
- Consider documenting SELinux bind-mount labeling (`:z`/`:Z` or an equivalent container-writable label) alongside the UID/GID `10001:10001` ownership contract for operators on SELinux-enforcing hosts.

### Verdict

**PASS WITH WARNINGS**

The amended zero-Docker-runtime-scripts contract is implemented and covered by current runtime/static evidence. Archive can proceed once the orchestrator accepts the documented local SELinux tempdir warning as non-blocking.
