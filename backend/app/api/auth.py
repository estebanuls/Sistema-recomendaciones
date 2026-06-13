"""Authentication endpoints."""

from __future__ import annotations

from backend.app.core.security import create_access_token
from backend.app.schemas.user import AuthResponse, UserCreate, UserLogin, UserPublic
from backend.app.services import user_service


def register(*, context, connection, body, **_):
    payload = UserCreate.model_validate(body)
    user = user_service.create_user(connection, payload, context.settings)
    token = create_access_token(
        subject=user.id,
        secret_key=context.settings.secret_key,
        ttl_minutes=context.settings.token_ttl_minutes,
    )
    response = AuthResponse(access_token=token, user=UserPublic(**user.to_public_dict()))
    return 201, response.model_dump()


def login(*, context, connection, body, **_):
    payload = UserLogin.model_validate(body)
    user = user_service.authenticate_user(
        connection,
        payload.username,
        payload.password,
        context.settings,
    )
    token = create_access_token(
        subject=user.id,
        secret_key=context.settings.secret_key,
        ttl_minutes=context.settings.token_ttl_minutes,
    )
    response = AuthResponse(access_token=token, user=UserPublic(**user.to_public_dict()))
    return 200, response.model_dump()


def me(*, current_user, **_):
    return 200, {"user": current_user.to_public_dict()}
