# Packs

Un pack es un conjunto versionado de archivos de instrucciones y skills. Publicás un pack una vez y después asignás esa versión, o `latest`, a proyectos.

## Layout del pack

Empezá con esta forma:

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

Un pack puede contener instrucciones, skills o ambas. Debe incluir al menos un archivo de instrucciones o una skill. Las skills usan un directorio por nombre de skill.

## Manifest

Creá `agh.pack.toml` desde este template:

```toml
domain = "acme"
name = "onboarding"
version = "1.0.0"
description = "Shared onboarding instructions and review skills."
```

Todavía no hay comando generator para este archivo. Copiá el template y editá los valores para tu equipo y pack.

Reglas:

- `version` debe ser una versión SemVer exacta, como `1.0.0`.
- Las versiones publicadas son inmutables. Publicá `1.0.1` para cambios.
- No publiques `latest`. Usá `latest` cuando asignás un pack a un proyecto.

## Archivos permitidos

AGH acepta los archivos de pack que sabe colocar:

- `agh.pack.toml`
- `instructions/AGENTS.md`
- `instructions/CLAUDE.md`
- `skills/<name>/SKILL.md`

Usá archivos de texto UTF-8. No incluyas symlinks en el directorio del pack.

## Publicar un pack

Desde el repo de AGH o cualquier shell con `agh` instalado:

```bash
agh pack publish ./my-pack
```

Salida exitosa:

```text
Published acme/onboarding@1.0.0.
Pack ID: pack_...
Description: Shared onboarding instructions and review skills.
Checksum: sha256:...
```

## Listar packs publicados

```bash
agh pack list
```

Ejemplo:

```text
PACK_REF               DESCRIPTION
acme/onboarding@1.0.0  Shared onboarding instructions and review skills.
```

## Próximo paso

Asigná el pack a un proyecto:

```bash
agh project pack add prj_... acme/onboarding@latest
```

Mirá [Proyectos](projects.md) para assignments y [Workspace](workspace.md) para `agh pull`.
