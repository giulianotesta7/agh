---
name: agh-changelog
description: "Trigger: AGH user-facing change, Towncrier fragment, changelog, release notes. Decide and write changelog fragments."
license: Apache-2.0
metadata:
  author: "giulianotesta7"
  version: "1.0"
---

# AGH — Changelog Skill

## Activation Contract

Load this skill when changing user-visible AGH behavior, preparing release notes,
creating or validating Towncrier fragments, or deciding whether a change needs a
changelog entry.

Use it with `agh-work-unit-commits` for implementation work and with
`agh-docs-alignment` when contributor docs, release docs, or validation commands
change.

Do not use this skill for tests-only changes, invisible refactors, formatting,
typing cleanup, or minor documentation typos unless the user explicitly asks for
release-note coverage.

## Hard Rules

1. **Changelog entries are for users, integrators, and operators.** Record what
   changes for someone installing, upgrading, operating, or scripting AGH.
2. **Create one Towncrier fragment per user-facing work unit.** Keep tests,
   docs, and the fragment with the behavior they describe.
   Do not defer fragments to a later aggregate/final PR when the current PR
   changes user-visible behavior; AGH CI runs `towncrier check` on every PR
   unless the documented `no-changelog-needed` label is present.
3. **Do not map commit types blindly.** A `feat` or `fix` usually needs a
   fragment; `build`, `ci`, `docs`, or `refactor` need one only when the result
   is observable by AGH users or operators.
4. **Write fragments in user language, not implementation language.** Describe
   the outcome, not internal files or helper names.
5. **Use orphan fragments for changes without an issue.** Prefix the fragment
   id with `+`, for example `changelog.d/+workspace-lock-validation.fixed.md`.
6. **Use issue or PR numbers when available.** Prefer
   `changelog.d/123.fixed.md` when the change is tracked by issue/PR `#123`.
7. **Do not edit `CHANGELOG.md` during normal PR work.** Release maintainers run
   `uv run towncrier build --version X.Y.Z --yes` before tagging.
8. **Use only documented labels.** If no fragment is required, request or apply
   `no-changelog-needed` only because it is documented in `CONTRIBUTING.md`;
   never invent a replacement label.
9. **Generated technical artifacts stay in English.** Changelog fragments,
   release notes, filenames, and validation commands are English by default.
10. **SDD/chained PR slices still need fragments per user-facing slice.** A
   later docs/changelog cleanup slice may consolidate README or release-note
   prose, but it does not satisfy CI for earlier behavior-changing PRs.

## Fragment Types

| Type | Use for |
| --- | --- |
| `added` | New CLI, server, package, workspace, Docker, or distribution behavior. |
| `changed` | Changed behavior, output, configuration, operational flow, or defaults. |
| `fixed` | User-visible bugs, confusing errors, broken resolution, install/runtime defects. |
| `breaking` | Incompatible API, CLI, config, lockfile, package, or distribution changes. |
| `docs` | Important operator-facing docs that change how users install, upgrade, or run AGH. |

## Decision Gates

| Change | Fragment? |
| --- | --- |
| CLI command, option, output, or error behavior changes | Yes |
| Server/API behavior, validation, auth, persistence, or response changes | Yes |
| Package publish/pull/assignment/lockfile behavior changes | Yes |
| Docker runtime, PyPI, Homebrew, GHCR, install, or release behavior changes | Yes |
| Security, data exposure, compatibility, migration, or breaking change | Yes |
| User-facing docs that affect operation or upgrade decisions | Usually `docs` |
| Tests-only, lint, formatting, typing, private helper refactor | No |
| Broad internal refactor with no observable behavior change | No |
| Minor typo or prose cleanup | No |

When unsure, ask: "Should someone upgrading AGH learn this from the release
notes?" If yes, create a fragment. If no, rely on the PR and commit history and
use/request the documented `no-changelog-needed` label when CI needs a skip.

## Execution Steps

1. Identify the work unit and whether it changes observable behavior.
2. Choose the fragment type from the table above.
3. Choose the fragment id:
   - issue/PR number when known, e.g. `57.fixed.md`;
   - orphan id for untracked changes, e.g. `+clear-ambiguous-package-error.fixed.md`.
4. Create the file under `changelog.d/` with one concise sentence.
5. Start with an imperative or outcome verb such as `Add`, `Change`, `Fix`,
   `Remove`, `Document`, or `Require`.
6. Avoid implementation details, test names, file paths, and agent/process
   language unless they are user-visible.
7. Validate with `uv run towncrier check` when the branch should contain a
   fragment, and `git diff --check` for whitespace sanity.
8. For SDD or stacked/chained work, repeat this decision for each PR slice. If
   the slice is user-facing, add the fragment in that slice; if it is not,
   document why `no-changelog-needed` applies.

## Examples

Good fragment:

```text
Fix package reference resolution when multiple domains contain the same package name.
```

Weak fragment:

```text
Refactor package resolver and update tests.
```

Good filenames:

```text
changelog.d/57.fixed.md
changelog.d/+workspace-status.added.md
changelog.d/+docker-data-ownership.changed.md
changelog.d/+legacy-lockfile.breaking.md
```

## Validation

```bash
uv run towncrier check
uv run towncrier build --version X.Y.Z --yes
```

Use `towncrier check` for PR validation. Use `towncrier build` only during the
release-preparation commit; it updates `CHANGELOG.md` and removes consumed
fragments.

## Output Contract

Return:

- Whether a changelog fragment was required, and why.
- Fragment path created or the reason no fragment was needed.
- Fragment type chosen.
- Validation commands run and results.
- Any release-note ambiguity that needs human review.

## References

- `pyproject.toml` — Towncrier configuration.
- `CHANGELOG.md` — generated release history.
- `changelog.d/README.md` — fragment naming and type guide.
- `CONTRIBUTING.md` — contributor-facing changelog policy.
- `skills/agh-work-unit-commits/SKILL.md` — keep fragments with the work unit.
- `skills/agh-docs-alignment/SKILL.md` — docs and validation command alignment.
