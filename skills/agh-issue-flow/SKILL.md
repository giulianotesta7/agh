---
name: agh-issue-flow
description: "Trigger: AGH issue, bug report, feature request, question, triage. Create useful AGH issues without PR permission gates."
license: Apache-2.0
metadata:
  author: "giulianotesta7"
  version: "1.0"
---

# AGH — Issue Flow Skill

## Activation Contract

Load this skill when creating, shaping, or triaging GitHub issues for Agent Guidance Hub.

Use the current AGH policy: issues are for useful discussion and traceability, not mandatory approval before every PR. Small, clear work can go straight to PR; issues help when the problem, scope, or desired behavior needs conversation first.

## Hard Rules

1. **Do not treat issues as PR permission slips** — AGH does not require `status:approved` before work starts.
2. **Search first** — avoid duplicate issues; comment on an existing issue when it already covers the same problem.
3. **Use templates when they fit** — bug reports use `bug_report.yml`; feature requests use `feature_request.yml`.
4. **Blank issues are allowed** — use them for cases that do not fit a bug or feature template.
5. **Questions and early ideas go to Discussions** — `.github/ISSUE_TEMPLATE/config.yml` links questions, not-ready ideas, and support requests to GitHub Discussions.
6. **Use only AGH's minimal labels** — `bug`, `enhancement`, `documentation`, `question`.
7. **No invented status workflow** — do not add or require `status:needs-review`, `status:approved`, priority labels, or `type:*` labels.

## Workflow

```text
1. Search existing open and closed issues.
2. Decide whether this belongs in Issues, Discussions, or a direct PR.
3. Choose the right issue shape: bug, feature, documentation/question, or blank issue.
4. Write a title that matches the issue type and affected area.
5. Fill the minimum useful context so a maintainer can decide or reproduce.
6. Apply only documented labels when needed.
7. State whether the issue blocks a PR or is just context for future work.
```

## Decision Tree

| Situation | Destination | Reason |
| --- | --- | --- |
| Reproducible defect | Bug report issue | Needs reproduction, expected behavior, actual behavior, area, OS. |
| Clear improvement request | Feature request issue | Needs problem, proposed solution, affected area, alternatives. |
| Question, support request, or idea not ready | Discussion | Matches `.github/ISSUE_TEMPLATE/config.yml`. |
| Docs gap with clear fix | Direct PR or issue with `documentation` | Direct PR is fine when the fix is obvious. |
| Small clear code fix | Direct PR | No issue needed. |
| Ambiguous scope or behavior | Issue first | Use the issue to clarify before coding. |

## Bug Report

Template: `.github/ISSUE_TEMPLATE/bug_report.yml`
Auto-label: `bug`

Required fields:

| Field | What to provide |
| --- | --- |
| Pre-flight checks | Confirm you searched existing issues. |
| Bug description | One clear statement of what is broken. |
| Steps to reproduce | Numbered steps from a clean state. |
| Expected behavior | What should happen. |
| Actual behavior | What happens instead, including error text. |
| Affected area | CLI, Server/API, Docker/runtime, Packs, Workspace pull, Documentation, CI/release, or Other. |
| Operating system | macOS, Linux, Windows, WSL, or Other. |

Good title examples:

```text
fix(cli): reject invalid pack manifest
fix(docker): preserve owner token across restart
fix(workspace): avoid overwriting local AGENTS.md
```

## Feature Request

Template: `.github/ISSUE_TEMPLATE/feature_request.yml`
Auto-label: `enhancement`

Required fields:

| Field | What to provide |
| --- | --- |
| Pre-flight checks | Confirm you searched existing issues. |
| Problem | The user pain or workflow gap. |
| Proposed solution | User-facing behavior, command, or API shape. |
| Affected area | CLI, Server/API, Docker/runtime, Packs, Workspace pull, Documentation, CI/release, or Other. |

Good title examples:

```text
feat(cli): add workspace status command
feat(server): expose package assignment audit trail
feat(docs): document self-hosted upgrade flow
```

## Labels

Use the minimal AGH label set from `CONTRIBUTING.md`:

| Label | Use |
| --- | --- |
| `bug` | Reproducible defects. |
| `enhancement` | New behavior or product improvements. |
| `documentation` | Documentation changes or gaps. |
| `question` | Questions that need maintainer input. |

Templates apply `bug` or `enhancement`. Do not invent status, priority, or PR type labels.

## Commands

```bash
# Search existing issues
gh issue list --repo giulianotesta7/AgentGuidanceHub --state all --search "<keywords>"

# Create a bug report
gh issue create \
  --repo giulianotesta7/AgentGuidanceHub \
  --template bug_report.yml \
  --title "fix(<scope>): <short description>"

# Create a feature request
gh issue create \
  --repo giulianotesta7/AgentGuidanceHub \
  --template feature_request.yml \
  --title "feat(<scope>): <short description>"

# View an issue
gh issue view <number> --repo giulianotesta7/AgentGuidanceHub
```

## Output Contract

Return:
- Issue destination: bug report, feature request, discussion, blank issue, or direct PR.
- Duplicate-search result.
- Proposed issue title.
- Proposed labels from AGH's minimal set.
- Issue body or fields to submit.
- Whether the issue blocks a PR, and why or why not.

## References

- `CONTRIBUTING.md` — current contribution and label policy.
- `.github/ISSUE_TEMPLATE/bug_report.yml` — bug report fields.
- `.github/ISSUE_TEMPLATE/feature_request.yml` — feature request fields.
- `.github/ISSUE_TEMPLATE/config.yml` — blank issues and Discussions routing.

## Notices

Adapted from `skills/issue-creation/SKILL.md` in
[`Gentleman-Programming/gentle-ai`](https://github.com/Gentleman-Programming/gentle-ai),
licensed under Apache-2.0. This version was modified for Agent Guidance Hub's
PR-first contribution policy and minimal issue-label workflow.
