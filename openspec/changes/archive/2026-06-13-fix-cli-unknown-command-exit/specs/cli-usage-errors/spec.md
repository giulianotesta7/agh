# Delta for CLI Usage Errors

## ADDED Requirements

### Requirement: Unknown command exits with usage error

The CLI MUST preserve the current help-first visible output for unknown root commands and unknown nested subcommands, while returning a non-zero usage-error exit status, preferably `2`. For currently implemented/tested unknown nested subcommands, the preserved visible output is the root/no-argument `APP_HELP`, not group-specific help.

#### Scenario: Unknown root command

- GIVEN the user runs `agh does-not-exist`
- WHEN the CLI resolves the command
- THEN it MUST show the existing root/no-argument `APP_HELP` output
- AND it MUST exit with a non-zero usage-error status

#### Scenario: Unknown nested subcommand

- GIVEN the user runs `agh config does-not-exist`
- WHEN the CLI resolves the command
- THEN it MUST show the current visible help output preserved as implemented/tested: root/no-argument `APP_HELP`
- AND it MUST exit with a non-zero usage-error status

### Requirement: Applicability covers routed command groups

The CLI MUST apply unknown-command usage-error behavior to root and applicable nested groups, including config, user, token, project, project member, project pack, pack, and agent.

#### Scenario: Nested group typo in project member path

- GIVEN the user runs `agh project member does-not-exist`
- WHEN the CLI resolves the command
- THEN it MUST show the current visible help output preserved as implemented/tested: root/no-argument `APP_HELP`
- AND it MUST exit with a non-zero usage-error status

#### Scenario: Nested group typo in agent path

- GIVEN the user runs `agh agent does-not-exist`
- WHEN the CLI resolves the command
- THEN it MUST show the current visible help output preserved as implemented/tested: root/no-argument `APP_HELP`
- AND it MUST exit with a non-zero usage-error status

### Requirement: Valid help paths remain successful

The CLI MUST keep explicit help paths and no-argument help behavior successful where currently intended.

#### Scenario: Root help succeeds

- GIVEN the user runs `agh --help`
- WHEN the CLI resolves the command
- THEN it MUST exit successfully
- AND it MUST display the standard help output

#### Scenario: Group help succeeds

- GIVEN the user runs `agh config --help`
- WHEN the CLI resolves the command
- THEN it MUST exit successfully
- AND it MUST display the standard group help output
