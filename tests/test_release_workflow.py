"""Static checks for Windows release assets in the release workflow."""

from __future__ import annotations

import re
from pathlib import Path


def _read(path: str) -> str:
    return Path(path).read_text(encoding="utf-8")


def _job(name: str) -> str:
    match = re.search(
        rf"^  {name}:\n.*?(?=^  [\w-]+:|\Z)",
        _read(".github/workflows/release.yml"),
        flags=re.MULTILINE | re.DOTALL,
    )
    assert match, f"missing job {name}"
    return match.group(0)


def test_release_workflow_runs_windows_builds_before_tag_publish() -> None:
    workflow = _read(".github/workflows/release.yml")
    build = _job("build-windows")
    for expected in [
        "pull_request:",
        '"v*"',
        "^permissions:\n  contents: read",
        "arch: amd64",
        "runner: windows-2022",
        "python-architecture: x64",
        "arch: arm64",
        "runner: windows-11-arm",
        "python-architecture: arm64",
        "enable-cache: false",
    ]:
        source = workflow if expected.startswith(("pull", '"', "^")) else build
        assert (
            re.search(expected, source, re.MULTILINE)
            if expected.startswith("^")
            else expected in source
        )


def test_release_workflow_hardens_release_actions() -> None:
    workflow = _read(".github/workflows/release.yml")
    assert not re.search(r"uses: [^\n]+@v\d", workflow)
    assert workflow.count("persist-credentials: false") == workflow.count(
        "actions/checkout@"
    )
    for job_name, permission in [
        ("build-windows", "contents: read"),
        ("publish-pypi", "id-token: write"),
        ("publish-ghcr", "packages: write"),
        ("github-release", "contents: write"),
    ]:
        assert permission in _job(job_name)


def test_build_windows_creates_and_validates_pyinstaller_zips() -> None:
    build = _job("build-windows")
    for expected in [
        "SETUPTOOLS_SCM_PRETEND_VERSION_FOR_AGH",
        "pyinstaller",
        "--copy-metadata agh",
        "& .\\dist\\agh.exe --version",
        "agh-$env:VERSION-windows-$env:ARCH.zip",
        'if ($entries -notcontains "agh.exe")',
        "if-no-files-found: error",
    ]:
        assert expected in build


def test_github_release_attaches_windows_assets_before_publish_jobs() -> None:
    release = _job("github-release")
    for expected in [
        "if: startsWith(github.ref, 'refs/tags/v')",
        "- build-windows",
        "VERSION: ${{ needs.validate.outputs.version }}",
        "actions/download-artifact@",
        "windows-assets/agh-${{ env.VERSION }}-windows-amd64.zip",
        "windows-assets/agh-${{ env.VERSION }}-windows-arm64.zip",
    ]:
        assert expected in release
    assert "- publish-pypi" not in release
    assert "- publish-ghcr" not in release
    for job_name in ("publish-pypi", "publish-ghcr"):
        job = _job(job_name)
        assert "- build-windows" in job
        assert "- github-release" in job


def test_pyinstaller_is_a_locked_release_dependency_only() -> None:
    pyproject = _read("pyproject.toml")
    deps = pyproject[pyproject.index("dependencies = [") :].split("]", 1)[0]
    assert "pyinstaller" not in deps.lower()
    assert "release" in pyproject and "pyinstaller" in pyproject.lower()
    assert "pyinstaller" in _read("uv.lock").lower()


# ---------------------------------------------------------------------------
# PR 2: update-scoop job
# ---------------------------------------------------------------------------


def test_scoop_preflight_runs_before_publication() -> None:
    preflight = _job("preflight-scoop")
    for expected in [
        "SCOOP_BUCKET_TOKEN",
        "test -n",
        "gh repo view giulianotesta7/scoop-agh",
        "contents/bucket/agh.json",
        "agh-preflight-${GITHUB_RUN_ID}",
        "git commit --allow-empty",
        "push --force-with-lease",
        "gh pr create",
        "--draft",
        "gh pr close",
        "--delete-branch",
    ]:
        assert expected in preflight
    for job_name in ("github-release", "publish-pypi", "publish-ghcr"):
        assert "- preflight-scoop" in _job(job_name)


def test_update_scoop_runs_after_publication_and_is_hard_failing() -> None:
    workflow = _read(".github/workflows/release.yml")
    scoop = _job("update-scoop")
    assert workflow.index("  update-scoop:") > workflow.index("  github-release:")
    for expected in [
        "- github-release",
        "- publish-pypi",
        "- publish-ghcr",
        "- preflight-scoop",
        "giulianotesta7/scoop-agh",
        "bucket/agh.json",
        "agh-${VERSION}",
        "::error::Merge ${pr_url}, then rerun update-scoop.",
        "exit 1",
    ]:
        assert expected in scoop
    assert "continue-on-error" not in scoop
    assert "SCOOP_BUCKET_TOKEN" not in _job("update-scoop").split("steps:", 1)[0]


def test_update_scoop_maps_architecture_urls_and_hashes_to_helper() -> None:
    scoop = _job("update-scoop")
    for expected in [
        'AMD64_URL="${base}/agh-${VERSION}-windows-amd64.zip"',
        'ARM64_URL="${base}/agh-${VERSION}-windows-arm64.zip"',
        'echo "AMD64_URL=$AMD64_URL" >> "$GITHUB_ENV"',
        'echo "ARM64_URL=$ARM64_URL" >> "$GITHUB_ENV"',
        '--amd64-url "${AMD64_URL}"',
        '--amd64-hash "${AMD64_HASH}"',
        '--arm64-url "${ARM64_URL}"',
        '--arm64-hash "${ARM64_HASH}"',
    ]:
        assert expected in scoop
    assert "pypi.org" not in scoop.lower()


def test_update_scoop_uses_retrying_downloads_and_tested_helper() -> None:
    scoop = _job("update-scoop")
    assert "curl --fail --location --retry 3 --connect-timeout 10" in scoop
    assert "--max-time 120" in scoop
    assert "sha256sum" in scoop
    assert "scripts/update_scoop_manifest.py" in scoop
