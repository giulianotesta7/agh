# Admin

AGH administration covers the first owner token, users, roles, and token lifecycle. Tokens are shown once when AGH creates or resets them.

## Bootstrap owner

Start the Docker service with an owner email from `compose.yaml`:

```bash
docker compose up -d
```

On first startup, AGH creates the owner and writes the first token once:

```text
/data/secrets/initial_owner_token
```

Use that token to log in:

```bash
agh login \
  --url http://127.0.0.1:8912 \
  --email owner@example.com \
  --token "$(docker run --rm -v agh-data:/data busybox cat /data/secrets/initial_owner_token)"
```

Treat that file as a secret. AGH stores token hashes in SQLite, not plaintext tokens.

## Roles

| Role | Current scope |
|------|---------------|
| `owner` | Full administration. Can manage owners, admins, members, projects, packs, and tokens. |
| `admin` | Can manage member users and project access. Cannot manage owners. |
| `member` | Can read assigned active projects and pull assigned packs. |

## Show local config

```bash
agh config show
```

Example:

```text
instance_url = http://127.0.0.1:8912
email = owner@example.com
token = ****
```

`config show` masks the stored token.

## List users

```bash
agh user list
```

Example:

```text
USER_ID               EMAIL              ROLE   STATUS
usr_...               owner@example.com  owner  active
usr_...               dev@example.com    member active
```

## Create a user

```bash
agh user create dev@example.com --role member
```

Example:

```text
Created user dev@example.com (usr_...).
Role: member
Status: active
Token: <plaintext-token>
Store this token now. AGH will not show it again.
```

Copy the token immediately. AGH will not show that plaintext token again.

## Update or deactivate a user

```bash
agh user update usr_... --role admin
agh user update usr_... --inactive
agh user delete usr_...
```

Examples:

```text
Updated user dev@example.com (usr_...).
Role: admin
Status: active
```

```text
Deactivated user dev@example.com (usr_...).
```

## Rotate or reset tokens

Use `rotate` or `reset` when an owner or admin-capable user issues a replacement token for a target user. Both commands take the target `usr_...` id.

```bash
agh token rotate usr_...
agh token reset usr_...
```

Example:

```text
Rotated token for user usr_...
Token: <plaintext-token>
Store this token now. AGH will not show it again.
```

Token commands revoke previous active tokens for that user and print the replacement token once.

## Admin checklist

- Save first owner token securely.
- Create one user per person instead of sharing tokens.
- Rotate or reset tokens when a token leaks.
- Use `agh config show` to confirm which server and account your CLI uses.
