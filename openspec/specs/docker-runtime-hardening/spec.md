# Delta: docker-runtime-hardening

## ADDED Requirements

### Requirement: Zero Docker runtime scripts

Docker runtime hardening MUST be represented by Dockerfile metadata, Docker Compose settings, tests, and CI/release validation. The image MUST NOT copy or execute Docker runtime helper scripts.

#### Scenario: Image command review
- GIVEN the Docker image is built
- WHEN its config is inspected
- THEN it runs as `10001:10001`
- AND it has no helper-script entrypoint.

#### Scenario: Source tree review
- GIVEN the repository is checked out
- WHEN Docker runtime artifacts are inspected
- THEN `scripts/docker-entrypoint.py` and `scripts/docker-runtime-smoke.sh` are absent
- AND `scripts/install.sh` remains present.

### Requirement: Image-owned data tree

The Dockerfile MUST create UID/GID `10001:10001`, prepare `/data`, `/data/logs`, `/data/secrets`, `/data/packs`, and `/data/agh.sqlite3`, chown them in the image, set `USER 10001:10001`, and use the direct exec-form `uvicorn` command.

#### Scenario: Named volume initialization
- GIVEN an empty Docker named volume is mounted at `/data`
- WHEN the container starts
- THEN Docker initializes the volume from the image-owned `/data` tree
- AND AGH can write required runtime paths as `10001:10001`.

### Requirement: Bind mount ownership contract

Bind mounts MUST be treated as operator-owned storage. The container MUST NOT repair host ownership; bind-mounted `/data` paths MUST already be writable by UID/GID `10001:10001`.

#### Scenario: Pre-owned bind mount
- GIVEN a bind-mounted `/data` path owned by `10001:10001`
- WHEN the container starts
- THEN AGH reaches health and writes required runtime paths.

#### Scenario: Root-owned bind mount
- GIVEN a bind-mounted `/data` path owned by root
- WHEN the container starts
- THEN the container does not repair host ownership
- AND health is not expected until the operator fixes permissions.

### Requirement: Compose and CI hardening

Compose SHOULD run the service as `10001:10001`, set `no-new-privileges:true`, and drop all capabilities when compatible. CI/release validation MUST run Dockerfile checks and Docker-backed pytest runtime tests directly.

#### Scenario: Validation path
- GIVEN CI or release validation runs
- WHEN hardening is checked
- THEN validation uses Dockerfile checks and pytest runtime tests
- AND does not call auxiliary Docker runtime scripts.
