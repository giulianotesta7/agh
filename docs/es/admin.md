# Admin

La administración de AGH cubre el primer owner token, usuarios, roles y ciclo de vida de tokens. AGH muestra tokens una sola vez cuando los crea o resetea.

## Bootstrap owner

Levantá el servicio Docker con el email owner definido en `compose.yaml`:

```bash
docker compose up -d
```

En el primer startup, AGH crea el owner y escribe el primer token una sola vez:

```text
/data/secrets/initial_owner_token
```

Usá ese token para loguearte:

```bash
agh login \
  --url http://127.0.0.1:8912 \
  --email owner@example.com \
  --token "$(docker run --rm -v agh-data:/data busybox cat /data/secrets/initial_owner_token)"
```

Tratà ese archivo como secret. AGH guarda hashes de tokens en SQLite, no tokens plaintext.

## Roles

| Role | Alcance actual |
|------|----------------|
| `owner` | Administración completa. Puede gestionar owners, admins, members, proyectos, packs y tokens. |
| `admin` | Puede gestionar usuarios member y acceso a proyectos. No puede gestionar owners. |
| `member` | Puede leer proyectos activos asignados y hacer pull de packs asignados. |

## Ver config local

```bash
agh config show
```

Ejemplo:

```text
instance_url = http://127.0.0.1:8912
email = owner@example.com
token = ****
```

`config show` enmascara el token guardado.

## Listar usuarios

```bash
agh user list
```

Ejemplo:

```text
USER_ID               EMAIL              ROLE   STATUS
usr_...               owner@example.com  owner  active
usr_...               dev@example.com    member active
```

## Crear un usuario

```bash
agh user create dev@example.com --role member
```

Ejemplo:

```text
Created user dev@example.com (usr_...).
Role: member
Status: active
Token: <plaintext-token>
Store this token now. AGH will not show it again.
```

Copiá el token en ese momento. AGH no vuelve a mostrar ese plaintext token.

## Actualizar o desactivar un usuario

```bash
agh user update usr_... --role admin
agh user update usr_... --inactive
agh user delete usr_...
```

Ejemplos:

```text
Updated user dev@example.com (usr_...).
Role: admin
Status: active
```

```text
Deactivated user dev@example.com (usr_...).
```

## Rotar o resetear tokens

Usá `rotate` o `reset` cuando un owner o usuario con permisos admin emite un token nuevo para un usuario target. Ambos comandos reciben el id target `usr_...`.

```bash
agh token rotate usr_...
agh token reset usr_...
```

Ejemplo:

```text
Rotated token for user usr_...
Token: <plaintext-token>
Store this token now. AGH will not show it again.
```

Los comandos de token revocan tokens activos previos para ese usuario y muestran el replacement token una sola vez.

## Checklist admin

- Guardá el primer owner token de forma segura.
- Creá usuarios con nombre en vez de compartir un token.
- Rotá o reseteá tokens cuando un token se filtre.
- Usá `agh config show` para confirmar qué server y cuenta usa tu CLI.
