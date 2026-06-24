## Exploration: add-scoop-windows-installer

### Current State

AGH already publishes three release outputs from
`.github/workflows/release.yml`: a PyPI package, a GHCR image, and a GitHub
Release entry. The workflow also has an `update-homebrew` job that derives
release metadata from the just-published PyPI sdist, updates
`giulianotesta7/homebrew-tap`, and opens or updates a PR with
`HOMEBREW_TAP_TOKEN`.

What is missing is a Windows-native install path. There is no Scoop bucket
automation, no Windows binary build job, and the GitHub Release job currently
creates release notes only; it does not attach Windows assets. README install
guidance currently mentions Homebrew, the install script, and `uv tool
install`, but not Scoop.

### Affected Areas

- `.github/workflows/release.yml` — extend the existing tag-release pipeline
  to build Windows binaries, attach them to the GitHub Release, and update the
  Scoop bucket PR.
- `pyproject.toml` / `uv.lock` — likely add PyInstaller as a release-time
  dependency or tool input if binaries are built from repo code in CI.
- `agh/__init__.py` — verify frozen-binary version behavior, because
  `importlib.metadata.version("agh")` may fall back to `0.0.0` inside a
  PyInstaller build if package metadata is not bundled.
- `tests/test_docs_guidance.py` — update static release-workflow assertions to
  cover the new Windows/Scoop release path.
- `README.md` / `README.es.md` — document Scoop as the Windows install path
  after implementation.
- `changelog.d/` — add a user-facing release/install fragment because this
  changes AGH distribution behavior.

### Approach Options

1. **Extend `release.yml` with Windows build + release asset + Scoop PR jobs**
   - Build Windows binaries in dedicated jobs before the GitHub Release
     publish step.
   - Upload build outputs as workflow artifacts.
   - Change the existing GitHub Release job to publish the release and attach
     the Windows assets.
   - Add a Scoop update job modeled after `update-homebrew`, but targeting
     `giulianotesta7/scoop-agh` and `bucket/agh.json`.
   - Pros: matches the requested scope, keeps release automation centralized,
     mirrors the existing Homebrew pattern.
   - Cons: `release.yml` grows further; more embedded scripting in workflow
     YAML.
   - Effort: Medium

2. **Add helper script/module(s) for manifest generation while keeping
orchestration in `release.yml`**
   - Keep one workflow file, but move manifest rewriting/hash logic into repo
     code for testability.
   - Pros: easier unit testing for bucket-manifest updates; less inline Python
     in YAML.
   - Cons: slightly wider implementation surface; may conflict with the
     preference to keep this close to the existing Homebrew automation style.
   - Effort: Medium

3. **Publish Scoop directly from PyPI or an install script**
   - Not recommended.
   - Pros: less binary-build work.
   - Cons: conflicts with the user requirement that Scoop install from GitHub
     Release binary assets, not PyPI.
   - Effort: Low, but out of scope.

### Recommendation

Use option 1: extend the existing `.github/workflows/release.yml` so the
release pipeline remains the single source of truth for AGH publishing. Mirror
the Homebrew automation structure, but source Scoop from versioned GitHub
Release assets instead of PyPI.

Recommended release shape:

- Add a Windows build matrix job that produces versioned assets for
  `windows-amd64` and `windows-arm64`.
- Prefer zipped release artifacts containing `agh.exe` so Scoop can install
  from stable archive URLs and future asset expansion stays possible.
- Make `github-release` depend on the Windows build job, download those
  artifacts, and attach them with `softprops/action-gh-release@v2` using
  `files:`.
- Add `update-scoop` after `github-release`, analogous to `update-homebrew`,
  to:
  - clone/tap `giulianotesta7/scoop-agh`,
  - update `bucket/agh.json`,
  - set version, URLs, and SHA256s for `64bit` and `arm64`,
  - commit on branch `agh-${VERSION}`,
  - push with a dedicated secret such as `SCOOP_BUCKET_TOKEN`,
  - open or update the PR in the bucket repo.

### Key Design Notes

- **Asset naming must be deterministic.** Scoop manifest URLs should point to
  stable release assets such as `agh-${VERSION}-windows-amd64.zip` and
  `agh-${VERSION}-windows-arm64.zip`.
- **Release ordering matters.** Scoop should update only after the GitHub
  Release exists and the Windows assets are attached.
- **Windows-arm64 feasibility must be confirmed in CI design.** If
  GitHub-hosted Windows ARM runners are unavailable or unsuitable, that
  becomes the main delivery risk because PyInstaller does not provide a
  trivial cross-compile substitute.
- **Frozen version metadata is a real risk.** AGH currently derives
  `__version__` from installed package metadata; PyInstaller builds may need
  explicit metadata collection or a version-file strategy.
- **Homebrew flow is the template, not the source artifact.** Homebrew stays
  PyPI-sdist-based; Scoop should be GitHub-Release-binary-based.

### Validation Forecast

Implementation should at minimum add:

- static workflow assertions in `tests/test_docs_guidance.py` for new release
  job strings,
- focused tests for any extracted manifest-update helper if the implementation
  chooses option 2,
- `uv run pytest tests/test_docs_guidance.py -q` during iteration,
- broader `uv run pytest -q` before PR because release workflow behavior is
  user-facing,
- `uv run towncrier check` because release/install behavior changes.

### Work-Unit Forecast

This likely fits in one reviewable PR if kept focused:

- `ci(release): add Windows release assets and Scoop bucket PR automation`
- plus the paired docs/tests/changelog updates in the same unit.

Expected review size risk is moderate but still likely within the 400-line
target if the implementation reuses the current Homebrew-job pattern and
avoids adding extra workflows.

### Risks

- Windows ARM64 runner availability may block native asset production.
- PyInstaller may need extra configuration for package metadata, console
  entrypoint behavior, or bundled resources.
- Scoop manifest schema/details (`bin`, `architecture`, hash fields) must
  exactly match the chosen archive layout.
- New secret management is required for the bucket PR flow.
- README install guidance must be mirrored in `README.es.md` when
  implementation lands.

### Ready for Proposal

Yes. The scope is clear enough to move to proposal/spec/design around one main
decision: the exact Windows build strategy and release asset layout to support
both amd64 and arm64 within the existing release workflow.
