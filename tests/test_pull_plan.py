from __future__ import annotations

from pathlib import Path

import pytest

from agh.cli.pull_markers import render_managed_block
from agh.cli.pull_plan import (
    EXIT_CONFLICT,
    EXIT_OK,
    EXIT_VALIDATION,
    PullArtifact,
    PullPlanError,
    plan_pull,
)


def _artifact(
    *,
    target_path: str = "AGENTS.md",
    artifact_path: str = "instructions/AGENTS.md",
    content: str = "Use AGH guidance.\n",
) -> PullArtifact:
    return PullArtifact(
        package_ref="acme/onboarding@1.0.0",
        artifact_path=artifact_path,
        target_path=target_path,
        content=content,
    )


def test_plan_pull_dry_run_inserts_without_writing(tmp_path: Path) -> None:
    target = tmp_path / "AGENTS.md"
    target.write_text("# Manual\n", encoding="utf-8")

    plan = plan_pull(tmp_path, [_artifact()], dry_run=True)

    assert plan.dry_run is True
    assert plan.status == "changed"
    assert plan.exit_code == EXIT_OK
    assert len(plan.changes) == 1
    assert plan.changes[0].status == "insert"
    assert "# Manual\n\n<!-- AGH-BEGIN" in plan.changes[0].content
    assert target.read_text(encoding="utf-8") == "# Manual\n"


def test_plan_pull_updates_existing_clean_marker(tmp_path: Path) -> None:
    target = tmp_path / "AGENTS.md"
    target.write_text(
        "before\n"
        + render_managed_block(
            "acme/onboarding@1.0.0", "instructions/AGENTS.md", "old\n"
        )
        + "after\n",
        encoding="utf-8",
    )

    plan = plan_pull(tmp_path, [_artifact(content="new\n")])

    assert plan.status == "changed"
    assert plan.exit_code == EXIT_OK
    assert plan.changes[0].status == "update"
    assert plan.changes[0].content.startswith("before\n")
    assert plan.changes[0].content.endswith("after\n")
    assert "new\n" in plan.changes[0].content
    assert target.read_text(encoding="utf-8").count("old") == 1


def test_plan_pull_noops_when_marker_is_current(tmp_path: Path) -> None:
    target = tmp_path / "AGENTS.md"
    target.write_text(
        render_managed_block(
            "acme/onboarding@1.0.0", "instructions/AGENTS.md", "same\n"
        ),
        encoding="utf-8",
    )

    plan = plan_pull(tmp_path, [_artifact(content="same\n")])

    assert plan.status == "noop"
    assert plan.exit_code == EXIT_OK
    assert plan.changes[0].status == "noop"


def test_plan_pull_conflicts_return_exit_3_without_writing(tmp_path: Path) -> None:
    target = tmp_path / "AGENTS.md"
    clean = render_managed_block(
        "acme/onboarding@1.0.0", "instructions/AGENTS.md", "original\n"
    )
    target.write_text(clean.replace("original\n", "human edit\n"), encoding="utf-8")

    plan = plan_pull(tmp_path, [_artifact(content="server update\n")], dry_run=True)

    assert plan.status == "conflict"
    assert plan.exit_code == EXIT_CONFLICT
    assert len(plan.conflicts) == 1
    assert plan.changes[0].status == "conflict"
    assert target.read_text(encoding="utf-8") == clean.replace(
        "original\n", "human edit\n"
    )


def test_plan_pull_preserves_conflict_for_multiple_artifacts_same_target(
    tmp_path: Path,
) -> None:
    target = tmp_path / "AGENTS.md"
    clean = render_managed_block(
        "acme/onboarding@1.0.0", "instructions/AGENTS.md", "original\n"
    )
    target.write_text(clean.replace("original\n", "human edit\n"), encoding="utf-8")

    plan = plan_pull(
        tmp_path,
        [
            _artifact(artifact_path="instructions/AGENTS.md", content="server\n"),
            _artifact(artifact_path="instructions/CLAUDE.md", content="claude\n"),
        ],
        dry_run=True,
    )

    assert plan.status == "conflict"
    assert plan.exit_code == EXIT_CONFLICT
    assert len(plan.conflicts) == 1
    assert len(plan.changes) == 1
    assert plan.changes[0].status == "conflict"


def test_plan_pull_preserves_changed_status_after_same_target_noop(
    tmp_path: Path,
) -> None:
    existing_claude = render_managed_block(
        "acme/onboarding@1.0.0", "instructions/CLAUDE.md", "claude\n"
    )
    (tmp_path / "AGENTS.md").write_text(existing_claude, encoding="utf-8")

    plan = plan_pull(
        tmp_path,
        [
            _artifact(artifact_path="instructions/AGENTS.md", content="agents\n"),
            _artifact(artifact_path="instructions/CLAUDE.md", content="claude\n"),
        ],
        dry_run=True,
    )

    assert plan.status == "changed"
    assert plan.exit_code == EXIT_OK
    assert len(plan.changes) == 1
    assert plan.changes[0].status == "insert"
    assert plan.changes[0].content.count("<!-- AGH-BEGIN") == 2


def test_plan_pull_plans_multiple_artifacts_for_same_target(tmp_path: Path) -> None:
    plan = plan_pull(
        tmp_path,
        [
            _artifact(artifact_path="instructions/AGENTS.md", content="agents\n"),
            _artifact(artifact_path="instructions/CLAUDE.md", content="claude\n"),
        ],
        dry_run=True,
    )

    assert plan.status == "changed"
    assert plan.exit_code == EXIT_OK
    assert len(plan.changes) == 1
    assert plan.changes[0].content.count("<!-- AGH-BEGIN") == 2
    assert "instructions/AGENTS.md" in plan.changes[0].content
    assert "instructions/CLAUDE.md" in plan.changes[0].content


@pytest.mark.parametrize(
    "target_path", ["../AGENTS.md", "/tmp/AGENTS.md", "./AGENTS.md"]
)
def test_plan_pull_rejects_invalid_target_paths(
    tmp_path: Path, target_path: str
) -> None:
    with pytest.raises(PullPlanError) as exc_info:
        plan_pull(tmp_path, [_artifact(target_path=target_path)])

    assert exc_info.value.code == EXIT_VALIDATION


def test_plan_pull_rejects_symlinked_target(tmp_path: Path) -> None:
    outside = tmp_path / "outside.md"
    outside.write_text("secret\n", encoding="utf-8")
    (tmp_path / "AGENTS.md").symlink_to(outside)

    with pytest.raises(PullPlanError) as exc_info:
        plan_pull(tmp_path, [_artifact()])

    assert exc_info.value.code == EXIT_VALIDATION
    assert "symlinked" in str(exc_info.value)


def test_plan_pull_rejects_corrupt_existing_markers(tmp_path: Path) -> None:
    (tmp_path / "AGENTS.md").write_text(
        '<!-- AGH-BEGIN package="acme/onboarding@1.0.0" '
        'artifact="instructions/AGENTS.md" checksum="sha256:nothex" -->\n'
        "payload\n"
        '<!-- AGH-END package="acme/onboarding@1.0.0" -->\n',
        encoding="utf-8",
    )

    with pytest.raises(PullPlanError) as exc_info:
        plan_pull(tmp_path, [_artifact()])

    assert exc_info.value.code == EXIT_VALIDATION
