from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
import tomllib

from agh.common.validation import is_semver, is_valid_slug, is_valid_tag


class PackageManifestError(ValueError):
    pass


@dataclass(frozen=True)
class PackageManifest:
    domain: str
    name: str
    version: str
    description: str
    tags: list[str]


def _as_non_empty_string(value: object, field: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise PackageManifestError(f"{field} is required")
    return value.strip()


def load_package_manifest(path: Path) -> PackageManifest:
    if not path.is_file():
        raise PackageManifestError("agh.package.toml is required")

    try:
        data = tomllib.loads(path.read_text(encoding="utf-8"))
    except tomllib.TOMLDecodeError as exc:
        raise PackageManifestError(f"invalid agh.package.toml: {exc}") from exc

    domain = _as_non_empty_string(data.get("domain"), "domain")
    name = _as_non_empty_string(data.get("name"), "name")
    version = _as_non_empty_string(data.get("version"), "version")
    description = _as_non_empty_string(data.get("description"), "description")

    if not is_valid_slug(domain):
        raise PackageManifestError(f"invalid domain: {domain}")
    if not is_valid_slug(name):
        raise PackageManifestError(f"invalid name: {name}")
    if not is_semver(version):
        raise PackageManifestError(f"invalid version: {version}")

    raw_tags = data.get("tags", [])
    if not isinstance(raw_tags, list):
        raise PackageManifestError("tags must be a list")

    tags: list[str] = []
    for tag in raw_tags:
        if not isinstance(tag, str) or not is_valid_tag(tag):
            raise PackageManifestError(f"invalid tag: {tag}")
        tags.append(tag)

    return PackageManifest(
        domain=domain,
        name=name,
        version=version,
        description=description,
        tags=tags,
    )
