from __future__ import annotations

from collections.abc import Callable
from typing import Any
from urllib.parse import quote

from agh.common.validation import parse_package_ref, parse_package_version_ref


class PackageVersionRefResolutionError(ValueError):
    def __init__(self, message: str, *, code: int = 1) -> None:
        super().__init__(message)
        self.code = code


ApiRequest = Callable[..., Any]


def resolve_package_version_ref(package_ref: str, api_request: ApiRequest) -> str:
    try:
        parse_package_ref(package_ref, allow_latest=True)
        return package_ref
    except ValueError:
        pass

    try:
        parsed = parse_package_version_ref(package_ref, allow_latest=False)
    except ValueError as exc:
        raise PackageVersionRefResolutionError(str(exc), code=2) from exc

    if parsed.kind == "canonical":
        return package_ref

    payload = api_request(
        "GET", f"/packages/versions:resolve?ref={quote(package_ref, safe='')}"
    )
    canonical_ref = payload.get("package_ref") if isinstance(payload, dict) else None
    if not isinstance(canonical_ref, str) or not canonical_ref:
        raise PackageVersionRefResolutionError(
            "package resolver response did not include a canonical package ref"
        )
    return canonical_ref
