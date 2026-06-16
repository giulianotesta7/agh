# Spec: Package Artifact Read Errors

## ADDED Requirements

### Requirement: Controlled package file download read errors

The system MUST preserve existing traversal and unsafe-path protections for published package downloads. Missing expected artifacts MUST return JSON 404. Artifact storage that is present but unreadable, corrupt, permission-denied, or failing during I/O MUST return JSON 503.

#### Scenario: Missing artifact returns JSON 404

- GIVEN a published package exists and the requested file path is valid
- WHEN the artifact file is missing from storage
- THEN the download response is JSON 404
- AND no raw filesystem exception is exposed

#### Scenario: Unreadable artifact returns JSON 503

- GIVEN a published package exists and the requested file path is valid
- WHEN the artifact cannot be read because of I/O, permissions, or decode failure
- THEN the download response is JSON 503
- AND the response uses the stable JSON error shape

#### Scenario: Unsafe path still denied

- GIVEN a download request uses traversal or another unsafe path
- WHEN the route evaluates the request
- THEN the response is JSON 404
- AND the route does not read outside the package artifact boundary

### Requirement: Controlled pull-manifest artifact assembly errors

The system MUST apply the same classification while assembling pull-manifest artifact metadata. Missing expected artifacts MUST fail with a JSON 404-equivalent response, unreadable storage MUST fail with a JSON 503-equivalent response, and expected artifact failures MUST NOT be silently dropped. Legacy manifests that lack stored artifact path inventory MAY continue conservative discovery fallback; full storage-loss detection for those legacy packages is deferred because the server cannot distinguish intentionally absent optional files from lost historical files.

#### Scenario: Missing artifact is reported during pull-manifest assembly

- GIVEN a project pull-manifest is assembled from published artifacts
- WHEN an expected artifact is missing from storage
- THEN manifest assembly reports a JSON 404-equivalent error
- AND the artifact is not silently omitted

#### Scenario: Legacy fallback without artifact inventory remains conservative

- GIVEN a legacy package lacks stored artifact path inventory
- AND it originally contained instruction or skill artifacts that are now missing from storage
- WHEN pull-manifest assembly uses legacy discovery fallback
- THEN the response may include only remaining discoverable artifacts
- AND change notes document that full legacy storage-loss detection is deferred

#### Scenario: Unreadable artifact is reported during pull-manifest assembly

- GIVEN pull-manifest assembly reads published artifact storage
- WHEN storage raises I/O, permission, or decode failure
- THEN manifest assembly reports a JSON 503-equivalent error
- AND the manifest response remains predictable
