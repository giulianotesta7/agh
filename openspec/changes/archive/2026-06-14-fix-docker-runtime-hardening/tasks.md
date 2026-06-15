# Tasks: Fix Docker Runtime Hardening

## Review Workload Forecast

| Field | Value |
|-------|-------|
| Estimated changed lines | 260-380 |
| 400-line budget risk | Medium |
| Chained PRs recommended | No |
| Suggested split | Single PR |
| Delivery strategy | ask-always; user-approved amendment scope |
| Chain strategy | pending |

Decision needed before apply: No
Chained PRs recommended: No
Chain strategy: pending
400-line budget risk: Medium

### Suggested Work Units

| Unit | Goal | Likely PR | Notes |
|------|------|-----------|-------|
| 1 | Remove Docker runtime scripts and encode the runtime contract in image/Compose metadata | PR 1 | Includes Dockerfile, Compose, script/test cleanup |
| 2 | Prove named-volume and bind-mount behavior through pytest/docs/CI validation | PR 1 | Same PR; verification stays with behavior |

## Phase 1: Artifact Amendment

- [x] 1.1 Update proposal/spec/design/tasks to require zero Docker runtime scripts and bind-mount operator ownership.
- [x] 1.2 Preserve the prior apply-progress history and add new Strict TDD evidence for the amendment.

## Phase 2: Test-First Contract Update

- [x] 2.1 Update `tests/test_docs_guidance.py` to fail while Dockerfile/Compose/docs still reference helper-script repair.
- [x] 2.2 Replace entrypoint/runtime tests with `tests/test_docker_runtime.py` coverage for image config, named volumes, pre-owned bind mounts, and root-owned bind mount non-repair.

## Phase 3: Runtime Implementation

- [x] 3.1 Delete `scripts/docker-entrypoint.py` and `tests/test_docker_entrypoint.py`; keep `scripts/install.sh` intact.
- [x] 3.2 Update `Dockerfile` to prepare image-owned `/data`, set `USER 10001:10001`, and use direct exec-form `uvicorn` command.
- [x] 3.3 Update `docker-compose.yml` to run as `10001:10001` with `no-new-privileges:true` and compatible `cap_drop: [ALL]`.
- [x] 3.4 Update README guidance for named volumes and bind-mount ownership responsibility.

## Phase 4: Validation

- [x] 4.1 Run focused RED/GREEN pytest cycles for Docker docs/runtime tests.
- [x] 4.2 Run required validation: `uv run pytest`, Ruff format/check, Pyright, `docker build --check .`, and `docker compose config` where available.
