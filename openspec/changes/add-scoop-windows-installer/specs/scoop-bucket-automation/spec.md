# Scoop Bucket Automation Specification

## Purpose

Keep the public Scoop bucket manifest aligned with each AGH GitHub Release so Windows users can install the released CLI through Scoop.

## Requirements

### Requirement: Scoop Manifest PR Is Updated Per Release

For each supported AGH release, the release system MUST open or update a pull request in `giulianotesta7/scoop-agh` that changes `bucket/agh.json` for the released version.

#### Scenario: Bucket PR targets the released version

- GIVEN AGH version `1.2.3` has been published to GitHub Releases
- WHEN the Scoop bucket automation runs
- THEN a pull request MUST exist in `giulianotesta7/scoop-agh`
- AND the pull request MUST update `bucket/agh.json` for version `1.2.3`

### Requirement: Scoop Manifest Includes Both Architectures

The Scoop manifest update MUST include `64bit` and `arm64` entries that reference the GitHub Release assets and SHA256 hashes for the same AGH version.

#### Scenario: Manifest includes amd64 and arm64 metadata

- GIVEN release version `1.2.3` has Windows `amd64` and `arm64` GitHub Release assets
- WHEN `bucket/agh.json` is updated for that release
- THEN the `64bit` manifest entry MUST reference the `agh-1.2.3-windows-amd64.zip` GitHub Release asset URL
- AND the `64bit` manifest entry MUST include the SHA256 hash for that asset
- AND the `arm64` manifest entry MUST reference the `agh-1.2.3-windows-arm64.zip` GitHub Release asset URL
- AND the `arm64` manifest entry MUST include the SHA256 hash for that asset

### Requirement: Scoop Manifest Uses Published Release Assets

The Scoop manifest MUST consume AGH GitHub Release assets and MUST NOT reference PyPI artifacts or unpublished build outputs.

#### Scenario: Manifest URLs point to GitHub Releases

- GIVEN `bucket/agh.json` is updated for an AGH release
- WHEN a reviewer inspects the architecture URLs
- THEN each URL MUST point to a published AGH GitHub Release asset for the same version
- AND no URL MUST point to a PyPI package artifact

### Requirement: Scoop Update Requires Complete Metadata

The Scoop bucket automation MUST fail instead of opening or updating a manifest PR with missing version, URL, architecture, or SHA256 metadata.

#### Scenario: Missing hash blocks manifest update

- GIVEN the Windows `arm64` asset SHA256 hash is unavailable
- WHEN the Scoop bucket automation prepares `bucket/agh.json`
- THEN the automation MUST fail
- AND the bucket PR MUST NOT be updated with incomplete `arm64` metadata

## Acceptance Criteria

- `bucket/agh.json` PR updates include version, URL, and SHA256 metadata for `64bit` and `arm64`.
- Manifest URLs reference GitHub Release assets, not PyPI artifacts.
- Incomplete manifest metadata blocks the bucket update.
