# Packs

A pack is a versioned set of instruction files and skills. Publish a pack once, then assign that version, or `latest`, to projects.

## Pack layout

Start with this shape:

```text
my-pack/
├── agh.pack.toml
├── instructions/
│   ├── AGENTS.md
│   └── CLAUDE.md
└── skills/
    └── reviewer/
        └── SKILL.md
```

A pack can contain instructions, skills, or both. It must include at least one instruction file or skill. Skills use one directory per skill name.

## Manifest

Create `agh.pack.toml` from this template:

```toml
domain = "acme"
name = "onboarding"
version = "1.0.0"
description = "Shared onboarding instructions and review skills."
```

There is no generator command for this file yet. Copy the template, then edit the values for your team and pack.

Rules:

- `version` must be an exact SemVer version such as `1.0.0`.
- Published versions are immutable. Publish `1.0.1` for changes.
- Do not publish `latest`. Use `latest` when assigning a pack to a project.

## Allowed files

AGH accepts the pack files it knows how to place:

- `agh.pack.toml`
- `instructions/AGENTS.md`
- `instructions/CLAUDE.md`
- `skills/<name>/SKILL.md`

Use UTF-8 text files. Do not include symlinks in a pack directory.

## Publish a pack

From the AGH repo or any shell with `agh` installed:

```bash
agh pack publish ./my-pack
```

Successful output uses the plain CLI style:

```text
Published acme/onboarding@1.0.0.
Pack ID: pack_...
Description: Shared onboarding instructions and review skills.
Checksum: sha256:...
```

## List published packs

```bash
agh pack list
```

Example:

```text
PACK_REF               DESCRIPTION
acme/onboarding@1.0.0  Shared onboarding instructions and review skills.
```

## Next step

Assign the pack to a project:

```bash
agh project pack add prj_... acme/onboarding@latest
```

See [Projects](projects.md) for assignments and [Workspace guide](workspace.md) for `agh pull`.
