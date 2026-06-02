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

## Crear un template de pack

Usá `agh pack init` para crear el manifest y los directorios vacíos del pack:

```bash
agh pack init ./my-pack --domain acme --name onboarding --version 1.0.0
```

Esto crea:

```text
my-pack/
├── agh.pack.toml
├── instructions/
└── skills/
```

El manifest default empieza así:

```toml
domain = "acme"
name = "onboarding"
version = "1.0.0"
description = "TODO"
```

Customizá metadata y starter files opcionales con flags:

```bash
agh pack init ./review-pack \
  --domain acme \
  --name review \
  --version 1.0.0 \
  --description "Shared review skills" \
  --with-skill reviewer
```

Starter flags disponibles:

- `--with-agents` crea `instructions/AGENTS.md`.
- `--with-claude` crea `instructions/CLAUDE.md`.
- `--with-skill NAME` crea `skills/NAME/SKILL.md`; repetilo para crear varias skills.

## Reglas del manifest

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
