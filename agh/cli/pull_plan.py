"""Dry-run pull planning for AGH workspace artifacts."""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path

from agh.cli.pull_markers import (
    ManagedBlockRequest,
    MarkerConflict,
    MarkerError,
    MarkerPlan,
    plan_managed_update,
)

EXIT_OK = 0
EXIT_RUNTIME = 1
EXIT_VALIDATION = 2
EXIT_CONFLICT = 3
EXIT_AUTH = 4
EXIT_NOT_LINKED = 5


class PullPlanError(RuntimeError):
    """Raised for pull planning failures with a stable CLI exit code."""

    def __init__(self, message: str, *, code: int) -> None:
        super().__init__(message)
        self.code = code


@dataclass(frozen=True)
class PullArtifact:
    """One resolved artifact to apply to a workspace target."""

    package_ref: str
    artifact_path: str
    target_path: str
    content: str


@dataclass(frozen=True)
class PullTargetChange:
    """Planned change for one target file."""

    target_path: str
    status: str
    content: str
    conflicts: list[MarkerConflict] = field(default_factory=list)


@dataclass(frozen=True)
class PullPlan:
    """Complete dry-run-safe pull plan."""

    status: str
    exit_code: int
    dry_run: bool
    changes: list[PullTargetChange]

    @property
    def conflicts(self) -> list[MarkerConflict]:
        return [conflict for change in self.changes for conflict in change.conflicts]


def plan_pull(
    workspace: Path,
    artifacts: list[PullArtifact],
    *,
    dry_run: bool = False,
    force: bool = False,
) -> PullPlan:
    """Build a pull plan without writing files."""
    root = workspace.resolve()
    target_text: dict[str, str] = {}
    target_status: dict[str, str] = {}
    target_conflicts: dict[str, list[MarkerConflict]] = {}

    for artifact in artifacts:
        target_path = _validate_target_path(artifact.target_path)
        target_key = target_path.as_posix()
        current_text = target_text.get(target_key)
        if current_text is None:
            current_text = _read_target(root, target_path)
        marker_plan = _plan_marker_update(current_text, artifact, force=force)
        target_text[target_key] = marker_plan.content
        target_status[target_key] = _combine_status(
            target_status.get(target_key, "noop"), marker_plan.status
        )
        target_conflicts.setdefault(target_key, []).extend(marker_plan.conflicts)

    ordered_changes = [
        PullTargetChange(
            target_path=key,
            status=target_status[key],
            content=target_text[key],
            conflicts=target_conflicts.get(key, []),
        )
        for key in sorted(target_text)
    ]
    if any(change.conflicts for change in ordered_changes):
        return PullPlan(
            status="conflict",
            exit_code=EXIT_CONFLICT,
            dry_run=dry_run,
            changes=ordered_changes,
        )
    if any(change.status in {"insert", "update"} for change in ordered_changes):
        return PullPlan(
            status="changed",
            exit_code=EXIT_OK,
            dry_run=dry_run,
            changes=ordered_changes,
        )
    return PullPlan(
        status="noop", exit_code=EXIT_OK, dry_run=dry_run, changes=ordered_changes
    )


def _combine_status(previous: str, current: str) -> str:
    if "conflict" in {previous, current}:
        return "conflict"
    if current == "noop":
        return previous
    if previous == "noop":
        return current
    if "update" in {previous, current}:
        return "update"
    return "insert"


def _plan_marker_update(
    current_text: str, artifact: PullArtifact, *, force: bool = False
) -> MarkerPlan:
    try:
        return plan_managed_update(
            current_text,
            ManagedBlockRequest(
                package_ref=artifact.package_ref,
                artifact_path=artifact.artifact_path,
                payload=artifact.content,
            ),
            force=force,
        )
    except MarkerError as exc:
        raise PullPlanError(str(exc), code=EXIT_VALIDATION) from exc


def _validate_target_path(path: str) -> Path:
    if path.startswith("./") or path.endswith("/") or "//" in path:
        raise PullPlanError(f"invalid pull target path: {path}", code=EXIT_VALIDATION)
    candidate = Path(path)
    if candidate.is_absolute() or any(
        part in {"", ".", ".."} for part in candidate.parts
    ):
        raise PullPlanError(f"invalid pull target path: {path}", code=EXIT_VALIDATION)
    return candidate


def _read_target(root: Path, target_path: Path) -> str:
    path = root / target_path
    try:
        resolved = path.resolve(strict=False)
        resolved.relative_to(root)
    except ValueError as exc:
        raise PullPlanError(
            f"pull target escapes workspace: {target_path.as_posix()}",
            code=EXIT_VALIDATION,
        ) from exc
    if path.is_symlink():
        raise PullPlanError(
            f"refusing to read symlinked pull target: {target_path.as_posix()}",
            code=EXIT_VALIDATION,
        )
    if not path.exists():
        return ""
    if not path.is_file():
        raise PullPlanError(
            f"pull target is not a file: {target_path.as_posix()}",
            code=EXIT_VALIDATION,
        )
    try:
        return path.read_text(encoding="utf-8")
    except UnicodeDecodeError as exc:
        raise PullPlanError(
            f"pull target must be UTF-8 text: {target_path.as_posix()}",
            code=EXIT_VALIDATION,
        ) from exc
