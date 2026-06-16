"""Movie and recommendation schemas."""

from __future__ import annotations

from pydantic import BaseModel


class MoviePayload(BaseModel):
    id: int
    title: str
    genres: list[str]
    mean_rating: float
    rating_count: int
    popularity_score: float
    predicted_score: float | None = None
    explanation: str | None = None


class MovieListResponse(BaseModel):
    count: int
    items: list[MoviePayload]


class RecommendationResponse(BaseModel):
    strategy: str
    model_ready: bool
    count: int
    items: list[MoviePayload]