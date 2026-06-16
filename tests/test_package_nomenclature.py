from __future__ import annotations

import ast
from pathlib import Path
import re

from fastapi.testclient import TestClient
import pytest
from typer.testing import CliRunner

from agh.cli.main import app
from agh.common.ids import generate_prefixed_id, is_valid_prefixed_id
from agh.common.package_manifest import PackageManifestError, load_package_manifest
from agh.common.validation import parse_package_ref, parse_package_version_ref
from agh.server.app import create_app


def test_package_ids_use_pkg_prefixes_and_reject_legacy_pack_prefixes() -> None:
    package_id = generate_prefixed_id("pkg")
    version_id = generate_prefixed_id("pkgv")

    assert package_id.startswith("pkg_")
    assert version_id.startswith("pkgv_")
    assert is_valid_prefixed_id(package_id, "pkg")
    assert is_valid_prefixed_id(version_id, "pkgv")
    assert not is_valid_prefixed_id("pack_0123456789abcdef", "package")
    assert not is_valid_prefixed_id("packv_0123456789abcdef", "packv")


def test_package_ref_helpers_accept_pkgv_ids_and_package_wording() -> None:
    parsed = parse_package_ref("acme/onboarding@1.2.3", allow_latest=True)
    assert parsed.domain == "acme"
    assert parsed.name == "onboarding"
    assert parsed.version == "1.2.3"

    by_id = parse_package_version_ref("pkgv_0123456789abcdef", allow_latest=False)
    assert by_id.kind == "id"
    assert by_id.value == "pkgv_0123456789abcdef"


def test_package_manifest_loader_uses_package_manifest_only(tmp_path: Path) -> None:
    legacy_manifest = tmp_path / "agh.pack.toml"
    legacy_manifest.write_text(
        'domain = "acme"\nname = "onboarding"\nversion = "1.0.0"\ndescription = "desc"\n',
        encoding="utf-8",
    )

    with pytest.raises(PackageManifestError, match="agh.package.toml is required"):
        load_package_manifest(tmp_path / "agh.package.toml")

    package_manifest = tmp_path / "agh.package.toml"
    package_manifest.write_text(
        legacy_manifest.read_text(encoding="utf-8"), encoding="utf-8"
    )

    manifest = load_package_manifest(package_manifest)
    assert manifest.domain == "acme"
    assert manifest.name == "onboarding"


def test_cli_exposes_package_command_and_rejects_pack_alias() -> None:
    runner = CliRunner()

    package_help = runner.invoke(app, ["package", "--help"])
    legacy_pack_help = runner.invoke(app, ["pack", "--help"])
    pkg_help = runner.invoke(app, ["pkg", "--help"])

    assert package_help.exit_code == 0
    assert "guidance packages" in package_help.output.lower()
    assert legacy_pack_help.exit_code == 2
    assert pkg_help.exit_code == 2


def test_api_exposes_package_routes_and_rejects_pack_routes(
    tmp_path: Path, monkeypatch
) -> None:
    monkeypatch.setenv("AGH_DATA_DIR", str(tmp_path))
    client = TestClient(create_app())

    assert client.get("/api/v1/packages").status_code == 401
    assert client.get("/api/v1/packs").status_code == 404


def test_public_surfaces_do_not_expose_legacy_pack_terms() -> None:
    repo = Path(__file__).resolve().parents[1]
    scanned = [repo / "README.md", repo / "README.es.md", repo / "Dockerfile"]
    scanned.extend((repo / "agh").rglob("*.py"))
    allowed = {
        repo / "agh" / "server" / "db.py",
        repo / "agh" / "server" / "migrations" / "003_rename_packs_to_packages.sql",
    }
    pattern = re.compile(r"\b[Pp]acks?\b|pack_|packv_|/packs|\.pack\.toml|packageage")

    violations: list[str] = []
    for path in sorted(set(scanned)):
        if path in allowed or not path.is_file():
            continue
        for line_number, line in enumerate(
            path.read_text(encoding="utf-8").splitlines(), start=1
        ):
            if pattern.search(line) and not _is_audited_legacy_exception(
                repo=repo, path=path, line=line
            ):
                violations.append(f"{path.relative_to(repo)}:{line_number}: {line}")

    assert violations == []


def _is_audited_legacy_exception(*, repo: Path, path: Path, line: str) -> bool:
    legacy_context = line.lower()
    return (
        path == repo / "agh" / "cli" / "pull_markers.py"
        and "legacy" in legacy_context
        and "marker" in legacy_context
    ) or (
        path == repo / "agh" / "cli" / "workspace_pull.py"
        and "legacy" in legacy_context
        and "cache" in legacy_context
    )


def test_global_authenticated_package_registry_access_is_explicitly_documented() -> (
    None
):
    repo = Path(__file__).resolve().parents[1]
    spec = repo / "openspec" / "specs" / "guidance-packages" / "spec.md"

    assert "global authenticated package registry" in spec.read_text(encoding="utf-8")


def test_package_publish_limits_are_shared_between_cli_and_server() -> None:
    from agh.cli import package_publish
    from agh.common import package_limits
    from agh.server.routes import packages

    assert package_publish.MAX_PACKAGE_FILES == package_limits.MAX_PACKAGE_FILES
    assert (
        package_publish.MAX_PACKAGE_PATH_LENGTH
        == package_limits.MAX_PACKAGE_PATH_LENGTH
    )
    assert (
        package_publish.MAX_PACKAGE_FILE_BYTES == package_limits.MAX_PACKAGE_FILE_BYTES
    )
    assert (
        package_publish.MAX_PACKAGE_TOTAL_BYTES
        == package_limits.MAX_PACKAGE_TOTAL_BYTES
    )
    assert (
        packages.MAX_PACKAGE_PUBLISH_BODY_BYTES
        == package_limits.MAX_PACKAGE_PUBLISH_BODY_BYTES
    )
    assert package_publish.MAX_PACKAGE_FILES is package_limits.MAX_PACKAGE_FILES
    assert packages.MAX_PACKAGE_FILES is package_limits.MAX_PACKAGE_FILES


def test_package_publish_limits_are_not_redeclared_in_publishers() -> None:
    repo = Path(__file__).resolve().parents[1]
    limit_names = {
        "MAX_PACKAGE_FILES",
        "MAX_PACKAGE_PATH_LENGTH",
        "MAX_PACKAGE_FILE_BYTES",
        "MAX_PACKAGE_TOTAL_BYTES",
    }
    publisher_files = [
        repo / "agh" / "cli" / "package_publish.py",
        repo / "agh" / "server" / "routes" / "packages.py",
    ]

    redeclared: list[str] = []
    for path in publisher_files:
        tree = ast.parse(path.read_text(encoding="utf-8"))
        assigned_names = {
            target.id
            for node in tree.body
            if isinstance(node, ast.Assign)
            for target in node.targets
            if isinstance(target, ast.Name)
        }
        for name in sorted(limit_names & assigned_names):
            redeclared.append(f"{path.relative_to(repo)}:{name}")

    assert redeclared == []
