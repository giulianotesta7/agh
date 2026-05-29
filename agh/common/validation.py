from __future__ import annotations

import re
from dataclasses import dataclass

_SLUG_RE = re.compile(r"^[a-z0-9](?:[a-z0-9-]{0,61}[a-z0-9])?$")
_EMAIL_RE = re.compile(r"^[^\s@]+@[^\s@]+\.[^\s@]+$")
_SEMVER_RE = re.compile(r"^(0|[1-9]\d*)\.(0|[1-9]\d*)\.(0|[1-9]\d*)$")
_TAG_RE = re.compile(r"^[a-z0-9]+(?:-[a-z0-9]+)*$")


@dataclass(frozen=True)
class PackRef:
    domain: str
    name: str
    version: str


def is_valid_email(value: str) -> bool:
    return bool(_EMAIL_RE.fullmatch(value))


def is_valid_slug(value: str) -> bool:
    return value != "latest" and bool(_SLUG_RE.fullmatch(value))


def validate_slug(value: str, *, label: str = "slug") -> str:
    if not is_valid_slug(value):
        raise ValueError(f"invalid {label}: {value}")
    return value


def is_semver(value: str) -> bool:
    return bool(_SEMVER_RE.fullmatch(value))


def compare_semver(left: str, right: str) -> int:
    if not is_semver(left) or not is_semver(right):
        raise ValueError("compare_semver requires exact semver values")
    left_parts = tuple(int(piece) for piece in left.split("."))
    right_parts = tuple(int(piece) for piece in right.split("."))
    return (left_parts > right_parts) - (left_parts < right_parts)


def parse_pack_ref(value: str, *, allow_latest: bool) -> PackRef:
    if "@" not in value or "/" not in value:
        raise ValueError(f"invalid pack ref: {value}")

    pair, version = value.rsplit("@", 1)
    domain, name = pair.split("/", 1)
    validate_slug(domain, label="domain")
    validate_slug(name, label="name")

    if version == "latest":
        if not allow_latest:
            raise ValueError("latest is not allowed here")
    elif not is_semver(version):
        raise ValueError(f"invalid pack version: {version}")

    return PackRef(domain=domain, name=name, version=version)


def validate_pack_publish_ref(value: str) -> PackRef:
    return parse_pack_ref(value, allow_latest=False)


def is_valid_tag(value: str) -> bool:
    return bool(_TAG_RE.fullmatch(value))
