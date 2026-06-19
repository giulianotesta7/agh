---
name: agh-chained-pr
description: "Trigger: AGH chained PR, stacked PR, review slice, over 400 lines. Split large AGH changes into focused PR chains."
license: Apache-2.0
metadata:
  author: "giulianotesta7"
  version: "1.0"
---

# AGH — Chained PR Skill

## Activation Contract

Load this skill when an AGH change may exceed the 400 changed-line review budget, contains multiple independent work units, or the user asks for stacked PRs, chained PRs, review slices, or reviewer-load control.

Use it with `agh-work-unit-commits` and `agh-branch-pr`. AGH is PR-first: do not add issue gates or label gates while planning a chain.

## Hard Rules

- Split PRs over **400 changed lines** unless the maintainer explicitly accepts the size and the PR body explains why.
- Use one deliverable work unit per PR whenever possible.
- Keep tests, docs, fixtures, and validation with the slice they prove.
- Prefer **stacked-to-main** when each slice can land independently.
- Use a **feature branch chain** only when the full feature must integrate before `main` or rollback needs one coordinated boundary.
- Add Chain Context to the AGH PR template; do not replace Summary, Related issue, Context, Validation, or Notes.
- Treat polluted diffs as branching bugs. Retarget or rebase until each PR shows only its current slice.
- Do not require `status:approved`, `type:*` labels, or mandatory issue links.

## Decision Gates

| Condition | Action |
| --- | --- |
| PR is focused and ≤400 changed lines | Keep one PR. |
| PR is >400 lines but can split by behavior/workflow | Split into stacked PRs to `main`. |
| Slices depend on prior code but can land in order | Use stacked-to-main. |
| Work must be reviewed in slices but released/integrated together | Use feature branch chain with a draft tracker PR. |
| Generated or mechanical diff cannot split cleanly | Ask/record maintainer size acceptance and explain in PR body. |
| SDD provides `delivery_strategy` | Follow it, but still use AGH's PR template and validation policy. |

## Strategy: Stacked to Main

Default for AGH.

Use when each PR can merge to `main` in order:

```text
main
 └── PR 1: foundation
      └── PR 2: focused behavior built on PR 1
           └── PR 3: docs or follow-up slice
```

After a parent merges, rebase or retarget the next PR so GitHub shows only the current work unit.

## Strategy: Feature Branch Chain

Use only when slices should not land on `main` until the full feature is integrated.

```text
main
 └── feat/<feature>              ← draft tracker PR to main, no merge yet
      └── feat/<feature>-01-core ← PR targets tracker
           └── feat/<feature>-02-slice ← PR targets previous child
```

Rules:
- Open the tracker PR as draft/no-merge.
- Child PR #1 targets the tracker branch.
- Later child PRs target the immediate parent branch.
- Merge/integrate children in order; merge the tracker only after the chain is complete.

## Chain Context

Append this to the AGH PR template when a PR is part of a chain:

```markdown
## Chain Context

| Field | Value |
|-------|-------|
| Chain | <feature or stack name> |
| Strategy | <stacked-to-main or feature-branch-chain> |
| Tracker PR | <#NNN or Not needed> |
| Position | <N of total> |
| Base | `<target branch>` |
| Depends on | <PR/issue/link or None> |
| Follow-up | <next PR or None> |
| Review budget | <additions + deletions> / 400 |
| Starts at | <branch, PR, or state this builds on> |
| Ends with | <standalone result delivered by this PR> |

### Chain Overview

```text
main
 └── #NNN Previous PR
      └── 📍 #NNN This PR
           └── #NNN Next PR
```

### Scope
- Includes: <focused unit>
- Excludes: <deferred work>

### Autonomy
- [ ] CI is expected to pass for this PR branch
- [ ] This PR has one deliverable scope
- [ ] This PR can be rolled back without unrelated changes
- [ ] Tests, docs, or manual verification cover this unit
```

## AGH Slice Examples

| Large change | Better chain |
| --- | --- |
| New CLI workflow plus server changes plus docs | PR 1 server/API, PR 2 CLI wiring, PR 3 docs/examples. |
| Package publishing change plus workspace pull behavior | PR 1 package model/API, PR 2 workspace pull behavior, PR 3 docs/tests. |
| Docker/runtime plus release automation | PR 1 Docker/runtime, PR 2 release workflow, PR 3 docs. |
| Contribution workflow overhaul | PR 1 CONTRIBUTING/templates, PR 2 local skills, PR 3 docs/notices. |

## Commands

```bash
# Inspect size before deciding
git diff --stat

# Inspect an open PR's review load
gh pr view <PR_NUMBER> --json additions,deletions,changedFiles,title,url

# Stacked-to-main PR
gh pr create --base main --head <branch> --title "<type(scope): slice>" --body-file pr-body.md

# Feature branch chain child PR
gh pr create --base feat/<feature> --head feat/<feature>-01-core --title "<type(scope): focused slice>" --body-file pr-body.md
```

## Output Contract

Return:
- Chosen strategy: `single-pr`, `stacked-to-main`, `feature-branch-chain`, or `size-exception`.
- PR order and branch names.
- Current PR boundary: included and excluded scope.
- Dependency diagram with the current PR marked.
- Review budget estimate for each PR.
- Validation plan for each slice.
- Any maintainer-approved size exception rationale.

## References

- `CONTRIBUTING.md` — 400-line review budget and PR policy.
- `skills/agh-work-unit-commits/SKILL.md` — work-unit split rules.
- `skills/agh-branch-pr/SKILL.md` — AGH PR creation policy.

## Notices

Adapted from `skills/chained-pr/SKILL.md` and `skills/chained-pr/references/chaining-details.md`
in [`Gentleman-Programming/gentle-ai`](https://github.com/Gentleman-Programming/gentle-ai),
licensed under Apache-2.0. This version was modified for Agent Guidance Hub's
PR-first contribution policy, minimal labels, Python/uv validation, and single-maintainer review flow.
