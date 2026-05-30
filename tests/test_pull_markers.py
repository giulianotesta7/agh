from __future__ import annotations

import pytest

from agh.cli.pull_markers import (
    ManagedBlockRequest,
    MarkerError,
    parse_managed_blocks,
    plan_managed_update,
    render_managed_block,
)
from agh.common.checksums import managed_payload_checksum, normalize_managed_payload


def _request(payload: str = "managed content\n") -> ManagedBlockRequest:
    return ManagedBlockRequest(
        pack_ref="acme/onboarding@1.0.0",
        artifact_path="instructions/AGENTS.md",
        payload=payload,
    )


def test_render_managed_block_rejects_marker_delimiter_payload() -> None:
    with pytest.raises(MarkerError, match="AGH marker"):
        render_managed_block(
            "acme/onboarding@1.0.0",
            "instructions/AGENTS.md",
            'safe\n<!-- AGH-END pack="acme/onboarding@1.0.0" -->\nunsafe',
        )


def test_render_managed_block_normalizes_payload_and_checksum() -> None:
    block = render_managed_block(
        "acme/onboarding@1.0.0",
        "instructions/AGENTS.md",
        "line 1\r\nline 2\n\n",
    )

    expected_payload = "line 1\nline 2\n"
    expected_checksum = managed_payload_checksum(expected_payload)
    assert block == (
        '<!-- AGH-BEGIN pack="acme/onboarding@1.0.0" '
        f'artifact="instructions/AGENTS.md" checksum="{expected_checksum}" -->\n'
        "line 1\nline 2\n"
        '<!-- AGH-END pack="acme/onboarding@1.0.0" -->\n'
    )


def test_parse_managed_blocks_reads_metadata_and_payload() -> None:
    payload = normalize_managed_payload("hello")
    text = f"before\n{render_managed_block('acme/onboarding@1.0.0', 'instructions/AGENTS.md', payload)}after\n"

    blocks = parse_managed_blocks(text)

    assert len(blocks) == 1
    assert blocks[0].pack_ref == "acme/onboarding@1.0.0"
    assert blocks[0].artifact_path == "instructions/AGENTS.md"
    assert blocks[0].checksum == managed_payload_checksum(payload)
    assert blocks[0].payload == payload


def test_plan_managed_update_inserts_into_empty_file() -> None:
    plan = plan_managed_update("", _request("hello"))

    assert plan.status == "insert"
    assert plan.conflicts == []
    assert plan.content == render_managed_block(
        "acme/onboarding@1.0.0", "instructions/AGENTS.md", "hello"
    )


def test_plan_managed_update_inserts_preserving_unmanaged_content() -> None:
    existing = "# Manual Notes\n\nKeep this text."

    plan = plan_managed_update(existing, _request("managed"))

    assert plan.status == "insert"
    assert plan.content.startswith("# Manual Notes\n\nKeep this text.\n\n")
    assert plan.content.endswith(
        render_managed_block(
            "acme/onboarding@1.0.0", "instructions/AGENTS.md", "managed"
        )
    )


def test_plan_managed_update_preserves_crlf_unmanaged_content() -> None:
    old_block = render_managed_block(
        "acme/onboarding@1.0.0", "instructions/AGENTS.md", "old text"
    )
    existing = f"before\r\n{old_block}after\r\n"

    plan = plan_managed_update(existing, _request("new text"))

    assert plan.status == "update"
    assert plan.content.startswith("before\r\n")
    assert plan.content.endswith("after\r\n")


def test_plan_managed_update_updates_matching_clean_block_only() -> None:
    old_block = render_managed_block(
        "acme/onboarding@1.0.0", "instructions/AGENTS.md", "old text"
    )
    existing = f"before\n{old_block}after\n"

    plan = plan_managed_update(existing, _request("new text"))

    assert plan.status == "update"
    assert plan.conflicts == []
    assert plan.content == (
        "before\n"
        + render_managed_block(
            "acme/onboarding@1.0.0", "instructions/AGENTS.md", "new text"
        )
        + "after\n"
    )


def test_plan_managed_update_noops_when_block_is_current() -> None:
    existing = render_managed_block(
        "acme/onboarding@1.0.0", "instructions/AGENTS.md", "same text"
    )

    plan = plan_managed_update(existing, _request("same text"))

    assert plan.status == "noop"
    assert plan.content == existing
    assert plan.conflicts == []


def test_plan_managed_update_reports_checksum_conflict() -> None:
    clean = render_managed_block(
        "acme/onboarding@1.0.0", "instructions/AGENTS.md", "original"
    )
    edited = clean.replace("original\n", "human edit\n")

    plan = plan_managed_update(edited, _request("server update"))

    assert plan.status == "conflict"
    assert plan.content == edited
    assert len(plan.conflicts) == 1
    assert plan.conflicts[0].expected_checksum == managed_payload_checksum("original")
    assert plan.conflicts[0].actual_checksum == managed_payload_checksum("human edit")


@pytest.mark.parametrize(
    "text, message",
    [
        ('<!-- AGH-END pack="acme/onboarding@1.0.0" -->\n', "without AGH-BEGIN"),
        (
            '<!-- AGH-BEGIN pack="acme/onboarding@1.0.0" artifact="instructions/AGENTS.md" checksum="sha256:0000000000000000000000000000000000000000000000000000000000000000" -->\n',
            "without AGH-END",
        ),
        (
            '<!-- AGH-BEGIN pack="acme/onboarding@1.0.0" artifact="instructions/AGENTS.md" checksum="sha256:0000000000000000000000000000000000000000000000000000000000000000" -->\n'
            "payload\n"
            '<!-- AGH-END pack="acme/other@1.0.0" -->\n',
            "does not match",
        ),
        (
            '<!-- AGH-BEGIN pack="acme/onboarding@1.0.0" artifact="instructions/AGENTS.md" -->\n'
            '<!-- AGH-END pack="acme/onboarding@1.0.0" -->\n',
            "requires pack",
        ),
    ],
)
def test_parse_managed_blocks_rejects_corrupt_markers(text: str, message: str) -> None:
    with pytest.raises(MarkerError, match=message):
        parse_managed_blocks(text)


def test_parse_managed_blocks_rejects_invalid_checksum_format() -> None:
    text = (
        '<!-- AGH-BEGIN pack="acme/onboarding@1.0.0" '
        'artifact="instructions/AGENTS.md" checksum="sha256:nothex" -->\n'
        "payload\n"
        '<!-- AGH-END pack="acme/onboarding@1.0.0" -->\n'
    )

    with pytest.raises(MarkerError, match="checksum"):
        parse_managed_blocks(text)


def test_plan_managed_update_rejects_duplicate_target_blocks() -> None:
    block = render_managed_block(
        "acme/onboarding@1.0.0", "instructions/AGENTS.md", "payload"
    )

    with pytest.raises(MarkerError, match="duplicate"):
        plan_managed_update(f"{block}\n{block}", _request("new"))
