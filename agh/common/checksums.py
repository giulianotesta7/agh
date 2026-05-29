from __future__ import annotations

import hashlib


def normalize_managed_payload(content: str) -> str:
    normalized = content.replace("\r\n", "\n").replace("\r", "\n")
    return normalized.rstrip("\n") + "\n"


def managed_payload_checksum(content: str) -> str:
    payload = normalize_managed_payload(content).encode("utf-8")
    digest = hashlib.sha256(payload).hexdigest()
    return f"sha256:{digest}"
