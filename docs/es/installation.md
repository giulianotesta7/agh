# Instalación

AGH tiene dos partes:

- el server, que corre con Docker;
- el CLI local `agh`, que instalás en tu workstation.

Instalá el CLI primero. Después usalo para login, administración de packs/proyectos y operaciones de workspace.

## Instalar el CLI desde el paquete

Instalalo sin clonar el repo:

```bash
curl -fsSL https://raw.githubusercontent.com/giulianotesta7/AgentGuidanceHub/main/scripts/install.sh | sh
```

El instalador ejecuta:

```bash
uv tool install --force agh
```

El instalador no edita archivos de arranque del shell, estado de Docker, config de AGH ni credenciales de login.

Verificá el comando:

```bash
agh --help
```

El instalador deja el binario `agh` disponible en el `PATH` del usuario. Los comandos de workspace resuelven el repo desde el directorio de trabajo actual.

## Instalar el CLI desde un checkout

Para desarrollo antes de publicar el paquete, cloná el repo e instalá desde el checkout directamente:

```bash
git clone https://github.com/giulianotesta7/AgentGuidanceHub.git
cd AgentGuidanceHub
uv tool install --force .
```

## PATH troubleshooting

Si el script termina pero `agh` no aparece, agregá el bin dir de uv tool al shell:

```bash
uv tool update-shell
```

Reiniciá el shell y probá otra vez:

```bash
agh --help
```

Para ver el directorio de uv tools:

```bash
uv tool dir
```

## Desinstalar

```bash
uv tool uninstall agh
```

## Instalar el server

El server es Docker-first. Usá Docker Compose con la imagen publicada y un volumen persistente en `/data`:

```bash
docker compose up -d
```

El compose file usa:

```text
ghcr.io/giulianotesta7/agent-guidance-hub:0.1.0
```

Para un comando directo con `docker run`, `/data`, logs, healthcheck, backup y upgrades, mirá [Operaciones](operations.md).
