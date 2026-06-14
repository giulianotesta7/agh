# Proposal: Fix Review Findings First Slice

## Intent

Review findings exposed pack publish reliability and UX gaps: request-time data-root drift, orphaned final pack directories after partial publish failure, and malformed `Content-Length` leaking uncontrolled errors. Fix the highest-impact slice without bundling unrelated hardening into one oversized PR.

## Scope

### In Scope
- Make pack publish use startup-derived storage state consistently.
- Clean or recover orphaned final pack directories only when no matching DB row can be proven.
- Return `400 Bad Request` JSON for malformed, non-numeric, or invalid `Content-Length`; preserve existing `413` behavior for oversized payloads.
- Add focused regression tests and only minimal risk-reducing restructuring.

### Out of Scope
- Unknown CLI commands exiting `0`.
- Missing/corrupt pack files returning `500`.
- Git subprocess timeouts and non-atomic workspace pull.
- Duplicate project-name migration startup risk.
- Docker mutable/root defaults.
- Broad CLI HTTP handling or large-module refactors.

## Capabilities

### New Capabilities
- `pack-publish-integrity`: consistent publish storage roots and safe orphan cleanup/recovery.
- `request-body-validation`: invalid `Content-Length` becomes controlled JSON client errors.

### Modified Capabilities
- None — no existing OpenSpec capability files are present.

## Approach

Use sliced remediation. Keep changes local to publish and request validation paths. Add small helpers only where they reduce deletion or transaction risk. Orphan handling must be conservative: act only on final pack directories with no corresponding DB row and no ambiguity.

## Affected Areas

| Area | Impact | Description |
|------|--------|-------------|
| `agh/server/app.py` | Modified | Validate `Content-Length` safely. |
| `agh/server/routes/packs.py` | Modified | Stabilize storage root and orphan handling. |
| `tests/` | Modified | Cover invalid headers and orphan publish behavior. |
| `openspec/changes/fix-review-findings/` | New | Proposal and later change artifacts. |

## Risks

| Risk | Likelihood | Mitigation |
|------|------------|------------|
| Deleting valid pack files | Med | Clean only when DB absence is proven; test ambiguous states. |
| PR exceeds 400-line budget | Med | Defer unrelated findings; avoid broad refactors. |
| Publish regression | Med | Cover success path and orphan recovery. |

## Rollback Plan

Revert the first-slice PR. No migration dependency is expected. If cleanup behavior is risky before merge, disable cleanup and keep header validation as a smaller slice.

## Dependencies

- Track each deferred review finding as a separate follow-up change/backlog item.

## Success Criteria

- [ ] Valid publishes still create one DB row and usable final pack files.
- [ ] Safely provable orphan final directories no longer block republish UX.
- [ ] Invalid `Content-Length` returns `400` JSON; oversized payloads still return existing `413`.
- [ ] First PR stays near the 400-line review budget or is split before apply.
