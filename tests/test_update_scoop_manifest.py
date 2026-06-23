"""Tests for the Scoop manifest update helper."""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

HELPER = Path("scripts/update_scoop_manifest.py")
BASE = "https://github.com/giulianotesta7/AgentGuidanceHub/releases/download"


def _url(version: str, arch: str) -> str:
    return f"{BASE}/v{version}/agh-{version}-windows-{arch}.zip"


def _run(path: Path, **overrides: str) -> subprocess.CompletedProcess[str]:
    defaults = {
        "version": "1.2.3",
        "amd64_url": _url("1.2.3", "amd64"),
        "amd64_hash": "a" * 64,
        "arm64_url": _url("1.2.3", "arm64"),
        "arm64_hash": "b" * 64,
    } | overrides
    args = [sys.executable, str(HELPER), str(path)]
    for key, value in defaults.items():
        args.extend([f"--{key.replace('_', '-')}", value])
    return subprocess.run(args, capture_output=True, text=True)


def _write_manifest(path: Path) -> None:
    path.write_text(
        json.dumps(
            {
                "version": "0.0.0",
                "architecture": {},
                "bin": "agh.exe",
                "homepage": "https://example.com",
            }
        )
    )


def test_helper_updates_architectures_and_preserves_fields(tmp_path: Path) -> None:
    manifest = tmp_path / "agh.json"
    _write_manifest(manifest)

    result = _run(manifest)

    assert result.returncode == 0, result.stderr
    data = json.loads(manifest.read_text())
    assert data["version"] == "1.2.3"
    assert data["architecture"] == {
        "64bit": {"url": _url("1.2.3", "amd64"), "hash": "a" * 64},
        "arm64": {"url": _url("1.2.3", "arm64"), "hash": "b" * 64},
    }
    assert data["bin"] == "agh.exe"
    assert data["homepage"] == "https://example.com"


def test_helper_rejects_wrong_origin_version_arch_or_hash(tmp_path: Path) -> None:
    cases = [
        {"amd64_url": "https://pypi.org/project/agh/1.2.3/"},
        {"arm64_url": _url("1.2.4", "arm64")},
        {"amd64_url": _url("1.2.3", "arm64")},
        {"amd64_hash": "tooshort"},
        {"version": "1.2"},
    ]
    for overrides in cases:
        manifest = tmp_path / f"agh-{len(list(tmp_path.iterdir()))}.json"
        _write_manifest(manifest)
        result = _run(manifest, **overrides)
        assert result.returncode != 0
