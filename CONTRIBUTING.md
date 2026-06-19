# Contributing

Open a PR directly for small, focused changes. Open an issue first when a change needs discussion: large features, behavior changes, or architecture, security, and product decisions.

Keep changes small and reviewable.

## Workflow

1. Branch off `main`.
2. Make a focused change.
3. Run the validation commands.
4. Open a PR with a clear summary.

Open an issue before the PR when the work is large, ambiguous, or touches a shared decision. Small fixes and docs can go straight to a PR.

## Labels

These labels track the kind of work:

| Label | Use it for |
|-------|------------|
| `bug` | Reproducible defects. |
| `enhancement` | New behavior or product improvements. |
| `documentation` | Documentation changes or gaps. |
| `question` | Questions that need maintainer input. |

Issue templates apply `bug` or `enhancement`. Maintainers add the rest during triage.

## Review size

Keep PRs small enough for one focused review. Aim for **400 changed lines or less** (`additions + deletions`).

Split a change by behavior or workflow when it grows past that budget. If a large diff is unavoidable, say why in the PR body before asking for review.

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
