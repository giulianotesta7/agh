---
name: agh-work-unit-commits
description: "Trigger: AGH commit, commit splitting, work unit, review size, large diff. Plan AGH commits and PR slices as reviewable units."
license: Apache-2.0
metadata:
  author: "giulianotesta7"
  version: "1.0"
---

# AGH — Work Unit Commits Skill

## Activation Contract

Load this skill when deciding what belongs in each AGH commit, how to split a PR, or whether a change is too large for one review.

Use it with `agh-branch-pr` before committing or opening a PR. AGH prefers one focused change per PR and a 400 changed-line review budget.

## Hard Rules

| Rule | Requirement |
| --- | --- |
| Commit by work unit | A commit represents one reviewable behavior, fix, workflow, docs unit, or repo-maintenance outcome. |
| Do not split by file type | Avoid separate `models`, `routes`, `tests`, or `docs` commits when none makes sense alone. |
| Keep validation with the change | Tests, docs, fixtures, or workflow assertions belong with the unit they prove. |
| Keep user-facing docs mirrored | If `README.md` changes user-facing behavior, update `README.es.md` in the same work unit unless intentionally out of scope. |
| Stay reviewable | Aim for 400 changed lines or less per PR. Split by behavior or workflow when the diff grows. |
| Explain unavoidable size | If a large diff must stay together, document the reason in the PR body. |
| No AI attribution | Never add `Co-Authored-By` or AI-generated trailers. |

## Work Unit Checklist

Before committing, confirm:

- [ ] The unit has one clear purpose.
- [ ] The repo still makes sense after applying only this commit.
- [ ] Validation for this unit is included or explicitly documented.
- [ ] Docs are included with user-visible behavior changes.
- [ ] Rollback would not remove unrelated work.
- [ ] The commit subject says the outcome, not the file list.

## AGH Split Examples

| Weak split | Better work-unit split |
| --- | --- |
| `add cli files` | `feat(cli): add workspace status command and tests` |
| `update server` | `feat(server): expose package assignment audit trail` |
| `fix tests` | Tests included with the behavior or regression they prove. |
| `update docs` | `docs: document self-hosted upgrade flow` with README mirrors when needed. |
| `add workflow stuff` | `ci: validate release metadata before publish` |
| `skill changes` | `chore(skills): add AGH branch PR workflow` |

## PR Split Decision

| Condition | Action |
| --- | --- |
| One focused unit under 400 changed lines | Keep one PR and one or more clear commits. |
| Multiple independent behaviors | Split into separate commits, and separate PRs if review would be mixed. |
| Docs plus code for one behavior | Keep together in the same unit. |
| Runtime code plus broad docs rewrite | Split unless the docs are required to understand the behavior. |
| Generated, vendored, or mechanical diff dominates size | Explain the size in the PR body; split hand-written logic when possible. |
| SDD produces a high review forecast | Group tasks into PR-sized work units before implementation. |

## AGH Areas

Use these boundaries when splitting work:

- CLI commands and config.
- Server/API behavior.
- Package publishing, assignment, and lockfile behavior.
- Workspace pull and native agent targets.
- Docker/runtime and release workflows.
- Documentation and contribution workflow.
- Project-local skills and guidance artifacts.

Prefer behavior/workflow boundaries over directory boundaries.

## Commit Subject Rules

Use Conventional Commits:

```text
<type>(optional-scope): <imperative outcome>
```

Allowed AGH types:

| Type | Use |
| --- | --- |
| `feat` | New product behavior. |
| `fix` | Defect or regression fix. |
| `docs` | Documentation-only change. |
| `test` | Test-only change. |
| `refactor` | Internal restructure without behavior change. |
| `ci` | GitHub Actions or release automation. |
| `build` | Packaging, container, or build-system change. |
| `chore` | Maintenance, metadata, skills, or repo hygiene. |

Examples:

```text
feat(cli): add workspace status command
fix(packs): handle invalid pack manifest
docs: clarify Docker setup
test(docs): cover contribution workflow guidance
chore(skills): add AGH issue workflow
```

## Validation Pairing

Pair the validation with the work unit:

| Unit | Validation |
| --- | --- |
| Runtime Python behavior | `uv run pytest` plus relevant focused tests when possible. |
| Lint/type-sensitive changes | `uv run --with ruff ruff check .`, `uv run --with pyright pyright agh tests`. |
| Formatting-sensitive changes | `uv run --with ruff ruff format --check .`. |
| Docs/workflow guidance | Focused docs tests when available, plus `git diff --check`. |
| Docker/runtime | `docker build --check .`. |

## Commands

```bash
# Review current size and story
git diff --stat
git diff --name-only

# Review staged story before committing
git diff --cached --stat
git diff --cached --name-only

# Check recent style
git log --oneline -5
```

## Output Contract

Return:
- Proposed commit/PR split.
- Commit subject for each work unit.
- Files or areas included in each unit.
- Validation paired with each unit.
- Review-size estimate and whether it stays under 400 changed lines.
- Any size exception rationale.

## References

- `CONTRIBUTING.md` — review size, commits, validation, docs mirror policy.
- `skills/agh-branch-pr/SKILL.md` — AGH branch and PR flow.

## Notices

Adapted from `skills/work-unit-commits/SKILL.md` in
[`Gentleman-Programming/gentle-ai`](https://github.com/Gentleman-Programming/gentle-ai),
licensed under Apache-2.0. This version was modified for Agent Guidance Hub's
Python/uv validation workflow, docs mirror policy, and PR-first contribution model.
