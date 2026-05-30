# Projects Specification

## Purpose

Projects as the unit linking git repositories to assigned guidance packs and developer membership.

## Requirements

### Requirement: Project CRUD

Users with appropriate admin privileges MUST be able to create, read, update, and deactivate projects via the API and CLI. Each project MUST have a human-readable name and a linked git repository URL stored in normalized form.

#### Scenario: Admin creates project

- GIVEN an authenticated `admin`
- WHEN they create a project with name `Platform` and repo URL `git@github.com:org/app.git`
- THEN the project is persisted with a prefixed id and normalized repo URL

#### Scenario: Member reads accessible project

- GIVEN user U is a project developer on project P
- WHEN U requests project P
- THEN project metadata is returned

### Requirement: Normalized git repository URL matching

The system MUST normalize git remote URLs before storage and comparison (scheme/host/path canonicalization per shared `agh.common` rules). Project linkage and `agh sync` matching MUST use normalized URLs only.

#### Scenario: Equivalent URLs normalize equally

- GIVEN `https://github.com/org/app.git` and `git@github.com:org/app.git` normalize to the same key
- WHEN either URL is stored on a project
- THEN sync matching treats an equivalent local remote as the same repository

#### Scenario: Different repos do not match

- GIVEN project P is linked to normalized URL for `org/app`
- WHEN a local repo remote normalizes to `org/other`
- THEN sync does not link to P

### Requirement: Duplicate normalized repo URL policy

The system MUST reject creation or update that would result in two active projects with the same normalized repository URL.

#### Scenario: Second project same repo rejected

- GIVEN active project P1 uses normalized URL `github.com/org/app`
- WHEN an admin creates project P2 with a URL that normalizes to the same key
- THEN the create fails with a client error
- AND P1 remains unchanged

### Requirement: Role-less project developer membership

Project membership MUST NOT assign per-project roles for MVP. A user is either a project developer (member of the project) or not. Any active authenticated user MAY be added as a project developer.

#### Scenario: Member added as developer

- GIVEN active user `dev@example.com` with global role `member`
- WHEN an admin adds them to project P as developer
- THEN they can access P-scoped resources including pull-manifest

#### Scenario: Non-member denied project pull-manifest

- GIVEN user U is not a developer on project P
- WHEN U requests P's pull-manifest
- THEN the request is rejected without confirming whether project P exists

### Requirement: Project-pack assignment

Admins MUST be able to assign packs to a project by pack id, allowing `latest` as the version tag on assignment. Assignments MUST be ordered and retrievable for pull-manifest generation.

#### Scenario: Assign concrete version

- GIVEN pack `acme/onboarding@1.0.0` exists
- WHEN admin assigns it to project P
- THEN pull-manifest for P includes that pack at `1.0.0`

#### Scenario: Assign latest resolves at pull time

- GIVEN assignment `acme/onboarding@latest` and published versions `1.0.0`, `1.1.0`
- WHEN pull-manifest is generated
- THEN the assignment resolves to `1.1.0`

### Requirement: Deactivated project behavior

Deactivated projects MUST NOT accept new assignments or serve pull-manifests for sync/pull consumption. Existing consumer lockfiles MAY remain until the next pull attempt, which MUST fail clearly.

#### Scenario: Pull-manifest denied for inactive project

- GIVEN project P is deactivated
- WHEN a former developer requests pull-manifest
- THEN the request is rejected
