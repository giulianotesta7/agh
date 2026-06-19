# global-skill-collections Specification

## Purpose

Provide admin-curated global skill collections that members can discover and install into their selected agent’s native global skill directory without changing repo/workspace-scoped project behavior.

## Requirements

### Requirement: Collection governance

The system MUST treat collections as global tooling catalogs, separate from repo-backed projects. Only owners and admins MAY create, edit, or assign collections; members MAY list available collection skills.
Collections and collection package assignments MUST support active/inactive state. Available skill listing and install resolution MUST include only active collections and active collection package assignments.

#### Scenario: Admin manages a collection

- GIVEN an authenticated owner or admin
- WHEN they create or update a collection or assign a package to it
- THEN the change is accepted

#### Scenario: Member lists collections

- GIVEN an authenticated member
- WHEN they request available collection skills
- THEN the system returns readable collection listings

#### Scenario: Inactive collection is excluded

- GIVEN a collection is inactive
- WHEN a member lists or resolves available skills
- THEN skills from that collection are not returned

#### Scenario: Inactive collection package assignment is excluded

- GIVEN an active collection has an inactive package assignment
- WHEN a member lists or resolves available skills
- THEN skills from that package assignment are not returned

### Requirement: Skill-only package assignment

The system MUST accept only skill-only packages for collection assignment. Packages containing `instructions/AGENTS.md` or `instructions/CLAUDE.md` MUST be rejected.

#### Scenario: Valid skill package is assigned

- GIVEN a package that contains only skill artifacts
- WHEN an owner or admin assigns it to a collection
- THEN the assignment succeeds

#### Scenario: Instruction-bearing package is rejected

- GIVEN a package that contains `instructions/AGENTS.md` or `instructions/CLAUDE.md`
- WHEN it is assigned to a collection
- THEN the system rejects the assignment

### Requirement: Admin collection CLI

The `agh collection ...` CLI MUST provide admin-only collection management for create, list, get, update, and deactivate actions. It MUST use the configured AGH server and existing `agh login` credentials, and it MUST remain separate from consumer `agh skill ...` commands.

#### Scenario: Admin manages a collection

- GIVEN an authenticated owner or admin
- WHEN they run an `agh collection` management command
- THEN the request is sent to the configured AGH server
- AND the command succeeds or fails with the server authorization result

#### Scenario: Member is denied

- GIVEN an authenticated member
- WHEN they run an `agh collection` management command
- THEN the CLI surfaces the authorization failure
- AND it does not use any collection-specific auth or server override

### Requirement: Collection package assignment CLI

The `agh collection package ...` CLI MUST support assigning, listing, updating, and removing collection package assignments for skill-only packages. Deactivation of a collection MUST use the same active=false semantics as project deactivation.

#### Scenario: Assign a skill-only package

- GIVEN an owner or admin and a skill-only package reference
- WHEN they assign the package to a collection
- THEN the assignment succeeds
- AND the resulting assignment remains scoped to collection package management

#### Scenario: Reject instruction-bearing packages

- GIVEN a package containing `instructions/AGENTS.md` or `instructions/CLAUDE.md`
- WHEN it is assigned to a collection
- THEN the CLI surfaces the server rejection

#### Scenario: Deactivate a collection

- GIVEN an active collection
- WHEN the user deactivates it from the CLI
- THEN the request sets the collection inactive using active=false semantics
- AND inactive collections are not presented as active targets in follow-up CLI flows

### Requirement: Global skill install, list, and remove

The `agh skill install <package-ref> <skill-name>` command MUST install collection-backed skills globally for the selected agent, `agh skill list` MUST show skills available from active collections, and `agh skill remove <skill-name>` MUST remove the local global installation for the selected or default agent.

#### Scenario: Install resolves a concrete package version

- GIVEN an available collection package ref such as `@latest`
- WHEN a member installs a skill
- THEN the system records the resolved version and verified `SKILL.md` artifact checksum in local AGH state

#### Scenario: Remove clears the local installation record

- GIVEN a previously installed global skill
- WHEN the user removes it
- THEN the local installation is removed and the local lock is updated

### Requirement: Global skill target, checksum, and conflict rules

The system MUST install to the selected agent’s native global skill directory, maintain AGH-owned cache and lock state under user AGH state, and enforce update rules: same checksum is a no-op, AGH-owned version or checksum changes update automatically, same skill name from a different package conflicts, and untracked targets require `--force`.
Skill listing and resolution MUST expose a checksum for the downloaded `SKILL.md` artifact content. The CLI MUST verify downloaded artifact content against that checksum before writing the target, cache, or lock; `--force` MUST NOT bypass checksum verification. Package-level checksums MAY be exposed separately for compatibility, but local global-skill locks MUST use the artifact checksum for install integrity.

#### Scenario: AGH-owned install updates cleanly

- GIVEN an AGH-owned installed skill with a changed checksum or version
- WHEN the user installs again
- THEN the installation updates automatically

#### Scenario: Untracked target requires force

- GIVEN an existing local target not tracked by AGH
- WHEN the user installs without `--force`
- THEN the system rejects the overwrite

### Requirement: Collection by-name reference support

The system MUST expose an authenticated exact-name resolver for active collections and the admin collection CLI MUST accept collection targets as either canonical `col_...` IDs or exact collection names. The resolver MUST be visibility-scoped consistently with collection read/list behavior and MUST NOT resolve inactive collections by name.

#### Scenario: Resolve an active collection by exact name

- GIVEN an authenticated user and an active visible collection named `Team Skills`
- WHEN they request `GET /api/v1/collections/by-name/Team%20Skills`
- THEN the response includes the collection `id` and `name`
- AND the name match is exact

#### Scenario: Do not resolve inactive or mismatched names

- GIVEN an inactive collection named `Team Skills`
- WHEN an authenticated user resolves `Team Skills` by name
- THEN the response is not found
- AND resolving `team skills` is also not found

#### Scenario: CLI resolves collection names before target operations

- GIVEN an owner or admin and an active collection named `Team Skills`
- WHEN they run a collection-targeted CLI command with `Team Skills`
- THEN the CLI resolves the name through the by-name endpoint
- AND the follow-up request uses the resolved `col_...` ID

#### Scenario: CLI keeps canonical collection IDs unchanged

- GIVEN a collection target `col_123`
- WHEN the CLI runs a collection-targeted command
- THEN it uses `col_123` as the target ID
- AND it does not perform a by-name resolver request

### Requirement: Agent selection and defaults

The system MUST use the configured default global-skills agent when present. Otherwise it MUST prompt with the wording `Select the agent for global skills:` and allow the user to save a new default after selection.

#### Scenario: Default agent is used

- GIVEN a configured default global-skills agent
- WHEN the user runs a global skill command
- THEN that agent is selected automatically

#### Scenario: User selects and saves a default

- GIVEN no saved default agent
- WHEN the user is prompted and selects an agent
- THEN the command proceeds and the user MAY save that choice as the default
