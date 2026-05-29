from __future__ import annotations

from pathlib import Path

import pytest

from agh.common.checksums import managed_payload_checksum, normalize_managed_payload
from agh.common.ids import (
    generate_prefixed_id,
    is_valid_prefixed_id,
    validate_prefixed_id,
)
from agh.common.pack_manifest import PackManifestError, load_pack_manifest
from agh.common.repo_url import normalize_repo_url
from agh.common.validation import (
    compare_semver,
    is_valid_email,
    is_valid_slug,
    parse_pack_ref,
    validate_pack_publish_ref,
)


@pytest.mark.parametrize("prefix", ["usr", "tok", "prj", "pack", "packv", "asn"])
def test_prefixed_ids_generate_and_validate(prefix: str) -> None:
    ident = generate_prefixed_id(prefix)
    assert ident.startswith(f"{prefix}_")
    assert is_valid_prefixed_id(ident, prefix)
    validate_prefixed_id(ident, prefix)


def test_prefixed_ids_reject_wrong_prefix_and_unsupported_prefix() -> None:
    ident = generate_prefixed_id("usr")
    assert not is_valid_prefixed_id(ident, "tok")
    assert not is_valid_prefixed_id("proj_1234567890abcdef", "proj")
    with pytest.raises(ValueError):
        validate_prefixed_id("bad", "usr")
    with pytest.raises(ValueError):
        generate_prefixed_id("proj")


@pytest.mark.parametrize("email", ["a@b.co", "name.surname+tag@example.io"])
def test_email_validation_accepts_mvp_cases(email: str) -> None:
    assert is_valid_email(email)


@pytest.mark.parametrize("email", ["", "nope", "@example.com", "a@", "a @b.com"])
def test_email_validation_rejects_invalid(email: str) -> None:
    assert not is_valid_email(email)


def test_slug_validation_rejects_latest_and_bad_shapes() -> None:
    assert is_valid_slug("acme")
    assert is_valid_slug("my-team")
    assert not is_valid_slug("latest")
    assert not is_valid_slug("BadCase")
    assert not is_valid_slug("-start")


def test_pack_ref_parsing_and_publish_rules() -> None:
    parsed = parse_pack_ref("acme/onboarding@1.2.3", allow_latest=True)
    assert parsed.domain == "acme"
    assert parsed.name == "onboarding"
    assert parsed.version == "1.2.3"

    latest = parse_pack_ref("acme/onboarding@latest", allow_latest=True)
    assert latest.version == "latest"

    with pytest.raises(ValueError):
        validate_pack_publish_ref("acme/onboarding@latest")


def test_semver_comparison() -> None:
    assert compare_semver("1.0.0", "1.2.0") < 0
    assert compare_semver("2.0.0", "1.9.9") > 0
    assert compare_semver("1.0.0", "1.0.0") == 0


def test_repo_url_normalization_matches_common_github_forms() -> None:
    https = normalize_repo_url("https://github.com/org/app.git")
    ssh = normalize_repo_url("git@github.com:org/app.git")
    alt = normalize_repo_url("ssh://git@github.com/org/app")
    assert https == ssh == alt == "github.com/org/app"


def test_pack_manifest_loader_and_validation(tmp_path: Path) -> None:
    manifest = tmp_path / "agh.pack.toml"
    manifest.write_text(
        """
        domain = "acme"
        name = "onboarding"
        version = "1.0.0"
        description = "desc"
        tags = ["quick-start", "team"]
        """,
        encoding="utf-8",
    )
    data = load_pack_manifest(manifest)
    assert data.domain == "acme"
    assert data.tags == ["quick-start", "team"]

    manifest.write_text(
        """
        domain = "latest"
        name = "onboarding"
        version = "1.0.0"
        description = "desc"
        """,
        encoding="utf-8",
    )
    with pytest.raises(PackManifestError):
        load_pack_manifest(manifest)

    manifest.write_text('domain = "acme"\nname =', encoding="utf-8")
    with pytest.raises(PackManifestError, match="invalid agh.pack.toml"):
        load_pack_manifest(manifest)


def test_checksum_payload_normalization() -> None:
    normalized = normalize_managed_payload("a\r\nb")
    assert normalized == "a\nb\n"
    digest = managed_payload_checksum("a\r\nb")
    assert digest.startswith("sha256:")
    assert len(digest) == len("sha256:") + 64
