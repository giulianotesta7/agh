# Packs Specification

## Purpose

Versioned agent guidance packs: identity, manifest, sources, publishing immutability, and consumption rules.

## Requirements

### Requirement: Pack identity format

Every pack MUST be identified as `<domain>/<name>@<version>` where `domain` and `name` are non-empty slugs, and `version` is either an exact SemVer string or the tag `latest` (only for assignment/consumption references, not for publish).

#### Scenario: Valid pack id accepted

- GIVEN manifest for `acme/onboarding@1.0.0`
- WHEN the pack is published
- THEN the pack is stored under that id

#### Scenario: Invalid id rejected

- GIVEN a publish request with id `bad id@1.0.0`
- WHEN validation runs
- THEN publish is rejected

### Requirement: Required agh.pack.toml manifest

Every published pack MUST include `agh.pack.toml` declaring at minimum domain, name, version, and compatible metadata required for validation. Publish MUST fail if the manifest is missing or invalid.

#### Scenario: Publish without manifest fails

- GIVEN a pack archive without `agh.pack.toml`
- WHEN publish is attempted
- THEN the operation is rejected

### Requirement: Instruction sources

A published pack MUST include at least one instruction file: `instructions/AGENTS.md` and/or `instructions/CLAUDE.md`. The system MUST NOT synthesize or fall back to `default.md`.

#### Scenario: AGENTS-only pack valid

- GIVEN `instructions/AGENTS.md` exists and `CLAUDE.md` does not
- WHEN publish validates
- THEN publish succeeds

#### Scenario: default.md not used

- GIVEN a pack with only `instructions/default.md`
- WHEN publish validates
- THEN publish is rejected

### Requirement: Optional skills layout

A pack MAY include skills at `skills/<skill-name>/SKILL.md`. Each skill directory MUST contain `SKILL.md` when the skill is declared.

#### Scenario: Skill published

- GIVEN `skills/lint/SKILL.md` is present
- WHEN the pack is published
- THEN the skill is stored and exposed in pull-manifest artifacts

### Requirement: Immutable SemVer publish

Publishing MUST require an exact SemVer version. Once version `X` of `<domain>/<name>` is published, the system MUST NOT allow republishing or overwriting version `X`. New content MUST use a higher version.

#### Scenario: First publish succeeds

- GIVEN no version `1.0.0` of `acme/onboarding`
- WHEN `acme/onboarding@1.0.0` is published
- THEN the version is stored immutably

#### Scenario: Republish same version rejected

- GIVEN `acme/onboarding@1.0.0` already exists
- WHEN publish is attempted again for `1.0.0`
- THEN the operation is rejected

#### Scenario: Cannot publish latest tag

- GIVEN a publish request targeting `acme/onboarding@latest`
- WHEN publish is attempted
- THEN the operation is rejected

### Requirement: Latest resolution for assignment only

Assignments and pull-manifest generation MAY reference `@latest`. Resolution MUST choose the highest published SemVer for that domain/name at request time.

#### Scenario: Latest picks highest SemVer

- GIVEN published versions `1.0.0` and `1.2.0`
- WHEN `acme/onboarding@latest` is resolved
- THEN the resolved version is `1.2.0`

### Requirement: Free-form domain namespace

Pack domains MUST NOT be centrally restricted to a fixed enum for MVP; publishers MAY use any valid domain slug subject to validation rules in design.

#### Scenario: Custom domain allowed

- GIVEN domain slug `my-team`
- WHEN a valid pack manifest uses `my-team/widget@2.0.0`
- THEN publish succeeds if other validation passes

### Requirement: Out of scope packs MVP

The system MUST NOT provide pack signing, publish approval workflows, offline-only publish, or public marketplace distribution in this change.

#### Scenario: No signing verification

- GIVEN MVP server
- WHEN a pack is published
- THEN integrity is not verified via cryptographic pack signing
