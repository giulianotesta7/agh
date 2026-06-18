"""Tests for global skill install/remove/lock/cache CLI functions."""

from __future__ import annotations

from pathlib import Path
from typing import Any
from unittest.mock import MagicMock

import pytest
from pytest import MonkeyPatch

from agh.cli import global_skills as gs
from agh.cli.agent_integrations import global_skill_dir
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
    cache = (
        agh_state
        / "agh"
        / "global-skills"
        / "cache"
        / "acme"
        / "commenting"
        / "1.2.0"
        / "skills"
        / "reviewer"
        / "SKILL.md"
    )
    assert not target.exists()
    assert not cache.exists()
    assert gs.read_lock() == []


def test_list_installed_skills_rejects_path_traversal_in_agent(
    agh_state: Path,
) -> None:
    with pytest.raises(gs.GlobalSkillError, match="invalid agent"):
        gs.list_installed_skills("../escape")
