"""Application service that adapts the algorithm layer to API responses."""

from __future__ import annotations

from collections import Counter

from backend.app.models.movie import Movie
from backend.app.services import user_service
from backend.ml.recomendador import SVDRecommender


class RecommendationService:
    def __init__(self, settings):
        self.settings = settings
        self.recommender = SVDRecommender(
            artifacts_dir=settings.artifacts_dir,
            processed_dir=settings.processed_dir,
        )

    @property
    def model_ready(self) -> bool:
        return self.recommender.ready

    def refresh_model(self) -> None:
        self.recommender.reload()

    def _load_catalog(self, connection) -> list[Movie]:
        rows = connection.execute(
            """
            SELECT id, title, genres, mean_rating, rating_count, popularity_score
            FROM movies
            ORDER BY popularity_score DESC, mean_rating DESC, title ASC
            """
        ).fetchall()
        return [Movie.from_row(row) for row in rows]

    def _candidate_map(self, catalog: list[Movie]) -> dict[int, Movie]:
        return {movie.id: movie for movie in catalog}

    def _blend_latent_scores(
        self,
        catalog_map: dict[int, Movie],
        scored_items: list[tuple[int, float]],
        limit: int,
    ) -> list[dict[str, object]]:
        results: list[dict[str, object]] = []
        for movie_id, score in scored_items:
            movie = catalog_map.get(movie_id)
            if not movie:
                continue
            blended_score = score + (movie.popularity_score * 0.01)
            results.append(
                movie.to_public_dict(
                    predicted_score=blended_score,
                    explanation="Basada en las peliculas que has puntuado o marcado.",
                )
            )
            if len(results) >= limit:
                break
        return results

    def _genre_fallback(
        self,
        catalog: list[Movie],
        interactions,
        limit: int,
    ) -> list[dict[str, object]]:
        seen_ids = {item.movie_id for item in interactions}
        genre_counter: Counter[str] = Counter()

        for item in interactions:
            weight = 0.0
            if item.rating is not None:
                weight += (item.rating - 3.0) / 2.0
            if item.liked is True:
                weight += 0.75
            elif item.liked is False:
                weight -= 0.75
            if weight <= 0 or not item.movie_genres:
                continue
            for genre in item.movie_genres.split("|"):
                if genre and genre != "(no genres listed)":
                    genre_counter[genre] += weight

        scored_candidates: list[tuple[float, Movie, str]] = []
        for movie in catalog:
            if movie.id in seen_ids:
                continue
            overlap = sum(genre_counter.get(genre, 0.0) for genre in movie.genre_list)
            if genre_counter:
                total_score = overlap * 4.0 + movie.mean_rating + (movie.popularity_score * 0.02)
                explanation = "Afinada por tus generos favoritos y la popularidad del catalogo."
            else:
                total_score = movie.mean_rating + (movie.popularity_score * 0.02)
                explanation = "Popular entre la base de datos filtrada de MovieLens."
            scored_candidates.append((total_score, movie, explanation))

        scored_candidates.sort(key=lambda item: item[0], reverse=True)
        return [
            movie.to_public_dict(predicted_score=score, explanation=explanation)
            for score, movie, explanation in scored_candidates[:limit]
        ]

    def recommend_for_user(self, connection, user_id: int, limit: int = 10) -> tuple[str, list[dict[str, object]]]:
        catalog = self._load_catalog(connection)
        catalog_map = self._candidate_map(catalog)
        interactions = user_service.list_user_interactions(connection, user_id, limit=500)
        seen_ids = {item.movie_id for item in interactions}
        enough_interactions = len(interactions) >= self.settings.min_cold_start_interactions

        if self.recommender.ready and enough_interactions:
            preferences = {}
            for item in interactions:
                weight = 0.0
                if item.rating is not None:
                    weight += (item.rating - 3.0) / 2.0
                if item.liked is True:
                    weight += 0.75
                elif item.liked is False:
                    weight -= 0.75
                if abs(weight) > 0:
                    preferences[item.movie_id] = weight

            latent_scores = self.recommender.score_from_preferences(
                preferences=preferences,
                excluded_movie_ids=seen_ids,
                limit=max(limit * 3, limit),
            )
            if latent_scores:
                return "latent-svd", self._blend_latent_scores(catalog_map, latent_scores, limit)

        strategy = "genre-popularity" if interactions else "catalog-popularity"
        return strategy, self._genre_fallback(catalog, interactions, limit)
