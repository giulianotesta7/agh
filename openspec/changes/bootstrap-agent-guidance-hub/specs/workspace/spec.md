# Workspace Specification

## Purpose

Local repository integration: project link file, sync, pull with managed blocks, lockfile, cache, agent targets, and version-control guidance.

## Requirements

### Requirement: Project link file

After successful `agh sync`, the repository MUST contain `.agh/project.toml` recording the linked AGH project id and instance metadata needed for subsequent pulls. With `--force`, sync MUST replace only `.agh/project.toml` and MUST NOT delete unrelated `.agh` artifacts without explicit pull behavior.

#### Scenario: Sync writes project.toml

- GIVEN a matching remote and accessible project P
- WHEN `agh sync` succeeds
- THEN `.agh/project.toml` references project P

#### Scenario: Force replaces link only

- GIVEN an existing `.agh/project.toml` and `.agh/lock.toml`
- WHEN `agh sync --force` runs successfully
- THEN `.agh/project.toml` is updated
- AND `.agh/lock.toml` is not removed by sync alone

### Requirement: Sync remote selection

`agh sync` MUST read the URL of the selected git remote (default `origin`) and MUST support `--remote <name>`. Matching MUST use normalized URL comparison.

#### Scenario: Non-default remote

- GIVEN remote `upstream` matches project P
- WHEN `agh sync --remote upstream` runs
- THEN `.agh/project.toml` links to P

### Requirement: Pull applies assigned packs with managed blocks

`agh pull` MUST fetch the pull-manifest for the linked project, download pack artifacts into `.agh-cache/packs/` cache, and apply instruction content using managed block markers with per-block checksums. The CLI MUST NOT replace entire target files outside managed regions.

#### Scenario: Managed block inserted

- GIVEN target file has no AGH markers
- WHEN pull applies an instruction
- THEN the file contains delimited managed blocks with checksum metadata defined in design
- AND content outside blocks is preserved

#### Scenario: Checksum mismatch detected as conflict

- GIVEN a managed block was manually edited after last pull
- WHEN pull runs without `--force`
- THEN the command fails with a conflict indication and non-zero exit
- AND previously applied blocks are not silently overwritten

### Requirement: Pull dry-run and force

`agh pull` MUST support `--dry-run` reporting planned changes without writing files. `agh pull --force` MUST allow replacing managed blocks that conflict due to checksum mismatch.

#### Scenario: Dry-run makes no changes

- GIVEN pending updates exist
- WHEN `agh pull --dry-run` runs
- THEN no managed files or lockfile are modified
- AND a summary of planned changes is printed

#### Scenario: Force accepts checksum conflict

- GIVEN a managed block checksum mismatch
- WHEN `agh pull --force` runs
- THEN managed blocks are updated to match server content

### Requirement: Lockfile pins resolved state

`agh pull` MUST write `.agh/lock.toml` recording resolved pack versions, checksums, and applied artifact state sufficient to detect drift on subsequent pulls.

#### Scenario: Lock updated after successful pull

- GIVEN pull succeeds
- WHEN the command completes
- THEN `.agh/lock.toml` reflects resolved versions and checksums

### Requirement: Packs cache directory

Downloaded pack trees MUST be stored under `.agh-cache/packs/` as a local cache. This directory is machine-local cache, not source of truth for teams.

#### Scenario: Cache populated on pull

- GIVEN pull downloads pack content
- WHEN pull completes
- THEN artifacts exist under `.agh-cache/packs/`

### Requirement: Claude agent integration paths

For Claude Code integration, pull MUST apply `instructions/CLAUDE.md` content to repository `CLAUDE.md` (via managed blocks) and MUST place skills under `.claude/skills/<skill-name>/SKILL.md` (symlink when supported, otherwise copy per platform policy in design).

#### Scenario: Claude instruction target

- GIVEN assigned pack includes `instructions/CLAUDE.md`
- WHEN pull runs with Claude integration enabled
- THEN `CLAUDE.md` receives managed content

#### Scenario: Claude skill path

- GIVEN pack includes `skills/foo/SKILL.md`
- WHEN pull applies skills for Claude
- THEN `.claude/skills/foo/SKILL.md` exists

### Requirement: OpenCode agent integration paths

For OpenCode integration, pull MUST apply `instructions/AGENTS.md` to repository `AGENTS.md` (via managed blocks) and MUST place skills under `.opencode/skills/<skill-name>/SKILL.md`.

#### Scenario: OpenCode instruction target

- GIVEN assigned pack includes `instructions/AGENTS.md`
- WHEN pull runs with OpenCode integration enabled
- THEN `AGENTS.md` receives managed content

### Requirement: Agent availability advisory

`agh agent` MUST detect whether Claude and OpenCode integrations appear available in the local environment and MUST display advisory ✓/✗ indicators without failing solely because an agent is absent.

#### Scenario: Agent status display

- GIVEN a repository with linked project
- WHEN `agh agent` runs
- THEN output shows Claude and OpenCode availability as ✓ or ✗

### Requirement: Version control guidance

Documentation and CLI hints MUST state: commit `.agh/project.toml` and `.agh/lock.toml`; do not commit `.agh-cache/`. A recommended `.gitignore` entry for `.agh-cache/` SHOULD be suggested on first pull.

#### Scenario: Gitignore recommendation

- GIVEN first successful pull in a git repo without ignore rule
- WHEN pull completes
- THEN the user is advised to ignore `.agh-cache/`

#### Scenario: Project and lock are committable artifacts

- GIVEN successful sync and pull
- WHEN a developer inspects guidance
- THEN `.agh/project.toml` and `.agh/lock.toml` are described as team-committed files

### Requirement: Out of scope workspace MVP

Workspace commands MUST NOT integrate Cursor, Codex, or Pi paths; MUST NOT use `default.md`; MUST NOT support manual `sync --project` override.

#### Scenario: No Cursor paths

- GIVEN MVP pull
- WHEN applying skills
- THEN no `.cursor/` paths are written
