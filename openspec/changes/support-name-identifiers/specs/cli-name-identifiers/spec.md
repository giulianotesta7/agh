## Purpose

CLI project commands accepting project refs MUST resolve exact project names to canonical project IDs before action. Prefixed project IDs and all-digit project refs bypass name resolution.

CLI user commands accepting user refs MUST accept exact email addresses as user refs and resolve them to canonical user IDs before action.

CLI project-pack commands accepting pack refs MUST accept pack-version refs and resolve them to canonical domain-qualified pack refs before action.

## Requirements

### Requirement: Project Input Format Detection

The CLI MUST detect `prj_...`, all-digit project refs, and project names before routing project commands.

#### Scenario: Prefixed project ID passes through

- GIVEN an argument starting with `prj_`
- WHEN the project command runs
- THEN the ID MUST pass directly without resolution

#### Scenario: All-digit project ref passes through

- GIVEN `agh project get 12345`
- WHEN the argument is entirely digits
- THEN the CLI MUST pass it directly without name resolution

### Requirement: Project Reference by Name

The CLI MUST treat non-prefixed, non-all-digit project arguments as project names.

#### Scenario: Name resolves

- GIVEN `agh project get my-project`
- WHEN the argument does not start with `prj_` and is not all digits
- THEN the CLI MUST pass the resolved ID to the action

#### Scenario: Name not found

- GIVEN `agh project get nonexistent`
- WHEN resolution returns 404
- THEN the CLI MUST print not-found and exit non-zero

### Requirement: Numeric-Safe Project Names

Project names MUST NOT consist entirely of digits. The CLI/server behavior MUST prevent ambiguous project refs by rejecting digit-only project names at creation and rename.

#### Scenario: Digit-only name rejected at create

- GIVEN `agh project create 12345`
- WHEN the command runs
- THEN the CLI MUST report a validation error

#### Scenario: Digit-only name rejected at rename

- GIVEN `agh project update prj_... --name 12345`
- WHEN the command runs
- THEN the CLI MUST report a validation error

### Requirement: Project Resolution Before Action

The CLI MUST resolve human-readable project names to canonical project IDs before server mutation/detail calls.

#### Scenario: Resolution precedes delete

- GIVEN `agh project delete my-project`
- WHEN the CLI runs
- THEN it MUST resolve the name to a `prj_...` ID before calling the delete endpoint

### Requirement: Project Backward Compatibility

Existing project ID-based scripts MUST continue to work unchanged.

#### Scenario: Existing project ID script

- GIVEN `agh project get prj_abc123def456`
- WHEN the command runs
- THEN behavior MUST be identical to the current release

### Requirement: Unauthorized Project Resolution

When the project resolution endpoint returns 401, the CLI MUST surface the auth error.

#### Scenario: Expired token

- GIVEN `agh project get my-project`
- AND the auth token is expired
- WHEN resolution returns 401
- THEN the CLI MUST print an auth error and suggest re-login

### Requirement: User Input Format Detection

The CLI MUST deterministically classify user refs before routing user commands.

#### Scenario: Valid email wins over ID prefix

- GIVEN `agh user show usr_jane@example.com`
- WHEN the ref is a syntactically valid email address
- THEN the CLI MUST resolve it through the user email lookup endpoint
- AND it MUST NOT pass it through as a `usr_...` ID

#### Scenario: Prefixed user ID passes through when not an email

- GIVEN `agh user show usr_abc123def456`
- WHEN the ref starts with `usr_` and is not a syntactically valid email address
- THEN the CLI MUST pass it directly as the user ID

#### Scenario: Malformed email-like ref rejected

- GIVEN `agh user show not-an-email`
- WHEN the ref is neither a valid email address nor a `usr_...` ID
- THEN the CLI MUST reject it before the action request

### Requirement: User Email Resolution Before Action

The CLI MUST resolve exact email refs to canonical user IDs before user mutation, token, and project membership calls.

#### Scenario: User update by email resolves first

- GIVEN `agh user update member@example.com --role admin`
- WHEN the command runs
- THEN the CLI MUST resolve `member@example.com` to a `usr_...` ID before calling the user update endpoint

#### Scenario: User delete by email resolves first

- GIVEN `agh user delete member@example.com`
- WHEN the command runs
- THEN the CLI MUST resolve `member@example.com` to a `usr_...` ID before calling the user delete endpoint

#### Scenario: Token reset by email resolves first

- GIVEN `agh token reset member@example.com`
- WHEN the command runs
- THEN the CLI MUST resolve `member@example.com` to a `usr_...` ID before calling the token reset endpoint

#### Scenario: Project member removal by email resolves first

- GIVEN `agh project member remove my-project member@example.com`
- WHEN the command runs
- THEN the CLI MUST resolve the project ref and user email ref before calling the membership removal endpoint

### Requirement: Pack-Version Resolution Before Project-Pack Action

The CLI MUST resolve pack-version refs to canonical domain-qualified pack refs before project-pack assignment create or update calls.

#### Scenario: Project pack add resolves no-domain pack-version ref

- GIVEN `agh project pack add my-project onboarding@1.0.0`
- WHEN the command runs
- THEN the CLI MUST resolve `onboarding@1.0.0` through the pack-version resolver
- AND it MUST send the returned canonical `domain/name@version` ref in the assignment request

#### Scenario: Project pack update resolves pack-version ID

- GIVEN `agh project pack update my-project asn_abc --pack-ref packv_abc123`
- WHEN the command runs
- THEN the CLI MUST resolve `packv_abc123` through the pack-version resolver
- AND it MUST send the returned canonical `domain/name@version` ref in the update request

#### Scenario: Canonical pack ref passes through

- GIVEN `agh project pack add my-project acme/onboarding@latest`
- WHEN the command runs
- THEN the CLI MUST pass the canonical pack ref without resolver lookup
