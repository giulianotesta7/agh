from __future__ import annotations

from collections.abc import Callable
from typing import Any
from urllib.parse import quote

from agh.common.validation import is_valid_email


class UserRefResolutionError(ValueError):
    """Raised when a CLI user ref cannot be resolved to a user ID."""

    def __init__(self, message: str, *, code: int = 1) -> None:
        super().__init__(message)
        self.code = code


ApiRequest = Callable[..., Any]


def resolve_user_ref(user_ref: str, api_request: ApiRequest) -> str:
    """Resolve a CLI user ref to a canonical user ID.

    Canonical user IDs are passed through unchanged. Other refs must be exact
    email addresses and are resolved through the API.
    """

    email = user_ref
    if is_valid_email(email):
        payload = api_request("GET", f"/users/by-email/{quote(email, safe='')}")
        user_id = payload.get("id") if isinstance(payload, dict) else None
        if not isinstance(user_id, str) or not user_id:
            raise UserRefResolutionError(
                "USER_REF resolver response did not include a user id"
            )
        return user_id

    if user_ref.startswith("usr_"):
        return user_ref

    raise UserRefResolutionError(
        "USER_REF must be a user id (usr_...) or exact email", code=2
    )
