from __future__ import annotations

from urllib.parse import unquote, urlparse


def normalize_repo_url(url: str) -> str:
    candidate = url.strip()
    if not candidate:
        raise ValueError("repository URL is required")

    if "://" in candidate:
        parsed = urlparse(candidate)
        host = unquote(parsed.hostname or "").lower().rstrip(".")
        path = parsed.path or ""
    elif "@" in candidate and ":" in candidate:
        _, rest = candidate.split("@", 1)
        host, path = rest.split(":", 1)
        host = unquote(host).lower().rstrip(".")
        path = f"/{path}"
    else:
        raise ValueError(f"unsupported repository URL: {url}")

    normalized_parts: list[str] = []
    for part in unquote(path).lower().split("/"):
        if not part or part == ".":
            continue
        if part == "..":
            if not normalized_parts:
                raise ValueError(f"unsupported repository URL: {url}")
            normalized_parts.pop()
            continue
        normalized_parts.append(part)

    if normalized_parts and normalized_parts[-1].endswith(".git"):
        normalized_parts[-1] = normalized_parts[-1][:-4]

    normalized_path = "/".join(part for part in normalized_parts if part)
    if not host or not normalized_path:
        raise ValueError(f"unsupported repository URL: {url}")
    return f"{host}/{normalized_path}"
