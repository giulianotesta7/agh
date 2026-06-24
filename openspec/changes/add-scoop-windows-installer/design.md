# Design: Add Scoop Windows Installer

## Technical Approach

Extend the existing tag-triggered `.github/workflows/release.yml` rather than adding a second release workflow. The release pipeline will first validate the tag, then build native PyInstaller Windows binaries for both supported Windows architectures, then publish the existing PyPI/GHCR channels, then create the GitHub Release with the Windows zip assets attached, and finally open or update a Scoop bucket PR that points at those published GitHub Release assets.

The implementation must treat Windows `amd64` and `arm64` as an all-or-nothing release requirement. PyInstaller does not provide a supported cross-compilation path for Windows binaries, so each artifact is built on a native Windows runner/Python architecture. If the native `arm64` runner, Python distribution, PyInstaller support, or dependency set cannot produce a working `agh.exe`, the change remains blocked and Scoop docs must not be shipped.

## Architecture Decisions

| Concern | Options / tradeoff | Decision |
|---|---|---|
| Release workflow shape | Let PyPI/GHCR publish in parallel with Windows builds, or require Windows assets before any publication. | Add a `build-windows` matrix job immediately after `validate` and make `publish-pypi` and `publish-ghcr` depend on it. This blocks publication before any channel is released if mandatory Windows binaries cannot be produced. |
| Windows `arm64` build | Cross-compile from x64 Windows, emulate on Linux, or use native hosted Windows ARM64. | Use a native Windows ARM64 runner label such as `windows-11-arm` with `actions/setup-python` `architecture: arm64`. If the label/toolchain is unavailable for this repo, delivery is blocked. |
| PyInstaller dependency | Fetch PyInstaller ad hoc in the workflow, or add a locked build-time dependency. | Add PyInstaller to a release/build dependency group in `pyproject.toml` and commit `uv.lock` changes so release builds are reproducible enough for CI review. It must not become a runtime dependency of `agh`. |
| Frozen version metadata | Trust importlib metadata, inspect archive contents, or expose a runtime version check. | Preserve package metadata with `pyinstaller --copy-metadata agh` and add/verify a root `agh --version` CLI option if no equivalent exists. The workflow must execute the frozen binary and assert it reports `${VERSION}`. |
| Archive layout | Put files under a versioned folder, or put the executable at zip root. | Put `agh.exe` at the archive root for both architectures. Scoop manifest `bin` can then remain the stable string `agh.exe`. |
| Scoop manifest data source | Reuse workflow build artifacts, PyPI artifacts, or published GitHub Release assets. | The Scoop job reads/downloads the GitHub Release assets after `github-release` completes and hashes those published assets. It must not reference PyPI or unpublished workflow artifacts. |
| Scoop failure semantics | Best-effort post-release automation, or release-failing post-publication step. | No `continue-on-error`; any clone, hash, manifest, push, or PR failure in `update-scoop` fails the overall release workflow after publication. |

## GitHub Actions Job Structure

The release workflow keeps the current tag trigger and top-level permissions, then uses this job graph:

```text
validate
  -> build-windows (matrix: amd64, arm64)
       -> publish-pypi
       -> publish-ghcr
            -> github-release (attaches Windows assets)
                 -> update-homebrew
                 -> update-scoop
```

Exact intended `.github/workflows/release.yml` structure:

```yaml
jobs:
  validate:
    # existing job; keep outputs.version

  build-windows:
    name: Build Windows (${{ matrix.arch }})
    runs-on: ${{ matrix.runner }}
    needs: validate
    strategy:
      fail-fast: false
      matrix:
        include:
          - arch: amd64
            runner: windows-2022
            python-architecture: x64
          - arch: arm64
            runner: windows-11-arm
            python-architecture: arm64
    env:
      VERSION: ${{ needs.validate.outputs.version }}
      ARCH: ${{ matrix.arch }}
      SETUPTOOLS_SCM_PRETEND_VERSION_FOR_AGH: ${{ needs.validate.outputs.version }}
    steps:
      - uses: actions/checkout@v4
        with:
          fetch-depth: 0
      - uses: astral-sh/setup-uv@v5
        with:
          enable-cache: true
      - uses: actions/setup-python@v5
        with:
          python-version: "3.11"
          architecture: ${{ matrix.python-architecture }}
      - name: Check lockfile
        run: uv lock --locked
      - name: Build frozen CLI
        shell: pwsh
        run: |
          uv run --locked --group release pyinstaller `
            --clean `
            --noconfirm `
            --onefile `
            --name agh `
            --copy-metadata agh `
            agh/cli/main.py
      - name: Validate frozen CLI version
        shell: pwsh
        run: |
          $actual = (& .\dist\agh.exe --version).Trim()
          if ($actual -ne "agh $env:VERSION") {
            throw "Expected frozen version 'agh $env:VERSION', got '$actual'"
          }
      - name: Create deterministic zip
        shell: pwsh
        run: |
          $asset = "agh-$env:VERSION-windows-$env:ARCH.zip"
          New-Item -ItemType Directory -Force -Path release-root | Out-Null
          Copy-Item .\dist\agh.exe .\release-root\agh.exe
          Push-Location release-root
          Compress-Archive -Path agh.exe -DestinationPath "..\$asset" -Force
          Pop-Location
          New-Item -ItemType Directory -Force -Path release | Out-Null
          Move-Item $asset "release\$asset"
      - name: Validate zip layout
        shell: pwsh
        run: |
          $asset = "release\agh-$env:VERSION-windows-$env:ARCH.zip"
          Add-Type -AssemblyName System.IO.Compression.FileSystem
          $zip = [System.IO.Compression.ZipFile]::OpenRead($asset)
          try {
            $entries = @($zip.Entries | ForEach-Object { $_.FullName })
            if ($entries -notcontains "agh.exe") { throw "Archive is missing root agh.exe" }
          } finally {
            $zip.Dispose()
          }
      - uses: actions/upload-artifact@v4
        with:
          name: windows-${{ matrix.arch }}-asset
          path: release/agh-${{ needs.validate.outputs.version }}-windows-${{ matrix.arch }}.zip
          if-no-files-found: error

  publish-pypi:
    needs:
      - validate
      - build-windows
    # existing PyPI steps unchanged after needs update

  publish-ghcr:
    needs:
      - validate
      - build-windows
    # existing GHCR steps unchanged after needs update

  github-release:
    needs:
      - validate
      - build-windows
      - publish-pypi
      - publish-ghcr
    steps:
      - uses: actions/download-artifact@v4
        with:
          pattern: windows-*-asset
          path: windows-assets
          merge-multiple: true
      - name: Verify Windows release assets
        env:
          VERSION: ${{ needs.validate.outputs.version }}
        run: |
          test -f "windows-assets/agh-${VERSION}-windows-amd64.zip"
          test -f "windows-assets/agh-${VERSION}-windows-arm64.zip"
      - name: Create GitHub Release
        uses: softprops/action-gh-release@v2
        with:
          generate_release_notes: true
          files: |
            windows-assets/agh-${{ needs.validate.outputs.version }}-windows-amd64.zip
            windows-assets/agh-${{ needs.validate.outputs.version }}-windows-arm64.zip

  update-homebrew:
    needs:
      - validate
      - publish-pypi
      - publish-ghcr
      - github-release
    # existing Homebrew behavior unchanged

  update-scoop:
    name: Update Scoop bucket
    runs-on: ubuntu-latest
    permissions:
      contents: read
    needs:
      - validate
      - github-release
    env:
      VERSION: ${{ needs.validate.outputs.version }}
      GH_TOKEN: ${{ secrets.SCOOP_BUCKET_TOKEN }}
      SCOOP_BUCKET_TOKEN: ${{ secrets.SCOOP_BUCKET_TOKEN }}
    steps:
      - name: Validate Scoop token is configured
        run: test -n "$SCOOP_BUCKET_TOKEN"
      - name: Update Scoop manifest pull request
        run: |
          # Download/verify GitHub Release assets, hash them, clone the bucket,
          # edit bucket/agh.json, push branch agh-${VERSION}, and create/update PR.
```

`update-scoop` intentionally depends on `github-release`, not only on `build-windows`, so the Scoop manifest cannot point at assets until they have been attached to the public GitHub Release.

## Windows Binary Build and Validation

Build requirements:

- Use `windows-2022` + Python `x64` for `amd64`.
- Use a native Windows ARM64 hosted runner, expected label `windows-11-arm`, + Python `arm64` for `arm64`.
- Do not attempt Linux/macOS cross-compilation or Windows x64-to-arm64 cross-compilation with PyInstaller.
- Pin/add PyInstaller as a release/build dependency and keep it out of AGH runtime dependencies.
- Preserve package metadata with `--copy-metadata agh` so `importlib.metadata.version("agh")` works in frozen mode.
- Set `SETUPTOOLS_SCM_PRETEND_VERSION_FOR_AGH=${VERSION}` in the build job to make dynamic version resolution explicit and consistent with the Docker release build pattern.

Validation in each matrix leg:

1. `uv lock --locked` verifies the committed build dependency lock.
2. A source-tree metadata check should assert `agh.__version__ == VERSION` before freezing.
3. PyInstaller builds a one-file `dist/agh.exe`.
4. The frozen executable is run on the native runner: `dist\agh.exe --version` must print exactly `agh ${VERSION}`.
5. The executable is copied into a clean archive root and zipped.
6. The zip is inspected to ensure the entry `agh.exe` exists at the archive root.

Feasibility gate:

- Before implementation is considered deliverable, a PR run must demonstrate both matrix legs can schedule and pass.
- If `windows-11-arm` is unavailable, `actions/setup-python` lacks the requested ARM64 Python, PyInstaller does not support the target, or an AGH dependency blocks freezing on ARM64, the implementation must stop as blocked. Do not merge Scoop README guidance or an `amd64`-only manifest path.

## Asset Naming and Archive Layout

For release version `1.2.3`, the only Windows assets attached to the GitHub Release are:

```text
agh-1.2.3-windows-amd64.zip
agh-1.2.3-windows-arm64.zip
```

Each zip contains this stable layout:

```text
agh.exe
```

There is no versioned directory inside the archive. Scoop can therefore use:

```json
"bin": "agh.exe"
```

Published asset URLs are deterministic:

```text
https://github.com/giulianotesta7/AgentGuidanceHub/releases/download/v${VERSION}/agh-${VERSION}-windows-amd64.zip
https://github.com/giulianotesta7/AgentGuidanceHub/releases/download/v${VERSION}/agh-${VERSION}-windows-arm64.zip
```

## Scoop Bucket Update Flow

`update-scoop` runs after `github-release` and performs these steps in one failing shell script or a small inline Python-assisted script:

1. Validate `SCOOP_BUCKET_TOKEN` is non-empty.
2. Verify the GitHub Release `v${VERSION}` contains both deterministic Windows assets.
3. Download the published assets from the GitHub Release, not from workflow artifacts.
4. Compute SHA256 for both downloaded zips.
5. Clone `giulianotesta7/scoop-agh` with the token:
   `https://x-access-token:${SCOOP_BUCKET_TOKEN}@github.com/giulianotesta7/scoop-agh.git`.
6. Create/reset branch `agh-${VERSION}` from `origin/main`.
7. Edit `bucket/agh.json` only; bootstrap or create-missing-manifest behavior is out of scope.
8. Update these manifest fields while preserving unrelated manifest metadata:
   - `version`: `${VERSION}`
   - `architecture.64bit.url`: GitHub Release `amd64` asset URL
   - `architecture.64bit.hash`: SHA256 of published `amd64` zip
   - `architecture.arm64.url`: GitHub Release `arm64` asset URL
   - `architecture.arm64.hash`: SHA256 of published `arm64` zip
   - `bin`: `agh.exe` if the bucket manifest does not already have that stable value
9. Validate the resulting JSON contains complete version, URL, hash, architecture, and bin metadata; fail if any URL is missing, any hash is missing/non-hex, any URL points outside the AGH GitHub Release, or any URL points at PyPI.
10. If `bucket/agh.json` is already up to date on `origin/main`, exit successfully and print that no PR is required. Otherwise commit `bucket/agh.json` with message `agh ${VERSION}`.
11. Push with `--force-with-lease` to branch `agh-${VERSION}` in `giulianotesta7/scoop-agh`.
12. Create or update a PR in `giulianotesta7/scoop-agh`:
    - base: `main`
    - head: `agh-${VERSION}`
    - title: `agh ${VERSION}`
    - body: include the source release URL and both asset URLs/hashes.

Token and permission expectations:

- Secret name: `SCOOP_BUCKET_TOKEN`.
- The token must be usable by `git push` and `gh pr create/edit` against `giulianotesta7/scoop-agh`.
- A fine-grained PAT should have at least metadata read plus contents read/write and pull requests read/write for `giulianotesta7/scoop-agh`.
- The workflow job can keep GitHub Actions job permissions at `contents: read` because cross-repository writes are performed with `SCOOP_BUCKET_TOKEN`, not `GITHUB_TOKEN`.

Failure semantics:

- No `continue-on-error` on `update-scoop` or its steps.
- Missing token, missing release asset, failed download, missing hash, invalid manifest JSON, failed push, or failed PR create/update all fail the `update-scoop` job.
- Because `update-scoop` runs after `github-release`, these failures leave PyPI/GHCR/GitHub Release publication completed but the overall release workflow red, making stale Scoop automation visible.

## Data Flow

```text
vX.Y.Z tag
  -> validate derives VERSION=X.Y.Z
  -> build-windows native matrix
       -> agh-X.Y.Z-windows-amd64.zip (root agh.exe)
       -> agh-X.Y.Z-windows-arm64.zip (root agh.exe)
  -> github-release downloads workflow artifacts and attaches both zips
  -> update-scoop downloads published release zips and computes hashes
  -> bucket/agh.json branch agh-X.Y.Z
  -> PR in giulianotesta7/scoop-agh
```

## File Changes

| File | Action | Description |
|---|---|---|
| `.github/workflows/release.yml` | Modify | Add `build-windows` matrix, make publication depend on it, attach Windows zips in `github-release`, and add release-failing `update-scoop`. |
| `pyproject.toml` | Modify | Add locked release/build dependency group for PyInstaller if needed. |
| `uv.lock` | Modify | Lock PyInstaller and transitive build dependencies. |
| `agh/__init__.py` | Modify only if needed | Keep dynamic version metadata compatible with frozen execution; current importlib metadata path should work when PyInstaller copies metadata. |
| `agh/cli/main.py` | Modify | Add a root `--version` option if no existing runtime version command is available, so frozen binaries can prove embedded version metadata. |
| `tests/` | Modify | Add/update focused tests for CLI version behavior and release workflow/docs assertions. |
| `README.md` | Modify | Document Scoop installation under existing `## Install` without adding a new README H2. |
| `README.es.md` | Modify | Mirror the Scoop install guidance in Spanish with the same command semantics. |
| `changelog.d/+scoop-windows-installer.added.md` | Create | Announce the new Scoop Windows installation channel in user-facing terms. |

## Interfaces / Contracts

### GitHub Release assets

- `agh-${VERSION}-windows-amd64.zip`
- `agh-${VERSION}-windows-arm64.zip`
- Each asset contains `agh.exe` at zip root.
- Frozen `agh.exe --version` prints `agh ${VERSION}`.

### Scoop manifest contract

`bucket/agh.json` in `giulianotesta7/scoop-agh` must contain at least:

```json
{
  "version": "${VERSION}",
  "architecture": {
    "64bit": {
      "url": "https://github.com/giulianotesta7/AgentGuidanceHub/releases/download/v${VERSION}/agh-${VERSION}-windows-amd64.zip",
      "hash": "<sha256>"
    },
    "arm64": {
      "url": "https://github.com/giulianotesta7/AgentGuidanceHub/releases/download/v${VERSION}/agh-${VERSION}-windows-arm64.zip",
      "hash": "<sha256>"
    }
  },
  "bin": "agh.exe"
}
```

### User documentation contract

Document commands equivalent to:

```powershell
scoop bucket add agh https://github.com/giulianotesta7/scoop-agh
scoop install agh
```

Do not document Scoop support unless both Windows assets are produced by the release workflow.

## Testing Strategy

Strict TDD applies for implementation: add failing tests/assertions before changing workflow/docs/runtime behavior.

| Layer | What to Test | Approach |
|---|---|---|
| CLI version metadata | `agh --version` reports `agh <version>` through `agh.__version__`. | Add a focused Typer `CliRunner` test with monkeypatched `agh.cli.main.__version__` or equivalent. |
| Release workflow structure | Windows build matrix, native runner labels, PyInstaller invocation, deterministic asset names, `github-release` file attachment, and `update-scoop` dependency on `github-release`. | Extend `tests/test_docs_guidance.py` or create a workflow-focused test that reads `.github/workflows/release.yml` as text. |
| Scoop automation contract | Bucket repo, `bucket/agh.json`, `SCOOP_BUCKET_TOKEN`, branch `agh-${VERSION}`, asset URLs, SHA256 validation, and PR create/update commands are present. | Workflow text assertions plus any extracted manifest-update helper tests if implementation moves JSON editing into a script. |
| Docs alignment | README/README.es install guidance contains the Scoop bucket add/install commands and README H2 lists remain unchanged. | Extend existing docs guidance tests. |
| Changelog | User-facing fragment exists with an `added` type. | `uv run towncrier check`. |
| Frozen binary runtime | Built `agh.exe --version` equals `${VERSION}` for both architectures; zip has root `agh.exe`. | Enforced inside the release workflow matrix. |

Recommended validation commands for the implementation PR:

```bash
uv run pytest tests/test_docs_guidance.py -q
uv run pytest <focused-cli-version-test> -q
uv run towncrier check
git diff --check
uv lock --locked
uv run pytest -q
uv run --with ruff ruff check .
uv run --with ruff ruff format --check .
uv run --with pyright pyright agh tests
```

Release-only validation that cannot be fully proven locally:

- A GitHub Actions PR run must show both `build-windows (amd64)` and `build-windows (arm64)` matrix legs scheduling and passing.
- The first real tag release should be monitored through `github-release`, `update-homebrew`, and `update-scoop`; if `update-scoop` fails, the failure is expected to mark the workflow red after publication.

## Migration / Rollout

1. Confirm the public Scoop bucket repo already exists and contains `bucket/agh.json`.
2. Add `SCOOP_BUCKET_TOKEN` to the AGH repository secrets before merging or before the first tag using this workflow.
3. Merge the workflow/runtime/docs/tests/changelog change only after the Windows ARM64 matrix is proven feasible.
4. On the first tagged release, verify both release assets are attached before the Scoop PR is created.
5. Review and merge the generated `giulianotesta7/scoop-agh` PR.

Rollback is a normal revert of the workflow, build dependency, CLI version hook if added, docs, tests, and changelog fragment. Existing PyPI, GHCR, GitHub Release notes, and Homebrew behavior should return to the current state.

## Tradeoffs and Review-Size Risks

- Coupling PyPI/GHCR publication to Windows binary success makes the release more conservative. This is intentional because the product decision requires complete Windows architecture coverage and rejects an `amd64`-only installer path.
- The release YAML will grow substantially. Keep scripts inline only while they remain readable; if JSON editing becomes large, move it to a small tested script in the same work unit.
- Expected implementation size is near the 400 changed-line review budget because it touches workflow, lockfile, tests, bilingual docs, CLI metadata, and changelog. If the diff forecast exceeds the budget, split into two chained PRs:
  1. `ci: build Windows release assets` — PyInstaller dependency, CLI version validation, `build-windows`, GitHub Release attachment, tests.
  2. `ci: update Scoop bucket for releases` — `update-scoop`, README/README.es Scoop docs, changelog, workflow/docs tests.
  The second PR must not ship user docs until the first PR proves both architectures.
- Lockfile changes for PyInstaller may dominate diff size; call that out in PR review notes rather than splitting the lockfile away from the workflow that needs it.

## Open Questions

None for design. The only delivery gate is empirical: the Windows ARM64 hosted runner/toolchain must successfully build and run the frozen binary in CI before the Scoop install channel is advertised.
