# Tasks: Add Scoop Windows Installer

## Review Workload Forecast

| Field | Value |
|-------|-------|
| Estimated changed lines | 600-900 including workflow YAML, tests, bilingual docs, changelog, and `uv.lock` |
| 400-line budget risk | High |
| Chained PRs recommended | Yes |
| Suggested split | PR 1 Windows release assets + frozen version gate -> PR 2 Scoop bucket automation + docs/changelog |
| Delivery strategy | ask-on-risk |
| Chain strategy | pending |

Decision needed before apply: Yes
Chained PRs recommended: Yes
Chain strategy: pending
400-line budget risk: High

STRICT TDD MODE IS ACTIVE. Test runner: `uv run pytest`. Follow RED, GREEN, TRIANGULATE, REFACTOR. Record evidence for every RED failure, GREEN pass, CI feasibility run, and release-only manual verification.

### Suggested Work Units

| Unit | Start boundary | Finish boundary | Verification | Rollback boundary |
|------|----------------|-----------------|--------------|-------------------|
| PR 1 | `validate` release job is current baseline | `.github/workflows/release.yml` builds and attaches both Windows zips; CLI `--version` works in source/frozen mode; PyInstaller is locked | Focused pytest + `uv lock --locked` + PR CI proves `build-windows` `amd64` and `arm64` schedule and pass | Revert CLI version option, PyInstaller dependency/lock, Windows build job, release attachment, and tests |
| PR 2 | PR 1 merged or stacked and Windows ARM64 feasibility proven | `update-scoop` fails release on bucket errors; README/README.es document Scoop; changelog fragment exists | Focused pytest + `uv run towncrier check` + release workflow static assertions + first tag monitoring plan | Revert `update-scoop`, docs, changelog fragment, and related tests |

## PR 1: Windows Release Assets and Frozen Version Gate

### RED

- [x] 1.1 Add failing CLI version coverage in `tests/test_cli_version.py` asserting `CliRunner().invoke(cli_app, ["--version"])` exits 0 and prints exactly `agh <version>` using a monkeypatched/imported `agh.cli.main.__version__`.
- [x] 1.2 Add failing workflow/static assertions in `tests/test_release_workflow.py` for `.github/workflows/release.yml`: `build-windows` exists after `validate`, matrix includes `amd64` on `windows-2022`/`x64` and `arm64` on `windows-11-arm`/`arm64`, PyInstaller uses `--copy-metadata agh`, the frozen binary runs `agh.exe --version`, zip names are `agh-${VERSION}-windows-{amd64,arm64}.zip`, and zip validation checks root `agh.exe`.
- [x] 1.3 Add failing build-dependency assertions in `tests/test_release_workflow.py` or `tests/test_docs_guidance.py` that `pyproject.toml` has a non-runtime release/build dependency group containing PyInstaller and `uv.lock` records PyInstaller.

### GREEN

- [x] 1.4 Update `agh/cli/main.py` to expose a root `--version` option wired to `agh.__version__`; update `APP_HELP` if needed without regressing unknown-command/help behavior.
- [x] 1.5 Modify `agh/__init__.py` only if the RED/GREEN loop proves frozen metadata needs a safer fallback; keep `importlib.metadata.version("agh")` as the primary path and rely on PyInstaller `--copy-metadata agh` where possible.
- [x] 1.6 Add PyInstaller to a release/build dependency group in `pyproject.toml` and update `uv.lock`; do not add PyInstaller to `[project].dependencies`.
- [x] 1.7 Modify `.github/workflows/release.yml` to add `build-windows` after `validate` with native matrix legs for `amd64` and mandatory `arm64`, `SETUPTOOLS_SCM_PRETEND_VERSION_FOR_AGH`, `uv lock --locked`, source version check, PyInstaller one-file build, frozen `--version` check, deterministic zip creation, root `agh.exe` zip validation, and artifact upload.
- [x] 1.8 Update `.github/workflows/release.yml` so `publish-pypi` and `publish-ghcr` depend on `build-windows`, and `github-release` downloads both Windows artifacts, verifies both expected files, and attaches them with `softprops/action-gh-release@v2`.

### TRIANGULATE

- [x] 1.9 Extend workflow assertions to reject partial Windows delivery: no `amd64`-only path, `fail-fast: false` remains explicit, both release files are listed, and downstream jobs cannot skip missing `arm64` assets.
- [x] 1.10 Run and record focused evidence: `uv run pytest tests/test_cli_version.py tests/test_release_workflow.py -q` and `uv lock --locked`.
- [x] 1.11 Feasibility gate: PR #132 Release workflow proved both `build-windows (amd64)` and `build-windows (arm64)` scheduled and passed: <https://github.com/giulianotesta7/AgentGuidanceHub/actions/runs/28066756733>.

### REFACTOR

- [x] 1.12 Keep release YAML changes scoped to Windows artifacts and existing job dependency updates; avoid unrelated release refactors. If inline PowerShell grows hard to review, split only the smallest tested helper needed for the Windows build and keep validation with it.

## PR 2: Scoop Bucket Automation, Docs, and Changelog

### RED

- [x] 2.1 Add failing `tests/test_release_workflow.py` assertions that `.github/workflows/release.yml` contains `update-scoop`, depends on `github-release`, validates `SCOOP_BUCKET_TOKEN`, uses `giulianotesta7/scoop-agh`, edits only `bucket/agh.json`, hashes published GitHub Release assets, includes both `64bit` and `arm64`, uses branch `agh-${VERSION}`, and has no `continue-on-error`.
- [x] 2.2 Add failing docs assertions in `tests/test_docs_guidance.py` that `README.md` and `README.es.md` include equivalent Scoop commands: `scoop bucket add agh https://github.com/giulianotesta7/scoop-agh` and `scoop install agh`, while preserving the existing README H2 lists.
- [x] 2.3 Add failing changelog verification by planning `changelog.d/+scoop-windows-installer.added.md`; validate later with `uv run towncrier check` rather than editing `CHANGELOG.md`.

### GREEN

- [x] 2.4 Modify `.github/workflows/release.yml` to add release-failing `update-scoop` after `github-release`: validate token, verify/download published `v${VERSION}` Windows assets, compute SHA256, clone `giulianotesta7/scoop-agh`, update `bucket/agh.json` version/URLs/hashes/bin, validate complete GitHub Release-backed metadata, push `agh-${VERSION}`, and create or update the bucket PR.
- [x] 2.5 Preserve existing `update-homebrew`, PyPI, GHCR, and GitHub Release behavior while adding Scoop; do not change Homebrew's PyPI-based formula update flow.
- [x] 2.6 After PR 1 feasibility evidence is recorded, update `README.md` under existing `## Install` to document Scoop as the Windows install path without adding a new H2.
- [x] 2.7 Mirror the same user-facing Scoop guidance in `README.es.md` under existing `## Instalar`, keeping command semantics identical.
- [x] 2.8 Create `changelog.d/+scoop-windows-installer.added.md` with one user-facing sentence announcing the new Scoop Windows installation channel.

### TRIANGULATE

- [x] 2.9 Extend static assertions for failure semantics and data source: `update-scoop` must use GitHub Release asset URLs, must not reference PyPI or workflow-only artifacts for the manifest, must fail on missing hashes/metadata, and must not run before `github-release`.
- [x] 2.10 Run and record focused evidence: `uv run pytest tests/test_release_workflow.py tests/test_docs_guidance.py -q`, `uv run towncrier check`, `git diff --check`, and `uv lock --locked`.
- [x] 2.11 Before final review, run broader validation when practical: `uv run pytest -q`, `uv run --with ruff ruff check .`, `uv run --with ruff ruff format --check .`, and `uv run --with pyright pyright agh tests`.

### REFACTOR

- [x] 2.12 Keep Scoop manifest mutation readable and reviewable in `.github/workflows/release.yml`; if the JSON edit/validation block becomes too large, extract a focused helper under `scripts/` with paired tests before continuing.
- [x] 2.13 Record first real tag-release monitoring steps in the PR notes: verify GitHub Release assets, `update-homebrew`, generated `giulianotesta7/scoop-agh` PR, and expected red release status if `update-scoop` fails after publication.
