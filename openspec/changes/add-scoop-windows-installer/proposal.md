# Proposal: Add Scoop Windows Installer

## Intent

Add a supported Windows installation channel for AGH by publishing Windows release binaries, attaching them to GitHub Releases, and automatically updating the public Scoop bucket so Windows users can install AGH through Scoop without manual per-release steps.

## Scope

### In Scope

- Build Windows release artifacts for both `amd64` and `arm64` during the existing tag-based release workflow.
- Attach deterministic Windows assets to the GitHub Release for each version.
- Update the public Scoop bucket repo `giulianotesta7/scoop-agh` after release publication.
- Make the release fail if Scoop bucket update automation fails after PyPI/GHCR/GitHub Release publication.
- Treat support for both Windows architectures as mandatory for this change; if `arm64` cannot be produced with available CI/runners, the feature remains blocked.
- Add the paired docs/test/changelog updates required for the new distribution path.

### Out of Scope

- One-time bootstrap of the Scoop bucket repository or initial repo creation.
- Shipping an `amd64`-only Windows channel.
- Replacing the existing PyPI, GHCR, or Homebrew release paths.
- Introducing a separate release workflow outside `.github/workflows/release.yml`.

## Product Decisions Confirmed

- Scoop bucket update failure is release-failing, not best-effort.
- Windows `amd64` and `arm64` are both required.
- Bucket bootstrap is manual and already completed at `https://github.com/giulianotesta7/scoop-agh`.
- Scoop must consume GitHub Release assets, not PyPI artifacts.

## Capabilities

### New Capabilities

- `windows-release-assets`: Publish versioned Windows binaries for `amd64` and `arm64` as GitHub Release assets.
- `scoop-bucket-automation`: Update `bucket/agh.json` in the public Scoop bucket repo for each release.

### Modified Capabilities

- `release-pipeline`: Extend the existing release workflow so Windows asset publication and Scoop bucket updates are first-class release steps.
- `installation-docs`: Add Scoop as the documented Windows installation path.

## Approach

Extend the current release workflow with native Windows build jobs for both architectures, publish deterministic archive assets such as `agh-${VERSION}-windows-amd64.zip` and `agh-${VERSION}-windows-arm64.zip`, then update the `github-release` job to attach those assets. After the GitHub Release is published, run a Scoop update job modeled on the existing Homebrew automation to update `bucket/agh.json` in `giulianotesta7/scoop-agh`, push branch `agh-${VERSION}`, and open or update the bucket PR.

The proposal assumes native builds are required for both architectures. If GitHub Actions cannot reliably produce `windows-arm64` artifacts with supported runners/tooling, implementation should stop and report the blocker rather than silently downgrading scope.

## Affected Areas

| Area | Impact | Description |
|------|--------|-------------|
| `.github/workflows/release.yml` | Modified | Add Windows build, release-asset attachment, and Scoop bucket update jobs with release-failing semantics. |
| `agh/__init__.py` | Modified | Ensure packaged Windows binaries report the correct AGH version when frozen. |
| `pyproject.toml`, `uv.lock` | Modified | Add or configure build-time tooling needed for Windows binary packaging if required. |
| `tests/test_docs_guidance.py` | Modified | Cover release workflow/docs assertions for Windows assets and Scoop automation. |
| `README.md`, `README.es.md` | Modified | Document Scoop installation and keep bilingual user docs aligned. |
| `changelog.d/` | Modified | Add a user-facing fragment for the new Windows install/release behavior. |

## Risks

| Risk | Likelihood | Mitigation |
|------|------------|------------|
| Windows `arm64` runner/tooling support is unavailable. | Med | Validate feasibility first; block the feature rather than shipping partial architecture coverage. |
| Frozen binaries report the wrong version. | Med | Explicitly validate packaged version metadata during implementation. |
| Scoop manifest fields or archive layout do not match asset contents. | Med | Use deterministic asset names/layout and test manifest generation/update logic. |
| Release drift occurs between GitHub Release assets and the Scoop bucket. | Low | Make Scoop update failure release-failing after publication. |
| Release workflow YAML grows beyond an easy review slice. | Med | Keep implementation in one focused release/distribution work unit and avoid unrelated workflow refactors. |

## Rollback Plan

Revert the Windows build jobs, GitHub Release asset attachment changes, Scoop bucket automation, and paired docs/tests/changelog updates. Existing PyPI, GHCR, GitHub Release notes, and Homebrew behavior should continue unchanged.

## Dependencies

- Existing tag-based release pipeline in `.github/workflows/release.yml`.
- Access to a token/secret for writing to `giulianotesta7/scoop-agh`.
- CI support sufficient to build both Windows `amd64` and `arm64` artifacts.
- The already-created public bucket repo `giulianotesta7/scoop-agh`.

## Success Criteria

- [ ] A tagged release produces Windows GitHub Release assets for both `amd64` and `arm64`.
- [ ] Asset names and URLs are deterministic and suitable for Scoop manifest references.
- [ ] The release workflow updates `bucket/agh.json` in `giulianotesta7/scoop-agh` with version, URLs, and hashes for both architectures.
- [ ] If the Scoop update step fails after publication, the release workflow fails instead of leaving Windows distribution silently stale.
- [ ] If `windows-arm64` cannot be built with supported CI/runners, implementation stops as blocked rather than shipping `amd64` only.
- [ ] README install guidance adds Scoop and is mirrored in `README.es.md`.
- [ ] The change includes the required tests and changelog coverage for the new distribution path.
