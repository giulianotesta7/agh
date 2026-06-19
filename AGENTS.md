# AGH — Agent Skills Index

When working on this project, load the relevant skill(s) BEFORE creating issues,
commits, branches, pull requests, or review slices.

## How to Use

1. Check the trigger column to find skills that match your current task.
2. Load the skill by reading the `SKILL.md` file at the listed path.
3. Follow all patterns and rules from the loaded skill.
4. Multiple skills can apply simultaneously.
5. Prefer AGH-local skills over generic workflow skills when rules conflict.

## Skills

| Skill | Trigger | Path |
| --- | --- | --- |
| `agh-branch-pr` | Creating branches, commits, PRs, PR bodies, merge plans, or checking PR readiness. | `skills/agh-branch-pr/SKILL.md` |
| `agh-issue-flow` | Creating, shaping, or triaging AGH issues, bug reports, feature requests, questions, or duplicate checks. | `skills/agh-issue-flow/SKILL.md` |
| `agh-work-unit-commits` | Splitting commits, planning reviewable work units, pairing validation with changes, or checking review size. | `skills/agh-work-unit-commits/SKILL.md` |
| `agh-chained-pr` | Planning stacked/chained PRs, review slices, or changes that may exceed the 400-line review budget. | `skills/agh-chained-pr/SKILL.md` |

## Composition

- For normal PR work: load `agh-branch-pr`.
- Before committing non-trivial changes: load `agh-work-unit-commits` with
  `agh-branch-pr`.
- For unclear scope or discussion-first work: load `agh-issue-flow` before
  deciding whether to open an issue or direct PR.
- For large diffs: load `agh-chained-pr` with `agh-work-unit-commits`.
