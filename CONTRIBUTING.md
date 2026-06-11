# Contributing

AGH uses an issue-first workflow. Keep changes small and reviewable.

## Workflow

1. Search existing issues.
2. Open a bug report or feature request.
3. Wait for a maintainer to add `status:approved`.
4. Create a branch and open a PR that links the issue with `Closes #N`, `Fixes #N`, or `Resolves #N`.
5. Add exactly one `type:*` label to the PR.

PRs without an approved linked issue or exactly one `type:*` label fail validation.

## Labels

Add exactly one PR type label:

| Label | Use it for |
|-------|------------|
| `type:bug` | Bug fixes. |
| `type:feature` | New behavior or product improvements. |
| `type:docs` | Documentation-only changes. |
| `type:refactor` | Code changes without behavior changes. |
| `type:chore` | Tooling, dependency, workflow, or repo maintenance. |
| `type:breaking-change` | Breaking API, CLI, config, or packaging changes. |

Issue status labels:

| Label | Meaning |
|-------|---------|
| `status:needs-review` | A maintainer still needs to review the issue. |
| `status:approved` | The issue is approved for implementation. |
| `status:blocked` | Work cannot move yet. |

## Review size

Keep PRs small enough for one focused review. Aim for **400 changed lines or less** (`additions + deletions`).

If a change grows past that budget, split it by behavior or workflow. If a large diff is unavoidable, say why in the PR body before asking for review.

## Branches and commits

Use conventional commits:

```text
feat: add workspace option
fix: handle invalid pack manifest
docs: clarify Docker setup
chore: update workflow checks
```

Prefer one focused change per PR. Split large changes before review becomes hard.

## Before opening a PR

Check this before opening a PR:

- [ ] The issue has `status:approved`.
- [ ] The PR body links the issue with `Closes #N`, `Fixes #N`, or `Resolves #N`.
- [ ] The PR has exactly one `type:*` label.
- [ ] The diff is reviewable, or the PR body explains why it is large.
- [ ] Commits use conventional commit messages.
- [ ] You ran the relevant validation commands.
- [ ] You self-reviewed the diff.

## Development

Install dependencies:

```bash
uv sync
```

Run validation before opening a PR:

```bash
uv run pytest
uv run --with ruff ruff check .
uv run --with ruff ruff format --check .
uv run --with pyright pyright agh tests
```

For Docker/runtime changes, also run:

```bash
docker build --check .
```

## Docs

README is the landing page and the usage guide. Keep user-facing docs in `README.md` and mirror them in `README.es.md`.

When a user-facing docs change affects both languages, update the English README and the Spanish mirror in the same PR.

## Releases

Most docs, workflow, and repo-hygiene changes do not need a release tag.

Tag a release only when publishing a package or container change:

```bash
git tag vX.Y.Z
git push origin vX.Y.Z
```
