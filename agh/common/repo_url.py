from __future__ import annotations

from urllib.parse import urlparse


def normalize_repo_url(url: str) -> str:
    candidate = url.strip()
    if not candidate:
        raise ValueError("repository URL is required")

    if "://" in candidate:
        parsed = urlparse(candidate)
        host = (parsed.hostname or "").lower()
        path = parsed.path or ""
    elif "@" in candidate and ":" in candidate:
        _, rest = candidate.split("@", 1)
        host, path = rest.split(":", 1)
        host = host.lower()
        path = f"/{path}"
    else:
        raise ValueError(f"unsupported repository URL: {url}")

    normalized_path = path.strip("/")
    if normalized_path.endswith(".git"):
        normalized_path = normalized_path[:-4]

    normalized_path = "/".join(part for part in normalized_path.split("/") if part)
    if not host or not normalized_path:
        raise ValueError(f"unsupported repository URL: {url}")
    return f"{host}/{normalized_path}"
