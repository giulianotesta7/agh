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
| ------ | ---------- |
| `bug` | Reproducible defects. |
| `enhancement` | New behavior or product improvements. |
| `documentation` | Documentation changes or gaps. |
| `question` | Questions that need maintainer input. |
| `no-changelog-needed` | Internal changes that do not need release notes. |

Issue templates apply `bug` or `enhancement`. Maintainers add the rest during
triage. Do not create or request labels outside this table unless the label is
added here in the same change.

## Review size

Keep PRs small enough for one focused review. Aim for **400 changed lines or
less** (`additions + deletions`).

Split a change by behavior or workflow when it grows past that budget. If a
large diff is unavoidable, say why in the PR body before asking for review.

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
- [ ] User-facing changes include a Towncrier fragment in `changelog.d/`.
- [ ] You ran the relevant validation commands.
- [ ] You self-reviewed the diff.

## Changelog

AGH uses Towncrier for release notes. Add one fragment for each user-facing
work unit so release maintainers can build `CHANGELOG.md` before tagging.

Create fragments with an issue or PR number when available:

```bash
uv run towncrier create 123.fixed.md
```

Use an orphan fragment for direct changes without a tracker number:

```bash
uv run towncrier create +clear-package-error.fixed.md
```

Use these types:

| Type | Use it for |
| ---- | ---------- |
| `added` | New user-visible behavior. |
| `changed` | Changed behavior, output, configuration, or operations. |
| `fixed` | User-visible bug fixes. |
| `breaking` | Incompatible API, CLI, config, lockfile, or releases. |
| `docs` | Important operator-facing documentation changes. |

Do not add fragments for tests-only changes, internal refactors, formatting,
typing cleanup, or minor documentation typos. Maintainers can apply the
`no-changelog-needed` label when CI should skip the Towncrier check for those
PRs.

Before opening a PR that needs a fragment, run:

```bash
uv run towncrier check
```

Before tagging a release, build the changelog and commit the result:

```bash
uv run towncrier build --version X.Y.Z --yes
```

## Development

Install dependencies:

```bash
uv sync
```

Run validation before opening a PR:

```bash
uv run pytest
uv run towncrier check
uv run --with ruff ruff check .
uv run --with ruff ruff format --check .
uv run --with pyright pyright agh tests
```

For Docker/runtime changes, also run:

```bash
docker build --check .
```

## Docs

README is the landing page and the usage guide. Keep user-facing docs in
`README.md` and mirror them in `README.es.md`.

When a user-facing docs change affects both languages, update the English README
and the Spanish mirror in the same PR.

## Releases

Most docs, workflow, and repo-hygiene changes do not need a release tag.

Tag a release only when publishing a package or container change:

```bash
git tag vX.Y.Z
git push origin vX.Y.Z
```
