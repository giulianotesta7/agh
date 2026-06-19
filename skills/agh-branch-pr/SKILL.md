---
name: agh-branch-pr
description: "Trigger: AGH branch, commit, PR, pull request, merge. Prepare reviewable AGH PRs using the repo contribution policy."
license: Apache-2.0
metadata:
  author: "giulianotesta7"
  version: "1.0"
---

# AGH — Branch & PR Skill

## Activation Contract

Load this skill when creating a branch, preparing commits, opening a pull request, checking PR readiness, or merging changes for Agent Guidance Hub.

Use the current AGH policy: PR-first is allowed. Issues are for discussion, questions, unclear scope, or idea validation before coding; they are not permission slips for every change.

## Hard Rules

1. **Do not require an issue for small direct PRs** — docs, small fixes, obvious refactors, and focused workflow changes can go straight to PR.
2. **Use an issue when discussion is needed** — open or link one for questions, unclear scope, disputed behavior, or idea validation before coding.
3. **Keep PRs reviewable** — aim for 400 changed lines or less (`additions + deletions`). Split large changes or explain why the size is unavoidable in the PR body.
4. **Use Conventional Commits** — examples: `docs: simplify contribution flow`, `fix(cli): handle invalid config`.
5. **Run relevant validation** — use AGH's Python/uv validation commands; add Docker validation only for Docker/runtime changes.
6. **No invented gates** — do not require `status:approved`, `type:*` labels, mandatory issue links, or labels not documented in `CONTRIBUTING.md`.
7. **No AI attribution** — never add `Co-Authored-By` or AI-generated trailers.

## Workflow

```text
1. Start from main and inspect the current state.
2. Decide whether an issue is needed.
3. Create a focused branch using the naming convention below.
4. Make one reviewable work unit.
5. Run relevant validation.
6. Commit with a Conventional Commit subject.
7. Open a PR using `.github/pull_request_template.md`.
8. Wait for required checks, then merge only with maintainer approval.
```

## Issue Decision

| Situation | Action |
| --- | --- |
| Typo, docs-only update, small bug fix, clear refactor | Open a direct PR. Leave `Related issue` blank or say none. |
| Question, unclear behavior, uncertain scope, idea validation | Open or link an issue first. |
| Large but maintainer-approved change with clear scope | Direct PR is allowed; explain context and size. |
| PR exceeds 400 changed lines | Split it, or explain why it stays large in `Context` or `Notes`. |

## Branch Naming

Use lowercase branches with a Conventional Commit-style prefix:

```text
docs/<short-topic>
fix/<short-topic>
feat/<short-topic>
refactor/<short-topic>
test/<short-topic>
ci/<short-topic>
chore/<short-topic>
```

Rules:
- Branch from `main`.
- Use lowercase words separated by hyphens.
- Keep the branch scoped to one reviewable outcome.

Examples:

```text
docs/simplify-contribution-flow
fix/invalid-pack-manifest
ci/update-release-validation
chore/add-branch-pr-skill
```

## PR Body Format

Follow `.github/pull_request_template.md`.

```markdown
## Summary

- <what changed>

## Related issue

Closes #<N>
```

Use `Closes/Fixes/Resolves #N` only when the PR closes an issue. For a direct PR, write `None` or leave a short explanation.

```markdown
## Context

<why this change is needed and what it changes>

## Validation

- [x] `uv run pytest`
- [x] `uv run --with ruff ruff check .`
- [x] `uv run --with ruff ruff format --check .`
- [x] `uv run --with pyright pyright agh tests`

## Notes

- Release needed: yes/no
- Docs updated: yes/no
```

If validation is intentionally narrower, state the exact command and why it is sufficient.

## Validation Commands

Default full validation:

```bash
uv run pytest
uv run --with ruff ruff check .
uv run --with ruff ruff format --check .
uv run --with pyright pyright agh tests
```

For docs or workflow metadata changes, use the narrowest relevant test when available, then say why full runtime validation was not needed.

For Docker/runtime changes, also run:

```bash
docker build --check .
```

## Commit Rules

Use this format:

```text
<type>(optional-scope): <imperative summary>
```

Allowed types:

| Type | Use |
| --- | --- |
| `feat` | New behavior or product improvement. |
| `fix` | Bug fix. |
| `docs` | Documentation-only change. |
| `refactor` | Code restructuring without behavior change. |
| `test` | Test-only change. |
| `ci` | GitHub Actions or automation. |
| `chore` | Maintenance, tooling, metadata. |
| `build` | Build/package/container changes. |

Examples:

```text
docs: simplify contribution flow
fix(cli): handle invalid pack manifest
test(docs): align contribution flow assertions
chore(skills): add AGH branch PR workflow
```

## Commands

```bash
# Start clean
git checkout main
git pull --ff-only

# Create a branch
git checkout -b docs/<short-topic>

# Inspect review size
git diff --stat

# Commit
git add <files>
git commit -m "docs: describe the change"

# Push and open PR
git push -u origin docs/<short-topic>
gh pr create --base main --head docs/<short-topic>
```

## Output Contract

Return:
- Branch name and PR URL.
- Commit subject(s).
- Whether an issue was linked, and why or why not.
- Changed-line estimate and whether it stays within the review budget.
- Validation commands and results.
- Merge status and any maintainer-approved exception.

## References

- `CONTRIBUTING.md` — current contribution policy.
- `.github/pull_request_template.md` — PR body contract.
- `.github/workflows/ci.yml` — required CI validation.

## Notices

Adapted from `skills/branch-pr/SKILL.md` in
[`Gentleman-Programming/gentle-ai`](https://github.com/Gentleman-Programming/gentle-ai),
licensed under Apache-2.0. This version was modified for Agent Guidance Hub's
PR-first contribution policy.
