from __future__ import annotations

import threading
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from typing import Any, ClassVar

import pytest

from agh.cli.config import AghConfig
from agh.cli.workspace_pull import WorkspacePullError, populate_cache_and_write_lock
from agh.common.checksums import managed_payload_checksum


class _ArtifactHandler(BaseHTTPRequestHandler):
    artifact_responses: ClassVar[dict[str, tuple[int, str]]] = {}
    requests: ClassVar[list[dict[str, Any]]] = []

    def do_GET(self) -> None:  # noqa: N802
        type(self).requests.append(
            {"path": self.path, "authorization": self.headers.get("Authorization")}
        )
        status, body = type(self).artifact_responses.get(self.path, (404, "missing"))
        self.send_response(status)
        self.send_header("Content-Type", "text/plain; charset=utf-8")
        self.end_headers()
        self.wfile.write(body.encode("utf-8"))

    def log_message(self, format: str, *args: object) -> None:  # noqa: A002
        return


def _serve_artifacts(responses: dict[str, tuple[int, str]]):
    class Handler(_ArtifactHandler):
        pass

    Handler.artifact_responses = responses
    Handler.requests = []
    server = ThreadingHTTPServer(("127.0.0.1", 0), Handler)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    return server, Handler, f"http://127.0.0.1:{server.server_port}"


def _config(url: str) -> AghConfig:
    return AghConfig(instance_url=url, email="owner@example.com", token="pull-token")


def _manifest(*, content: str = "Use AGH.\n") -> dict[str, Any]:
    return {
        "project": {"id": "prj_1", "name": "Demo"},
        "packs": [
            {
                "id": "acme/onboarding@1.0.0",
                "assignment_id": "asn_1",
                "position": 0,
                "manifest": {
                    "domain": "acme",
                    "name": "onboarding",
                    "version": "1.0.0",
                    "description": "Demo",
                },
                "artifacts": [
                    {
                        "kind": "instruction",
                        "path": "instructions/AGENTS.md",
                        "target_agent": "opencode",
                        "target_path": "AGENTS.md",
                        "checksum": managed_payload_checksum(content),
                        "download_url": "/api/v1/packs/acme/onboarding/versions/1.0.0/files/instructions/AGENTS.md",
                    }
                ],
            }
        ],
    }


def test_populate_cache_downloads_artifacts_and_writes_lock(tmp_path: Path) -> None:
    content = "Use AGH.\n"
    server, handler, url = _serve_artifacts(
        {
            "/api/v1/packs/acme/onboarding/versions/1.0.0/files/instructions/AGENTS.md": (
                200,
                content,
            )
        }
    )
    try:
        result = populate_cache_and_write_lock(
            tmp_path, config=_config(url), manifest=_manifest(content=content)
        )
    finally:
        server.shutdown()

    cached = (
        tmp_path
        / ".agh"
        / "packs"
        / "acme"
        / "onboarding"
        / "1.0.0"
        / "instructions"
        / "AGENTS.md"
    )
    lock_path = tmp_path / ".agh" / "lock.toml"
    assert result.cache_dir == tmp_path / ".agh" / "packs"
    assert result.lock_path == lock_path
    assert cached.read_text(encoding="utf-8") == content
    assert result.artifacts[0].cache_path == Path(
        ".agh/packs/acme/onboarding/1.0.0/instructions/AGENTS.md"
    )
    assert handler.requests == [
        {
            "path": "/api/v1/packs/acme/onboarding/versions/1.0.0/files/instructions/AGENTS.md",
            "authorization": "Bearer pull-token",
        }
    ]
    lock = lock_path.read_text(encoding="utf-8")
    assert "version = 1" in lock
    assert 'id = "prj_1"' in lock
    assert 'ref = "acme/onboarding@1.0.0"' in lock
    assert 'path = "instructions/AGENTS.md"' in lock
    assert 'target_path = "AGENTS.md"' in lock
    assert f'checksum = "{managed_payload_checksum(content)}"' in lock
    assert 'mode = "cache"' in lock
    assert 'source = ".agh/packs/acme/onboarding/1.0.0/instructions/AGENTS.md"' in lock
    assert str(tmp_path) not in lock


def test_populate_cache_rejects_checksum_mismatch_without_lock(tmp_path: Path) -> None:
    server, _handler, url = _serve_artifacts(
        {
            "/api/v1/packs/acme/onboarding/versions/1.0.0/files/instructions/AGENTS.md": (
                200,
                "different\n",
            )
        }
    )
    try:
        with pytest.raises(WorkspacePullError, match="checksum mismatch"):
            populate_cache_and_write_lock(
                tmp_path, config=_config(url), manifest=_manifest(content="expected\n")
            )
    finally:
        server.shutdown()

    assert not (tmp_path / ".agh" / "lock.toml").exists()


@pytest.mark.parametrize(
    "artifact_update",
    [
        {"path": "../secret.md"},
        {"target_path": "../AGENTS.md"},
        {"download_url": "https://evil.example/file"},
        {"download_url": "/other/file"},
        {"download_url": "/api/v1/../admin"},
        {"download_url": "/api/v1/%2e%2e/admin"},
        {"download_url": "/api/v1/%2e%2e%2fadmin"},
        {"download_url": "/api/v1/%2e%2fadmin"},
        {"download_url": "/api/v1/packs;param/bar"},
        {"download_url": "/api/v1/..\\admin"},
        {"download_url": "/api/v1/%5c..%5cadmin"},
        {"download_url": "%2fapi%2fv1/packs/acme/onboarding"},
        {"download_url": "/api/v1/packs?x=1"},
        {"path": "instructions/BAD\nNAME.md"},
        {"target_path": "BAD\nTARGET.md"},
        {"path": "bad\x01name.md"},
        {"target_path": "bad\x7fname.md"},
        {"path": ""},
        {"target_path": ""},
        {"path": "."},
        {"path": "a/."},
        {"path": "a/./b"},
        {"path": "a\\..\\secret.md"},
        {"target_path": "."},
        {"target_path": "a/."},
        {"target_path": "a\\..\\AGENTS.md"},
        {"path": None},
        {"target_path": None},
        {"checksum": None},
        {"download_url": None},
    ],
)
def test_populate_cache_rejects_unsafe_manifest_values(
    tmp_path: Path, artifact_update: dict[str, object]
) -> None:
    manifest = _manifest()
    manifest["packs"][0]["artifacts"][0].update(artifact_update)

    with pytest.raises(WorkspacePullError) as exc_info:
        populate_cache_and_write_lock(
            tmp_path, config=_config("http://127.0.0.1:9"), manifest=manifest
        )

    assert exc_info.value.code == 2


def test_populate_cache_rejects_non_string_project_id(tmp_path: Path) -> None:
    manifest = _manifest()
    manifest["project"]["id"] = None

    with pytest.raises(WorkspacePullError) as exc_info:
        populate_cache_and_write_lock(
            tmp_path, config=_config("http://127.0.0.1:9"), manifest=manifest
        )

    assert exc_info.value.code == 2


def test_populate_cache_rejects_non_object_project(tmp_path: Path) -> None:
    manifest = _manifest()
    manifest["project"] = "bad"

    with pytest.raises(WorkspacePullError) as exc_info:
        populate_cache_and_write_lock(
            tmp_path, config=_config("http://127.0.0.1:9"), manifest=manifest
        )

    assert exc_info.value.code == 2


def test_populate_cache_rejects_non_object_manifest(tmp_path: Path) -> None:
    with pytest.raises(WorkspacePullError) as exc_info:
        populate_cache_and_write_lock(
            tmp_path, config=_config("http://127.0.0.1:9"), manifest="bad"
        )

    assert exc_info.value.code == 2


def test_populate_cache_rejects_symlinked_packs_dir(tmp_path: Path) -> None:
    outside = tmp_path / "outside"
    outside.mkdir()
    agh_dir = tmp_path / ".agh"
    agh_dir.mkdir()
    (agh_dir / "packs").symlink_to(outside, target_is_directory=True)

    with pytest.raises(WorkspacePullError, match="symlinked"):
        populate_cache_and_write_lock(
            tmp_path, config=_config("http://127.0.0.1:9"), manifest=_manifest()
        )


def test_populate_cache_rejects_symlinked_intermediate_cache_dir(
    tmp_path: Path,
) -> None:
    outside = tmp_path / "outside"
    outside.mkdir()
    cache_root = tmp_path / ".agh" / "packs" / "acme"
    cache_root.parent.mkdir(parents=True)
    cache_root.symlink_to(outside, target_is_directory=True)

    with pytest.raises(WorkspacePullError, match="symlinked"):
        populate_cache_and_write_lock(
            tmp_path, config=_config("http://127.0.0.1:9"), manifest=_manifest()
        )


def test_populate_cache_rejects_non_object_manifest_entries(tmp_path: Path) -> None:
    manifest = _manifest()
    manifest["packs"].append("bad")

    with pytest.raises(WorkspacePullError, match="packs must be objects"):
        populate_cache_and_write_lock(
            tmp_path, config=_config("http://127.0.0.1:9"), manifest=manifest
        )

    manifest = _manifest()
    manifest["packs"][0]["artifacts"].append("bad")

    with pytest.raises(WorkspacePullError, match="artifacts must be objects"):
        populate_cache_and_write_lock(
            tmp_path, config=_config("http://127.0.0.1:9"), manifest=manifest
        )


def test_populate_cache_rejects_symlinked_agh_dir(tmp_path: Path) -> None:
    outside = tmp_path / "outside"
    outside.mkdir()
    (tmp_path / ".agh").symlink_to(outside, target_is_directory=True)

    with pytest.raises(WorkspacePullError, match="symlinked AGH directory"):
        populate_cache_and_write_lock(
            tmp_path, config=_config("http://127.0.0.1:9"), manifest=_manifest()
        )


def test_lock_source_is_workspace_relative_even_under_dot_agh_parent(
    tmp_path: Path,
) -> None:
    workspace = tmp_path / ".agh" / "nested-workspace"
    workspace.mkdir(parents=True)
    content = "Use AGH.\n"
    server, _handler, url = _serve_artifacts(
        {
            "/api/v1/packs/acme/onboarding/versions/1.0.0/files/instructions/AGENTS.md": (
                200,
                content,
            )
        }
    )
    try:
        populate_cache_and_write_lock(
            workspace, config=_config(url), manifest=_manifest(content=content)
        )
    finally:
        server.shutdown()

    lock = (workspace / ".agh" / "lock.toml").read_text(encoding="utf-8")
    assert 'source = ".agh/packs/acme/onboarding/1.0.0/instructions/AGENTS.md"' in lock
    assert ".agh/nested-workspace/.agh/packs" not in lock


def test_lockfile_rejects_project_id_control_characters(tmp_path: Path) -> None:
    manifest = _manifest()
    manifest["project"]["id"] = "prj_\x01"

    with pytest.raises(WorkspacePullError, match="control character"):
        populate_cache_and_write_lock(
            tmp_path, config=_config("http://127.0.0.1:9"), manifest=manifest
        )


def test_lockfile_is_valid_toml(tmp_path: Path) -> None:
    content = "Use AGH.\n"
    server, _handler, url = _serve_artifacts(
        {
            "/api/v1/packs/acme/onboarding/versions/1.0.0/files/instructions/AGENTS.md": (
                200,
                content,
            )
        }
    )
    try:
        populate_cache_and_write_lock(
            tmp_path, config=_config(url), manifest=_manifest(content=content)
        )
    finally:
        server.shutdown()

    import tomllib

    parsed = tomllib.loads((tmp_path / ".agh" / "lock.toml").read_text())
    assert parsed["version"] == 1
    assert parsed["project"]["id"] == "prj_1"
    assert parsed["packs"][0]["ref"] == "acme/onboarding@1.0.0"
    assert parsed["artifacts"][0]["path"] == "instructions/AGENTS.md"
