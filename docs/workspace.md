# Workspace Guide

A workspace is a git repo linked to one AGH project. The repo gets the packs assigned to that project.

## Commands

| Command | What it does | Writes files? |
|---------|--------------|---------------|
| `agh sync` | Matches the git remote to an AGH project and writes `.agh/project.toml`. | Yes |
| `agh pull --dry-run` | Fetches the server plan and downloads files in memory. | No |
| `agh pull` | Applies instructions and skills, refreshes `.agh-cache/packs/`, and writes `.agh/lock.toml`. | Yes |
| `agh pull --force` | Replaces conflicted AGH blocks or skill targets. | Yes |
| `agh agent` | Shows whether Claude Code/OpenCode paths look available. | No |

## Pull flow

```text
1. Read .agh/project.toml
2. Ask the server what this project should use
3. Download pack files through relative /api/v1/... URLs
4. Check each checksum
5. Apply instructions and skills
6. Write .agh/lock.toml
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

Skills do not use AGH markers. AGH writes or links them at the paths agents already expect:

```text
.claude/skills/<skill>/SKILL.md
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
| `.agh/lock.toml` | Records versions, checksums, source paths, and placement modes. | Yes |
| `.agh-cache/packs/` | Downloaded pack files. AGH can rebuild it. | No |
| `.claude/skills/`, `.opencode/skills/` | Generated skill targets. Commit only if your team wants them reviewed in Git. | Team choice |

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
| `2` | Local validation or malformed manifest. |
| `3` | Conflict. |
| `4` | Authentication/authorization failure. |
| `5` | Workspace is not linked; run `agh sync`. |
