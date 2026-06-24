# Release Pipeline Specification

## Purpose

Ensure Windows asset publication and Scoop bucket updates are first-class parts of the existing tag-based AGH release flow without weakening existing release channels.

## Requirements

### Requirement: Windows Assets Are Attached Before Scoop Update

The release pipeline MUST attach the Windows `amd64` and `arm64` assets to the GitHub Release before any Scoop bucket update uses those assets.

#### Scenario: Scoop update sees published assets

- GIVEN a supported AGH version tag is being released
- WHEN the release pipeline reaches the Scoop bucket update
- THEN the GitHub Release MUST already contain the Windows `amd64` asset
- AND the GitHub Release MUST already contain the Windows `arm64` asset
- AND the Scoop bucket update MUST use the URLs for those published assets

### Requirement: Scoop Failure Fails The Release Workflow

If the Scoop bucket update fails after PyPI, GHCR, or GitHub Release publication, the release workflow MUST finish with a failed status and surface the Scoop failure as a release failure.

#### Scenario: Bucket PR creation fails after publication

- GIVEN PyPI, GHCR, and GitHub Release publication have completed for a tag
- WHEN the Scoop bucket update cannot create or update the bucket pull request
- THEN the release workflow MUST fail
- AND the failure MUST identify the Scoop bucket update as the failing release step

### Requirement: Existing Release Channels Remain Intact

The addition of Windows assets and Scoop automation MUST NOT remove or replace the existing PyPI, GHCR, GitHub Release, or Homebrew release behavior.

#### Scenario: Non-Windows release outputs are preserved

- GIVEN a supported AGH version tag is released
- WHEN the release workflow completes successfully
- THEN existing PyPI publication behavior MUST remain available
- AND existing GHCR publication behavior MUST remain available
- AND existing GitHub Release behavior MUST remain available
- AND existing Homebrew automation behavior MUST remain available

### Requirement: Unsupported Arm64 Blocks Release Delivery

The release pipeline MUST NOT proceed with a successful Windows installer delivery when Windows `arm64` cannot be produced with supported CI runners and tooling.

#### Scenario: Arm64 build support is unavailable

- GIVEN supported CI runners and tooling cannot produce the Windows `arm64` asset
- WHEN a tag release attempts to include the Scoop Windows installer channel
- THEN the release pipeline MUST fail or remain blocked before advertising Scoop availability
- AND the release MUST NOT publish an `amd64`-only Scoop installer path

## Acceptance Criteria

- Scoop automation runs only after both Windows assets are attached to the GitHub Release.
- A Scoop update failure after publication produces an overall failed release workflow status.
- Existing release channels continue to operate when the Windows/Scoop path succeeds.
