"""Recommendations endpoint."""

from __future__ import annotations

from backend.app.api import ApiError
from backend.app.schemas.movie import MoviePayload, RecommendationResponse


def list_recommendations(*, context, connection, current_user, query_params, **_):
    raw_limit = query_params.get("limit", [str(context.settings.default_recommendation_count)])[0]
    try:
        limit = int(raw_limit)
    except ValueError as exc:
        raise ApiError(400, "El parametro limit debe ser numerico.") from exc
    limit = max(context.settings.default_recommendation_count, min(limit, 40))

    strategy, items = context.recommendation_service.recommend_for_user(
        connection=connection,
        user_id=current_user.id,
        limit=limit,
    )
    response = RecommendationResponse(
        strategy=strategy,
        model_ready=context.recommendation_service.model_ready,
        count=len(items),
        items=[MoviePayload(**item) for item in items],
    )
    return 200, response.model_dump()
