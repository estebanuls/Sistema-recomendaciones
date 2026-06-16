"""Interactions endpoints."""

from __future__ import annotations

from backend.app.api import ApiError
from backend.app.schemas.interaction import InteractionPayload, LikeMovieRequest, RateMovieRequest
from backend.app.services import user_service


def rate_movie(*, connection, body, current_user, **_):
    payload = RateMovieRequest.model_validate(body)
    interaction = user_service.record_rating(
        connection=connection,
        user_id=current_user.id,
        movie_id=payload.movie_id,
        rating=payload.rating,
    )
    return 200, {"interaction": InteractionPayload(**interaction.to_public_dict()).model_dump()}


def like_movie(*, connection, body, current_user, **_):
    payload = LikeMovieRequest.model_validate(body)
    interaction = user_service.record_like(
        connection=connection,
        user_id=current_user.id,
        movie_id=payload.movie_id,
        liked=payload.liked,
    )
    return 200, {"interaction": InteractionPayload(**interaction.to_public_dict()).model_dump()}


def history(*, connection, current_user, query_params, **_):
    raw_limit = query_params.get("limit", ["25"])[0]
    try:
        limit = int(raw_limit)
    except ValueError as exc:
        raise ApiError(400, "El parametro limit debe ser numerico.") from exc
    limit = max(1, min(limit, 100))
    items = [
        InteractionPayload(**interaction.to_public_dict()).model_dump()
        for interaction in user_service.list_user_interactions(connection, current_user.id, limit=limit)
    ]
    return 200, {"count": len(items), "items": items}
