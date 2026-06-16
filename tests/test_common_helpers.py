from __future__ import annotations

from pathlib import Path

import pytest

from agh.common.checksums import managed_payload_checksum, normalize_managed_payload
from agh.common.ids import (
    generate_prefixed_id,
    is_valid_prefixed_id,
    validate_prefixed_id,
)
from agh.common.package_manifest import PackageManifestError, load_package_manifest
from agh.common.repo_url import normalize_repo_url
from agh.common.validation import (
    compare_semver,
    is_valid_email,
    is_valid_slug,
    parse_package_ref,
    parse_package_version_ref,
    validate_project_name,
    validate_package_publish_ref,
)


@pytest.mark.parametrize("prefix", ["usr", "tok", "prj", "pkg", "pkgv", "asn"])
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


def test_project_name_validation_trims_and_rejects_digit_only_names() -> None:
    assert validate_project_name("  Agent Guidance Hub  ") == "Agent Guidance Hub"

    with pytest.raises(ValueError, match="project name is required"):
        validate_project_name("   ")
    with pytest.raises(ValueError, match="cannot contain only digits"):
        validate_project_name("12345")


def test_package_ref_parsing_and_publish_rules() -> None:
    parsed = parse_package_ref("acme/onboarding@1.2.3", allow_latest=True)
    assert parsed.domain == "acme"
    assert parsed.name == "onboarding"
    assert parsed.version == "1.2.3"

    latest = parse_package_ref("acme/onboarding@latest", allow_latest=True)
    assert latest.version == "latest"

    with pytest.raises(ValueError):
        validate_package_publish_ref("acme/onboarding@latest")


def test_package_version_ref_parsing_accepts_id_canonical_and_name_version() -> None:
    by_id = parse_package_version_ref("pkgv_0123456789abcdef", allow_latest=False)
    assert by_id.kind == "id"
    assert by_id.value == "pkgv_0123456789abcdef"

    canonical = parse_package_version_ref("acme/onboarding@1.2.3", allow_latest=False)
    assert canonical.kind == "canonical"
    assert canonical.domain == "acme"
    assert canonical.name == "onboarding"
    assert canonical.version == "1.2.3"

    no_domain = parse_package_version_ref("onboarding@1.2.3", allow_latest=False)
    assert no_domain.kind == "name_version"
    assert no_domain.domain is None
    assert no_domain.name == "onboarding"
    assert no_domain.version == "1.2.3"


def test_package_version_ref_parsing_rejects_malformed_refs() -> None:
    for value in ["", "pkgv_bad", "onboarding", "Bad/name@1.0.0", "package@latest"]:
        with pytest.raises(ValueError):
            parse_package_version_ref(value, allow_latest=False)


def test_semver_comparison() -> None:
    assert compare_semver("1.0.0", "1.2.0") < 0
    assert compare_semver("2.0.0", "1.9.9") > 0
    assert compare_semver("1.0.0", "1.0.0") == 0


def test_repo_url_normalization_matches_common_github_forms() -> None:
    https = normalize_repo_url("https://github.com/org/app.git")
    ssh = normalize_repo_url("git@github.com:org/app.git")
    alt = normalize_repo_url("ssh://git@github.com/org/app")
    mixed_case = normalize_repo_url("git@github.com:Org/App.git")
    uppercase_suffix = normalize_repo_url("git@github.com:Org/App.GIT")
    encoded_host_https = normalize_repo_url("https://github%2ecom/org/app.git")
    host_dot_https = normalize_repo_url("https://github.com./Org/App.GIT/")
    host_dot_ssh_url = normalize_repo_url("ssh://git@github.com./Org/App.GIT/")
    host_dot_scp = normalize_repo_url("git@github.com.:Org/App.GIT")
    percent_encoded_suffix = normalize_repo_url("https://github.com/org/app%2Egit")
    percent_encoded_path = normalize_repo_url("ssh://git@github.com/org%2Fapp.git")
    encoded_trailing_slash = normalize_repo_url("https://github.com/org/app.git%2F")
    dot_segment = normalize_repo_url("https://github.com/org/./app.git")
    encoded_dot_segment = normalize_repo_url("https://github.com/org/%2e/app.git")
    parent_segment = normalize_repo_url("https://github.com/org/../org/app.git")
    scp_dot_segment = normalize_repo_url("git@github.com:org/./app.git")
    git_suffix_dot = normalize_repo_url("https://github.com/org/app.git/.")
    assert (
        https
        == ssh
        == alt
        == mixed_case
        == uppercase_suffix
        == encoded_host_https
        == host_dot_https
        == host_dot_ssh_url
        == host_dot_scp
        == percent_encoded_suffix
        == percent_encoded_path
        == encoded_trailing_slash
        == dot_segment
        == encoded_dot_segment
        == parent_segment
        == scp_dot_segment
        == git_suffix_dot
        == "github.com/org/app"
    )


def test_package_manifest_loader_and_validation(tmp_path: Path) -> None:
    manifest = tmp_path / "agh.package.toml"
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
    data = load_package_manifest(manifest)
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
    with pytest.raises(PackageManifestError):
        load_package_manifest(manifest)

    manifest.write_text('domain = "acme"\nname =', encoding="utf-8")
    with pytest.raises(PackageManifestError, match="invalid agh.package.toml"):
        load_package_manifest(manifest)


def test_checksum_payload_normalization() -> None:
    normalized = normalize_managed_payload("a\r\nb")
    assert normalized == "a\nb\n"
    digest = managed_payload_checksum("a\r\nb")
    assert digest.startswith("sha256:")
    assert len(digest) == len("sha256:") + 64
