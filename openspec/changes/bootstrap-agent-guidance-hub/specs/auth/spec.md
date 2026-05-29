# Auth Specification

## Purpose

Identity, API token lifecycle, bootstrap owner creation, and role-based authorization for Agent Guidance Hub (AGH).

## Requirements

### Requirement: Bootstrap owner on first server start

On the first successful server start with an empty user store, the system MUST create exactly one active user with role `owner` using the email from `AGH_BOOTSTRAP_OWNER_EMAIL`. The system MUST generate one initial API token for that owner and MUST write the plaintext token only to `/data/secrets/initial_owner_token`. The system MUST NOT log the token value; it MAY log only the file path.

#### Scenario: First start creates owner and secret file

- GIVEN no users exist in the database and `AGH_BOOTSTRAP_OWNER_EMAIL` is set to a valid email
- WHEN the server completes its first successful startup
- THEN an `owner` user exists with that email
- AND a plaintext token exists only in `/data/secrets/initial_owner_token`
- AND server logs do not contain the token value

#### Scenario: Subsequent starts do not re-bootstrap

- GIVEN at least one user already exists
- WHEN the server starts
- THEN no new bootstrap owner is created
- AND `/data/secrets/initial_owner_token` is not overwritten by bootstrap

### Requirement: Email as user identifier

The system MUST use a valid email address as the canonical user identifier for authentication and administration. The system MUST reject user creation or login identifiers that are not valid email addresses.

#### Scenario: Valid email accepted

- GIVEN an admin creates a user with email `dev@example.com`
- WHEN the user record is stored
- THEN the user's identifier is `dev@example.com`

#### Scenario: Invalid email rejected

- GIVEN a create-user request with identifier `not-an-email`
- WHEN the request is processed
- THEN the request is rejected with a client error
- AND no user is created

### Requirement: API tokens stored hashed only

The system MUST store API tokens only in hashed form in the database. The system MUST NOT persist plaintext API tokens in the database or in application logs. The bootstrap initial-owner file is the only permitted server-side plaintext token storage for MVP.

#### Scenario: Token issuance stores hash

- GIVEN an owner or admin issues a new API token for a user
- WHEN the token is saved
- THEN the database contains only a hash of the token
- AND the plaintext token is returned once to the caller

#### Scenario: Authentication compares hash

- GIVEN a user has an active hashed token
- WHEN a request presents the correct plaintext token
- THEN authentication succeeds

### Requirement: No automatic token expiry

The system MUST NOT expire API tokens automatically based on age or inactivity for MVP. Tokens remain valid until explicitly rotated, reset, or revoked by an authorized actor.

#### Scenario: Old token remains valid

- GIVEN a token was issued months ago and not rotated
- WHEN the token is used on an authenticated request
- THEN the request is authorized

### Requirement: Global roles owner, admin, member

Each user MUST have exactly one global role: `owner`, `admin`, or `member`. Role semantics MUST be: `owner` — full control including admin promotion; `admin` — manage members and operational resources except owner lifecycle; `member` — standard authenticated access without global admin powers.

#### Scenario: Owner can perform admin-only operations

- GIVEN a user with role `owner`
- WHEN they call an endpoint restricted to `admin` or `owner`
- THEN the request succeeds

#### Scenario: Member denied global admin operations

- GIVEN a user with role `member`
- WHEN they attempt to create or delete another user
- THEN the request is rejected with forbidden

### Requirement: Owner protection

The system MUST NOT allow demotion, deletion, or deactivation of the last remaining `owner` user. The system MUST NOT allow changing an `owner` user's role to `admin` or `member` if that would leave zero owners.

#### Scenario: Cannot demote sole owner

- GIVEN exactly one `owner` exists
- WHEN an admin attempts to change that user's role to `member`
- THEN the operation is rejected
- AND the user remains `owner`

#### Scenario: Cannot delete sole owner

- GIVEN exactly one `owner` exists
- WHEN any actor attempts to delete that user
- THEN the operation is rejected

### Requirement: Admin management of members

Users with role `admin` or `owner` MUST be able to create, update, and deactivate `member` users. Only `owner` MUST be able to create or promote users to `admin`.

#### Scenario: Admin creates member

- GIVEN an authenticated `admin`
- WHEN they create a user with role `member`
- THEN the user is created

#### Scenario: Admin cannot create admin

- GIVEN an authenticated `admin`
- WHEN they attempt to create a user with role `admin`
- THEN the request is rejected with forbidden

#### Scenario: Owner creates admin

- GIVEN an authenticated `owner`
- WHEN they create a user with role `admin`
- THEN the user is created with role `admin`

### Requirement: Token rotate and reset

Authorized `owner` or `admin` actors MUST be able to rotate or reset a user's API token. Rotation MUST invalidate the previous token for authentication. The system MUST return the new plaintext token exactly once at issuance.

#### Scenario: Rotate invalidates old token

- GIVEN user U has token T1
- WHEN an authorized actor rotates U's token and receives T2
- THEN requests using T1 are rejected
- AND requests using T2 succeed

#### Scenario: Reset after compromise

- GIVEN a user's token may be compromised
- WHEN an admin resets the token
- THEN only the new token authenticates as that user

### Requirement: Out of scope for auth MVP

The system MUST NOT provide web UI login, SSO/LDAP, or automatic token expiry in this change.

#### Scenario: No SSO endpoints

- GIVEN the MVP server deployment
- WHEN a client requests SSO or OAuth login flows
- THEN such flows are not available
