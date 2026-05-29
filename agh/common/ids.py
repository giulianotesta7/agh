from __future__ import annotations

import re
import secrets

_ALLOWED_PREFIXES = {"usr", "tok", "prj", "pack", "packv", "asn"}
_ID_RE = re.compile(r"^(?P<prefix>[a-z]+)_[a-z0-9]{16}$")


def generate_prefixed_id(prefix: str) -> str:
    if prefix not in _ALLOWED_PREFIXES:
        raise ValueError(f"unsupported prefix: {prefix}")
    return f"{prefix}_{secrets.token_hex(8)}"


def is_valid_prefixed_id(value: str, prefix: str) -> bool:
    if prefix not in _ALLOWED_PREFIXES:
        return False
    match = _ID_RE.fullmatch(value)
    return bool(match and match.group("prefix") == prefix)


def validate_prefixed_id(value: str, prefix: str) -> str:
    if not is_valid_prefixed_id(value, prefix):
        raise ValueError(f"invalid {prefix} id: {value}")
    return value
