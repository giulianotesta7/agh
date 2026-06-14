# Delta for request-body-validation

## ADDED Requirements

### Requirement: Invalid Content-Length becomes JSON 400

The server MUST return a JSON 400 response for malformed, non-numeric, or otherwise invalid `Content-Length` values.

#### Scenario: Malformed header is rejected

- GIVEN a request contains a malformed `Content-Length`
- WHEN the server validates the request body
- THEN it MUST respond with HTTP 400
- AND the response MUST be JSON

#### Scenario: Non-numeric header is rejected

- GIVEN a request contains a non-numeric `Content-Length`
- WHEN the server validates the request body
- THEN it MUST respond with HTTP 400
- AND it MUST NOT raise an unhandled exception

### Requirement: Oversized payloads still return 413

The server MUST preserve existing `413 Payload Too Large` behavior when a request body exceeds the allowed size.

#### Scenario: Oversized request remains 413

- GIVEN a request body exceeds the configured limit
- WHEN the server checks request size
- THEN it MUST return HTTP 413
- AND it MUST NOT be converted into HTTP 400
