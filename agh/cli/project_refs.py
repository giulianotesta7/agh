from __future__ import annotations

from collections.abc import Callable
from typing import Any
from urllib.parse import quote


class ProjectRefResolutionError(ValueError):
    """Raised when the project resolver endpoint returns an invalid payload."""


ApiRequest = Callable[..., Any]


def resolve_project_ref(project_ref: str, api_request: ApiRequest) -> str:
    """Resolve a CLI project ref to a canonical project ID.

    Canonical project IDs and numeric legacy IDs are passed through unchanged.
    Other refs are treated as exact project names and resolved through the API.
    """

    if project_ref.startswith("prj_") or project_ref.isdigit():
        return project_ref

    payload = api_request("GET", f"/projects/by-name/{quote(project_ref, safe='')}")
    project_id = payload.get("id") if isinstance(payload, dict) else None
    if not isinstance(project_id, str) or not project_id:
        raise ProjectRefResolutionError(
            "PROJECT_REF resolver response did not include a project id"
        )
    return project_id
