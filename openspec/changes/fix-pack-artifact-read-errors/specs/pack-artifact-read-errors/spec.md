# Spec: Pack Artifact Read Errors

## ADDED Requirements

### Requirement: Controlled pack file download read errors

The system MUST preserve existing traversal and unsafe-path protections for published pack downloads. Missing expected artifacts MUST return JSON 404. Artifact storage that is present but unreadable, corrupt, permission-denied, or failing during I/O MUST return JSON 503.

#### Scenario: Missing artifact returns JSON 404

- GIVEN a published pack exists and the requested file path is valid
- WHEN the artifact file is missing from storage
- THEN the download response is JSON 404
- AND no raw filesystem exception is exposed

#### Scenario: Unreadable artifact returns JSON 503

- GIVEN a published pack exists and the requested file path is valid
- WHEN the artifact cannot be read because of I/O, permissions, or decode failure
- THEN the download response is JSON 503
- AND the response uses the stable JSON error shape

#### Scenario: Unsafe path still denied

- GIVEN a download request uses traversal or another unsafe path
- WHEN the route evaluates the request
- THEN the response is JSON 404
- AND the route does not read outside the pack artifact boundary

### Requirement: Controlled pull-manifest artifact assembly errors

The system MUST apply the same classification while assembling pull-manifest artifact metadata. Missing expected artifacts MUST fail with a JSON 404-equivalent response, unreadable storage MUST fail with a JSON 503-equivalent response, and expected artifact failures MUST NOT be silently dropped.

#### Scenario: Missing artifact is reported during pull-manifest assembly

- GIVEN a project pull-manifest is assembled from published artifacts
- WHEN an expected artifact is missing from storage
- THEN manifest assembly reports a JSON 404-equivalent error
- AND the artifact is not silently omitted

#### Scenario: Legacy mixed-pack storage loss is not returned as a partial manifest

- GIVEN a legacy pack lacks stored artifact path inventory
- AND it originally contained instruction and skill artifacts
- WHEN the skill storage directory is missing
- THEN manifest assembly reports a JSON 404-equivalent error
- AND the response does not return only the remaining instruction artifacts

#### Scenario: Unreadable artifact is reported during pull-manifest assembly

- GIVEN pull-manifest assembly reads published artifact storage
- WHEN storage raises I/O, permission, or decode failure
- THEN manifest assembly reports a JSON 503-equivalent error
- AND the manifest response remains predictable
