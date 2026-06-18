# Delta for global-skill-collections

## ADDED Requirements

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
