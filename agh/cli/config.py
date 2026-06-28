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

# Flat config keys, written in this stable order so partial edits keep a
# stable, reviewable file shape. Instance URL and credentials are stored
# independently so `config clear` (instance) and `logout` (credentials) do not
# trample each other.
_CONFIG_KEYS = ("instance_url", "email", "token")
INSTANCE_MISSING_MESSAGE = (
    "No AGH instance configured. Run: agh config set INSTANCE_URL"
)


def corrupt_config_recovery_message(path: Path, reason: str) -> str:
    """User-facing guidance for an unparseable config file (no overwrite)."""
    return (
        f"AGH config at {path} is invalid ({reason}). "
        "Fix or remove that file, then run: agh config set INSTANCE_URL"
    )


class ConfigError(RuntimeError):
    """Raised when local CLI configuration cannot be read or written."""


class ConfigCorruptError(ConfigError):
    """Raised when a config file exists but cannot be parsed as TOML.

    Carries the offending path so commands can surface a clear recovery
    message instead of silently masking a corrupt file as "not set".
    """

    def __init__(self, path: Path, reason: str) -> None:
        self.path = path
        self.reason = reason
        super().__init__(f"Invalid AGH config at {path}: {reason}")


class LoginValidationError(RuntimeError):
    """Raised when remote login validation fails."""


@dataclass(frozen=True)
class AghConfig:
    """Local AGH connection configuration."""

    instance_url: str
    email: str
    token: str


@dataclass(frozen=True)
class InstanceUpdate:
    """Result of persisting an instance URL via :func:`save_instance_url`.

    ``credentials_cleared`` is True when stored credentials were dropped
    because the configured instance changed (or were orphaned), so the caller
    can tell the user to re-authenticate.
    """

    instance_url: str
    credentials_cleared: bool


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
        raise ConfigCorruptError(config_path, str(exc)) from exc

    try:
        return AghConfig(
            instance_url=str(raw["instance_url"]),
            email=str(raw["email"]),
            token=str(raw["token"]),
        )
    except KeyError as exc:
        raise ConfigError(f"AGH config missing required field: {exc.args[0]}") from exc


def load_instance_url(path: Path | None = None) -> str:
    """Return the configured instance URL, or raise a guided ConfigError."""
    data = _read_config_dict(path or get_config_path())
    instance_url = data.get("instance_url", "").strip()
    if not instance_url:
        raise ConfigError(INSTANCE_MISSING_MESSAGE)
    return instance_url


def save_instance_url(url: str, path: Path | None = None) -> InstanceUpdate:
    """Normalize and persist the instance URL.

    Trust-boundary contract: credentials are only valid for the instance they
    were validated against. When the normalized URL differs from the currently
    configured instance (or credentials are orphaned with no current instance),
    stored email/token are cleared so they can never be sent to a different
    host. Re-setting the same normalized instance preserves credentials.
    """
    normalized = normalize_instance_url(url)
    config_path = path or get_config_path()
    data = _read_config_dict(config_path)
    previous_instance = data.get("instance_url", "").strip()

    credentials_cleared = False
    if "email" in data or "token" in data:
        # Preserve only when the instance is genuinely unchanged.
        keep_credentials = bool(previous_instance) and previous_instance == normalized
        if not keep_credentials:
            data.pop("email", None)
            data.pop("token", None)
            credentials_cleared = True

    data["instance_url"] = normalized
    _write_config_dict(config_path, data)
    return InstanceUpdate(
        instance_url=normalized, credentials_cleared=credentials_cleared
    )


def clear_instance_url(path: Path | None = None) -> bool:
    """Remove only the instance URL, preserving credentials. Return whether it existed."""
    config_path = path or get_config_path()
    data = _read_config_dict(config_path)
    if "instance_url" not in data:
        return False
    del data["instance_url"]
    _write_or_remove(config_path, data)
    return True


def save_credentials(*, email: str, token: str, path: Path | None = None) -> None:
    """Persist credentials, preserving any configured instance URL."""
    config_path = path or get_config_path()
    data = _read_config_dict(config_path)
    data["email"] = email
    data["token"] = token
    _write_config_dict(config_path, data)


def clear_credentials(path: Path | None = None) -> bool:
    """Remove only credentials, preserving the instance URL. Return whether any existed."""
    config_path = path or get_config_path()
    data = _read_config_dict(config_path)
    if "email" not in data and "token" not in data:
        return False
    data.pop("email", None)
    data.pop("token", None)
    _write_or_remove(config_path, data)
    return True


def _read_config_dict(path: Path) -> dict[str, str]:
    """Read the flat config into a dict of known keys (empty if absent)."""
    try:
        raw = tomllib.loads(path.read_text(encoding="utf-8"))
    except FileNotFoundError:
        return {}
    except tomllib.TOMLDecodeError as exc:
        raise ConfigCorruptError(path, str(exc)) from exc
    return {key: str(raw[key]) for key in _CONFIG_KEYS if key in raw}


def _write_config_dict(path: Path, data: dict[str, str]) -> None:
    """Atomically write the known config keys in stable order with 0o600 perms."""
    path.parent.mkdir(parents=True, exist_ok=True)
    text = _format_partial_config(data)
    fd, temp_name = tempfile.mkstemp(
        prefix=f".{path.name}.", suffix=".tmp", dir=path.parent
    )
    temp_path = Path(temp_name)
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as handle:
            handle.write(text)
            handle.flush()
            os.fsync(handle.fileno())
        with suppress(OSError):
            os.chmod(temp_path, 0o600)
        os.replace(temp_path, path)
        with suppress(OSError):
            os.chmod(path, 0o600)
    except Exception:
        with suppress(FileNotFoundError):
            temp_path.unlink()
        raise


def _write_or_remove(path: Path, data: dict[str, str]) -> None:
    """Write remaining keys, or remove the file when nothing is left."""
    if not data:
        with suppress(FileNotFoundError):
            path.unlink()
        return
    _write_config_dict(path, data)


def _format_partial_config(data: dict[str, str]) -> str:
    return "".join(
        f'{key} = "{_toml_escape(data[key])}"\n' for key in _CONFIG_KEYS if key in data
    )


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


def _toml_escape(value: str) -> str:
    return value.replace("\\", "\\\\").replace('"', '\\"')


def fail(message: str, *, code: int = 1) -> NoReturn:
    """Print an error and exit with a stable non-zero status."""
    typer.secho(f"Error: {message}", fg=typer.colors.RED, err=False)
    raise typer.Exit(code)
