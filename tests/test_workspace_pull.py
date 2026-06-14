from __future__ import annotations

import threading
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from typing import Any, ClassVar

import pytest

import agh.cli.workspace_pull as workspace_pull
from agh.cli.config import AghConfig
from agh.cli.workspace_pull import (
    DownloadedArtifact,
    WorkspacePullError,
    _cleanup_cache_stage_dirs,
    _cleanup_stale_cache_staging_dirs,
    _commit_pull_writes,
    _stage_cache_artifacts,
    populate_cache_and_write_lock,
)
from agh.cli.pull_plan import PullPlan, PullTargetChange
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


def _downloaded_artifact(*, content: str = "Use AGH.\n") -> DownloadedArtifact:
    return DownloadedArtifact(
        pack_ref="acme/onboarding@1.0.0",
        path="instructions/AGENTS.md",
        target_path="AGENTS.md",
        checksum=managed_payload_checksum(content),
        content=content,
        kind="instruction",
        target_agent="opencode",
        domain="acme",
        name="onboarding",
        version="1.0.0",
    )


def _downloaded_extra_artifact(*, content: str = "Use Claude.\n") -> DownloadedArtifact:
    return DownloadedArtifact(
        pack_ref="acme/onboarding@1.0.0",
        path="instructions/CLAUDE.md",
        target_path="CLAUDE.md",
        checksum=managed_payload_checksum(content),
        content=content,
        kind="instruction",
        target_agent="claude",
        domain="acme",
        name="onboarding",
        version="1.0.0",
    )


def _committed_cache_artifact(workspace: Path) -> Path:
    return workspace / ".agh-cache/packs/acme/onboarding/1.0.0/instructions/AGENTS.md"


def _downloaded_skill_artifact(
    *, name: str = "reviewer", content: str = "Review carefully.\n"
) -> DownloadedArtifact:
    return DownloadedArtifact(
        pack_ref="acme/onboarding@1.0.0",
        path=f"skills/{name}/SKILL.md",
        target_path=f".opencode/skills/{name}/SKILL.md",
        checksum=managed_payload_checksum(content),
        content=content,
        kind="skill",
        target_agent="opencode",
        domain="acme",
        name="onboarding",
        version="1.0.0",
    )


def _changed_plan(target_path: str, content: str) -> PullPlan:
    return PullPlan(
        status="changed",
        exit_code=0,
        dry_run=False,
        changes=[
            PullTargetChange(
                target_path=target_path,
                status="insert",
                content=content,
                conflicts=[],
            )
        ],
    )


def test_commit_pull_writes_target_failure_restores_old_cache_and_lock(
    tmp_path: Path, monkeypatch
) -> None:
    committed = _committed_cache_artifact(tmp_path)
    committed.parent.mkdir(parents=True)
    committed.write_text("previous cache\n", encoding="utf-8")
    lock = tmp_path / ".agh" / "lock.toml"
    lock.parent.mkdir()
    lock.write_text("previous lock\n", encoding="utf-8")

    def fail_target_write(_root: Path, target_path: Path, _content: str) -> None:
        raise OSError(f"target failed at {target_path.as_posix()}")

    monkeypatch.setattr(workspace_pull, "_write_target_file", fail_target_write)

    with pytest.raises(OSError, match="target failed"):
        _commit_pull_writes(
            tmp_path,
            manifest=_manifest(content="new cache\n"),
            artifacts=[_downloaded_artifact(content="new cache\n")],
            instruction_plan=_changed_plan("AGENTS.md", "new target\n"),
            skill_artifacts=[],
        )

    assert committed.read_text(encoding="utf-8") == "previous cache\n"
    assert lock.read_text(encoding="utf-8") == "previous lock\n"
    assert not (tmp_path / "AGENTS.md").exists()
    assert not list(committed.parents[2].glob(".agh-pull-stage-*"))


def test_commit_pull_writes_skill_failure_restores_instruction_target_and_cache(
    tmp_path: Path, monkeypatch
) -> None:
    committed = _committed_cache_artifact(tmp_path)
    committed.parent.mkdir(parents=True)
    committed.write_text("previous cache\n", encoding="utf-8")
    target = tmp_path / "AGENTS.md"
    target.write_text("previous target\n", encoding="utf-8")
    first_skill = tmp_path / ".opencode" / "skills" / "reviewer" / "SKILL.md"
    first_skill.parent.mkdir(parents=True)
    first_skill.write_text("previous skill\n", encoding="utf-8")
    lock = tmp_path / ".agh" / "lock.toml"
    lock.parent.mkdir()
    lock.write_text("previous lock\n", encoding="utf-8")

    def fail_skill_write(*, target: Path, source: Path, content: str) -> str:
        if target.name != "SKILL.md" or "second" in target.parts:
            raise OSError(f"skill failed at {target}")
        target.write_text(content, encoding="utf-8")
        return "copy"

    def fail_second_skill_write(*, target: Path, source: Path, content: str) -> str:
        if "second" in target.parts:
            raise OSError(f"skill failed at {target}")
        return fail_skill_write(target=target, source=source, content=content)

    monkeypatch.setattr(workspace_pull, "_write_skill_target", fail_second_skill_write)

    with pytest.raises(OSError, match="skill failed"):
        _commit_pull_writes(
            tmp_path,
            manifest=_manifest(content="new cache\n"),
            artifacts=[
                _downloaded_artifact(content="new cache\n"),
                _downloaded_skill_artifact(name="reviewer"),
                _downloaded_skill_artifact(name="second", content="Second skill.\n"),
            ],
            instruction_plan=_changed_plan("AGENTS.md", "new target\n"),
            skill_artifacts=[
                _downloaded_skill_artifact(name="reviewer"),
                _downloaded_skill_artifact(name="second", content="Second skill.\n"),
            ],
        )

    assert committed.read_text(encoding="utf-8") == "previous cache\n"
    assert target.read_text(encoding="utf-8") == "previous target\n"
    assert first_skill.read_text(encoding="utf-8") == "previous skill\n"
    assert lock.read_text(encoding="utf-8") == "previous lock\n"
    assert not (tmp_path / ".opencode" / "skills" / "second" / "SKILL.md").exists()


def test_commit_pull_writes_lock_failure_restores_promoted_outputs(
    tmp_path: Path, monkeypatch
) -> None:
    committed = _committed_cache_artifact(tmp_path)
    committed.parent.mkdir(parents=True)
    committed.write_text("previous cache\n", encoding="utf-8")
    lock = tmp_path / ".agh" / "lock.toml"
    lock.parent.mkdir()
    lock.write_text("previous lock\n", encoding="utf-8")

    skill = tmp_path / ".opencode" / "skills" / "reviewer" / "SKILL.md"

    def fail_lock_write(_path: Path, *, manifest: dict, artifacts: list) -> None:
        assert committed.read_text(encoding="utf-8") == "new cache\n"
        assert "new target\n" in (tmp_path / "AGENTS.md").read_text(encoding="utf-8")
        assert skill.exists()
        raise OSError("lock failed")

    monkeypatch.setattr(workspace_pull, "_write_lockfile", fail_lock_write)

    with pytest.raises(OSError, match="lock failed"):
        _commit_pull_writes(
            tmp_path,
            manifest=_manifest(content="new cache\n"),
            artifacts=[
                _downloaded_artifact(content="new cache\n"),
                _downloaded_skill_artifact(),
            ],
            instruction_plan=_changed_plan("AGENTS.md", "new target\n"),
            skill_artifacts=[_downloaded_skill_artifact()],
        )

    assert committed.read_text(encoding="utf-8") == "previous cache\n"
    assert lock.read_text(encoding="utf-8") == "previous lock\n"
    assert not (tmp_path / "AGENTS.md").exists()
    assert not skill.exists()


def test_stage_cache_artifacts_writes_sibling_stage_dir_only(tmp_path: Path) -> None:
    staged = _stage_cache_artifacts(tmp_path, artifacts=[_downloaded_artifact()])

    stage_dir = staged.stage_dirs[0]
    assert stage_dir.parent == (
        tmp_path / ".agh-cache" / "packs" / "acme" / "onboarding"
    )
    assert stage_dir.name.startswith(".agh-pull-stage-1.0.0-")
    assert (stage_dir / "instructions" / "AGENTS.md").read_text(
        encoding="utf-8"
    ) == "Use AGH.\n"
    assert staged.artifacts[0].cache_path == Path(
        ".agh-cache/packs/acme/onboarding/1.0.0/instructions/AGENTS.md"
    )
    assert not (
        tmp_path
        / ".agh-cache"
        / "packs"
        / "acme"
        / "onboarding"
        / "1.0.0"
        / "instructions"
        / "AGENTS.md"
    ).exists()


def test_stage_cache_artifacts_failure_preserves_committed_cache_and_lock(
    tmp_path: Path, monkeypatch
) -> None:
    committed = (
        tmp_path
        / ".agh-cache"
        / "packs"
        / "acme"
        / "onboarding"
        / "1.0.0"
        / "instructions"
        / "AGENTS.md"
    )
    committed.parent.mkdir(parents=True)
    committed.write_text("previous cache\n", encoding="utf-8")
    lock = tmp_path / ".agh" / "lock.toml"
    lock.parent.mkdir()
    lock.write_text("previous lock\n", encoding="utf-8")

    def fail_cache_write(path: Path, _content: str) -> None:
        raise OSError(f"staging failed at {path.name}")

    monkeypatch.setattr(workspace_pull, "_write_cache_file", fail_cache_write)

    with pytest.raises(OSError, match="staging failed"):
        _stage_cache_artifacts(
            tmp_path, artifacts=[_downloaded_artifact(content="new\n")]
        )

    assert committed.read_text(encoding="utf-8") == "previous cache\n"
    assert lock.read_text(encoding="utf-8") == "previous lock\n"
    assert not list(committed.parents[2].glob(".agh-pull-stage-*"))


def test_stage_cache_artifacts_second_write_failure_cleans_partial_stage(
    tmp_path: Path, monkeypatch
) -> None:
    committed = (
        tmp_path
        / ".agh-cache"
        / "packs"
        / "acme"
        / "onboarding"
        / "1.0.0"
        / "instructions"
        / "AGENTS.md"
    )
    committed.parent.mkdir(parents=True)
    committed.write_text("previous cache\n", encoding="utf-8")
    lock = tmp_path / ".agh" / "lock.toml"
    lock.parent.mkdir()
    lock.write_text("previous lock\n", encoding="utf-8")
    write_cache_file = workspace_pull._write_cache_file

    def fail_second_cache_write(path: Path, content: str) -> None:
        if path.name == "CLAUDE.md":
            raise OSError("staging failed on second artifact")
        write_cache_file(path, content)

    monkeypatch.setattr(workspace_pull, "_write_cache_file", fail_second_cache_write)

    with pytest.raises(OSError, match="second artifact"):
        _stage_cache_artifacts(
            tmp_path,
            artifacts=[
                _downloaded_artifact(content="new\n"),
                _downloaded_extra_artifact(),
            ],
        )

    assert committed.read_text(encoding="utf-8") == "previous cache\n"
    assert lock.read_text(encoding="utf-8") == "previous lock\n"
    assert not list(committed.parents[2].glob(".agh-pull-stage-*"))


def test_cleanup_stale_cache_staging_dirs_removes_only_agh_stage_siblings(
    tmp_path: Path,
) -> None:
    pack_parent = tmp_path / ".agh-cache" / "packs" / "acme" / "onboarding"
    stale = pack_parent / ".agh-pull-stage-1.0.0-old"
    stale_file = stale / "instructions" / "AGENTS.md"
    stale_file.parent.mkdir(parents=True)
    stale_file.write_text("stale\n", encoding="utf-8")
    committed = pack_parent / "1.0.0"
    committed.mkdir()
    unrelated = pack_parent / "manual-stage"
    unrelated.mkdir()

    _cleanup_stale_cache_staging_dirs(tmp_path, manifest=_manifest())

    assert not stale.exists()
    assert committed.exists()
    assert unrelated.exists()


def test_cleanup_cache_stage_dirs_rejects_stage_like_path_outside_cache(
    tmp_path: Path,
) -> None:
    cache_dir = tmp_path / "workspace" / ".agh-cache" / "packs"
    outside_stage = tmp_path / "outside" / ".agh-pull-stage-1.0.0-evil"
    outside_stage.mkdir(parents=True)

    with pytest.raises(WorkspacePullError, match="outside AGH cache"):
        _cleanup_cache_stage_dirs([outside_stage], cache_dir=cache_dir)

    assert outside_stage.exists()


def test_cleanup_stale_cache_staging_dirs_unlinks_stage_symlink_without_target_delete(
    tmp_path: Path,
) -> None:
    pack_parent = tmp_path / ".agh-cache" / "packs" / "acme" / "onboarding"
    pack_parent.mkdir(parents=True)
    outside = tmp_path / "outside"
    outside.mkdir()
    outside_file = outside / "keep.txt"
    outside_file.write_text("keep\n", encoding="utf-8")
    stage_link = pack_parent / ".agh-pull-stage-1.0.0-link"
    stage_link.symlink_to(outside, target_is_directory=True)

    _cleanup_stale_cache_staging_dirs(tmp_path, manifest=_manifest())

    assert outside_file.read_text(encoding="utf-8") == "keep\n"
    assert not stage_link.is_symlink()


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
        / ".agh-cache"
        / "packs"
        / "acme"
        / "onboarding"
        / "1.0.0"
        / "instructions"
        / "AGENTS.md"
    )
    lock_path = tmp_path / ".agh" / "lock.toml"
    assert result.cache_dir == tmp_path / ".agh-cache" / "packs"
    assert result.lock_path == lock_path
    assert cached.read_text(encoding="utf-8") == content
    assert result.artifacts[0].cache_path == Path(
        ".agh-cache/packs/acme/onboarding/1.0.0/instructions/AGENTS.md"
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
    assert (
        'source = ".agh-cache/packs/acme/onboarding/1.0.0/instructions/AGENTS.md"'
        in lock
    )
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


def test_populate_cache_rejects_symlinked_cache_root(tmp_path: Path) -> None:
    outside = tmp_path / "outside"
    outside.mkdir()
    (tmp_path / ".agh-cache").symlink_to(outside, target_is_directory=True)

    with pytest.raises(WorkspacePullError, match="symlinked AGH cache"):
        populate_cache_and_write_lock(
            tmp_path, config=_config("http://127.0.0.1:9"), manifest=_manifest()
        )


def test_populate_cache_rejects_symlinked_cache_dir(tmp_path: Path) -> None:
    outside = tmp_path / "outside"
    outside.mkdir()
    cache_dir = tmp_path / ".agh-cache"
    cache_dir.mkdir()
    (cache_dir / "packs").symlink_to(outside, target_is_directory=True)

    with pytest.raises(WorkspacePullError, match="symlinked"):
        populate_cache_and_write_lock(
            tmp_path, config=_config("http://127.0.0.1:9"), manifest=_manifest()
        )


def test_populate_cache_rejects_symlinked_intermediate_cache_dir(
    tmp_path: Path,
) -> None:
    outside = tmp_path / "outside"
    outside.mkdir()
    cache_root = tmp_path / ".agh-cache" / "packs" / "acme"
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
    assert (
        'source = ".agh-cache/packs/acme/onboarding/1.0.0/instructions/AGENTS.md"'
        in lock
    )
    assert ".agh/nested-workspace/.agh-cache/packs" not in lock


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
