from __future__ import annotations

from collections.abc import Callable
from typing import Any
from urllib.parse import quote

from agh.common.ids import is_valid_prefixed_id


class CollectionRefResolutionError(ValueError):
    """Raised when the collection resolver endpoint returns an invalid payload."""


ApiRequest = Callable[..., Any]


def resolve_collection_ref(collection_ref: str, api_request: ApiRequest) -> str:
    """Resolve a CLI collection ref to a canonical collection id.

    Canonical ``col_...`` ids are passed through unchanged. Any other ref is
    treated as an exact active collection name and resolved through the API.
    """

    if is_valid_prefixed_id(collection_ref, "col"):
        return collection_ref

    payload = api_request(
        "GET", f"/collections/by-name/{quote(collection_ref, safe='')}"
    )
    collection_id = payload.get("id") if isinstance(payload, dict) else None
    if not isinstance(collection_id, str) or not collection_id:
        raise CollectionRefResolutionError(
            "COLLECTION_REF resolver response did not include a collection id"
        )
    return collection_id
