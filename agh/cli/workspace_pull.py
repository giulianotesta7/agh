"""Workspace pull cache and lockfile helpers."""

from __future__ import annotations

from contextlib import suppress
from dataclasses import dataclass, replace
from pathlib import Path
import json
import os
import re
import tempfile
import tomllib
import urllib.error
import urllib.parse
import urllib.request

from agh.cli.agent_integrations import relative_symlink_target, symlink_points_to
from agh.cli.config import AghConfig, ConfigError, load_config
from agh.cli.pull_markers import MarkerConflict
from agh.cli.pull_plan import (
    EXIT_CONFLICT,
    EXIT_NOT_LINKED,
    PullArtifact,
    PullPlan,
    PullPlanError,
    PullTargetChange,
    plan_pull,
)
from agh.common.checksums import managed_payload_checksum
from agh.common.validation import parse_pack_ref


class WorkspacePullError(RuntimeError):
    """Raised for user-facing pull failures with a stable exit code."""

    def __init__(self, message: str, *, code: int = 1) -> None:
        super().__init__(message)
        self.code = code


class _NoRedirectHandler(urllib.request.HTTPRedirectHandler):
    """Reject redirects so Bearer tokens are never forwarded to another URL."""

    def redirect_request(self, req, fp, code, msg, headers, newurl):  # type: ignore[no-untyped-def]
        return None


_NO_REDIRECT_OPENER = urllib.request.build_opener(_NoRedirectHandler)
_CHECKSUM_RE = re.compile(r"^sha256:[0-9a-f]{64}$")


@dataclass(frozen=True)
class DownloadedArtifact:
    """One resolved artifact downloaded and verified from a pull manifest."""

    pack_ref: str
    path: str
    target_path: str
    checksum: str
    content: str
    kind: str
    domain: str
    name: str
    version: str


@dataclass(frozen=True)
class CachedArtifact:
    """One artifact downloaded into the local cache."""

    pack_ref: str
    path: str
    target_path: str
    checksum: str
    cache_path: Path
    mode: str = "cache"


@dataclass(frozen=True)
class WorkspacePullCacheResult:
    """Result of cache population and lockfile write."""

    cache_dir: Path
    lock_path: Path
    artifacts: list[CachedArtifact]


@dataclass(frozen=True)
class WorkspacePullResult:
    """Result of a CLI pull operation."""

    status: str
    exit_code: int
    dry_run: bool
    plan: PullPlan
    cache_result: WorkspacePullCacheResult | None = None


@dataclass(frozen=True)
class ProjectLink:
    """Local workspace link to an AGH project."""

    project_id: str


def pull_workspace(
    *, cwd: Path | None = None, dry_run: bool = False, force: bool = False
) -> WorkspacePullResult:
    """Fetch a manifest, plan/apply target updates, and update cache/lock."""
    workspace = (cwd or Path.cwd()).resolve()
    link = _read_project_link(workspace)
    config = _load_config_or_error()
    manifest = fetch_pull_manifest(config=config, project_id=link.project_id)
    downloaded = download_manifest_artifacts(config=config, manifest=manifest)
    instruction_artifacts = [
        artifact for artifact in downloaded if artifact.kind == "instruction"
    ]
    skill_artifacts = [artifact for artifact in downloaded if artifact.kind == "skill"]
    artifacts = [
        PullArtifact(
            pack_ref=artifact.pack_ref,
            artifact_path=artifact.path,
            target_path=artifact.target_path,
            content=artifact.content,
        )
        for artifact in instruction_artifacts
    ]
    try:
        instruction_plan = plan_pull(workspace, artifacts, dry_run=dry_run, force=force)
    except PullPlanError as exc:
        raise WorkspacePullError(str(exc), code=exc.code) from exc
    skill_changes = _plan_skill_placements(workspace, skill_artifacts, force=force)
    plan = _merge_pull_and_skill_plans(
        instruction_plan, skill_changes=skill_changes, dry_run=dry_run
    )
    if dry_run or plan.exit_code == EXIT_CONFLICT:
        return WorkspacePullResult(
            status=plan.status, exit_code=plan.exit_code, dry_run=dry_run, plan=plan
        )
    _preflight_workspace_cache_boundaries(workspace, manifest)
    try:
        _apply_pull_plan(workspace, instruction_plan)
        cache_result = write_cache_artifacts(workspace, artifacts=downloaded)
        mode_overrides = _place_skill_artifacts(
            workspace,
            skill_artifacts=skill_artifacts,
            cached_artifacts=cache_result.artifacts,
        )
        cached_artifacts = [
            replace(
                artifact,
                mode=mode_overrides.get(
                    (artifact.pack_ref, artifact.path, artifact.target_path),
                    artifact.mode,
                ),
            )
            for artifact in cache_result.artifacts
        ]
        cache_result = write_lock_for_cached_artifacts(
            workspace, manifest=manifest, artifacts=cached_artifacts
        )
    except OSError as exc:
        raise WorkspacePullError(
            f"failed to write pull results: {exc}", code=1
        ) from exc
    return WorkspacePullResult(
        status=plan.status,
        exit_code=plan.exit_code,
        dry_run=dry_run,
        plan=plan,
        cache_result=cache_result,
    )


def populate_cache_and_write_lock(
    workspace: Path,
    *,
    config: AghConfig,
    manifest: object,
) -> WorkspacePullCacheResult:
    """Download manifest artifacts into .agh/packs and atomically write lockfile."""
    manifest = _validate_manifest(manifest)
    _preflight_workspace_cache_boundaries(workspace, manifest)
    downloaded = download_manifest_artifacts(config=config, manifest=manifest)
    return write_cache_and_lock(workspace, manifest=manifest, artifacts=downloaded)


def _preflight_workspace_cache_boundaries(workspace: Path, manifest: dict) -> None:
    root = workspace.resolve()
    agh_dir = root / ".agh"
    if agh_dir.is_symlink():
        raise WorkspacePullError(
            f"refusing to write through symlinked AGH directory: {agh_dir}", code=2
        )
    cache_dir = agh_dir / "packs"
    _ensure_safe_directory_boundary(agh_dir, cache_dir)
    _preflight_cache_boundaries(cache_dir=cache_dir, manifest=manifest)


def _preflight_cache_boundaries(*, cache_dir: Path, manifest: dict) -> None:
    for pack in _manifest_packs(manifest):
        pack_ref = _pack_id(pack)
        domain, name, version = _parse_resolved_pack_ref(pack_ref)
        for artifact in _pack_artifacts(pack):
            artifact_path = _artifact_path(artifact)
            cache_path = _cache_path(
                cache_dir=cache_dir,
                domain=domain,
                name=name,
                version=version,
                artifact_path=artifact_path,
            )
            _ensure_safe_directory_boundary(cache_dir.parent, cache_path.parent)


def _load_config_or_error() -> AghConfig:
    try:
        return load_config()
    except ConfigError as exc:
        raise WorkspacePullError(str(exc), code=4) from exc


def _read_project_link(workspace: Path) -> ProjectLink:
    link_path = workspace / ".agh" / "project.toml"
    if not link_path.exists():
        raise WorkspacePullError(
            "workspace is not linked; run `agh sync` first", code=EXIT_NOT_LINKED
        )
    if link_path.is_symlink() or link_path.parent.is_symlink():
        raise WorkspacePullError(
            "refusing to read symlinked AGH project link", code=EXIT_NOT_LINKED
        )
    try:
        data = tomllib.loads(link_path.read_text(encoding="utf-8"))
    except tomllib.TOMLDecodeError as exc:
        raise WorkspacePullError(
            f"invalid AGH project link: {exc}", code=EXIT_NOT_LINKED
        ) from exc
    except OSError as exc:
        raise WorkspacePullError(
            f"failed to read AGH project link: {exc}", code=EXIT_NOT_LINKED
        ) from exc
    project_id = data.get("project_id") if isinstance(data, dict) else None
    if not isinstance(project_id, str) or not project_id:
        raise WorkspacePullError(
            "AGH project link missing project_id", code=EXIT_NOT_LINKED
        )
    _validate_toml_string(project_id, "project_id")
    return ProjectLink(project_id=project_id)


def fetch_pull_manifest(*, config: AghConfig, project_id: str) -> dict:
    _validate_toml_string(project_id, "project_id")
    quoted_project_id = urllib.parse.quote(project_id, safe="")
    request = urllib.request.Request(
        f"{config.instance_url}/api/v1/projects/{quoted_project_id}/pull-manifest",
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
            raise WorkspacePullError(
                "pull-manifest request redirected; refusing to forward token", code=1
            ) from exc
        code = 4 if exc.code in {401, 403} else 1
        raise WorkspacePullError(
            f"pull-manifest request failed with HTTP {exc.code}", code=code
        ) from exc
    except urllib.error.URLError as exc:
        reason = getattr(exc, "reason", exc)
        raise WorkspacePullError(
            f"pull-manifest request failed: {reason}", code=1
        ) from exc
    except TimeoutError as exc:
        raise WorkspacePullError(
            f"pull-manifest request failed: {exc}", code=1
        ) from exc
    except (json.JSONDecodeError, UnicodeDecodeError) as exc:
        raise WorkspacePullError(
            f"pull-manifest returned invalid JSON: {exc}", code=1
        ) from exc
    return _validate_manifest(payload)


def download_manifest_artifacts(
    *, config: AghConfig, manifest: object
) -> list[DownloadedArtifact]:
    manifest = _validate_manifest(manifest)
    _validate_manifest_metadata(manifest)
    artifacts: list[DownloadedArtifact] = []
    for pack in _manifest_packs(manifest):
        pack_ref = _pack_id(pack)
        domain, name, version = _parse_resolved_pack_ref(pack_ref)
        for artifact in _pack_artifacts(pack):
            artifact_path = _artifact_path(artifact)
            target_path = _target_path(artifact)
            checksum = _artifact_checksum(artifact)
            kind = _artifact_kind(artifact)
            target_agent = _target_agent(artifact)
            _validate_artifact_target(
                kind=kind, target_agent=target_agent, target_path=target_path
            )
            download_url = _download_url(artifact)
            content = _download_text(config=config, url=download_url)
            actual_checksum = managed_payload_checksum(content)
            if actual_checksum != checksum:
                raise WorkspacePullError(
                    f"checksum mismatch for {pack_ref} {artifact_path}", code=1
                )
            artifacts.append(
                DownloadedArtifact(
                    pack_ref=pack_ref,
                    path=artifact_path,
                    target_path=target_path,
                    checksum=checksum,
                    content=content,
                    kind=kind,
                    domain=domain,
                    name=name,
                    version=version,
                )
            )
    return artifacts


def write_cache_and_lock(
    workspace: Path, *, manifest: object, artifacts: list[DownloadedArtifact]
) -> WorkspacePullCacheResult:
    cache_result = write_cache_artifacts(workspace, artifacts=artifacts)
    return write_lock_for_cached_artifacts(
        workspace, manifest=manifest, artifacts=cache_result.artifacts
    )


def write_cache_artifacts(
    workspace: Path, *, artifacts: list[DownloadedArtifact]
) -> WorkspacePullCacheResult:
    root = workspace.resolve()
    agh_dir = root / ".agh"
    if agh_dir.is_symlink():
        raise WorkspacePullError(
            f"refusing to write through symlinked AGH directory: {agh_dir}", code=2
        )
    agh_dir.mkdir(parents=True, exist_ok=True)
    cache_dir = agh_dir / "packs"
    _ensure_safe_directory_boundary(agh_dir, cache_dir)
    cached: list[CachedArtifact] = []
    for artifact in artifacts:
        cache_path = _cache_path(
            cache_dir=cache_dir,
            domain=artifact.domain,
            name=artifact.name,
            version=artifact.version,
            artifact_path=artifact.path,
        )
        _ensure_safe_directory_boundary(cache_dir.parent, cache_path.parent)
        _write_cache_file(cache_path, artifact.content)
        cached.append(
            CachedArtifact(
                pack_ref=artifact.pack_ref,
                path=artifact.path,
                target_path=artifact.target_path,
                checksum=artifact.checksum,
                cache_path=cache_path.relative_to(root),
            )
        )
    return WorkspacePullCacheResult(
        cache_dir=cache_dir, lock_path=agh_dir / "lock.toml", artifacts=cached
    )


def write_lock_for_cached_artifacts(
    workspace: Path, *, manifest: object, artifacts: list[CachedArtifact]
) -> WorkspacePullCacheResult:
    root = workspace.resolve()
    agh_dir = root / ".agh"
    if agh_dir.is_symlink():
        raise WorkspacePullError(
            f"refusing to write through symlinked AGH directory: {agh_dir}", code=2
        )
    agh_dir.mkdir(parents=True, exist_ok=True)
    cache_dir = agh_dir / "packs"
    lock_path = agh_dir / "lock.toml"
    manifest = _validate_manifest(manifest)
    _validate_manifest_metadata(manifest)
    _write_lockfile(lock_path, manifest=manifest, artifacts=artifacts)
    return WorkspacePullCacheResult(
        cache_dir=cache_dir, lock_path=lock_path, artifacts=artifacts
    )


def _plan_skill_placements(
    workspace: Path, skill_artifacts: list[DownloadedArtifact], *, force: bool
) -> list[PullTargetChange]:
    root = workspace.resolve()
    changes: list[PullTargetChange] = []
    for artifact in skill_artifacts:
        target_path = _safe_relative_path(artifact.target_path)
        cache_path = _relative_cache_path_for_artifact(artifact)
        status, conflicts = _plan_one_skill_placement(
            root=root,
            target_path=target_path,
            cache_path=cache_path,
            artifact=artifact,
            force=force,
        )
        changes.append(
            PullTargetChange(
                target_path=target_path.as_posix(),
                status=status,
                content="",
                conflicts=conflicts,
            )
        )
    return changes


def _plan_one_skill_placement(
    *,
    root: Path,
    target_path: Path,
    cache_path: Path,
    artifact: DownloadedArtifact,
    force: bool,
) -> tuple[str, list[MarkerConflict]]:
    path = root / target_path
    _ensure_target_parent_safe(root, path.parent)
    if not path.exists() and not path.is_symlink():
        return "insert", []
    if path.is_symlink():
        if symlink_points_to(path, root / cache_path):
            return "noop", []
        if force:
            return "update", []
        return "conflict", [_skill_conflict(artifact, actual_checksum="symlink")]
    if path.is_file():
        try:
            current = path.read_text(encoding="utf-8")
        except UnicodeDecodeError:
            if force:
                return "update", []
            return "conflict", [_skill_conflict(artifact, actual_checksum="non-utf8")]
        actual_checksum = managed_payload_checksum(current)
        if actual_checksum == artifact.checksum:
            return "noop", []
        if force:
            return "update", []
        return "conflict", [_skill_conflict(artifact, actual_checksum=actual_checksum)]
    return "conflict", [_skill_conflict(artifact, actual_checksum="non-file")]


def _skill_conflict(
    artifact: DownloadedArtifact, *, actual_checksum: str
) -> MarkerConflict:
    return MarkerConflict(
        pack_ref=artifact.pack_ref,
        artifact_path=artifact.path,
        expected_checksum=artifact.checksum,
        actual_checksum=actual_checksum,
    )


def _merge_pull_and_skill_plans(
    instruction_plan: PullPlan,
    *,
    skill_changes: list[PullTargetChange],
    dry_run: bool,
) -> PullPlan:
    changes = sorted(
        [*instruction_plan.changes, *skill_changes],
        key=lambda change: change.target_path,
    )
    if any(change.conflicts for change in changes):
        return PullPlan(
            status="conflict", exit_code=EXIT_CONFLICT, dry_run=dry_run, changes=changes
        )
    if any(change.status in {"insert", "update"} for change in changes):
        return PullPlan(status="changed", exit_code=0, dry_run=dry_run, changes=changes)
    return PullPlan(status="noop", exit_code=0, dry_run=dry_run, changes=changes)


def _place_skill_artifacts(
    workspace: Path,
    *,
    skill_artifacts: list[DownloadedArtifact],
    cached_artifacts: list[CachedArtifact],
) -> dict[tuple[str, str, str], str]:
    root = workspace.resolve()
    cached_by_key = {
        (artifact.pack_ref, artifact.path, artifact.target_path): artifact
        for artifact in cached_artifacts
    }
    modes: dict[tuple[str, str, str], str] = {}
    for artifact in skill_artifacts:
        key = (artifact.pack_ref, artifact.path, artifact.target_path)
        cached = cached_by_key[key]
        target_path = _safe_relative_path(artifact.target_path)
        target = root / target_path
        source = root / cached.cache_path
        _ensure_target_parent_safe(root, target.parent)
        target.parent.mkdir(parents=True, exist_ok=True)
        modes[key] = _write_skill_target(
            target=target, source=source, content=artifact.content
        )
    return modes


def _write_skill_target(*, target: Path, source: Path, content: str) -> str:
    if target.exists() and not target.is_file() and not target.is_symlink():
        raise WorkspacePullError(
            f"refusing to replace non-file skill target: {target}", code=3
        )
    if target.is_symlink():
        target.unlink()
    relative_source = relative_symlink_target(source=source, target=target)
    try:
        if target.exists():
            target.unlink()
        target.symlink_to(relative_source)
        return "symlink"
    except OSError:
        _write_plain_file(target, content)
        return "copy"


def _write_plain_file(path: Path, content: str) -> None:
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


def _relative_cache_path_for_artifact(artifact: DownloadedArtifact) -> Path:
    return (
        Path(".agh")
        / "packs"
        / artifact.domain
        / artifact.name
        / artifact.version
        / _safe_relative_path(artifact.path)
    )


def _apply_pull_plan(workspace: Path, plan: PullPlan) -> None:
    root = workspace.resolve()
    for change in plan.changes:
        if change.status not in {"insert", "update"}:
            continue
        target_path = _safe_relative_path(change.target_path)
        _write_target_file(root, target_path, change.content)


def _write_target_file(root: Path, target_path: Path, content: str) -> None:
    path = root / target_path
    _ensure_target_parent_safe(root, path.parent)
    path.parent.mkdir(parents=True, exist_ok=True)
    if path.is_symlink():
        raise WorkspacePullError(
            f"refusing to write symlinked pull target: {target_path.as_posix()}", code=2
        )
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


def _ensure_target_parent_safe(root: Path, directory: Path) -> None:
    root_resolved = root.resolve(strict=False)
    try:
        relative = directory.relative_to(root_resolved)
    except ValueError as exc:
        raise WorkspacePullError("pull target escapes workspace", code=2) from exc
    current = root_resolved
    for part in relative.parts:
        current = current / part
        if current.is_symlink():
            raise WorkspacePullError(
                f"refusing to write through symlinked directory: {current}", code=2
            )


def _validate_manifest(manifest: object) -> dict:
    if not isinstance(manifest, dict):
        raise WorkspacePullError("pull manifest must be an object", code=2)
    return manifest


def _validate_manifest_metadata(manifest: dict) -> None:
    raw_project = manifest.get("project")
    if raw_project is None:
        return
    if not isinstance(raw_project, dict):
        raise WorkspacePullError("pull manifest project must be an object", code=2)
    if "id" not in raw_project:
        return
    project_id = raw_project["id"]
    if not isinstance(project_id, str):
        raise WorkspacePullError("pull manifest project id must be a string", code=2)
    if project_id:
        _validate_toml_string(project_id, "project id")


def _download_text(*, config: AghConfig, url: str) -> str:
    full_url = _absolute_download_url(config.instance_url, url)
    request = urllib.request.Request(
        full_url,
        headers={"Authorization": f"Bearer {config.token}", "Accept": "text/plain"},
        method="GET",
    )
    try:
        with _NO_REDIRECT_OPENER.open(request, timeout=10) as response:  # noqa: S310 - configured AGH URL
            return response.read().decode("utf-8")
    except urllib.error.HTTPError as exc:
        if 300 <= exc.code < 400:
            raise WorkspacePullError(
                "artifact download redirected; refusing to forward token", code=1
            ) from exc
        code = 4 if exc.code in {401, 403} else 1
        raise WorkspacePullError(
            f"artifact download failed with HTTP {exc.code}", code=code
        ) from exc
    except urllib.error.URLError as exc:
        reason = getattr(exc, "reason", exc)
        raise WorkspacePullError(f"artifact download failed: {reason}", code=1) from exc
    except TimeoutError as exc:
        raise WorkspacePullError(f"artifact download failed: {exc}", code=1) from exc
    except UnicodeDecodeError as exc:
        raise WorkspacePullError(
            "artifact download must be UTF-8 text", code=1
        ) from exc


def _absolute_download_url(instance_url: str, url: str) -> str:
    parsed = urllib.parse.urlparse(url)
    if parsed.scheme or parsed.netloc:
        raise WorkspacePullError("artifact download URL must be relative", code=2)
    if parsed.params or parsed.query or parsed.fragment:
        raise WorkspacePullError("artifact download URL must be a plain path", code=2)
    if not parsed.path.startswith("/api/v1/"):
        raise WorkspacePullError(
            "artifact download URL must stay under /api/v1", code=2
        )
    _validate_api_download_path(parsed.path)
    return f"{instance_url.rstrip('/')}{parsed.path}"


def _validate_api_download_path(path: str) -> None:
    if ";" in path:
        raise WorkspacePullError(
            "artifact download URL must not contain params", code=2
        )
    if "\\" in path:
        raise WorkspacePullError("artifact download URL contains backslash", code=2)
    decoded_path = urllib.parse.unquote(path)
    if "\\" in decoded_path:
        raise WorkspacePullError("artifact download URL contains backslash", code=2)
    if not decoded_path.startswith("/api/v1/"):
        raise WorkspacePullError(
            "artifact download URL must stay under /api/v1", code=2
        )
    decoded_parts = decoded_path.split("/")
    if any(part in {".", ".."} for part in decoded_parts):
        raise WorkspacePullError("artifact download URL contains dot segments", code=2)
    if any(part == "" for part in decoded_parts[1:]):
        raise WorkspacePullError(
            "artifact download URL contains empty segments", code=2
        )


def _write_cache_file(path: Path, content: str) -> None:
    _ensure_safe_directory_boundary(path.parents[4], path.parent)
    path.parent.mkdir(parents=True, exist_ok=True)
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


def _write_lockfile(
    path: Path, *, manifest: dict, artifacts: list[CachedArtifact]
) -> None:
    if path.parent.is_symlink():
        raise WorkspacePullError(
            f"refusing to write through symlinked AGH directory: {path.parent}", code=2
        )
    path.parent.mkdir(parents=True, exist_ok=True)
    text = _lockfile_toml(manifest=manifest, artifacts=artifacts)
    fd, temp_name = tempfile.mkstemp(
        prefix=".lock.toml.", suffix=".tmp", dir=path.parent
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


def _lockfile_toml(*, manifest: dict, artifacts: list[CachedArtifact]) -> str:
    lines = ["version = 1\n"]
    raw_project = manifest.get("project")
    project = raw_project if isinstance(raw_project, dict) else {}
    project_id = project.get("id", "")
    if not isinstance(project_id, str):
        raise WorkspacePullError("pull manifest project id must be a string", code=2)
    if project_id:
        lines.extend(["\n[project]\n", f'id = "{_toml_escape(project_id)}"\n'])
    seen_packs: set[str] = set()
    for artifact in artifacts:
        if artifact.pack_ref in seen_packs:
            continue
        seen_packs.add(artifact.pack_ref)
        lines.extend(["\n[[packs]]\n", f'ref = "{_toml_escape(artifact.pack_ref)}"\n'])
    for artifact in artifacts:
        source = _lock_source_path(artifact.cache_path)
        lines.extend(
            [
                "\n[[artifacts]]\n",
                f'pack_ref = "{_toml_escape(artifact.pack_ref)}"\n',
                f'path = "{_toml_escape(artifact.path)}"\n',
                f'target_path = "{_toml_escape(artifact.target_path)}"\n',
                f'checksum = "{_toml_escape(artifact.checksum)}"\n',
                f'mode = "{_toml_escape(artifact.mode)}"\n',
                f'source = "{_toml_escape(source)}"\n',
            ]
        )
    return "".join(lines)


def _lock_source_path(cache_path: Path) -> str:
    parts = cache_path.parts
    if len(parts) < 3 or parts[0] != ".agh" or parts[1] != "packs":
        raise WorkspacePullError("cache path is not under .agh/packs", code=2)
    return cache_path.as_posix()


def _cache_path(
    *, cache_dir: Path, domain: str, name: str, version: str, artifact_path: str
) -> Path:
    safe_artifact_path = _safe_relative_path(artifact_path)
    return cache_dir / domain / name / version / safe_artifact_path


def _safe_relative_path(path: str) -> Path:
    _validate_toml_string(path, "path")
    if not path:
        raise WorkspacePullError("path is required", code=2)
    if "\\" in path:
        raise WorkspacePullError(f"invalid artifact path: {path}", code=2)
    if path.startswith("./") or path.endswith("/") or "//" in path:
        raise WorkspacePullError(f"invalid artifact path: {path}", code=2)
    raw_parts = path.split("/")
    if any(part in {"", ".", ".."} for part in raw_parts):
        raise WorkspacePullError(f"invalid artifact path: {path}", code=2)
    candidate = Path(path)
    if candidate.is_absolute() or any(
        part in {"", ".", ".."} for part in candidate.parts
    ):
        raise WorkspacePullError(f"invalid artifact path: {path}", code=2)
    return candidate


def _manifest_packs(manifest: dict) -> list[dict]:
    packs = manifest.get("packs")
    if not isinstance(packs, list):
        raise WorkspacePullError("pull manifest missing packs", code=2)
    if not all(isinstance(pack, dict) for pack in packs):
        raise WorkspacePullError("pull manifest packs must be objects", code=2)
    return packs


def _pack_artifacts(pack: dict) -> list[dict]:
    artifacts = pack.get("artifacts")
    if not isinstance(artifacts, list):
        raise WorkspacePullError("pull manifest pack missing artifacts", code=2)
    if not all(isinstance(artifact, dict) for artifact in artifacts):
        raise WorkspacePullError("pull manifest artifacts must be objects", code=2)
    return artifacts


def _required_string(mapping: dict, key: str, label: str) -> str:
    value = mapping.get(key)
    if not isinstance(value, str):
        raise WorkspacePullError(f"pull manifest {label} must be a string", code=2)
    if not value:
        raise WorkspacePullError(f"pull manifest missing {label}", code=2)
    return value


def _pack_id(pack: dict) -> str:
    return _required_string(pack, "id", "pack id")


def _parse_resolved_pack_ref(pack_ref: str) -> tuple[str, str, str]:
    try:
        parsed = parse_pack_ref(pack_ref, allow_latest=False)
    except ValueError as exc:
        raise WorkspacePullError(
            f"invalid resolved pack ref: {pack_ref}", code=2
        ) from exc
    return parsed.domain, parsed.name, parsed.version


def _artifact_path(artifact: dict) -> str:
    path = _required_string(artifact, "path", "artifact path")
    _safe_relative_path(path)
    return path


def _target_path(artifact: dict) -> str:
    path = _required_string(artifact, "target_path", "artifact target_path")
    _safe_relative_path(path)
    return path


def _artifact_checksum(artifact: dict) -> str:
    checksum = _required_string(artifact, "checksum", "artifact checksum")
    if not _CHECKSUM_RE.fullmatch(checksum):
        raise WorkspacePullError(
            "pull manifest artifact checksum must be sha256:<hex>", code=2
        )
    return checksum


def _artifact_kind(artifact: dict) -> str:
    kind = _required_string(artifact, "kind", "artifact kind")
    if kind not in {"instruction", "skill"}:
        raise WorkspacePullError(
            f"unsupported pull manifest artifact kind: {kind}", code=2
        )
    return kind


def _target_agent(artifact: dict) -> str:
    agent = _required_string(artifact, "target_agent", "artifact target_agent")
    if agent not in {"claude", "opencode"}:
        raise WorkspacePullError(
            f"unsupported pull manifest target_agent: {agent}", code=2
        )
    return agent


def _validate_artifact_target(
    *, kind: str, target_agent: str, target_path: str
) -> None:
    if kind != "skill":
        return
    parts = Path(target_path).parts
    expected_prefix = {
        "claude": (".claude", "skills"),
        "opencode": (".opencode", "skills"),
    }[target_agent]
    if len(parts) != 4 or parts[0:2] != expected_prefix or parts[3] != "SKILL.md":
        raise WorkspacePullError(
            f"invalid {target_agent} skill target path: {target_path}", code=2
        )


def _download_url(artifact: dict) -> str:
    url = _required_string(artifact, "download_url", "artifact download_url")
    _validate_toml_string(url, "download_url")
    return url


def _validate_toml_string(value: str, field: str) -> None:
    if any(ord(character) < 0x20 or ord(character) == 0x7F for character in value):
        raise WorkspacePullError(f"invalid control character in {field}", code=2)


def _ensure_safe_directory_boundary(root: Path, directory: Path) -> None:
    root_resolved = root.resolve(strict=False)
    current = root_resolved
    relative = directory.relative_to(root_resolved)
    for part in relative.parts:
        if part in {"", ".", ".."}:
            raise WorkspacePullError(
                f"refusing unsafe directory boundary: {directory}", code=2
            )
        current = current / part
        if current.is_symlink():
            raise WorkspacePullError(
                f"refusing to write through symlinked directory: {current}", code=2
            )


def _toml_escape(value: str) -> str:
    _validate_toml_string(value, "toml value")
    return value.replace("\\", "\\\\").replace('"', '\\"')
