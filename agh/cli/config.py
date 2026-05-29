"""Local AGH CLI configuration and login helpers."""

from __future__ import annotations

from contextlib import suppress
from dataclasses import dataclass
import json
import os
from pathlib import Path
import tempfile
import tomllib
from typing import Any, NoReturn
import urllib.error
import urllib.request

import typer


class _NoRedirectHandler(urllib.request.HTTPRedirectHandler):
    """Reject redirects so Bearer tokens are never forwarded to another URL."""

    def redirect_request(self, req, fp, code, msg, headers, newurl):  # type: ignore[no-untyped-def]
        return None


_NO_REDIRECT_OPENER = urllib.request.build_opener(_NoRedirectHandler)

DEFAULT_CONFIG_PATH = Path.home() / ".config" / "agh" / "config.toml"
CONFIG_PATH_ENV = "AGH_CONFIG_FILE"


class ConfigError(RuntimeError):
    """Raised when local CLI configuration cannot be read or written."""


class LoginValidationError(RuntimeError):
    """Raised when remote login validation fails."""


@dataclass(frozen=True)
class AghConfig:
    """Local AGH connection configuration."""

    instance_url: str
    email: str
    token: str


def get_config_path() -> Path:
    """Return the effective config path, allowing tests/users to override it."""
    override = os.environ.get(CONFIG_PATH_ENV, "").strip()
    if override:
        return Path(override).expanduser()
    return DEFAULT_CONFIG_PATH


def normalize_instance_url(url: str) -> str:
    """Normalize an AGH instance URL for storage and request composition."""
    normalized = url.strip().rstrip("/")
    if not normalized:
        raise ConfigError("Instance URL is required")
    if not normalized.startswith(("http://", "https://")):
        raise ConfigError("Instance URL must start with http:// or https://")
    return normalized


def load_config(path: Path | None = None) -> AghConfig:
    """Load local config from TOML."""
    config_path = path or get_config_path()
    try:
        raw = tomllib.loads(config_path.read_text(encoding="utf-8"))
    except FileNotFoundError as exc:
        raise ConfigError(
            f"No AGH config found at {config_path}. Run 'agh login'."
        ) from exc
    except tomllib.TOMLDecodeError as exc:
        raise ConfigError(f"Invalid AGH config at {config_path}: {exc}") from exc

    try:
        return AghConfig(
            instance_url=str(raw["instance_url"]),
            email=str(raw["email"]),
            token=str(raw["token"]),
        )
    except KeyError as exc:
        raise ConfigError(f"AGH config missing required field: {exc.args[0]}") from exc


def save_config(config: AghConfig, path: Path | None = None) -> None:
    """Atomically write local config with restrictive permissions where supported."""
    config_path = path or get_config_path()
    config_path.parent.mkdir(parents=True, exist_ok=True)
    text = _format_config(config)

    fd, temp_name = tempfile.mkstemp(
        prefix=f".{config_path.name}.", suffix=".tmp", dir=config_path.parent
    )
    temp_path = Path(temp_name)
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as handle:
            handle.write(text)
            handle.flush()
            os.fsync(handle.fileno())
        with suppress(OSError):
            os.chmod(temp_path, 0o600)
        os.replace(temp_path, config_path)
        with suppress(OSError):
            os.chmod(config_path, 0o600)
    except Exception:
        with suppress(FileNotFoundError):
            temp_path.unlink()
        raise


def validate_login(*, instance_url: str, email: str, token: str) -> dict[str, Any]:
    """Validate login credentials using GET /api/v1/me."""
    request = urllib.request.Request(
        f"{instance_url}/api/v1/me",
        headers={"Authorization": f"Bearer {token}", "Accept": "application/json"},
        method="GET",
    )
    try:
        with _NO_REDIRECT_OPENER.open(request, timeout=10) as response:  # noqa: S310 - user-provided AGH URL
            status_code = response.status
            body = response.read()
    except urllib.error.HTTPError as exc:
        if 300 <= exc.code < 400:
            raise LoginValidationError(
                "Login validation failed: /me redirects are not allowed"
            ) from exc
        raise LoginValidationError(
            f"Login validation failed: /me returned HTTP {exc.code}"
        ) from exc
    except urllib.error.URLError as exc:
        reason = getattr(exc, "reason", exc)
        raise LoginValidationError(f"Login validation failed: {reason}") from exc
    except TimeoutError as exc:
        raise LoginValidationError(f"Login validation failed: {exc}") from exc

    if status_code != 200:
        raise LoginValidationError(
            f"Login validation failed: /me returned HTTP {status_code}"
        )

    try:
        payload = json.loads(body.decode("utf-8"))
    except json.JSONDecodeError as exc:
        raise LoginValidationError(
            "Login validation failed: /me returned invalid JSON"
        ) from exc

    actual_email = str(payload.get("email", ""))
    if actual_email.lower() != email.lower():
        raise LoginValidationError(
            f"Login validation failed: /me email {actual_email!r} does not match {email!r}"
        )
    return payload


def mask_token(token: str) -> str:
    """Return a display-safe token mask."""
    if len(token) <= 4:
        return "****"
    if len(token) <= 8:
        return f"{token[:2]}****"
    return f"{token[:4]}****{token[-4:]}"


def _format_config(config: AghConfig) -> str:
    return "".join(
        [
            f'instance_url = "{_toml_escape(config.instance_url)}"\n',
            f'email = "{_toml_escape(config.email)}"\n',
            f'token = "{_toml_escape(config.token)}"\n',
        ]
    )


def _toml_escape(value: str) -> str:
    return value.replace("\\", "\\\\").replace('"', '\\"')


def fail(message: str, *, code: int = 1) -> NoReturn:
    """Print an error and exit with a stable non-zero status."""
    typer.secho(f"Error: {message}", fg=typer.colors.RED, err=False)
    raise typer.Exit(code)
