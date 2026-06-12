## Purpose

Resolve an exact active user email address to its canonical `usr_...` identifier via a dedicated server endpoint so CLI user refs can use emails without changing action endpoints.

## Requirements

### Requirement: Email-to-ID Resolution

The system MUST provide `GET /api/v1/users/by-email/{email:path}` returning `{id, email}` on exact active-user match.

#### Scenario: Exact active email resolves

- GIVEN an authenticated admin or owner request to the user email resolution endpoint
- AND an active user exists with email `member@example.com`
- WHEN the request is processed
- THEN the response MUST be 200 with that user's canonical ID and email

#### Scenario: Case variance returns not found

- GIVEN an active user exists with email `member@example.com`
- WHEN the request uses `Member@example.com`
- THEN the response MUST be 404

#### Scenario: Inactive user returns not found

- GIVEN a user exists with email `member@example.com`
- AND that user is inactive
- WHEN the request is processed
- THEN the response MUST be 404

#### Scenario: Malformed email returns validation error

- GIVEN an authenticated admin or owner request with `not-an-email`
- WHEN the request is processed
- THEN the response MUST be 400

### Requirement: Admin-Scoped User Lookup

The user email resolution endpoint MUST use the same access control boundary as user administration.

#### Scenario: Unauthenticated request rejected

- GIVEN an unauthenticated request
- WHEN the request is processed
- THEN the response MUST be 401

#### Scenario: Non-admin request forbidden

- GIVEN an authenticated member request
- WHEN the request is processed
- THEN the response MUST be 403

### Requirement: User Show Endpoint

The system MUST provide `GET /api/v1/users/{user_id}` so the CLI can show a resolved user by canonical ID.

#### Scenario: Canonical user ID resolves after email lookup

- GIVEN an authenticated admin or owner request
- AND a canonical active user ID exists
- WHEN the request is processed
- THEN the response MUST be 200 with the user's detail payload
