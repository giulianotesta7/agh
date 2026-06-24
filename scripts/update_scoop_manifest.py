#!/usr/bin/env python3
"""Update a Scoop bucket manifest for an AGH release."""

from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path

VERSION = re.compile(r"^(0|[1-9]\d*)\.(0|[1-9]\d*)\.(0|[1-9]\d*)$")
HASH = re.compile(r"^[0-9a-f]{64}$")
URL = (
    "https://github.com/giulianotesta7/AgentGuidanceHub"
    "/releases/download/v{version}/agh-{version}-windows-{arch}.zip"
)


def _validate(version: str, arch: str, url: str, digest: str) -> None:
    expected = URL.format(version=version, arch=arch)
    if url != expected:
        sys.exit(f"{arch}: expected {expected}, got {url}")
    if not HASH.match(digest):
        sys.exit(f"{arch}: invalid SHA256 hash: {digest}")


def update_manifest(path: Path, args: argparse.Namespace) -> None:
    if not VERSION.match(args.version):
        sys.exit(f"version must be MAJOR.MINOR.PATCH SemVer, got: {args.version}")
    _validate(args.version, "amd64", args.amd64_url, args.amd64_hash)
    _validate(args.version, "arm64", args.arm64_url, args.arm64_hash)

    data = json.loads(path.read_text(encoding="utf-8"))
    data["version"] = args.version
    arch = data.setdefault("architecture", {})
    arch["64bit"] = {"url": args.amd64_url, "hash": args.amd64_hash}
    arch["arm64"] = {"url": args.arm64_url, "hash": args.arm64_hash}
    data.setdefault("bin", "agh.exe")
    path.write_text(json.dumps(data, indent=2) + "\n", encoding="utf-8")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("manifest")
    parser.add_argument("--version", required=True)
    parser.add_argument("--amd64-url", required=True)
    parser.add_argument("--amd64-hash", required=True)
    parser.add_argument("--arm64-url", required=True)
    parser.add_argument("--arm64-hash", required=True)
    args = parser.parse_args()
    update_manifest(Path(args.manifest), args)
    print(f"Updated {args.manifest} to version {args.version}")


if __name__ == "__main__":
    main()
