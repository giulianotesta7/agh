# Delta for workspace-git-subprocess-timeouts

## ADDED Requirements

### Requirement: Sync remote lookup timeout

Local Git remote discovery used by `agh sync` MUST use a 5-second timeout and MUST fail clearly when the lookup exceeds that limit.

The system MUST treat remote detection as required behavior for sync and MUST return a non-zero, user-facing error when the timeout is reached.

#### Scenario: Remote lookup times out during sync

- GIVEN a local repository whose configured remote cannot be resolved within 5 seconds
- WHEN the user runs `agh sync`
- THEN the command fails with a clear timeout error
- AND the exit status is non-zero

#### Scenario: Remote lookup succeeds within the timeout

- GIVEN a local repository with a reachable remote URL
- WHEN the user runs `agh sync`
- THEN the remote is resolved successfully
- AND sync continues normally

### Requirement: Pull hint checks are advisory

Local Git hint checks used by `agh pull` MUST use a 5-second timeout and SHOULD skip the hint when the timeout is exceeded.

The system MUST continue the pull result when advisory VCS hint checks time out, rather than failing the command.

#### Scenario: Advisory hint check times out during pull

- GIVEN a local repository where a VCS hint check exceeds 5 seconds
- WHEN the user runs `agh pull`
- THEN the pull completes normally
- AND the VCS hint is omitted

#### Scenario: Advisory hint check succeeds during pull

- GIVEN a local repository where the VCS hint check finishes within 5 seconds
- WHEN the user runs `agh pull`
- THEN the pull completes normally
- AND the VCS hint is shown when applicable
