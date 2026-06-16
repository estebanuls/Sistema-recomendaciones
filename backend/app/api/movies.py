"""Movies endpoints."""

from __future__ import annotations

from backend.app.api import ApiError
from backend.app.models.movie import Movie
from backend.app.schemas.movie import MovieListResponse, MoviePayload


def _parse_limit(query_params: dict[str, list[str]], default: int = 12, maximum: int = 50) -> int:
    raw_value = query_params.get("limit", [str(default)])[0]
    try:
        value = int(raw_value)
    except ValueError:
        raise ApiError(400, "El parametro limit debe ser numerico.")
    return max(1, min(value, maximum))


def list_movies(*, connection, query_params, **_):
    query = query_params.get("query", [""])[0].strip().lower()
    limit = _parse_limit(query_params)

    if query:
        rows = connection.execute(
            """
            SELECT id, title, genres, mean_rating, rating_count, popularity_score
            FROM movies
            WHERE lower(title) LIKE ? OR lower(genres) LIKE ?
            ORDER BY popularity_score DESC, mean_rating DESC, title ASC
            LIMIT ?
            """,
            (f"%{query}%", f"%{query}%", limit),
        ).fetchall()
    else:
        rows = connection.execute(
            """
            SELECT id, title, genres, mean_rating, rating_count, popularity_score
            FROM movies
            ORDER BY popularity_score DESC, mean_rating DESC, title ASC
            LIMIT ?
            """,
            (limit,),
        ).fetchall()

    items = [MoviePayload(**Movie.from_row(row).to_public_dict()) for row in rows]
    response = MovieListResponse(count=len(items), items=items)
    return 200, response.model_dump()


def get_movie(*, connection, path_params, **_):
    movie_id = int(path_params["movie_id"])
    row = connection.execute(
        """
        SELECT id, title, genres, mean_rating, rating_count, popularity_score
        FROM movies
        WHERE id = ?
        """,
        (movie_id,),
    ).fetchone()
    if not row:
        raise ApiError(404, "Pelicula no encontrada.")
    payload = MoviePayload(**Movie.from_row(row).to_public_dict())
    return 200, payload.model_dump()
