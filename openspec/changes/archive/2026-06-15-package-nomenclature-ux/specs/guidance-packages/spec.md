# guidance-packages Specification

## Purpose

Rename the AGH public guidance model from pack/packs to package/packages across CLI, API, persistence, storage, lockfiles, docs, and errors, while preserving existing data and assignments.

## Requirements

### Requirement: Package terminology and routes

The system SHALL use package/packages as the canonical public term. It SHALL expose `agh package ...` and `/api/v1/packages` / `/api/v1/projects/{id}/packages`, and it SHALL NOT support `agh pack ...`, `agh pkg`, or pack-named API routes.

The `/api/v1/packages`, `/api/v1/packages/versions:resolve`, and package file download endpoints SHALL remain a global authenticated package registry: any active authenticated user may list, resolve, and download published packages. Project membership SHALL apply to project package assignments and pull-manifest access, not to global package registry reads.

#### Scenario: Canonical package surface

- GIVEN a user invokes `agh package list`
- WHEN the command is processed
- THEN the command succeeds using package terminology

#### Scenario: Old pack surface rejected

- GIVEN a user invokes `agh pack list`
- WHEN the command is processed
- THEN the CLI reports the command is unknown or unsupported

#### Scenario: Authenticated members can read the global package registry

- GIVEN a member is authenticated
- AND the member has no membership in a project
- WHEN the member lists packages or downloads a package file
- THEN the registry read succeeds

### Requirement: Package manifest and storage names

The system SHALL read and write `agh.package.toml` only. It SHALL migrate filesystem and cache-visible paths from `packs` to `packages`, preserve artifact contents, and SHALL update lockfile output to `[[packages]]` and `package_ref`.

#### Scenario: Package manifest is required

- GIVEN a workspace contains `agh.package.toml`
- WHEN a package command loads local authoring metadata
- THEN the manifest is accepted

#### Scenario: Legacy manifest is not accepted

- GIVEN a workspace contains only `agh.pack.toml`
- WHEN a package command loads local authoring metadata
- THEN the manifest is rejected

### Requirement: Data and ID migration

The system SHALL preserve existing pack data by migrating it into package schema names and package paths. If ID migration is required by existing data, it SHALL rewrite pack identifiers to `pkg_...` and `pkgv_...` while preserving assignment IDs and relationships.

#### Scenario: Existing pack records are preserved

- GIVEN existing pack rows and relations are present
- WHEN migration completes
- THEN the same logical records remain reachable under package names

#### Scenario: IDs are rewritten when needed

- GIVEN existing data contains pack-prefixed identifiers that require migration
- WHEN migration completes
- THEN those identifiers use `pkg_` and `pkgv_` prefixes

### Requirement: Package assignment UX

The system SHALL make `agh project package add` fully interactive when both project ref and package ref are omitted. It SHALL first require an interactive TTY, list visible projects, prompt for the project, then show only unassigned packages for the selected project. It SHALL make `agh project package add <project>` interactive for package selection when no package ref is provided. It SHALL resolve one latest-stable `domain/name@version` per package, require confirmation before assignment, print `Cancelled.` and exit 130 on cancellation, and remain non-interactive when an explicit package ref is provided.

#### Scenario: Missing project and ref opens project then package selectors

- GIVEN the user runs `agh project package add` without a project ref or package ref in an interactive terminal
- WHEN the command starts
- THEN visible projects are listed for selection
- AND the package selector is shown for unassigned packages on the selected project

#### Scenario: No-argument command requires a TTY

- GIVEN the user runs `agh project package add` without a project ref or package ref outside an interactive terminal
- WHEN the command starts
- THEN the command exits with usage code 2 before making API calls

#### Scenario: No visible projects is a no-op

- GIVEN the user runs `agh project package add` in an interactive terminal
- AND no projects are visible to the user
- WHEN the project list is fetched
- THEN the command reports that no projects were found and exits successfully without prompting for a package

#### Scenario: Invalid project selection is a usage error

- GIVEN the user runs `agh project package add` in an interactive terminal
- WHEN the user selects a project number outside the visible list
- THEN the command exits with usage code 2

#### Scenario: Missing ref opens selector

- GIVEN the user runs `agh project package add <project>` without a ref
- WHEN the command starts
- THEN a selector is shown for unassigned packages only

#### Scenario: Single positional argument is always project

- GIVEN the user runs `agh project package add <project>` with one positional argument
- WHEN the command starts
- THEN that argument is resolved as a project ref
- AND it is not treated as a package ref

#### Scenario: Explicit ref stays CI-friendly

- GIVEN the user runs `agh project package add <project> domain/name@1.2.3`
- WHEN the command starts
- THEN no interactive prompt is shown

#### Scenario: All packages already assigned

- GIVEN every package is already assigned to the project
- WHEN the user opens the selector
- THEN the command explains no unassigned packages exist and suggests list or update
