## Future Slice Notes

These notes preserve context from the larger `support-name-identifiers` design. They are historical context for completed follow-up slices, not pending PR1 requirements or acceptance criteria.

## PR2: User Email Refs — completed

Intent: resolve a registered user email to its canonical `usr_...` identifier via a dedicated server endpoint. The API stays ID-only for actions; this is a read-only convenience lookup.

Completed behavior:
- Add `GET /api/v1/users/by-email/{email:path}` returning `{id, email}` on exact active visible-user match.
- Return `400` for malformed email, `401` for unauthenticated, and `404` for missing or out-of-scope emails.
- Keep exact stored-email matching only; no partial, prefix, fuzzy, or case-normalized matching.
- Add `agh user show` and resolve user refs for user update/delete/token/member commands while preserving `usr_...` passthrough.

## PR3: Pack Version Refs — completed

Intent: resolve pack-version refs for project-pack commands without making PR1 responsible for pack behavior.

Completed behavior:
- Add pack-version ref parsing helpers for `packv_...`, `<domain>/<name>@<version>`, and `<name>@<version>`.
- Add `GET /api/v1/packs/versions:resolve?ref=<ref>` returning `id`, `pack_ref`, `domain`, `name`, and `version`.
- Return `400` for malformed refs, `404` for missing refs, and `409` when a no-domain `name@version` ref matches multiple domains.
- Resolve project-pack `pack_ref` inputs through the pack resolver where needed, while preserving existing domain-qualified pack refs.

Remaining follow-up slices: none.
