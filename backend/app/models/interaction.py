"""Interaction model."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(slots=True)
class Interaction:
    id: int
    user_id: int
    movie_id: int
    rating: float | None
    liked: bool | None
    source: str
    created_at: str
    updated_at: str
    movie_title: str | None = None
    movie_genres: str | None = None

    @classmethod
    def from_row(cls, row: dict[str, object]) -> "Interaction":
        liked = row.get("liked")
        return cls(
            id=int(row["id"]),
            user_id=int(row["user_id"]),
            movie_id=int(row["movie_id"]),
            rating=float(row["rating"]) if row.get("rating") is not None else None,
            liked=bool(liked) if liked is not None else None,
            source=str(row["source"]),
            created_at=str(row["created_at"]),
            updated_at=str(row["updated_at"]),
            movie_title=str(row["movie_title"]) if row.get("movie_title") is not None else None,
            movie_genres=str(row["movie_genres"]) if row.get("movie_genres") is not None else None,
        )

    def to_public_dict(self) -> dict[str, object]:
        payload = {
            "id": self.id,
            "user_id": self.user_id,
            "movie_id": self.movie_id,
            "rating": self.rating,
            "liked": self.liked,
            "source": self.source,
            "created_at": self.created_at,
            "updated_at": self.updated_at,
        }
        if self.movie_title is not None:
            payload["movie_title"] = self.movie_title
        if self.movie_genres is not None:
            payload["movie_genres"] = [
                item for item in self.movie_genres.split("|") if item and item != "(no genres listed)"
            ]
        return payload