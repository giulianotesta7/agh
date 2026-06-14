# Delta for pack-publish-integrity

## ADDED Requirements

### Requirement: Startup-derived storage root

Pack publish operations MUST use the storage root established at application startup for all publish-time filesystem paths.

#### Scenario: Publish uses stable startup data directory

- GIVEN the application has started with a configured data directory
- WHEN a pack is published
- THEN the publish process MUST resolve storage paths from that startup state
- AND the final pack files MUST be written under the same configured root

#### Scenario: Request-time drift is ignored

- GIVEN the process environment changes after startup
- WHEN a pack is published
- THEN the publish result MUST remain bound to the startup-derived storage root

### Requirement: Safe orphan final-pack cleanup

The system MUST recover or remove a proven orphan final pack directory only when no matching database row can be established.

#### Scenario: Proven orphan is cleaned

- GIVEN a final pack directory exists for a version with no matching database row
- WHEN publish recovery runs for that version
- THEN the orphan directory MUST be cleaned or reused safely
- AND the publish MUST be allowed to proceed

#### Scenario: Ambiguous storage is preserved

- GIVEN a final pack directory cannot be proven orphaned
- WHEN recovery logic evaluates it
- THEN the directory MUST NOT be deleted
- AND the publish MUST fail closed rather than risking valid data
