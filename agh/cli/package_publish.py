"""Local package directory validation and publish payload building."""

from __future__ import annotations

from pathlib import Path

from agh.common.package_limits import (
    MAX_PACKAGE_FILE_BYTES,
    MAX_PACKAGE_FILES,
    MAX_PACKAGE_PATH_LENGTH,
    MAX_PACKAGE_TOTAL_BYTES,
)
from agh.common.package_manifest import PackageManifestError, load_package_manifest
from agh.common.validation import is_valid_slug

MAX_PACKAGE_TREE_ENTRIES = 512


class PackagePublishBuildError(ValueError):
    """Raised when a local package directory cannot be published."""


def build_package_publish_payload(path: Path) -> dict[str, dict[str, str]]:
    """Validate a local package directory and return the server JSON file-map payload."""
    root = _resolve_real_package_root(path)

    try:
        files = _read_text_files(root)
        load_package_manifest(root / "agh.package.toml")
        _validate_skills(root)
        _validate_publishable_artifacts(root)
    except (PackageManifestError, UnicodeDecodeError) as exc:
        raise PackagePublishBuildError(str(exc)) from exc
    return {"files": files}


def _resolve_real_package_root(path: Path) -> Path:
    candidate = path.expanduser()
    probe = candidate if candidate.is_absolute() else Path.cwd() / candidate
    current = Path(probe.anchor)
    for part in probe.parts[1:]:
        current = current / part
        if current.is_symlink():
            raise PackagePublishBuildError(
                f"package path must not contain symlinks: {path}"
            )
    if not probe.exists() or not probe.is_dir() or probe.is_symlink():
        raise PackagePublishBuildError(f"package path must be a directory: {path}")
    return probe.resolve(strict=True)


def _validate_publishable_artifacts(root: Path) -> None:
    agents = root / "instructions" / "AGENTS.md"
    claude = root / "instructions" / "CLAUDE.md"
    if _is_real_file(agents) or _is_real_file(claude) or _has_real_skill(root):
        return
    raise PackageManifestError(
        "package must include at least one instruction file or skill"
    )


def _has_real_skill(root: Path) -> bool:
    skills_dir = root / "skills"
    if not skills_dir.exists() or not skills_dir.is_dir() or skills_dir.is_symlink():
        return False
    for child in skills_dir.iterdir():
        if (
            child.is_dir()
            and not child.is_symlink()
            and _is_real_file(child / "SKILL.md")
        ):
            return True
    return False


def _validate_skills(root: Path) -> None:
    skills_dir = root / "skills"
    if not skills_dir.exists():
        return
    if not skills_dir.is_dir() or skills_dir.is_symlink():
        raise PackageManifestError("skills must be a directory")
    for child in _iter_directory_entries(skills_dir, Path("skills"), [0]):
        if not child.is_dir():
            raise PackageManifestError(f"invalid skill entry: {child.name}")
        if not is_valid_slug(child.name):
            raise PackageManifestError(f"invalid skill name: {child.name}")
        if not _is_real_file(child / "SKILL.md"):
            raise PackageManifestError(f"skills/{child.name}/SKILL.md is required")


def _is_real_file(path: Path) -> bool:
    return path.exists() and path.is_file() and not path.is_symlink()


def _read_text_files(root: Path) -> dict[str, str]:
    files: dict[str, str] = {}
    total_bytes = 0
    for path in _collect_package_files(root):
        relative_path = path.relative_to(root)
        relative_posix = relative_path.as_posix()
        if len(relative_posix) > MAX_PACKAGE_PATH_LENGTH:
            raise PackagePublishBuildError(
                f"package file path is too long: {relative_posix}"
            )
        file_bytes = path.stat().st_size
        if file_bytes > MAX_PACKAGE_FILE_BYTES:
            raise PackagePublishBuildError(
                f"package file is too large: {relative_posix}"
            )
        total_bytes += file_bytes
        if len(files) + 1 > MAX_PACKAGE_FILES:
            raise PackagePublishBuildError(
                f"package cannot contain more than {MAX_PACKAGE_FILES} files"
            )
        if total_bytes > MAX_PACKAGE_TOTAL_BYTES:
            raise PackagePublishBuildError("package payload is too large")
        try:
            files[relative_posix] = path.read_text(encoding="utf-8")
        except UnicodeDecodeError as exc:
            raise PackagePublishBuildError(
                f"package file must be UTF-8 text: {relative_posix}"
            ) from exc
    return files


def _collect_package_files(root: Path) -> list[Path]:
    files: list[Path] = []
    entry_budget = [0]
    for entry in _iter_directory_entries(root, Path(), entry_budget):
        if entry.name == "agh.package.toml":
            _append_real_file(root, files, entry)
        elif entry.name == "instructions":
            _collect_instruction_files(root, files, entry, entry_budget)
        elif entry.name == "skills":
            _collect_skill_files(root, files, entry, entry_budget)
        else:
            raise PackagePublishBuildError(
                f"unexpected package file path: {entry.relative_to(root).as_posix()}"
            )
    return sorted(files, key=lambda item: item.relative_to(root).as_posix())


def _collect_instruction_files(
    root: Path, files: list[Path], directory: Path, entry_budget: list[int]
) -> None:
    _ensure_real_directory(root, directory)
    allowed_names = {"AGENTS.md", "CLAUDE.md"}
    for entry in _iter_directory_entries(directory, Path("instructions"), entry_budget):
        if entry.name not in allowed_names:
            raise PackagePublishBuildError(
                f"unexpected package file path: {entry.relative_to(root).as_posix()}"
            )
        _append_real_file(root, files, entry)


def _collect_skill_files(
    root: Path, files: list[Path], directory: Path, entry_budget: list[int]
) -> None:
    _ensure_real_directory(root, directory)
    for skill_dir in _iter_directory_entries(directory, Path("skills"), entry_budget):
        _ensure_real_directory(root, skill_dir)
        if not is_valid_slug(skill_dir.name):
            raise PackagePublishBuildError(f"invalid skill name: {skill_dir.name}")
        for entry in _iter_directory_entries(
            skill_dir, Path("skills") / skill_dir.name, entry_budget
        ):
            if entry.name != "SKILL.md":
                raise PackagePublishBuildError(
                    f"unexpected package file path: {entry.relative_to(root).as_posix()}"
                )
            _append_real_file(root, files, entry)


def _iter_directory_entries(
    directory: Path, relative_dir: Path, entry_budget: list[int]
):
    for count, entry in enumerate(directory.iterdir(), start=1):
        prefix = relative_dir.as_posix() or "."
        if count > MAX_PACKAGE_FILES:
            raise PackagePublishBuildError(f"too many package entries under {prefix}")
        entry_budget[0] += 1
        if entry_budget[0] > MAX_PACKAGE_TREE_ENTRIES:
            raise PackagePublishBuildError(
                "package contains too many filesystem entries"
            )
        if entry.is_symlink():
            relative = (relative_dir / entry.name).as_posix()
            raise PackagePublishBuildError(
                f"refusing to read symlinked package path: {relative}"
            )
        yield entry


def _ensure_real_directory(root: Path, path: Path) -> None:
    if path.is_symlink() or not path.is_dir():
        raise PackagePublishBuildError(
            f"unexpected package file path: {path.relative_to(root).as_posix()}"
        )


def _append_real_file(root: Path, files: list[Path], path: Path) -> None:
    if path.is_symlink():
        raise PackagePublishBuildError(
            f"refusing to read symlinked package path: {path.relative_to(root).as_posix()}"
        )
    if not path.is_file():
        raise PackagePublishBuildError(
            f"unexpected package file path: {path.relative_to(root).as_posix()}"
        )
    files.append(path)
