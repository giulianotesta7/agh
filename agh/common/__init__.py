"""Shared AGH helper utilities."""

from agh.common.checksums import managed_payload_checksum, normalize_managed_payload
from agh.common.ids import (
    generate_prefixed_id,
    is_valid_prefixed_id,
    validate_prefixed_id,
)
from agh.common.pack_manifest import PackManifest, PackManifestError, load_pack_manifest
from agh.common.repo_url import normalize_repo_url
from agh.common.validation import (
    PackRef,
    PackVersionRef,
    compare_semver,
    is_semver,
    is_valid_email,
    is_valid_slug,
    parse_pack_ref,
    parse_pack_version_ref,
    validate_pack_publish_ref,
    validate_slug,
)

__all__ = [
    "PackManifest",
    "PackManifestError",
    "PackRef",
    "PackVersionRef",
    "compare_semver",
    "generate_prefixed_id",
    "is_semver",
    "is_valid_email",
    "is_valid_prefixed_id",
    "is_valid_slug",
    "load_pack_manifest",
    "managed_payload_checksum",
    "normalize_managed_payload",
    "normalize_repo_url",
    "parse_pack_ref",
    "parse_pack_version_ref",
    "validate_pack_publish_ref",
    "validate_prefixed_id",
    "validate_slug",
]
