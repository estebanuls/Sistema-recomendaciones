"""Users endpoints."""

from __future__ import annotations

from backend.app.services import user_service


def profile(*, connection, current_user, **_):
    return 200, user_service.get_user_profile(connection, current_user.id)
