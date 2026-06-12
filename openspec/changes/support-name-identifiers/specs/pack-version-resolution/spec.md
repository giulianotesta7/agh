Pack-version refs MUST be resolvable for project-pack CLI assignment workflows.

## Requirements

### Requirement: Pack-Version Ref Parsing

Pack-version parsing MUST accept pack version IDs, canonical domain-qualified refs, and no-domain name/version refs.

#### Scenario: Pack version ID accepted

- GIVEN `packv_0123456789abcdef`
- WHEN a pack-version ref is parsed
- THEN it MUST be classified as a pack version ID

#### Scenario: Canonical pack-version ref accepted

- GIVEN `acme/onboarding@1.0.0`
- WHEN a pack-version ref is parsed
- THEN it MUST be classified with domain `acme`, name `onboarding`, and version `1.0.0`

#### Scenario: No-domain pack-version ref accepted

- GIVEN `onboarding@1.0.0`
- WHEN a pack-version ref is parsed
- THEN it MUST be classified with name `onboarding` and version `1.0.0`

### Requirement: Pack-Version Resolve Endpoint

The server MUST expose `GET /api/v1/packs/versions:resolve?ref=<ref>` for authenticated callers and return the canonical pack-version identity.

#### Scenario: Canonical ref resolves

- GIVEN a published pack version `acme/onboarding@1.0.0`
- WHEN an authenticated caller requests `/api/v1/packs/versions:resolve?ref=acme/onboarding%401.0.0`
- THEN the response MUST include `id`, `pack_ref`, `domain`, `name`, and `version`
- AND `pack_ref` MUST be `acme/onboarding@1.0.0`

#### Scenario: No-domain ref resolves when unique

- GIVEN exactly one published pack version named `onboarding` at version `1.0.0`
- WHEN an authenticated caller requests `/api/v1/packs/versions:resolve?ref=onboarding%401.0.0`
- THEN the response MUST include the canonical domain-qualified `pack_ref`

#### Scenario: Pack version ID resolves

- GIVEN a published pack version with ID `packv_0123456789abcdef`
- WHEN an authenticated caller requests `/api/v1/packs/versions:resolve?ref=packv_0123456789abcdef`
- THEN the response MUST include the canonical domain-qualified `pack_ref`

#### Scenario: Unauthenticated resolve is rejected

- GIVEN no bearer token
- WHEN a caller requests `/api/v1/packs/versions:resolve?ref=acme/onboarding%401.0.0`
- THEN the server MUST return `401`

#### Scenario: Missing ref query is rejected by request validation

- GIVEN no `ref` query parameter
- WHEN an authenticated caller requests `/api/v1/packs/versions:resolve`
- THEN the server MUST return a request validation error

#### Scenario: Malformed ref is rejected

- GIVEN an invalid ref `not-a-ref`
- WHEN an authenticated caller requests `/api/v1/packs/versions:resolve?ref=not-a-ref`
- THEN the server MUST return `400`

#### Scenario: Missing ref returns not found

- GIVEN no matching published pack version
- WHEN an authenticated caller requests `/api/v1/packs/versions:resolve?ref=acme/missing%401.0.0`
- THEN the server MUST return `404`

#### Scenario: No-domain ambiguous ref returns conflict

- GIVEN two domains publish `onboarding@1.0.0`
- WHEN an authenticated caller requests `/api/v1/packs/versions:resolve?ref=onboarding%401.0.0`
- THEN the server MUST return `409`

### Requirement: Project-Pack CLI Resolution

Project-pack CLI commands MUST resolve non-canonical pack-version refs through the pack-version resolver before sending assignment requests.

#### Scenario: Add resolves no-domain pack-version ref

- GIVEN `agh project pack add my-project onboarding@1.0.0`
- WHEN the no-domain ref uniquely resolves to `acme/onboarding@1.0.0`
- THEN the CLI MUST send `acme/onboarding@1.0.0` as `pack_ref`

#### Scenario: Update resolves pack-version ID

- GIVEN `agh project pack update my-project asn_abc --pack-ref packv_0123456789abcdef`
- WHEN the ID resolves to `acme/onboarding@1.2.0`
- THEN the CLI MUST send `acme/onboarding@1.2.0` as `pack_ref`
