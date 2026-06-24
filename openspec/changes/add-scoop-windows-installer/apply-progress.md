# Apply Progress: add-scoop-windows-installer

## PR 1: Windows Release Assets and Frozen Version Gate

Status: implemented; CI feasibility gate 1.11 passed in PR #132.

## TDD Cycle Evidence

| Task | Phase | Evidence key |
| --- | --- | --- |
| 1.1 | RED | CLI version test failed first. |
| 1.2 | RED | Release workflow assertions failed first. |
| 1.3 | RED | PyInstaller dependency assertions failed first. |
| 1.4 | GREEN | Added root `agh --version`; tests passed. |
| 1.5 | GREEN | Kept `agh.__version__`; used PyInstaller metadata copy. |
| 1.6 | GREEN | Added release dependency group and lockfile. |
| 1.7 | GREEN | Added Windows matrix, freeze, zip, and upload. |
| 1.8 | GREEN | Attached both Windows assets in GitHub Release. |
| 1.9 | TRIANGULATE | Asserted complete dual-architecture delivery. |
| 1.10 | TRIANGULATE | Focused tests and lockfile checks passed. |
| 1.11 | GATE | PR #132 proved amd64 and arm64 jobs pass. |
| 1.12 | REFACTOR | Scoped YAML to release assets and hardening. |
| 2.1 | RED | Added `update-scoop` workflow assertions. |
| 2.2 | RED | Added mirrored Scoop docs assertions. |
| 2.3 | RED | Added Scoop changelog expectation. |
| 2.4 | GREEN | Added release-failing `update-scoop`. |
| 2.5 | GREEN | Preserved existing release channels. |
| 2.6 | GREEN | Added English Scoop docs. |
| 2.7 | GREEN | Added Spanish Scoop docs. |
| 2.8 | GREEN | Added Scoop changelog fragment. |
| 2.9 | TRIANGULATE | Added URL, arch, hash, and retry assertions. |
| 2.10 | TRIANGULATE | Focused validation passed. |
| 2.11 | TRIANGULATE | Full pytest, Ruff, format, and Pyright passed. |
| 2.12 | REFACTOR | Extracted tested manifest helper. |
| 2.13 | REFACTOR | PR notes captured release monitoring. |

## Review Workload Exception

PR #132 exceeded the 400-line review budget by 40 changed lines because the
Windows asset slice had to keep release workflow hardening, PyInstaller
lockfile updates, root version validation, and tests together to prove the
mandatory amd64/arm64 CI gate. The excess was disclosed in review notes and
addressed through fresh 4R review. PR #135 stayed under budget at 396 changed
lines.

Evidence: <https://github.com/giulianotesta7/AgentGuidanceHub/pull/132>
and Release workflow run
<https://github.com/giulianotesta7/AgentGuidanceHub/actions/runs/28066756733>.

## PR 2: Scoop Bucket Automation, Docs, and Changelog

Status: implemented locally on stacked branch `ci/scoop-bucket-automation`;
fresh review and PR creation still pending.

### RED

- [x] 2.1 Added failing workflow assertions for `update-scoop`,
  `SCOOP_BUCKET_TOKEN`, `giulianotesta7/scoop-agh`, `bucket/agh.json`, both
  architectures, branch `agh-${VERSION}`, no `continue-on-error`, release asset
  URLs, and SHA256 hashing.
- [x] 2.2 Added docs assertions for equivalent Scoop commands in `README.md`
  and `README.es.md` while preserving README H2 structure.
- [x] 2.3 Added the planned Scoop changelog fragment.

### GREEN

- [x] 2.4 Added release-failing `update-scoop` after `github-release`,
  `publish-pypi`, and `publish-ghcr`. The job validates `SCOOP_BUCKET_TOKEN`,
  downloads published Windows assets, computes SHA256 hashes, clones
  `giulianotesta7/scoop-agh`, updates `bucket/agh.json`, pushes
  `agh-${VERSION}`, and creates or updates the bucket PR.
- [x] 2.5 Preserved Homebrew's PyPI-based formula flow and existing PyPI,
  GHCR, and GitHub Release behavior.
- [x] 2.6 Added Scoop guidance to `README.md` under the existing `## Install`.
- [x] 2.7 Mirrored Scoop guidance in `README.es.md` under the existing install
  section.
- [x] 2.8 Added `changelog.d/+scoop-windows-installer.added.md`.

### TRIANGULATE

- [x] 2.9 Added assertions and helper tests ensuring Scoop manifest URLs point
  to AGH GitHub Release assets, not PyPI, and that hashes are valid SHA256
  values.
- [x] 2.10 Ran focused validation.
- [x] 2.11 Ran broader local validation.

### REFACTOR

- [x] 2.12 Extracted manifest JSON mutation and validation to
  `scripts/update_scoop_manifest.py` with tests, keeping workflow shell readable.
- [x] 2.13 PR notes must include first tag-release monitoring steps: GitHub
  Release assets, `update-homebrew`, generated `scoop-agh` PR, and red release
  status if `update-scoop` fails after publication.

## Files Changed for PR 2

- `.github/workflows/release.yml` — adds `update-scoop` after public release
  channels and uses the tested manifest helper.
- `scripts/update_scoop_manifest.py` — updates and validates `bucket/agh.json`.
- `tests/test_update_scoop_manifest.py` — covers manifest updates, preservation
  of unrelated fields, PyPI URL rejection, and invalid hash rejection.
- `tests/test_release_workflow.py` — adds static workflow assertions for
  `update-scoop`.
- `tests/test_docs_guidance.py` — asserts Scoop docs in English and Spanish.
- `README.md` and `README.es.md` — document Scoop installation.
- `changelog.d/+scoop-windows-installer.added.md` — announces Scoop support.

## Validation Commands Run for PR 2

```bash
uv run pytest tests/test_update_scoop_manifest.py \
  tests/test_release_workflow.py tests/test_docs_guidance.py -q
# → 31 passed

uv run pytest -q
# → 500 passed, 1 skipped

uv run --with ruff ruff check .
# → passed

uv run --with ruff ruff format --check .
# → passed

uv run --with pyright pyright agh tests
# → 0 errors
```

## Residual Risks

- `SCOOP_BUCKET_TOKEN` must be configured with permissions to push branches and
  create/edit PRs in `giulianotesta7/scoop-agh` before a real tag release.
- The first real tag release should be monitored for generated GitHub Release
  assets, Homebrew PR, Scoop PR, and expected workflow failure visibility if
  `update-scoop` fails after publication.
- `bucket/agh.json` must exist in the bucket repo before the first automated
  update, as bucket bootstrap is intentionally outside the release workflow.
