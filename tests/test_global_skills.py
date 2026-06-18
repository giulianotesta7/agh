"""Tests for global skill install/remove/lock/cache CLI functions."""

from __future__ import annotations

from pathlib import Path
from typing import Any
from unittest.mock import MagicMock

import pytest
from pytest import MonkeyPatch
from typer.testing import CliRunner

from agh.cli import global_skills as gs
from agh.cli.main import app as cli_app
from agh.cli.agent_integrations import (
    AgentPreferenceError,
    clear_global_skill_default_agent,
    global_skill_dir,
    read_global_skill_default_agent,
    write_global_skill_default_agent,
)
from agh.cli.config import AghConfig


@pytest.fixture
def agh_state(tmp_path: Path, monkeypatch: MonkeyPatch) -> Path:
    """Redirect AGH user state to a temp directory."""
    state = tmp_path / "agh-state"
    monkeypatch.setenv("XDG_STATE_HOME", str(state))
    return state


@pytest.fixture
def agent_home(tmp_path: Path, monkeypatch: MonkeyPatch) -> Path:
    """Redirect the user's home directory to a temp directory."""
    home = tmp_path / "home"
    home.mkdir()
    monkeypatch.setenv("HOME", str(home))
    return home


def _resolved(
    *,
    package_version_id: str = "pkgv_123",
    package_ref: str = "acme/commenting@1.2.0",
    checksum: str = "sha256:abc",
    artifact_path: str = "skills/reviewer/SKILL.md",
) -> dict[str, Any]:
    return {
        "package_version_id": package_version_id,
        "package_ref": package_ref,
        "checksum": checksum,
        "artifact_path": artifact_path,
        "download_url": f"/api/v1/packages/acme/commenting/versions/1.2.0/files/{artifact_path}",
    }


def _write_installed_skill_lock(target: Path) -> None:
    gs._write_lock(
        [{"name": "reviewer", "agent": "opencode", "target_path": str(target)}]
    )


def _cache_file(agh_state: Path) -> Path:
    return (
        agh_state
        / "agh/global-skills/cache/acme/commenting/1.2.0/skills/reviewer/SKILL.md"
    )


def _mock_skill_install(
    monkeypatch: MonkeyPatch, content: str = "# Skill content\n"
) -> None:
    monkeypatch.setattr(
        gs,
        "load_config",
        lambda: AghConfig("http://localhost:8912", "member@example.com", "t"),
    )
    monkeypatch.setattr(gs, "resolve_skill", lambda _api, _ref, _name: _resolved())
    monkeypatch.setattr(gs, "download_skill", lambda _r: content)


def test_global_skill_paths_use_xdg_state_home(agh_state: Path) -> None:
    assert gs.global_skill_cache_dir() == agh_state / "agh" / "global-skills" / "cache"
    assert (
        gs.global_skill_lock_path() == agh_state / "agh" / "global-skills" / "lock.toml"
    )
    assert (
        gs.global_skill_defaults_path()
        == agh_state / "agh" / "global-skills" / "defaults.toml"
    )


def test_global_skill_paths_fallback_to_local_state(
    tmp_path: Path, monkeypatch: MonkeyPatch
) -> None:
    home = tmp_path / "home"
    home.mkdir()
    monkeypatch.delenv("XDG_STATE_HOME", raising=False)
    monkeypatch.setenv("HOME", str(home))

    assert (
        gs.global_skill_cache_dir()
        == home / ".local" / "state" / "agh" / "global-skills" / "cache"
    )
    assert (
        gs.global_skill_lock_path()
        == home / ".local" / "state" / "agh" / "global-skills" / "lock.toml"
    )


def test_resolve_skill_calls_api(agh_state: Path) -> None:
    calls: list[tuple[str, str]] = []

    def fake_api(method: str, path: str, **kwargs: Any) -> dict[str, Any]:
        calls.append((method, path))
        return _resolved()

    result = gs.resolve_skill(fake_api, "acme/commenting@latest", "reviewer")

    assert result["package_ref"] == "acme/commenting@1.2.0"
    assert calls == [
        (
            "GET",
            "/skills:resolve?package_ref=acme%2Fcommenting%40latest&skill_name=reviewer",
        )
    ]


def test_download_skill_fetches_file_content(
    agh_state: Path, monkeypatch: MonkeyPatch
) -> None:
    monkeypatch.setattr(
        gs,
        "load_config",
        lambda: AghConfig(
            instance_url="http://localhost:8912",
            email="member@example.com",
            token="member-token",
        ),
    )

    captured: list[dict[str, Any]] = []

    class FakeResponse:
        def __init__(self, content: bytes) -> None:
            self._content = content

        def __enter__(self) -> "FakeResponse":
            return self

        def __exit__(self, *exc: object) -> None:
            return None

        def read(self) -> bytes:
            return self._content

    def fake_open(request: Any, timeout: int) -> FakeResponse:
        captured.append(
            {
                "url": request.full_url,
                "authorization": request.get_header("Authorization"),
                "method": request.get_method(),
            }
        )
        return FakeResponse(b"# Reviewer skill\n")

    monkeypatch.setattr(gs, "_NO_REDIRECT_OPENER", MagicMock(open=fake_open))

    resolved = {
        "download_url": "/api/v1/packages/acme/commenting/versions/1.2.0/files/skills/reviewer/SKILL.md"
    }
    content = gs.download_skill(resolved)

    assert content == "# Reviewer skill\n"
    assert captured == [
        {
            "url": "http://localhost:8912/api/v1/packages/acme/commenting/versions/1.2.0/files/skills/reviewer/SKILL.md",
            "authorization": "Bearer member-token",
            "method": "GET",
        }
    ]


def test_install_writes_target_lock_and_cache(
    agh_state: Path, agent_home: Path, monkeypatch: MonkeyPatch
) -> None:
    monkeypatch.setattr(
        gs,
        "load_config",
        lambda: AghConfig(
            instance_url="http://localhost:8912", email="member@example.com", token="t"
        ),
    )

    monkeypatch.setattr(
        gs, "resolve_skill", lambda _api, _ref, _name: _resolved(checksum="sha256:abc")
    )
    monkeypatch.setattr(gs, "download_skill", lambda _r: "# Skill content\n")

    result = gs.install_skill_global("opencode", "acme/commenting@latest", "reviewer")

    target = agent_home / ".config" / "opencode" / "skills" / "reviewer" / "SKILL.md"
    assert target.read_text(encoding="utf-8") == "# Skill content\n"
    assert result.target_path == target
    assert result.changed is True

    lock = gs.read_lock()
    assert len(lock) == 1
    entry = lock[0]
    assert entry["name"] == "reviewer"
    assert entry["agent"] == "opencode"
    assert entry["package_ref_requested"] == "acme/commenting@latest"
    assert entry["package_ref_resolved"] == "acme/commenting@1.2.0"
    assert entry["package_version_id"] == "pkgv_123"
    assert entry["checksum"] == "sha256:abc"
    assert entry["target_path"] == str(target)


def test_same_checksum_is_noop(
    agh_state: Path, agent_home: Path, monkeypatch: MonkeyPatch
) -> None:
    monkeypatch.setattr(
        gs,
        "load_config",
        lambda: AghConfig(
            instance_url="http://localhost:8912", email="member@example.com", token="t"
        ),
    )

    monkeypatch.setattr(
        gs, "resolve_skill", lambda _api, _ref, _name: _resolved(checksum="sha256:abc")
    )
    monkeypatch.setattr(gs, "download_skill", lambda _r: "# Skill content\n")

    gs.install_skill_global("opencode", "acme/commenting@latest", "reviewer")
    result = gs.install_skill_global("opencode", "acme/commenting@latest", "reviewer")

    assert result.changed is False
    lock = gs.read_lock()
    assert len(lock) == 1


def test_agh_owned_update_works(
    agh_state: Path, agent_home: Path, monkeypatch: MonkeyPatch
) -> None:
    monkeypatch.setattr(
        gs,
        "load_config",
        lambda: AghConfig(
            instance_url="http://localhost:8912", email="member@example.com", token="t"
        ),
    )

    checksums = ["sha256:abc", "sha256:def"]
    contents = ["# v1\n", "# v2\n"]
    call_count = 0

    def fake_resolve(_api: Any, _ref: str, _name: str) -> dict[str, Any]:
        nonlocal call_count
        resolved = _resolved(checksum=checksums[call_count])
        call_count += 1
        return resolved

    def fake_download(resolved: dict[str, Any]) -> str:
        return contents[checksums.index(resolved["checksum"])]

    monkeypatch.setattr(gs, "resolve_skill", fake_resolve)
    monkeypatch.setattr(gs, "download_skill", fake_download)

    gs.install_skill_global("opencode", "acme/commenting@latest", "reviewer")
    updated = gs.install_skill_global("opencode", "acme/commenting@latest", "reviewer")

    assert updated.changed is True
    target = agent_home / ".config" / "opencode" / "skills" / "reviewer" / "SKILL.md"
    assert target.read_text(encoding="utf-8") == "# v2\n"
    lock = gs.read_lock()
    assert len(lock) == 1
    assert lock[0]["checksum"] == "sha256:def"


def test_untracked_target_without_force_raises(
    agh_state: Path, agent_home: Path, monkeypatch: MonkeyPatch
) -> None:
    monkeypatch.setattr(
        gs,
        "load_config",
        lambda: AghConfig(
            instance_url="http://localhost:8912", email="member@example.com", token="t"
        ),
    )

    target = agent_home / ".config" / "opencode" / "skills" / "reviewer" / "SKILL.md"
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text("# Untracked\n", encoding="utf-8")

    monkeypatch.setattr(gs, "resolve_skill", lambda _api, _ref, _name: _resolved())
    monkeypatch.setattr(gs, "download_skill", lambda _r: "# Skill content\n")

    with pytest.raises(gs.GlobalSkillError, match="untracked"):
        gs.install_skill_global("opencode", "acme/commenting@latest", "reviewer")


def test_remove_deletes_target_and_lock(
    agh_state: Path, agent_home: Path, monkeypatch: MonkeyPatch
) -> None:
    monkeypatch.setattr(
        gs,
        "load_config",
        lambda: AghConfig(
            instance_url="http://localhost:8912", email="member@example.com", token="t"
        ),
    )

    monkeypatch.setattr(gs, "resolve_skill", lambda _api, _ref, _name: _resolved())
    monkeypatch.setattr(gs, "download_skill", lambda _r: "# Skill content\n")
    gs.install_skill_global("opencode", "acme/commenting@latest", "reviewer")

    gs.remove_skill_global("opencode", "reviewer")

    target = agent_home / ".config" / "opencode" / "skills" / "reviewer" / "SKILL.md"
    assert not target.exists()
    assert gs.read_lock() == []


def test_remove_rejects_tampered_target_path_outside_agent_dir(
    agh_state: Path, agent_home: Path, monkeypatch: MonkeyPatch
) -> None:
    _mock_skill_install(monkeypatch)
    gs.install_skill_global("opencode", "acme/commenting@latest", "reviewer")

    outside = agent_home / "outside" / "SKILL.md"
    outside.parent.mkdir(parents=True)
    outside.write_text("# Do not delete\n", encoding="utf-8")
    entries = gs.read_lock()
    entries[0]["target_path"] = str(outside)
    gs._write_lock(entries)

    with pytest.raises(gs.GlobalSkillError, match="does not match expected"):
        gs.remove_skill_global("opencode", "reviewer")

    assert outside.read_text(encoding="utf-8") == "# Do not delete\n"
    expected = agent_home / ".config" / "opencode" / "skills" / "reviewer" / "SKILL.md"
    assert expected.exists()


def test_remove_keeps_target_when_lock_update_fails(
    agh_state: Path, agent_home: Path, monkeypatch: MonkeyPatch
) -> None:
    _mock_skill_install(monkeypatch)
    gs.install_skill_global("opencode", "acme/commenting@latest", "reviewer")

    monkeypatch.setattr(
        gs, "_write_lock", lambda _entries: (_ for _ in ()).throw(OSError("disk full"))
    )

    with pytest.raises(gs.GlobalSkillError, match="target was left untouched"):
        gs.remove_skill_global("opencode", "reviewer")

    target = agent_home / ".config" / "opencode" / "skills" / "reviewer" / "SKILL.md"
    assert target.read_text(encoding="utf-8") == "# Skill content\n"
    assert len(gs.read_lock()) == 1


def test_remove_reports_recovery_when_delete_fails_after_lock_update(
    agh_state: Path, agent_home: Path, monkeypatch: MonkeyPatch
) -> None:
    _mock_skill_install(monkeypatch)
    gs.install_skill_global("opencode", "acme/commenting@latest", "reviewer")

    target = agent_home / ".config" / "opencode" / "skills" / "reviewer" / "SKILL.md"
    original_unlink = Path.unlink

    def failing_target_unlink(self: Path, *args: Any, **kwargs: Any) -> None:
        if self == target:
            raise OSError("permission denied")
        original_unlink(self, *args, **kwargs)

    monkeypatch.setattr(Path, "unlink", failing_target_unlink)

    with pytest.raises(
        gs.GlobalSkillError, match="lock updated, but failed to remove target"
    ) as exc_info:
        gs.remove_skill_global("opencode", "reviewer")

    assert "delete it manually or reinstall with --force" in str(exc_info.value)
    assert target.read_text(encoding="utf-8") == "# Skill content\n"
    assert gs.read_lock() == []


def test_list_installed_skills_filters_by_agent(
    agh_state: Path, agent_home: Path, monkeypatch: MonkeyPatch
) -> None:
    monkeypatch.setattr(
        gs,
        "load_config",
        lambda: AghConfig(
            instance_url="http://localhost:8912", email="member@example.com", token="t"
        ),
    )

    monkeypatch.setattr(gs, "resolve_skill", lambda _api, _ref, _name: _resolved())
    monkeypatch.setattr(gs, "download_skill", lambda _r: "# content\n")
    gs.install_skill_global("opencode", "acme/commenting@latest", "reviewer")
    gs.install_skill_global("claude", "acme/commenting@latest", "reviewer")

    opencode_skills = gs.list_installed_skills("opencode")
    assert len(opencode_skills) == 1
    assert opencode_skills[0]["agent"] == "opencode"


def test_global_skill_dir_maps_agents(agent_home: Path) -> None:
    assert (
        global_skill_dir("opencode") == agent_home / ".config" / "opencode" / "skills"
    )
    assert global_skill_dir("claude") == agent_home / ".claude" / "skills"


def test_global_skill_default_agent_roundtrip(agh_state: Path) -> None:
    assert read_global_skill_default_agent() is None

    write_global_skill_default_agent("claude")
    assert read_global_skill_default_agent() == "claude"

    clear_global_skill_default_agent()
    assert read_global_skill_default_agent() is None


def test_global_skill_default_clear_is_idempotent(agh_state: Path) -> None:
    clear_global_skill_default_agent()
    assert read_global_skill_default_agent() is None


def test_untracked_target_with_force_overwrites(
    agh_state: Path, agent_home: Path, monkeypatch: MonkeyPatch
) -> None:
    monkeypatch.setattr(
        gs,
        "load_config",
        lambda: AghConfig(
            instance_url="http://localhost:8912", email="member@example.com", token="t"
        ),
    )

    target = agent_home / ".config" / "opencode" / "skills" / "reviewer" / "SKILL.md"
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text("# Untracked\n", encoding="utf-8")

    monkeypatch.setattr(gs, "resolve_skill", lambda _api, _ref, _name: _resolved())
    monkeypatch.setattr(gs, "download_skill", lambda _r: "# Skill content\n")

    result = gs.install_skill_global(
        "opencode", "acme/commenting@latest", "reviewer", force=True
    )

    assert result.changed is True
    assert target.read_text(encoding="utf-8") == "# Skill content\n"


def test_different_package_same_skill_conflicts(
    agh_state: Path, agent_home: Path, monkeypatch: MonkeyPatch
) -> None:
    monkeypatch.setattr(
        gs,
        "load_config",
        lambda: AghConfig(
            instance_url="http://localhost:8912", email="member@example.com", token="t"
        ),
    )

    monkeypatch.setattr(
        gs,
        "resolve_skill",
        lambda _api, ref, _name: _resolved(
            package_ref=ref.replace("@latest", "@1.0.0")
        ),
    )
    monkeypatch.setattr(gs, "download_skill", lambda _r: "# content\n")
    gs.install_skill_global("opencode", "acme/commenting@latest", "reviewer")

    monkeypatch.setattr(
        gs,
        "resolve_skill",
        lambda _api, ref, _name: _resolved(
            package_ref="acme/other@2.0.0",
            package_version_id="pkgv_999",
            checksum="sha256:xyz",
        ),
    )

    with pytest.raises(gs.GlobalSkillError, match="already installed"):
        gs.install_skill_global("opencode", "acme/other@latest", "reviewer")


def test_remove_missing_skill_raises(agh_state: Path) -> None:
    with pytest.raises(gs.GlobalSkillError, match="not installed"):
        gs.remove_skill_global("opencode", "reviewer")


def test_global_skill_dir_rejects_invalid_agent() -> None:
    with pytest.raises(Exception):
        global_skill_dir("both")


@pytest.mark.parametrize(
    "bad_name",
    [
        "../escape",
        "escape/leaf",
        "..",
        "a\x00b",
        "",
        "UPPER",
        "under_score",
    ],
)
def test_install_rejects_path_traversal_in_skill_name(
    agh_state: Path, monkeypatch: MonkeyPatch, bad_name: str
) -> None:
    monkeypatch.setattr(
        gs,
        "load_config",
        lambda: AghConfig(
            instance_url="http://localhost:8912", email="member@example.com", token="t"
        ),
    )
    monkeypatch.setattr(gs, "resolve_skill", lambda _api, _ref, _name: _resolved())

    with pytest.raises(gs.GlobalSkillError, match="invalid skill name"):
        gs.install_skill_global("opencode", "acme/commenting@latest", bad_name)


def test_install_rejects_symlinked_target_parent(
    agh_state: Path, agent_home: Path, monkeypatch: MonkeyPatch
) -> None:
    monkeypatch.setattr(
        gs,
        "load_config",
        lambda: AghConfig(
            instance_url="http://localhost:8912", email="member@example.com", token="t"
        ),
    )
    monkeypatch.setattr(gs, "resolve_skill", lambda _api, _ref, _name: _resolved())
    monkeypatch.setattr(gs, "download_skill", lambda _r: "# content\n")

    skills_dir = agent_home / ".config" / "opencode" / "skills"
    skills_dir.mkdir(parents=True, exist_ok=True)
    symlink_target = agent_home / "evil"
    symlink_target.mkdir()
    (skills_dir / "reviewer").symlink_to(symlink_target)

    with pytest.raises(gs.GlobalSkillError, match="symlinked"):
        gs.install_skill_global("opencode", "acme/commenting@latest", "reviewer")


def test_install_rejects_symlinked_target(
    agh_state: Path, agent_home: Path, monkeypatch: MonkeyPatch
) -> None:
    monkeypatch.setattr(
        gs,
        "load_config",
        lambda: AghConfig(
            instance_url="http://localhost:8912", email="member@example.com", token="t"
        ),
    )
    monkeypatch.setattr(gs, "resolve_skill", lambda _api, _ref, _name: _resolved())
    monkeypatch.setattr(gs, "download_skill", lambda _r: "# content\n")

    target = agent_home / ".config" / "opencode" / "skills" / "reviewer" / "SKILL.md"
    target.parent.mkdir(parents=True, exist_ok=True)
    target.symlink_to(agent_home / "evil")

    with pytest.raises(gs.GlobalSkillError, match="symlinked"):
        gs.install_skill_global("opencode", "acme/commenting@latest", "reviewer")


def test_install_rejects_symlinked_native_skill_ancestor_above_boundary(
    agh_state: Path, agent_home: Path, monkeypatch: MonkeyPatch
) -> None:
    _mock_skill_install(monkeypatch, "# content\n")

    config_dir = agent_home / ".config"
    config_dir.mkdir()
    outside_opencode = agent_home / "outside-opencode"
    outside_opencode.mkdir()
    (config_dir / "opencode").symlink_to(outside_opencode, target_is_directory=True)

    with pytest.raises(gs.GlobalSkillError, match="symlinked path component"):
        gs.install_skill_global("opencode", "acme/commenting@latest", "reviewer")

    outside_target = outside_opencode / "skills" / "reviewer" / "SKILL.md"
    assert not outside_target.exists()
    assert gs.read_lock() == []


def test_install_rejects_symlinked_cache_parent(
    agh_state: Path, agent_home: Path, monkeypatch: MonkeyPatch
) -> None:
    monkeypatch.setattr(
        gs,
        "load_config",
        lambda: AghConfig(
            instance_url="http://localhost:8912", email="member@example.com", token="t"
        ),
    )
    monkeypatch.setattr(gs, "resolve_skill", lambda _api, _ref, _name: _resolved())
    monkeypatch.setattr(gs, "download_skill", lambda _r: "# content\n")

    cache_parent = (
        agh_state
        / "agh"
        / "global-skills"
        / "cache"
        / "acme"
        / "commenting"
        / "1.2.0"
        / "skills"
    )
    cache_parent.mkdir(parents=True, exist_ok=True)
    symlink_target = agh_state / "evil-cache"
    symlink_target.mkdir()
    (cache_parent / "reviewer").symlink_to(symlink_target)

    with pytest.raises(gs.GlobalSkillError, match="symlinked"):
        gs.install_skill_global("opencode", "acme/commenting@latest", "reviewer")


def test_install_rejects_symlinked_agh_state_ancestor(
    agh_state: Path, agent_home: Path, monkeypatch: MonkeyPatch
) -> None:
    _mock_skill_install(monkeypatch, "# content\n")
    outside_state = agh_state / "outside-state"
    outside_state.mkdir(parents=True)
    (agh_state / "agh").symlink_to(outside_state, target_is_directory=True)

    with pytest.raises(gs.GlobalSkillError, match="symlinked path component"):
        gs.install_skill_global("opencode", "acme/commenting@latest", "reviewer")

    target = agent_home / ".config/opencode/skills/reviewer/SKILL.md"
    assert not target.exists()
    assert not (outside_state / "global-skills/cache").exists()
    assert not (outside_state / "global-skills/lock.toml").exists()


def test_remove_rejects_symlinked_target(
    agh_state: Path, agent_home: Path, monkeypatch: MonkeyPatch
) -> None:
    monkeypatch.setattr(
        gs,
        "load_config",
        lambda: AghConfig(
            instance_url="http://localhost:8912", email="member@example.com", token="t"
        ),
    )
    monkeypatch.setattr(gs, "resolve_skill", lambda _api, _ref, _name: _resolved())
    monkeypatch.setattr(gs, "download_skill", lambda _r: "# content\n")
    gs.install_skill_global("opencode", "acme/commenting@latest", "reviewer")

    target = agent_home / ".config" / "opencode" / "skills" / "reviewer" / "SKILL.md"
    target.unlink()
    target.symlink_to(agent_home / "evil")

    with pytest.raises(gs.GlobalSkillError, match="symlinked"):
        gs.remove_skill_global("opencode", "reviewer")


def test_remove_rejects_symlinked_native_skill_ancestor_above_boundary(
    agh_state: Path, agent_home: Path
) -> None:
    config_dir = agent_home / ".config"
    config_dir.mkdir()
    outside_opencode = agent_home / "outside-opencode"
    outside_target = outside_opencode / "skills" / "reviewer" / "SKILL.md"
    outside_target.parent.mkdir(parents=True)
    outside_target.write_text("# Do not delete\n", encoding="utf-8")
    (config_dir / "opencode").symlink_to(outside_opencode, target_is_directory=True)

    target = agent_home / ".config" / "opencode" / "skills" / "reviewer" / "SKILL.md"
    _write_installed_skill_lock(target)

    with pytest.raises(gs.GlobalSkillError, match="symlinked path component"):
        gs.remove_skill_global("opencode", "reviewer")

    assert outside_target.read_text(encoding="utf-8") == "# Do not delete\n"
    assert len(gs.read_lock()) == 1


def test_install_rolls_back_partial_writes_on_lock_failure(
    agh_state: Path, agent_home: Path, monkeypatch: MonkeyPatch
) -> None:
    monkeypatch.setattr(
        gs,
        "load_config",
        lambda: AghConfig(
            instance_url="http://localhost:8912", email="member@example.com", token="t"
        ),
    )
    monkeypatch.setattr(gs, "resolve_skill", lambda _api, _ref, _name: _resolved())
    monkeypatch.setattr(gs, "download_skill", lambda _r: "# content\n")

    calls = 0

    def failing_write_lock(_entries: list[dict[str, Any]]) -> None:
        nonlocal calls
        calls += 1
        raise OSError("disk full")

    monkeypatch.setattr(gs, "_write_lock", failing_write_lock)

    with pytest.raises(OSError, match="disk full"):
        gs.install_skill_global("opencode", "acme/commenting@latest", "reviewer")

    target = agent_home / ".config" / "opencode" / "skills" / "reviewer" / "SKILL.md"
    cache = _cache_file(agh_state)
    assert not target.exists()
    assert not cache.exists()
    assert gs.read_lock() == []


def test_update_restores_existing_skill_when_lock_write_fails(
    agh_state: Path, agent_home: Path, monkeypatch: MonkeyPatch
) -> None:
    _mock_skill_install(monkeypatch, "# v1\n")
    gs.install_skill_global("opencode", "acme/commenting@latest", "reviewer")
    target = agent_home / ".config" / "opencode" / "skills" / "reviewer" / "SKILL.md"
    cache = _cache_file(agh_state)

    monkeypatch.setattr(
        gs, "resolve_skill", lambda _api, _ref, _name: _resolved(checksum="sha256:def")
    )
    monkeypatch.setattr(gs, "download_skill", lambda _r: "# v2\n")

    def failing_write_lock(_entries: list[dict[str, Any]]) -> None:
        raise OSError("disk full")

    monkeypatch.setattr(gs, "_write_lock", failing_write_lock)

    with pytest.raises(OSError, match="disk full"):
        gs.install_skill_global("opencode", "acme/commenting@latest", "reviewer")

    assert target.read_text(encoding="utf-8") == "# v1\n"
    assert cache.read_text(encoding="utf-8") == "# v1\n"
    lock = gs.read_lock()
    assert len(lock) == 1
    assert lock[0]["checksum"] == "sha256:abc"

    original_atomic_write = gs._atomic_write_text

    def failing_restore(path: Path, content: str) -> None:
        if path == target and content == "# v1\n":
            raise OSError("restore denied")
        original_atomic_write(path, content)

    monkeypatch.setattr(gs, "_atomic_write_text", failing_restore)

    with pytest.raises(
        gs.GlobalSkillError, match="rollback restore failed.*reinstall with --force"
    ):
        gs.install_skill_global("opencode", "acme/commenting@latest", "reviewer")


def test_list_installed_skills_rejects_path_traversal_in_agent(
    agh_state: Path,
) -> None:
    with pytest.raises(gs.GlobalSkillError, match="invalid agent"):
        gs.list_installed_skills("../escape")


def test_list_installed_skills_rejects_malformed_lock(agh_state: Path) -> None:
    lock = agh_state / "agh" / "global-skills" / "lock.toml"
    lock.parent.mkdir(parents=True, exist_ok=True)
    lock.write_text('skills = "not a list"\n', encoding="utf-8")

    with pytest.raises(
        gs.GlobalSkillError, match=f"invalid lock file {lock}"
    ) as exc_info:
        gs.list_installed_skills("opencode")

    assert f"Fix or delete {lock}" in str(exc_info.value)


def test_write_global_skill_default_rejects_invalid_agent() -> None:
    with pytest.raises(AgentPreferenceError):
        write_global_skill_default_agent("invalid-agent")


def test_read_global_skill_default_rejects_corrupt_toml(agh_state: Path) -> None:
    defaults = agh_state / "agh" / "global-skills" / "defaults.toml"
    defaults.parent.mkdir(parents=True, exist_ok=True)
    defaults.write_text("not valid toml [[[", encoding="utf-8")

    with pytest.raises(AgentPreferenceError):
        read_global_skill_default_agent()


def test_read_global_skill_default_rejects_non_directory_parent(
    agh_state: Path,
) -> None:
    defaults_parent = agh_state / "agh" / "global-skills"
    defaults_parent.parent.mkdir(parents=True, exist_ok=True)
    defaults_parent.write_text("not a directory", encoding="utf-8")

    with pytest.raises(AgentPreferenceError, match="non-directory"):
        read_global_skill_default_agent()


def test_clear_global_skill_default_rejects_non_directory_parent(
    agh_state: Path,
) -> None:
    defaults_parent = agh_state / "agh" / "global-skills"
    defaults_parent.parent.mkdir(parents=True, exist_ok=True)
    defaults_parent.write_text("not a directory", encoding="utf-8")

    with pytest.raises(AgentPreferenceError, match="non-directory"):
        clear_global_skill_default_agent()


def test_read_global_skill_default_rejects_invalid_utf8(agh_state: Path) -> None:
    defaults = agh_state / "agh" / "global-skills" / "defaults.toml"
    defaults.parent.mkdir(parents=True, exist_ok=True)
    defaults.write_bytes(b"[skills]\ndefault_agent = \xff\n")

    with pytest.raises(AgentPreferenceError):
        read_global_skill_default_agent()


def test_read_global_skill_default_rejects_symlinked_defaults(
    agh_state: Path,
) -> None:
    outside = agh_state / "outside-defaults.toml"
    outside.parent.mkdir(parents=True, exist_ok=True)
    outside.write_text('[skills]\ndefault_agent = "claude"\n', encoding="utf-8")
    defaults = agh_state / "agh" / "global-skills" / "defaults.toml"
    defaults.parent.mkdir(parents=True, exist_ok=True)
    defaults.symlink_to(outside)

    with pytest.raises(AgentPreferenceError, match="symlinked"):
        read_global_skill_default_agent()


def test_clear_global_skill_default_rejects_symlinked_defaults(
    agh_state: Path,
) -> None:
    outside = agh_state / "outside-defaults.toml"
    outside.parent.mkdir(parents=True, exist_ok=True)
    outside.write_text('[skills]\ndefault_agent = "claude"\n', encoding="utf-8")
    defaults = agh_state / "agh" / "global-skills" / "defaults.toml"
    defaults.parent.mkdir(parents=True, exist_ok=True)
    defaults.symlink_to(outside)

    with pytest.raises(AgentPreferenceError, match="symlinked"):
        clear_global_skill_default_agent()


def test_read_global_skill_default_rejects_symlinked_parent(
    agh_state: Path,
) -> None:
    outside_parent = agh_state / "outside-defaults"
    outside_parent.mkdir(parents=True)
    defaults_parent = agh_state / "agh" / "global-skills"
    defaults_parent.parent.mkdir(parents=True, exist_ok=True)
    defaults_parent.symlink_to(outside_parent, target_is_directory=True)

    with pytest.raises(AgentPreferenceError, match="symlinked"):
        read_global_skill_default_agent()


def test_clear_global_skill_default_rejects_symlinked_parent(
    agh_state: Path,
) -> None:
    outside_parent = agh_state / "outside-defaults"
    outside_parent.mkdir(parents=True)
    defaults_parent = agh_state / "agh" / "global-skills"
    defaults_parent.parent.mkdir(parents=True, exist_ok=True)
    defaults_parent.symlink_to(outside_parent, target_is_directory=True)

    with pytest.raises(AgentPreferenceError, match="symlinked"):
        clear_global_skill_default_agent()


def test_write_global_skill_default_rejects_non_directory_parent(
    agh_state: Path,
) -> None:
    defaults_parent = agh_state / "agh" / "global-skills"
    defaults_parent.parent.mkdir(parents=True, exist_ok=True)
    defaults_parent.write_text("not a directory", encoding="utf-8")

    with pytest.raises(AgentPreferenceError, match="non-directory"):
        write_global_skill_default_agent("opencode")


def test_write_global_skill_default_rejects_symlinked_parent(agh_state: Path) -> None:
    defaults_parent = agh_state / "agh" / "global-skills"
    defaults_parent.parent.mkdir(parents=True, exist_ok=True)
    outside_parent = agh_state / "outside-defaults"
    outside_parent.mkdir()
    defaults_parent.symlink_to(outside_parent, target_is_directory=True)

    with pytest.raises(AgentPreferenceError, match="symlinked"):
        write_global_skill_default_agent("opencode")


def test_skill_list_shows_available_skills(monkeypatch: MonkeyPatch) -> None:
    from agh.cli import main as cli_main

    monkeypatch.setattr(
        cli_main,
        "_api_request",
        lambda _method, _path: {
            "skills": [
                {
                    "skill_name": "reviewer",
                    "collection_name": "Acme Skills",
                    "package_ref": "acme/commenting@latest",
                    "resolved_ref": "acme/commenting@1.2.0",
                    "description": "Review comments",
                }
            ]
        },
    )

    result = CliRunner().invoke(cli_app, ["skill", "list"])

    assert result.exit_code == 0, result.stdout
    assert "reviewer" in result.stdout
    assert "Acme Skills" in result.stdout
    assert "acme/commenting@latest" in result.stdout


def test_skill_help_documents_global_paths_and_agent_default() -> None:
    runner = CliRunner()

    skill_help = runner.invoke(cli_app, ["skill", "--help"])
    install_help = runner.invoke(cli_app, ["skill", "install", "--help"])
    agent_help = runner.invoke(cli_app, ["skill", "agent", "--help"])
    select_help = runner.invoke(cli_app, ["skill", "agent", "select", "--help"])

    assert skill_help.exit_code == 0, skill_help.stdout
    assert (
        "Discover, install, and remove collection-backed global skills."
        in skill_help.stdout
    )
    assert "Claude: ~/.claude/skills" in skill_help.stdout
    assert "OpenCode: ~/.config/opencode/skills" in skill_help.stdout
    assert "Select the agent for global skills:" in skill_help.stdout

    assert install_help.exit_code == 0, install_help.stdout
    assert (
        "Install a collection-backed skill into the selected global agent."
        in install_help.stdout
    )
    assert "Use --agent to choose claude or opencode." in install_help.stdout
    assert "Overwrite an untracked target skill file." in install_help.stdout

    assert agent_help.exit_code == 0, agent_help.stdout
    assert (
        "Manage the saved default agent for global skill commands." in agent_help.stdout
    )
    assert "show" in agent_help.stdout
    assert "select" in agent_help.stdout
    assert "clear" in agent_help.stdout

    assert select_help.exit_code == 0, select_help.stdout
    assert "Default agent target: claude or opencode." in select_help.stdout


def test_skill_install_uses_agent_option(
    agh_state: Path, agent_home: Path, monkeypatch: MonkeyPatch
) -> None:
    from agh.cli import main as cli_main

    target = agent_home / ".config" / "opencode" / "skills" / "reviewer" / "SKILL.md"
    calls: list[tuple[str, str, str, bool]] = []

    def fake_install(
        agent: str, ref: str, name: str, *, force: bool
    ) -> gs.InstallResult:
        calls.append((agent, ref, name, force))
        return gs.InstallResult(target_path=target, changed=True)

    monkeypatch.setattr(
        cli_main.global_skills_module,
        "install_skill_global",
        fake_install,
    )

    result = CliRunner().invoke(
        cli_app,
        [
            "skill",
            "install",
            "acme/commenting@latest",
            "reviewer",
            "--agent",
            "opencode",
            "--force",
        ],
    )

    assert result.exit_code == 0, result.stdout
    assert calls == [("opencode", "acme/commenting@latest", "reviewer", True)]
    assert "Installed reviewer" in result.stdout
    assert "OpenCode" in result.stdout


def test_skill_remove_uses_default_agent(
    agh_state: Path, agent_home: Path, monkeypatch: MonkeyPatch
) -> None:
    from agh.cli import main as cli_main

    write_global_skill_default_agent("claude")
    removed: list[tuple[str, str]] = []

    def fake_remove(agent: str, name: str) -> Path:
        removed.append((agent, name))
        return agent_home / ".claude" / "skills" / name / "SKILL.md"

    monkeypatch.setattr(
        cli_main.global_skills_module, "remove_skill_global", fake_remove
    )

    result = CliRunner().invoke(cli_app, ["skill", "remove", "reviewer"])

    assert result.exit_code == 0, result.stdout
    assert removed == [("claude", "reviewer")]
    assert "Removed reviewer" in result.stdout


def test_skill_installed_lists_lock_entries(monkeypatch: MonkeyPatch) -> None:
    from agh.cli import main as cli_main

    monkeypatch.setattr(
        cli_main.global_skills_module,
        "list_installed_skills",
        lambda _agent: [
            {
                "name": "reviewer",
                "package_ref_resolved": "acme/commenting@1.2.0",
                "checksum": "sha256:abc",
            }
        ],
    )

    result = CliRunner().invoke(cli_app, ["skill", "installed", "--agent", "opencode"])

    assert result.exit_code == 0, result.stdout
    assert "reviewer" in result.stdout
    assert "acme/commenting@1.2.0" in result.stdout
    assert "sha256:abc" in result.stdout


def test_skill_agent_show_select_and_clear_roundtrip(agh_state: Path) -> None:
    runner = CliRunner()

    show_empty = runner.invoke(cli_app, ["skill", "agent", "show"])
    assert show_empty.exit_code == 0, show_empty.stdout
    assert "not set" in show_empty.stdout

    select = runner.invoke(cli_app, ["skill", "agent", "select", "opencode"])
    assert select.exit_code == 0, select.stdout
    assert "OpenCode" in select.stdout

    show_set = runner.invoke(cli_app, ["skill", "agent", "show"])
    assert show_set.exit_code == 0, show_set.stdout
    assert "OpenCode" in show_set.stdout

    clear = runner.invoke(cli_app, ["skill", "agent", "clear"])
    assert clear.exit_code == 0, clear.stdout
    assert "Cleared" in clear.stdout


def test_skill_agent_prompt_saves_default(
    agh_state: Path, monkeypatch: MonkeyPatch
) -> None:
    from agh.cli import main as cli_main

    monkeypatch.setattr(cli_main, "_stdin_is_interactive", lambda: True)

    result = CliRunner().invoke(cli_app, ["skill", "installed"], input="1\ny\n")

    assert result.exit_code == 0, result.stdout
    assert "Select the agent for global skills:" in result.stdout
    assert "Save this as the default agent for global skills?" in result.stdout
    assert read_global_skill_default_agent() == "claude"


def test_skill_agent_prompt_rejects_non_tty(
    agh_state: Path, monkeypatch: MonkeyPatch
) -> None:
    from agh.cli import main as cli_main

    monkeypatch.setattr(cli_main, "_stdin_is_interactive", lambda: False)

    result = CliRunner().invoke(cli_app, ["skill", "installed"])

    assert result.exit_code == 2
    assert "no default global skill agent" in result.stdout
