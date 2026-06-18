"""Global skill install, cache, lock, and removal for AGH CLI."""

from __future__ import annotations

from contextlib import suppress
from dataclasses import dataclass
from datetime import UTC, datetime
import os
from pathlib import Path
import tempfile
from typing import Any
from urllib.parse import quote
import urllib.request
import urllib.error

from agh.cli.agent_integrations import global_skill_dir
from agh.cli.config import load_config
from agh.common.validation import is_valid_slug, parse_package_ref


class GlobalSkillError(RuntimeError):
    """Raised for global skill install/remove failures."""

    def __init__(self, message: str, *, code: int = 1) -> None:
        super().__init__(message)
        self.code = code


class _NoRedirectHandler(urllib.request.HTTPRedirectHandler):
    """Reject redirects so Bearer tokens are never forwarded."""

    def redirect_request(self, req, fp, code, msg, headers, newurl):  # type: ignore[no-untyped-def]
        return None


_NO_REDIRECT_OPENER = urllib.request.build_opener(_NoRedirectHandler)


@dataclass(frozen=True)
class InstallResult:
    target_path: Path
    changed: bool


def _agh_state_dir() -> Path:
    xdg = _env_path("XDG_STATE_HOME")
    if xdg is not None:
        return xdg / "agh"
    return Path.home() / ".local" / "state" / "agh"


def _env_path(name: str) -> Path | None:
    value = __import__("os").environ.get(name, "").strip()
    if value:
        return Path(value).expanduser()
    return None


def global_skill_cache_dir() -> Path:
    """Return the AGH global skill cache directory."""
    return _agh_state_dir() / "global-skills" / "cache"


def global_skill_lock_path() -> Path:
    """Return the AGH global skill lock file path."""
    return _agh_state_dir() / "global-skills" / "lock.toml"


def global_skill_defaults_path() -> Path:
    """Return the AGH global skill defaults file path."""
    return _agh_state_dir() / "global-skills" / "defaults.toml"


def _validate_path_component(value: str, label: str) -> None:
    """Reject path traversal and invalid slugs in a filesystem path component."""
    if not value or "/" in value or ".." in value or "\0" in value:
        raise GlobalSkillError(f"invalid {label}: {value!r}")
    if not is_valid_slug(value):
        raise GlobalSkillError(f"invalid {label}: {value!r}")


def _target_path(agent: str, skill_name: str) -> Path:
    return global_skill_dir(agent) / skill_name / "SKILL.md"


def _cache_path(package_ref: str, skill_name: str) -> Path:
    parsed = parse_package_ref(package_ref, allow_latest=False)
    return (
        global_skill_cache_dir()
        / parsed.domain
        / parsed.name
        / parsed.version
        / "skills"
        / skill_name
        / "SKILL.md"
    )


def _now_iso() -> str:
    return datetime.now(UTC).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def read_lock() -> list[dict[str, Any]]:
    """Read the global skill lock file."""
    path = global_skill_lock_path()
    if not path.exists():
        return []
    recovery = f"Fix or delete {path}, then reinstall global skills."
    try:
        data = __import__("tomllib").loads(path.read_text(encoding="utf-8"))
    except Exception as exc:
        raise GlobalSkillError(
            f"failed to read lock file {path}: {exc}. {recovery}"
        ) from exc
    if not isinstance(data, dict):
        return []
    skills = data.get("skills")
    if skills is None:
        return []
    if not isinstance(skills, list):
        raise GlobalSkillError(
            f"invalid lock file {path}: skills must be a list. {recovery}"
        )
    entries: list[dict[str, Any]] = []
    for index, entry in enumerate(skills):
        if not isinstance(entry, dict):
            raise GlobalSkillError(
                f"invalid lock file {path}: skills[{index}] must be a table. {recovery}"
            )
        entries.append(dict(entry))
    return entries


def _write_lock(entries: list[dict[str, Any]]) -> None:
    path = global_skill_lock_path()
    _reject_symlinked_existing_prefixes(path, action="write lock")
    path.parent.mkdir(parents=True, exist_ok=True)
    lines: list[str] = []
    for entry in entries:
        lines.append("[[skills]]")
        for key, value in entry.items():
            if isinstance(value, str):
                lines.append(f'{key} = "{_escape_toml(value)}"')
            elif isinstance(value, bool):
                lines.append(f"{key} = {str(value).lower()}")
            elif isinstance(value, int):
                lines.append(f"{key} = {value}")
            else:
                lines.append(f'{key} = "{_escape_toml(str(value))}"')
        lines.append("")
    _atomic_write_text(path, "\n".join(lines))


def _escape_toml(value: str) -> str:
    return value.replace("\\", "\\\\").replace('"', '\\"')


def _atomic_write_text(path: Path, content: str) -> None:
    """Write content to path atomically via a temporary file."""
    fd, temp_name = tempfile.mkstemp(
        prefix=f".{path.name}.", suffix=".tmp", dir=path.parent
    )
    temp_path = Path(temp_name)
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as handle:
            handle.write(content)
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(temp_path, path)
    except Exception:
        with suppress(FileNotFoundError):
            temp_path.unlink()
        raise


def _find_entry(
    entries: list[dict[str, Any]], agent: str, skill_name: str
) -> dict[str, Any] | None:
    for entry in entries:
        if entry.get("agent") == agent and entry.get("name") == skill_name:
            return entry
    return None


def configure_api_request(api_request: Any) -> None:
    """Bind the CLI's API requester so global skill flows can reach the server."""
    global _api_request
    _api_request = api_request


def resolve_skill(
    api_request: Any, package_ref: str, skill_name: str
) -> dict[str, Any]:
    """Resolve a collection skill to concrete package version metadata."""
    query = (
        f"/skills:resolve?package_ref={quote(package_ref, safe='')}&"
        f"skill_name={quote(skill_name, safe='')}"
    )
    return api_request("GET", query)


def download_skill(resolved: dict[str, Any]) -> str:
    """Download SKILL.md content for a resolved skill."""
    config = load_config()
    download_url = str(resolved.get("download_url", ""))
    if not download_url:
        raise GlobalSkillError("resolved skill missing download_url")
    full_url = f"{config.instance_url}{download_url}"
    request = urllib.request.Request(
        full_url,
        headers={
            "Authorization": f"Bearer {config.token}",
            "Accept": "text/plain",
        },
        method="GET",
    )
    try:
        with _NO_REDIRECT_OPENER.open(request, timeout=10) as response:  # noqa: S310 - configured AGH URL
            return response.read().decode("utf-8")
    except urllib.error.HTTPError as exc:
        raise GlobalSkillError(f"download failed: HTTP {exc.code}") from exc
    except urllib.error.URLError as exc:
        raise GlobalSkillError(f"download failed: {exc.reason}") from exc
    except TimeoutError as exc:
        raise GlobalSkillError(f"download failed: {exc}") from exc


def install_skill_global(
    agent: str,
    package_ref: str,
    skill_name: str,
    *,
    force: bool = False,
) -> InstallResult:
    """Install a collection skill into the selected agent's native global path."""
    _validate_path_component(skill_name, "skill name")
    resolved = resolve_skill(_api_request, package_ref, skill_name)
    return _install_resolved(agent, package_ref, resolved, skill_name, force=force)


def _api_request(method: str, path: str, **kwargs: Any) -> Any:
    """Placeholder requester; replaced by the CLI's real requester at runtime."""
    raise GlobalSkillError("global skills API requester not configured")


def _install_resolved(
    agent: str,
    package_ref_requested: str,
    resolved: dict[str, Any],
    skill_name: str,
    *,
    force: bool,
) -> InstallResult:
    _validate_path_component(skill_name, "skill name")
    package_ref_resolved = str(resolved.get("package_ref", ""))
    package_version_id = str(resolved.get("package_version_id", ""))
    checksum = str(resolved.get("checksum", ""))
    if not package_ref_resolved or not package_version_id or not checksum:
        raise GlobalSkillError("resolved skill missing required metadata")

    native_skill_dir = global_skill_dir(agent)
    target = native_skill_dir / skill_name / "SKILL.md"
    _reject_symlinked_path_components(
        target, boundary=native_skill_dir, action="install"
    )
    entries = read_lock()
    existing = _find_entry(entries, agent, skill_name)

    if existing is not None:
        if existing.get("checksum") == checksum:
            return InstallResult(target_path=target, changed=False)
        if existing.get("package_ref_resolved") != package_ref_resolved:
            raise GlobalSkillError(
                f"skill {skill_name} is already installed from "
                f"{existing.get('package_ref_resolved')}; remove it first"
            )
    elif target.exists():
        if not force:
            raise GlobalSkillError(
                f"target {target} already exists and is not tracked by AGH; "
                "use --force to overwrite"
            )

    content = download_skill(resolved)
    cache = _cache_path(package_ref_resolved, skill_name)
    previous_target_content = None
    if existing is not None and target.exists() and not target.is_symlink():
        previous_target_content = target.read_text(encoding="utf-8")
    previous_cache_content = None
    if existing is not None and cache.exists() and not cache.is_symlink():
        _reject_symlinked_existing_prefixes(cache, action="read cache")
        previous_cache_content = cache.read_text(encoding="utf-8")
    try:
        _write_skill_file(target, content)
        _write_cache_file(package_ref_resolved, skill_name, content)

        new_entry = {
            "name": skill_name,
            "agent": agent,
            "package_ref_requested": package_ref_requested,
            "package_ref_resolved": package_ref_resolved,
            "package_version_id": package_version_id,
            "checksum": checksum,
            "target_path": str(target),
            "installed_at": _now_iso(),
        }
        if existing is not None:
            existing.update(new_entry)
        else:
            entries.append(new_entry)
        _write_lock(entries)
    except Exception as exc:
        if existing is None:
            _cleanup_partial_install(target, cache)
        else:
            _restore_previous_install(
                target, cache, previous_target_content, previous_cache_content, exc
            )
        raise
    return InstallResult(target_path=target, changed=True)


def _cleanup_partial_install(target: Path, cache: Path) -> None:
    """Remove partially written target and cache files after a failed install."""
    with suppress(FileNotFoundError, OSError):
        target.unlink()
    with suppress(GlobalSkillError, FileNotFoundError, OSError):
        _unlink_state_file(cache, action="clean up cache")


def _restore_previous_install(
    target: Path,
    cache: Path,
    previous_target_content: str | None,
    previous_cache_content: str | None,
    update_error: BaseException,
) -> None:
    """Restore an existing install target after a failed update."""
    try:
        if previous_target_content is None:
            with suppress(FileNotFoundError):
                target.unlink()
        else:
            _atomic_write_text(target, previous_target_content)
        if previous_cache_content is None:
            with suppress(FileNotFoundError):
                _unlink_state_file(cache, action="remove cache")
        else:
            _reject_symlinked_existing_prefixes(cache, action="restore cache")
            _atomic_write_text(cache, previous_cache_content)
    except (GlobalSkillError, OSError) as exc:
        raise GlobalSkillError(
            f"update failed ({update_error}); rollback restore failed for {target} "
            f"and {cache}: {exc}. Manually inspect and restore or delete "
            "inconsistent files, then reinstall with --force."
        ) from exc


def _write_skill_file(target: Path, content: str) -> None:
    parent = target.parent
    if parent.is_symlink():
        raise GlobalSkillError(
            f"refusing to write through symlinked directory: {parent}"
        )
    if parent.exists() and not parent.is_dir():
        raise GlobalSkillError(f"non-directory skill parent path: {parent}")
    parent.mkdir(parents=True, exist_ok=True)
    if target.is_symlink():
        raise GlobalSkillError(f"refusing to write through symlinked file: {target}")
    _atomic_write_text(target, content)


def _write_cache_file(package_ref: str, skill_name: str, content: str) -> None:
    cache = _cache_path(package_ref, skill_name)
    parent = cache.parent
    _reject_symlinked_existing_prefixes(cache, action="write cache")
    if parent.exists() and parent.is_file():
        raise GlobalSkillError(f"non-directory cache parent path: {parent}")
    parent.mkdir(parents=True, exist_ok=True)
    _atomic_write_text(cache, content)


def _unlink_state_file(path: Path, *, action: str) -> None:
    _reject_symlinked_existing_prefixes(path, action=action)
    path.unlink()


def remove_skill_global(agent: str, skill_name: str) -> Path:
    """Remove a globally installed skill from the agent path and lock."""
    _validate_path_component(skill_name, "skill name")
    entries = read_lock()
    existing = _find_entry(entries, agent, skill_name)
    if existing is None:
        raise GlobalSkillError(f"skill {skill_name} is not installed for {agent}")

    target = _validated_remove_target(existing, agent, skill_name)
    _reject_symlinked_path_components(
        target, boundary=global_skill_dir(agent), action="remove"
    )

    entries.remove(existing)
    try:
        _write_lock(entries)
    except Exception as exc:
        raise GlobalSkillError(
            f"failed to update lock before removing {skill_name}; "
            f"target was left untouched: {target}"
        ) from exc

    if target.exists():
        try:
            target.unlink()
            if target.parent.is_dir() and not any(target.parent.iterdir()):
                target.parent.rmdir()
        except OSError as exc:
            raise GlobalSkillError(
                f"lock updated, but failed to remove target {target}; "
                "delete it manually or reinstall with --force"
            ) from exc

    return target


def _validated_remove_target(
    entry: dict[str, Any], agent: str, skill_name: str
) -> Path:
    expected = _target_path(agent, skill_name)
    stored = Path(str(entry.get("target_path", expected)))
    try:
        stored_resolved = stored.resolve(strict=False)
        expected_resolved = expected.resolve(strict=False)
    except (OSError, RuntimeError) as exc:
        raise GlobalSkillError(
            f"failed to validate lock target_path for {skill_name}: {exc}"
        ) from exc
    if stored_resolved != expected_resolved:
        raise GlobalSkillError(
            "lock target_path does not match expected skill target; "
            f"refusing to remove {stored}. Expected {expected}"
        )
    return expected


def _reject_symlinked_path_components(
    path: Path, *, boundary: Path, action: str
) -> None:
    """Reject symlinks in existing native skill path components through leaf."""
    try:
        relative = path.relative_to(boundary)
    except ValueError as exc:
        raise GlobalSkillError(
            f"refusing to {action} outside native skill boundary: {path}"
        ) from exc

    _reject_symlinked_existing_prefixes(boundary, action=action)
    candidate = boundary
    for part in relative.parts:
        candidate = candidate / part
        if candidate.is_symlink():
            raise GlobalSkillError(
                f"refusing to {action} through symlinked path component: {candidate}"
            )


def _reject_symlinked_existing_prefixes(path: Path, *, action: str) -> None:
    candidate = Path(path.anchor) if path.anchor else Path()
    for part in path.parts[1 if path.anchor else 0 :]:
        candidate = candidate / part
        if candidate.is_symlink():
            raise GlobalSkillError(
                f"refusing to {action} through symlinked path component: {candidate}"
            )


def list_installed_skills(agent: str) -> list[dict[str, Any]]:
    """Return lock entries for the given agent."""
    _validate_path_component(agent, "agent")
    return [entry for entry in read_lock() if entry.get("agent") == agent]
