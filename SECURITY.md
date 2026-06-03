# Security

AGH stores API tokens, project metadata, pack files, and workspace guidance. Treat reports that expose tokens, private repository data, or server storage paths as sensitive.

## Reporting a vulnerability

Do not open a public issue for vulnerabilities or leaked secrets.

Email the maintainer with:

- affected version or commit;
- affected component: CLI, server/API, Docker image, auth, storage, or docs;
- reproduction steps;
- impact;
- suggested fix, if known.

Maintainer contact:

```text
giulianotesta15@gmail.com
```

If you do not have a private contact path, open a minimal GitHub issue that says you need to report a security issue. Do not include secrets, exploit details, logs with tokens, or private URLs.

## Supported versions

Security fixes target the latest released version. Older releases may receive fixes when the risk is severe and the patch is low-risk.

## Scope

In scope:

- token handling and storage;
- auth bypasses;
- path traversal in pack or workspace file handling;
- unsafe redirects or credential forwarding;
- Docker runtime behavior that exposes secrets.

Out of scope:

- issues caused by committing `.agh-cache/` or local secrets;
- public information in sample docs;
- unsupported local modifications.
