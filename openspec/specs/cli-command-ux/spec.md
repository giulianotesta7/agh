# Delta for cli-command-ux

## ADDED Requirements

### Requirement: Discoverable root and help output

`agh` MUST expose the full command tree from root help, support `--version`, and show command-specific help for every top-level and nested command.
Reference arguments MUST use honest `*_REF` names in help text and examples.

#### Scenario: Root help shows the command tree

- GIVEN a user runs `agh --help`
- WHEN help is rendered
- THEN it lists the available top-level commands and their nested subcommands
- AND it includes `--version`

#### Scenario: Command help is local and specific

- GIVEN a user runs `agh package --help`
- WHEN help is rendered
- THEN it describes package-only commands and flags
- AND it does not require reading root help first

### Requirement: Instance-scoped config and separated auth flows

The CLI MUST treat config as instance-only.
`login`, `whoami`, and `logout` MUST be separate commands.
`login` MUST support both interactive and flag-based authentication and MUST NOT prompt for an instance URL.

#### Scenario: Login uses the configured instance

- GIVEN an instance is already configured
- WHEN the user runs `agh login`
- THEN the CLI authenticates against that instance
- AND it does not prompt for an instance URL

#### Scenario: Whoami and logout are distinct commands

- GIVEN a user is logged in
- WHEN they run `agh whoami` or `agh logout`
- THEN each command performs only its own action

### Requirement: Resource verbs use list/describe/create/update/activate/deactivate

User, project, and collection resources MUST use list, describe, create, update, activate, and deactivate verbs.
User token rotation MUST be exposed as `user token rotate`.
Project member management MUST be available under `project member`.

#### Scenario: Resource vocabulary is consistent

- GIVEN a user runs `agh user --help`, `agh project --help`, or `agh collection --help`
- WHEN help is rendered
- THEN it uses the agreed verbs and shows member management under project

### Requirement: Package assignment is target-based and unambiguous

Package assignment MUST be expressed with `--project` or `--collection` and MUST NOT use positional targets.
The target flags MUST be mutually exclusive.
`assign`, `activate`, `deactivate`, and `unassign` MUST be available.
`describe` MUST resolve `@latest` to the highest SemVer version.

#### Scenario: Package target is chosen by flag

- GIVEN a user runs package assignment commands
- WHEN they provide `--project` or `--collection`
- THEN the CLI assigns to exactly one target
- AND it rejects both flags together

#### Scenario: Latest package describe resolves to highest version

- GIVEN a package reference uses `@latest`
- WHEN `agh package describe` runs
- THEN it describes the highest SemVer release

### Requirement: Target and skill commands respect scope and resolution order

`target` MUST support workspace and global scope.
Skill installation MUST resolve targets by explicit `--target`, then workspace, then global, then interactive prompt, and MUST fail non-interactively when unresolved.
Official skill commands MUST be reduced to the supported surface.

#### Scenario: Skill install resolves target deterministically

- GIVEN a target is not passed explicitly
- WHEN a workspace target exists
- THEN the CLI installs to the workspace target
- AND it falls back to global only when workspace is unavailable

### Requirement: Link replaces sync and pull help is explicit

`link` MUST replace `sync` as the supported command name.
`pull` help MUST clearly describe what it does and what it does not do.

#### Scenario: Legacy sync is not part of official behavior

- GIVEN a user inspects the command tree
- WHEN they look for synchronization commands
- THEN `link` is shown instead of `sync`

### Requirement: Legacy aliases are not part of the supported contract

The official CLI behavior MUST NOT promise legacy aliases for removed names or unsupported command forms.

#### Scenario: Removed names are absent from help

- GIVEN a user reads help output
- WHEN they search for legacy command names
- THEN unsupported aliases are not advertised as official behavior
