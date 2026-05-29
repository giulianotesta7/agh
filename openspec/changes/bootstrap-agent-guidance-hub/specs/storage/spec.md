# Storage Specification

## Purpose

Persistent metadata, pack artifact layout, container filesystem conventions, and logging paths for AGH.

## Requirements

### Requirement: SQLite metadata store

The system MUST persist AGH metadata (users, tokens, projects, memberships, packs, assignments) in SQLite. The database file MUST reside under the server data root (default `/data/`).

#### Scenario: Metadata survives restart

- GIVEN users and projects exist in SQLite
- WHEN the server restarts
- THEN previously stored metadata is available

### Requirement: Filesystem pack blob storage

Pack source artifacts (manifest, instructions, skills) MUST be stored on the filesystem under the server data root. Pack blobs MUST be addressable by pack identity and immutable version.

#### Scenario: Published pack retrievable from disk

- GIVEN pack `acme/onboarding@1.0.0` is published
- WHEN the server loads pack content for that version
- THEN files are read from the pack storage area under `/data/`

### Requirement: Container data layout

In the default container layout, the system MUST use `/data/` as the writable data root with at minimum: database, `packs/` for pack blobs, `secrets/` for bootstrap and sensitive files, and `logs/` for file logging.

#### Scenario: Expected directories exist on first write

- GIVEN a fresh container volume mounted at `/data`
- WHEN the server first writes bootstrap or pack data
- THEN `/data/secrets/`, `/data/logs/`, and pack storage paths under `/data/` are created as needed

### Requirement: Bootstrap secret path policy

The bootstrap owner plaintext token MUST be written only to `/data/secrets/initial_owner_token`. Application logs MUST record at most the path `/data/secrets/initial_owner_token`, never the token contents.

#### Scenario: Secret file location fixed

- GIVEN first-start bootstrap runs
- WHEN the initial owner token is persisted on disk
- THEN the file path is `/data/secrets/initial_owner_token`

### Requirement: Dual logging to stdout and file

When running with the container filesystem layout, the server MUST emit operational logs to stdout/stderr and MUST also append logs to `/data/logs/agh.log`.

#### Scenario: Health check logged to both sinks

- GIVEN the server is running in the default container layout
- WHEN a health check is served
- THEN a corresponding log entry appears on stdout/stderr
- AND the same class of entry is appended to `/data/logs/agh.log`

### Requirement: Out of scope storage MVP

The system MUST NOT require S3, multi-node HA storage, or external secret managers for MVP.

#### Scenario: No S3 backend

- GIVEN MVP configuration
- WHEN pack publish is attempted
- THEN storage uses local filesystem under `/data/` only
