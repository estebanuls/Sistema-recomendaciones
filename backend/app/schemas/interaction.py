"""Interaction validation schemas."""

from __future__ import annotations

from pydantic import BaseModel, Field, field_validator


class RateMovieRequest(BaseModel):
    movie_id: int
    rating: float = Field(ge=0.5, le=5.0)

    @field_validator("rating")
    @classmethod
    def validate_half_step(cls, value: float) -> float:
        doubled = value * 2
        if abs(doubled - round(doubled)) > 1e-8:
            raise ValueError("El rating debe avanzar en incrementos de 0.5.")
        return value


class LikeMovieRequest(BaseModel):
    movie_id: int
    liked: bool = True


class InteractionPayload(BaseModel):
    id: int
    user_id: int
    movie_id: int
    rating: float | None = None
    liked: bool | None = None
    source: str
    created_at: str
    updated_at: str
    movie_title: str | None = None
    movie_genres: list[str] | None = None