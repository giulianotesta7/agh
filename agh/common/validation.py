from __future__ import annotations

import re
from dataclasses import dataclass

from agh.common.ids import is_valid_prefixed_id

_SLUG_RE = re.compile(r"^[a-z0-9](?:[a-z0-9-]{0,61}[a-z0-9])?$")
_EMAIL_RE = re.compile(r"^[^\s@]+@[^\s@]+\.[^\s@]+$")
_SEMVER_RE = re.compile(r"^(0|[1-9]\d*)\.(0|[1-9]\d*)\.(0|[1-9]\d*)$")
_TAG_RE = re.compile(r"^[a-z0-9]+(?:-[a-z0-9]+)*$")


@dataclass(frozen=True)
class PackageRef:
    domain: str
    name: str
    version: str


@dataclass(frozen=True)
class PackageVersionRef:
    kind: str
    value: str
    domain: str | None = None
    name: str | None = None
    version: str | None = None


def is_valid_email(value: str) -> bool:
    return bool(_EMAIL_RE.fullmatch(value))


def is_valid_slug(value: str) -> bool:
    return value != "latest" and bool(_SLUG_RE.fullmatch(value))


def validate_slug(value: str, *, label: str = "slug") -> str:
    if not is_valid_slug(value):
        raise ValueError(f"invalid {label}: {value}")
    return value


def validate_project_name(value: str) -> str:
    cleaned = value.strip()
    if not cleaned:
        raise ValueError("project name is required")
    if cleaned.isdigit():
        raise ValueError("project name cannot contain only digits")
    return cleaned


def is_semver(value: str) -> bool:
    return bool(_SEMVER_RE.fullmatch(value))


def compare_semver(left: str, right: str) -> int:
    if not is_semver(left) or not is_semver(right):
        raise ValueError("compare_semver requires exact semver values")
    left_parts = tuple(int(piece) for piece in left.split("."))
    right_parts = tuple(int(piece) for piece in right.split("."))
    return (left_parts > right_parts) - (left_parts < right_parts)


def parse_package_ref(value: str, *, allow_latest: bool) -> PackageRef:
    if "@" not in value or "/" not in value:
        raise ValueError(f"invalid package ref: {value}")

    pair, version = value.rsplit("@", 1)
    domain, name = pair.split("/", 1)
    validate_slug(domain, label="domain")
    validate_slug(name, label="name")

    if version == "latest":
        if not allow_latest:
            raise ValueError("latest is not allowed here")
    elif not is_semver(version):
        raise ValueError(f"invalid package version: {version}")

    return PackageRef(domain=domain, name=name, version=version)


def parse_package_version_ref(value: str, *, allow_latest: bool) -> PackageVersionRef:
    if not value:
        raise ValueError("package version ref is required")

    if value.startswith("pkgv_"):
        if not is_valid_prefixed_id(value, "pkgv"):
            raise ValueError(f"invalid package version id: {value}")
        return PackageVersionRef(kind="id", value=value)

    if "@" not in value:
        raise ValueError(f"invalid package version ref: {value}")

    if "/" in value.rsplit("@", 1)[0]:
        package_ref = parse_package_ref(value, allow_latest=allow_latest)
        return PackageVersionRef(
            kind="canonical",
            value=value,
            domain=package_ref.domain,
            name=package_ref.name,
            version=package_ref.version,
        )

    name, version = value.rsplit("@", 1)
    validate_slug(name, label="name")
    if version == "latest":
        if not allow_latest:
            raise ValueError("latest is not allowed here")
    elif not is_semver(version):
        raise ValueError(f"invalid package version: {version}")

    return PackageVersionRef(
        kind="name_version",
        value=value,
        name=name,
        version=version,
    )


def validate_package_publish_ref(value: str) -> PackageRef:
    return parse_package_ref(value, allow_latest=False)


def is_valid_tag(value: str) -> bool:
    return bool(_TAG_RE.fullmatch(value))
