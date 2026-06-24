# Installation Docs Specification

## Purpose

Document Scoop as a supported Windows installation channel and ensure release notes communicate the new distribution path to users.

## Requirements

### Requirement: README Documents Scoop Installation

The user-facing installation guide MUST document Scoop as the supported Windows installation path for AGH.

#### Scenario: Windows user finds Scoop install guidance

- GIVEN a Windows user reads the AGH installation documentation
- WHEN they look for a Windows installation method
- THEN the documentation MUST show Scoop as a supported AGH install channel
- AND the documented command MUST install AGH from the public `giulianotesta7/scoop-agh` bucket

### Requirement: Spanish README Mirrors Scoop Guidance

The Spanish README mirror MUST include equivalent Scoop installation guidance whenever the English README documents the new Windows install channel.

#### Scenario: Spanish documentation stays aligned

- GIVEN the English README documents Scoop installation
- WHEN the Spanish README is reviewed
- THEN it MUST include equivalent Scoop installation guidance
- AND it MUST reference the same Scoop bucket and install command semantics

### Requirement: Documentation Matches Release Behavior

The installation documentation MUST describe only release behavior that is supported by the workflow, including both Windows architectures and GitHub Release-backed Scoop assets.

#### Scenario: Docs do not promise unsupported architecture coverage

- GIVEN Windows `arm64` asset production is not supported by the release workflow
- WHEN installation documentation is prepared
- THEN the documentation MUST NOT present Scoop as a supported install channel
- AND it MUST NOT imply an `amd64`-only Scoop channel is supported

### Requirement: Changelog Announces New Install Channel

The change MUST include a user-facing changelog fragment that announces Scoop-based Windows installation support.

#### Scenario: Release notes include Scoop support

- GIVEN the Scoop Windows installer change is included in a release
- WHEN changelog fragments are reviewed for the change
- THEN a fragment MUST describe the new Windows/Scoop installation channel in user-facing terms
- AND the fragment MUST NOT require readers to inspect implementation files to understand the release impact

## Acceptance Criteria

- English and Spanish README installation guidance both describe the Scoop channel.
- Documentation does not claim Scoop support unless both Windows architectures are supported by releases.
- A user-facing changelog fragment covers the new install channel.
