# Delta: workspace-pull-atomicity

## ADDED Requirements

### Requirement: Local pull commit boundary
`agh pull` MUST commit workspace targets, `.agh-cache/packages`, skill targets, and `.agh/lock.toml` consistently.

#### Scenario: Successful local pull
- GIVEN outputs can be staged
- WHEN pull completes
- THEN final outputs are consistent and no staging paths remain

#### Scenario: Failure before promotion
- GIVEN staging fails
- WHEN pull aborts
- THEN no new cache, target, skill, or lock output is committed and AGH-owned staging is cleaned up

### Requirement: Failure cleanup and preserved prior state
Local write failures MUST clean AGH-owned staging paths and MUST NOT publish a mismatched lockfile.

#### Scenario: Failure during promotion
- GIVEN one staged output succeeds and a later one fails
- WHEN pull exits with error
- THEN the old cache and lock remain unchanged and remaining staged outputs are removed
