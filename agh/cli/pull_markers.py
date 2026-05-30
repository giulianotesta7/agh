"""Managed AGH marker parsing and update planning."""

from __future__ import annotations

import re
from dataclasses import dataclass, field

from agh.common.checksums import managed_payload_checksum, normalize_managed_payload

_BEGIN_RE = re.compile(r"^<!-- AGH-BEGIN (?P<meta>.+) -->$")
_END_RE = re.compile(r'^<!-- AGH-END pack="(?P<pack>[^"]+)" -->$')
_META_RE = re.compile(r'(?P<key>[a-z_]+)="(?P<value>[^"]*)"')
_CHECKSUM_RE = re.compile(r"^sha256:[0-9a-f]{64}$")


class MarkerError(ValueError):
    """Raised when managed markers are malformed."""


@dataclass(frozen=True)
class ManagedBlock:
    """One AGH-managed block found in a text file."""

    pack_ref: str
    artifact_path: str
    checksum: str
    payload: str
    start: int
    end: int


@dataclass(frozen=True)
class ManagedBlockRequest:
    """A desired managed block state."""

    pack_ref: str
    artifact_path: str
    payload: str


@dataclass(frozen=True)
class MarkerConflict:
    """A checksum mismatch that prevents a safe marker update."""

    pack_ref: str
    artifact_path: str
    expected_checksum: str
    actual_checksum: str


@dataclass(frozen=True)
class MarkerPlan:
    """Planned marker update without performing filesystem writes."""

    status: str
    content: str
    conflicts: list[MarkerConflict] = field(default_factory=list)


def parse_managed_blocks(text: str) -> list[ManagedBlock]:
    """Parse all AGH-managed blocks from text."""
    blocks: list[ManagedBlock] = []
    active: dict[str, str] | None = None
    block_start = 0
    payload_start = 0
    offset = 0

    for line in text.splitlines(keepends=True):
        stripped = line.rstrip("\r\n")
        begin = _BEGIN_RE.match(stripped)
        end = _END_RE.match(stripped)

        if begin:
            if active is not None:
                raise MarkerError("nested AGH managed block")
            active = _parse_begin_metadata(begin.group("meta"))
            block_start = offset
            payload_start = offset + len(line)
        elif end:
            if active is None:
                raise MarkerError("AGH-END without AGH-BEGIN")
            end_pack = end.group("pack")
            if end_pack != active["pack"]:
                raise MarkerError("AGH-END pack does not match AGH-BEGIN pack")
            payload = text[payload_start:offset]
            blocks.append(
                ManagedBlock(
                    pack_ref=active["pack"],
                    artifact_path=active["artifact"],
                    checksum=active["checksum"],
                    payload=payload,
                    start=block_start,
                    end=offset + len(line),
                )
            )
            active = None
        offset += len(line)

    if active is not None:
        raise MarkerError("AGH-BEGIN without AGH-END")
    return blocks


def render_managed_block(pack_ref: str, artifact_path: str, payload: str) -> str:
    """Render one managed block with checksum metadata."""
    _validate_metadata_value("pack", pack_ref)
    _validate_metadata_value("artifact", artifact_path)
    normalized_payload = normalize_managed_payload(payload)
    _reject_marker_delimiters(normalized_payload)
    checksum = managed_payload_checksum(normalized_payload)
    return (
        f'<!-- AGH-BEGIN pack="{pack_ref}" artifact="{artifact_path}" '
        f'checksum="{checksum}" -->\n'
        f"{normalized_payload}"
        f'<!-- AGH-END pack="{pack_ref}" -->\n'
    )


def plan_managed_update(text: str, request: ManagedBlockRequest) -> MarkerPlan:
    """Plan inserting or updating a managed block while preserving unmanaged text."""
    blocks = parse_managed_blocks(text)
    matches = [
        block
        for block in blocks
        if block.pack_ref == request.pack_ref
        and block.artifact_path == request.artifact_path
    ]
    if len(matches) > 1:
        raise MarkerError("duplicate AGH managed block")

    rendered = render_managed_block(
        request.pack_ref, request.artifact_path, request.payload
    )
    if not matches:
        prefix = _append_separator(text)
        return MarkerPlan(status="insert", content=f"{prefix}{rendered}")

    block = matches[0]
    actual_checksum = managed_payload_checksum(block.payload)
    if actual_checksum != block.checksum:
        return MarkerPlan(
            status="conflict",
            content=text,
            conflicts=[
                MarkerConflict(
                    pack_ref=block.pack_ref,
                    artifact_path=block.artifact_path,
                    expected_checksum=block.checksum,
                    actual_checksum=actual_checksum,
                )
            ],
        )
    if rendered == text[block.start : block.end]:
        return MarkerPlan(status="noop", content=text)
    return MarkerPlan(
        status="update",
        content=f"{text[: block.start]}{rendered}{text[block.end :]}",
    )


def _parse_begin_metadata(raw: str) -> dict[str, str]:
    metadata = {
        match.group("key"): match.group("value") for match in _META_RE.finditer(raw)
    }
    if set(metadata) != {"pack", "artifact", "checksum"}:
        raise MarkerError("AGH-BEGIN requires pack, artifact, and checksum")
    if not _CHECKSUM_RE.fullmatch(metadata["checksum"]):
        raise MarkerError("AGH-BEGIN checksum must be sha256:<hex>")
    rebuilt = " ".join(
        f'{key}="{metadata[key]}"' for key in ("pack", "artifact", "checksum")
    )
    if rebuilt != raw:
        raise MarkerError("invalid AGH-BEGIN metadata")
    return metadata


def _reject_marker_delimiters(payload: str) -> None:
    for line in payload.splitlines():
        if _BEGIN_RE.match(line) or _END_RE.match(line):
            raise MarkerError("managed payload must not contain AGH marker delimiters")


def _validate_metadata_value(name: str, value: str) -> None:
    if not value or any(character in value for character in ('"', "\r", "\n")):
        raise MarkerError(f"invalid AGH marker {name}")


def _append_separator(text: str) -> str:
    if not text:
        return ""
    if text.endswith("\n\n"):
        return text
    if text.endswith("\n"):
        return f"{text}\n"
    return f"{text}\n\n"
