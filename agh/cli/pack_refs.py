from __future__ import annotations

from collections.abc import Callable
from typing import Any
from urllib.parse import quote

from agh.common.validation import parse_pack_ref, parse_pack_version_ref


class PackVersionRefResolutionError(ValueError):
    def __init__(self, message: str, *, code: int = 1) -> None:
        super().__init__(message)
        self.code = code


ApiRequest = Callable[..., Any]


def resolve_pack_version_ref(pack_ref: str, api_request: ApiRequest) -> str:
    try:
        parse_pack_ref(pack_ref, allow_latest=True)
        return pack_ref
    except ValueError:
        pass

    try:
        parsed = parse_pack_version_ref(pack_ref, allow_latest=False)
    except ValueError as exc:
        raise PackVersionRefResolutionError(str(exc), code=2) from exc

    if parsed.kind == "canonical":
        return pack_ref

    payload = api_request(
        "GET", f"/packs/versions:resolve?ref={quote(pack_ref, safe='')}"
    )
    canonical_ref = payload.get("pack_ref") if isinstance(payload, dict) else None
    if not isinstance(canonical_ref, str) or not canonical_ref:
        raise PackVersionRefResolutionError(
            "pack resolver response did not include a canonical pack ref"
        )
    return canonical_ref
