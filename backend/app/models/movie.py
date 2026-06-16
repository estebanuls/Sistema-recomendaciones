"""Movie model."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(slots=True)
class Movie:
    id: int
    title: str
    genres: str
    mean_rating: float
    rating_count: int
    popularity_score: float

    @property
    def genre_list(self) -> list[str]:
        return [item for item in self.genres.split("|") if item and item != "(no genres listed)"]

    @classmethod
    def from_row(cls, row: dict[str, object]) -> "Movie":
        return cls(
            id=int(row["id"]),
            title=str(row["title"]),
            genres=str(row["genres"]),
            mean_rating=float(row["mean_rating"] or 0.0),
            rating_count=int(row["rating_count"] or 0),
            popularity_score=float(row["popularity_score"] or 0.0),
        )

    def to_public_dict(
        self,
        predicted_score: float | None = None,
        explanation: str | None = None,
    ) -> dict[str, object]:
        payload = {
            "id": self.id,
            "title": self.title,
            "genres": self.genre_list,
            "mean_rating": round(self.mean_rating, 3),
            "rating_count": self.rating_count,
            "popularity_score": round(self.popularity_score, 3),
        }
        if predicted_score is not None:
            payload["predicted_score"] = round(predicted_score, 5)
        if explanation:
            payload["explanation"] = explanation
        return payload