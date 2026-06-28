"""Workspace sync: link a local git repository to an AGH project."""

from __future__ import annotations

import json
import os
from contextlib import suppress
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
import subprocess
import tempfile
from typing import Any
import urllib.error
import urllib.request

from agh.cli.config import AghConfig, ConfigCorruptError, ConfigError, load_config
from agh.common.repo_url import normalize_repo_url


class WorkspaceSyncError(RuntimeError):
    """Raised for user-facing sync failures with a stable exit code."""

    def __init__(self, message: str, *, code: int = 1) -> None:
        super().__init__(message)
        self.code = code


class _NoRedirectHandler(urllib.request.HTTPRedirectHandler):
    """Reject redirects so Bearer tokens are never forwarded to another URL."""

    def redirect_request(self, req, fp, code, msg, headers, newurl):  # type: ignore[no-untyped-def]
        return None


_NO_REDIRECT_OPENER = urllib.request.build_opener(_NoRedirectHandler)
GIT_SUBPROCESS_TIMEOUT_SECONDS = 5


@dataclass(frozen=True)
class SyncResult:
    """Information about a successful workspace link."""

    project_id: str
    project_name: str
    instance_url: str
    repo_url_normalized: str
    link_path: Path
    replaced: bool


def sync_workspace(
    *, remote: str = "origin", force: bool = False, cwd: Path | None = None
) -> SyncResult:
    """Link the current git workspace to the accessible AGH project for its remote."""
    workspace = (cwd or Path.cwd()).resolve()
    config = _load_config_or_error()
    remote_url = _git_remote_url(remote=remote, cwd=workspace)
    repo_url_normalized = _normalize_remote_or_error(remote_url)
    projects = _fetch_projects(config)
    project = _match_project(projects, repo_url_normalized)
    link_path = workspace / ".agh" / "project.toml"
    replaced = link_path.exists()
    _write_project_link(
        link_path,
        config=config,
        project=project,
        repo_url_normalized=repo_url_normalized,
        force=force,
    )
    return SyncResult(
        project_id=str(project["id"]),
        project_name=str(project.get("name", "")),
        instance_url=config.instance_url,
        repo_url_normalized=repo_url_normalized,
        link_path=link_path,
        replaced=replaced,
    )


def _load_config_or_error() -> AghConfig:
    try:
        return load_config()
    except ConfigCorruptError:
        # Let corrupt config surface recovery guidance in the command layer.
        raise
    except ConfigError as exc:
        raise WorkspaceSyncError(str(exc), code=4) from exc


def _git_remote_url(*, remote: str, cwd: Path) -> str:
    try:
        completed = subprocess.run(
            ["git", "remote", "get-url", remote],
            cwd=cwd,
            check=False,
            capture_output=True,
            text=True,
            timeout=GIT_SUBPROCESS_TIMEOUT_SECONDS,
        )
    except FileNotFoundError as exc:
        raise WorkspaceSyncError("git executable not found", code=1) from exc
    except subprocess.TimeoutExpired as exc:
        raise WorkspaceSyncError(
            f"timed out after {GIT_SUBPROCESS_TIMEOUT_SECONDS} seconds while reading "
            f"git remote {remote!r}",
            code=5,
        ) from exc
    except OSError as exc:
        raise WorkspaceSyncError(f"failed to run git: {exc}", code=1) from exc

    if completed.returncode != 0:
        detail = (completed.stderr or completed.stdout).strip()
        if not detail:
            detail = f"remote {remote!r} not found or current directory is not a git repository"
        raise WorkspaceSyncError(
            f"failed to read git remote {remote!r}: {detail}", code=5
        )
    remote_url = completed.stdout.strip()
    if not remote_url:
        raise WorkspaceSyncError(f"git remote {remote!r} has no URL", code=5)
    return remote_url


def _normalize_remote_or_error(remote_url: str) -> str:
    try:
        return normalize_repo_url(remote_url)
    except ValueError as exc:
        raise WorkspaceSyncError(str(exc), code=5) from exc


def _fetch_projects(config: AghConfig) -> list[dict[str, Any]]:
    request = urllib.request.Request(
        f"{config.instance_url}/api/v1/projects",
        headers={
            "Authorization": f"Bearer {config.token}",
            "Accept": "application/json",
        },
        method="GET",
    )
    try:
        # noqa: S310 - configured AGH URL
        with _NO_REDIRECT_OPENER.open(request, timeout=10) as response:
            payload = json.loads(response.read().decode("utf-8"))
    except urllib.error.HTTPError as exc:
        if 300 <= exc.code < 400:
            raise WorkspaceSyncError(
                "API request redirected; refusing to forward token", code=1
            ) from exc
        code = 4 if exc.code in {401, 403} else 1
        raise WorkspaceSyncError(
            f"project lookup failed with HTTP {exc.code}", code=code
        ) from exc
    except urllib.error.URLError as exc:
        reason = getattr(exc, "reason", exc)
        raise WorkspaceSyncError(f"project lookup failed: {reason}", code=1) from exc
    except TimeoutError as exc:
        raise WorkspaceSyncError(f"project lookup failed: {exc}", code=1) from exc
    except json.JSONDecodeError as exc:
        raise WorkspaceSyncError(
            f"project lookup returned invalid JSON: {exc}", code=1
        ) from exc

    projects = payload.get("projects") if isinstance(payload, dict) else None
    if not isinstance(projects, list):
        raise WorkspaceSyncError("project lookup returned invalid response", code=1)
    return [project for project in projects if isinstance(project, dict)]


def _match_project(
    projects: list[dict[str, Any]], repo_url_normalized: str
) -> dict[str, Any]:
    for project in projects:
        if (
            project.get("repo_url_normalized") == repo_url_normalized
            and project.get("active", True) is True
        ):
            return project
    raise WorkspaceSyncError(
        f"no accessible active AGH project matches git remote {repo_url_normalized}",
        code=5,
    )


def _write_project_link(
    path: Path,
    *,
    config: AghConfig,
    project: dict[str, Any],
    repo_url_normalized: str,
    force: bool,
) -> None:
    if path.parent.is_symlink():
        raise WorkspaceSyncError(
            f"refusing to write through symlinked AGH directory: {path.parent}",
            code=5,
        )
    if path.exists() and not force:
        raise WorkspaceSyncError(
            f"{path} already exists; use --force to replace the project link",
            code=5,
        )
    path.parent.mkdir(parents=True, exist_ok=True)
    text = _project_link_toml(
        instance_url=config.instance_url,
        project_id=str(project["id"]),
        repo_url_normalized=repo_url_normalized,
    )
    fd, temp_name = tempfile.mkstemp(
        prefix=".project.toml.", suffix=".tmp", dir=path.parent
    )
    temp_path = Path(temp_name)
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as handle:
            handle.write(text)
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(temp_path, path)
    except Exception:
        with suppress(FileNotFoundError):
            temp_path.unlink()
        raise


def _project_link_toml(
    *, instance_url: str, project_id: str, repo_url_normalized: str
) -> str:
    synced_at = (
        datetime.now(UTC).replace(microsecond=0).isoformat().replace("+00:00", "Z")
    )
    return "".join(
        [
            f'instance_url = "{_toml_escape(instance_url)}"\n',
            f'project_id = "{_toml_escape(project_id)}"\n',
            f'repo_url_normalized = "{_toml_escape(repo_url_normalized)}"\n',
            f'synced_at = "{synced_at}"\n',
        ]
    )


def _toml_escape(value: str) -> str:
    return value.replace("\\", "\\\\").replace('"', '\\"')
