# CLI Specification

## Purpose

The `agh` Typer CLI for authentication, configuration, administration, and invoking workspace commands.

## Requirements

### Requirement: agh binary entrypoint

The distribution MUST provide a `agh` command-line entrypoint implemented with Typer, subcommand groups for auth/config, admin operations, and workspace commands (`sync`, `pull`, `agent`).

#### Scenario: Help displays top-level commands

- GIVEN `agh` is installed
- WHEN the user runs `agh --help`
- THEN help lists `login`, config-related commands, and workspace commands

### Requirement: User config file location and permissions

The CLI MUST store instance connection settings in `~/.config/agh/config.toml` containing at minimum `instance_url`, `email`, and `token`. On write, the CLI MUST set file permissions to owner-read/write only (e.g., `0600` on Unix).

#### Scenario: Login writes restricted config

- GIVEN a successful `agh login`
- WHEN config is saved
- THEN `~/.config/agh/config.toml` exists with mode `0600` (or platform equivalent)
- AND contains `instance_url`, `email`, and `token`

### Requirement: Login validates against me endpoint

`agh login` MUST prompt for or accept instance URL, email, and API token, persist them to config, and MUST verify credentials by calling `GET /api/v1/me`. Login MUST fail with a non-zero exit if validation fails.

#### Scenario: Successful login

- GIVEN valid instance URL and token for `dev@example.com`
- WHEN the user runs `agh login`
- THEN config is written
- AND `GET /api/v1/me` succeeds
- AND exit code is 0

#### Scenario: Invalid token login fails

- GIVEN an invalid token
- WHEN the user runs `agh login`
- THEN config is not updated (or prior config retained per design)
- AND exit code is non-zero

### Requirement: Config inspection and management

The CLI MUST provide commands to show and update non-secret config fields (e.g., `instance_url`) without echoing secrets to logs by default. Token display MUST be masked unless an explicit show-secret flag is defined in design.

#### Scenario: Config show masks token

- GIVEN a saved config with token
- WHEN the user runs the config show command
- THEN output does not print the full plaintext token by default

### Requirement: Admin and developer command coverage

The CLI MUST expose commands for project CRUD/membership, user administration (within caller's role), token lifecycle, and pack publish/list aligned with `/api/v1` capabilities.

#### Scenario: Admin lists projects

- GIVEN an authenticated admin config
- WHEN `agh project list` (or equivalent) runs
- THEN projects visible to the caller are printed

### Requirement: Sync has no manual project override

`agh sync` MUST determine the AGH project solely by matching the local git remote URL (default remote `origin`, overridable via `--remote`) against accessible projects. The CLI MUST NOT provide `--project` or equivalent manual project override in MVP.

#### Scenario: Sync without override flag

- GIVEN `agh sync --help`
- WHEN the user inspects options
- THEN no `--project` option exists

#### Scenario: Sync uses git remote

- GIVEN local repo remote `origin` matches project P's normalized URL
- WHEN `agh sync` runs
- THEN `.agh/project.toml` links to P without manual id entry

### Requirement: Workspace command delegation

`agh sync`, `agh pull`, and `agh agent` MUST be implemented as CLI commands that orchestrate local git/workspace behavior and call server APIs as specified in the workspace and api specs.

#### Scenario: Pull invokes pull-manifest

- GIVEN linked project in `.agh/project.toml`
- WHEN `agh pull` runs
- THEN the CLI fetches the project pull-manifest before applying files

### Requirement: Out of scope CLI MVP

The CLI MUST NOT implement web UI, marketplace browsing, or agent integrations beyond delegating to workspace commands for Claude/OpenCode.

#### Scenario: No web UI launcher

- GIVEN MVP CLI
- WHEN user searches for browser/UI command
- THEN no such command exists
