# Proposal: Fix Docker Runtime Hardening

Run AGH as UID/GID `10001:10001` without Docker runtime helper scripts. Docker hardening is expressed through the Dockerfile, Docker Compose, pytest coverage, and CI/release workflows.

## Problem

The previous change still depended on `scripts/docker-entrypoint.py` to repair `/data` at container start. That keeps runtime behavior split between Docker metadata and a helper script, and it hides the real bind-mount contract from operators.

## Scope

- Remove Docker runtime helper scripts, including `scripts/docker-entrypoint.py` and the already-removed runtime smoke script.
- Keep `scripts/install.sh` intact.
- Create `agh:agh` as `10001:10001` during image build.
- Prepare `/data`, `/data/logs`, `/data/secrets`, `/data/packs`, and `/data/agh.sqlite3` in the image and chown them to `10001:10001`.
- Run the image directly as `USER 10001:10001` with the existing exec-form `uvicorn` command.
- Support Docker named volumes initialized from the image-owned `/data` tree.
- Treat bind mounts as operator responsibility: host paths must already be writable by `10001:10001`.
- Make Compose explicit with `user: "10001:10001"`, `no-new-privileges:true`, and compatible capability dropping.
- Validate through tests and CI/release workflow commands, not auxiliary runtime scripts.

## Out of Scope

- Runtime ownership repair for bind mounts.
- Changing the health endpoint or server port.
- Changing `scripts/install.sh`.

## Rollback

Restore the prior Dockerfile/Compose contract and reintroduce the entrypoint only if named-volume initialization or non-root startup fails in validation.
