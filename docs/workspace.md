# Workspace Guide

A workspace is a git repo linked to one AGH project. The repo gets the packs assigned to that project.

## Commands

| Command | What it does | Writes files? |
|---------|--------------|---------------|
| `agh sync` | Matches the git remote to an AGH project and writes `.agh/project.toml`. | Yes |
| `agh agent` / `agh agent show` | Shows Claude Code/OpenCode availability and the current local selection. | No |
| `agh agent select claude` | Selects Claude Code for this workspace in `.agh-cache/preferences.toml`. | Yes |
| `agh agent select opencode` | Selects OpenCode for this workspace in `.agh-cache/preferences.toml`. | Yes |
| `agh agent clear` | Removes the local workspace agent selection. | Yes |
| `agh pull --dry-run` | Fetches the server plan and downloads selected-agent files in memory. | No |
| `agh pull` | Applies instructions and skills for the selected agent, refreshes `.agh-cache/packs/`, and writes `.agh/lock.toml`. | Yes |
| `agh pull --force` | Replaces conflicted AGH blocks or skill targets for the selected agent. | Yes |

## Local agent selection

Each developer chooses one local agent target per workspace. AGH stores that preference in local cache state:

```toml
# .agh-cache/preferences.toml
[agents]
target = "opencode" # or "claude"
```

Use one of these commands:

```bash
agh agent select claude
agh agent select opencode
```

`agh pull` reads this file before applying anything. If it is missing and stdin is an interactive TTY, AGH asks:

```text
Which agent do you use for this workspace?
1. Claude Code
2. OpenCode
3. Skip for now
```

There is no `both` option. If you choose Skip, AGH exits with code `2` and does not apply guidance. In non-interactive shells, AGH exits with code `2` and tells you to run `agh agent select claude` or `agh agent select opencode`.

## Pull flow

```text
1. Read .agh/project.toml
2. Read or prompt for .agh-cache/preferences.toml
3. Ask the server what this project should use
4. Download only artifacts for the selected agent through relative /api/v1/... URLs
5. Check each checksum
6. Apply instructions and skills for the selected agent
7. Write .agh/lock.toml for the applied artifacts
```

AGH writes the lockfile only after the repo files are updated.

## Instructions use markers

`AGENTS.md` and `CLAUDE.md` can contain your own text plus AGH-managed blocks. AGH only updates the block it owns.

```md
<!-- AGH-BEGIN pack="<pack-ref>" artifact="instructions/AGENTS.md" checksum="sha256:..." -->
Project instructions from AGH live here.
<!-- AGH-END pack="<pack-ref>" -->
```

If you edit inside the block, the next `agh pull` exits with conflict code `3`. Use `agh pull --force` when you want AGH to replace that block.

## Skills stay clean

Skills do not use AGH markers. AGH writes or links them at the paths agents already expect. It only writes paths for the selected local agent:

```text
# claude
.claude/skills/<skill>/SKILL.md

# opencode
.opencode/skills/<skill>/SKILL.md
```

AGH tries a relative symlink to `.agh-cache/packs/...`. If the OS rejects symlinks, AGH copies the file. The lockfile records which one happened:

```toml
mode = "symlink" # or mode = "copy"
source = ".agh-cache/packs/<domain>/<name>/<version>/skills/<skill>/SKILL.md"
```

AGH only writes these MVP skill targets:

- `.claude/skills/<skill>/SKILL.md`
- `.opencode/skills/<skill>/SKILL.md`

It does not write Cursor, Codex, Pi, or global agent paths.

## Cache and lockfile

| Path | Purpose | Commit? |
|------|---------|---------|
| `.agh/project.toml` | Links the repo to an AGH project. | Yes |
| `.agh/lock.toml` | Records versions, checksums, source paths, and placement modes for applied artifacts. | Yes |
| `.agh-cache/preferences.toml` | Stores this developer's local agent selection. | No |
| `.agh-cache/packs/` | Downloaded pack files. AGH can rebuild it. | No |
| `.claude/skills/`, `.opencode/skills/` | Generated skill targets for the selected agent. Commit only if your team wants them reviewed in Git. | Team choice |

Add this to `.gitignore`:

```gitignore
.agh-cache/
```

After a successful non-dry-run pull, AGH prints a hint if the repo does not ignore `.agh-cache/`.

If skill targets are symlinks, a fresh clone needs `agh pull` to rebuild `.agh-cache/packs/` before those links resolve.

If this repo has an old pre-release `.agh/packs/` cache, you can delete it after running a current `agh pull`.

## Exit codes

| Code | Meaning |
|------|---------|
| `0` | Success or no changes. |
| `1` | Runtime/API/download failure. |
| `2` | Local validation, malformed manifest, or missing/skipped agent selection. |
| `3` | Conflict. |
| `4` | Authentication/authorization failure. |
| `5` | Workspace is not linked; run `agh sync`. |
