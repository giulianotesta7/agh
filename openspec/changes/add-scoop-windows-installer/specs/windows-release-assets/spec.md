# Windows Release Assets Specification

## Purpose

Provide complete, deterministic Windows release artifacts so Windows users and package managers can install the AGH CLI from GitHub Release assets.

## Requirements

### Requirement: Tag Releases Publish Windows Assets

The release system MUST produce and attach Windows GitHub Release assets for both `amd64` and `arm64` architectures during each supported tag release.

#### Scenario: Both Windows assets are published for a tag

- GIVEN a supported AGH version tag is released
- WHEN the release workflow publishes GitHub Release assets
- THEN the GitHub Release MUST include a Windows `amd64` asset
- AND the GitHub Release MUST include a Windows `arm64` asset

#### Scenario: Partial Windows architecture coverage is rejected

- GIVEN a supported AGH version tag is released
- WHEN only one Windows architecture asset is available
- THEN the release MUST NOT be treated as successfully published for Windows installation
- AND downstream Scoop update behavior MUST NOT proceed with an incomplete Windows asset set

### Requirement: Windows Asset Names Are Deterministic

Each Windows release asset MUST use a deterministic versioned name that uniquely identifies AGH, the released version, the Windows platform, and the architecture.

#### Scenario: Asset names are stable for package manifests

- GIVEN release version `1.2.3`
- WHEN Windows assets are attached to the GitHub Release
- THEN the `amd64` asset name MUST be `agh-1.2.3-windows-amd64.zip`
- AND the `arm64` asset name MUST be `agh-1.2.3-windows-arm64.zip`

### Requirement: Windows Archives Contain AGH Executable

Each Windows release archive MUST contain an executable named `agh.exe` at a stable archive path suitable for Scoop installation.

#### Scenario: Scoop can locate the executable in each archive

- GIVEN a Windows release archive for either supported architecture
- WHEN the archive contents are inspected
- THEN the archive MUST contain `agh.exe`
- AND the archive layout MUST be consistent across `amd64` and `arm64` assets for the same release

### Requirement: Windows Arm64 Support Is Mandatory

The project MUST block this installation channel if Windows `arm64` release assets cannot be produced with supported CI runners and tooling.

#### Scenario: Supported arm64 production is unavailable

- GIVEN the release process cannot produce a Windows `arm64` asset using supported CI runners and tooling
- WHEN the Scoop Windows installer change is evaluated for delivery
- THEN the change MUST remain blocked
- AND an `amd64`-only Windows installer path MUST NOT be shipped

## Acceptance Criteria

- A tag release publishes deterministic Windows `amd64` and `arm64` zip assets.
- Each Windows zip asset exposes `agh.exe` with the same archive layout.
- Windows installer delivery is blocked rather than downgraded when supported `arm64` production is unavailable.
