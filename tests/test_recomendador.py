from __future__ import annotations

from dataclasses import replace
import unittest

import pandas as pd

from backend.app.core.config import get_settings
from backend.app.db.base import ensure_database
from backend.app.db.session import get_connection
from backend.app.schemas.user import UserCreate
from backend.app.services.recommendation import RecommendationService
from backend.app.services import user_service
from tests.helpers import workspace_temp_dir


class TestRecomendador(unittest.TestCase):
    def test_genre_fallback_uses_positive_interactions(self) -> None:
        with workspace_temp_dir("recomendador") as root:
            backend_dir = root / "backend"
            raw_dir = backend_dir / "data" / "raw"
            processed_dir = backend_dir / "data" / "processed"
            artifacts_dir = backend_dir / "data" / "artifacts"
            frontend_dir = root / "frontend"
            logs_dir = backend_dir / "logs"

            for directory in (raw_dir, processed_dir, artifacts_dir, frontend_dir, logs_dir):
                directory.mkdir(parents=True, exist_ok=True)

            (frontend_dir / "index.html").write_text("<!doctype html><title>ok</title>", encoding="utf-8")

            movies = pd.DataFrame(
                [
                    {"movieId": 1, "title": "Galactic Quest", "genres": "Sci-Fi|Adventure"},
                    {"movieId": 2, "title": "Nebula Run", "genres": "Sci-Fi|Action"},
                    {"movieId": 3, "title": "Quiet Kitchen", "genres": "Documentary"},
                ]
            )
            ratings = pd.DataFrame(
                [
                    {"userId": 10, "movieId": 1, "rating": 5.0, "timestamp": 1},
                    {"userId": 11, "movieId": 2, "rating": 4.5, "timestamp": 2},
                    {"userId": 12, "movieId": 3, "rating": 2.5, "timestamp": 3},
                ]
            )
            movies.to_csv(raw_dir / "movies.csv", index=False)
            ratings.to_csv(raw_dir / "ratings_filtrado_nuevo.csv.gz", index=False, compression="gzip")

            base = get_settings()
            settings = replace(
                base,
                root_dir=root,
                backend_dir=backend_dir,
                frontend_dir=frontend_dir,
                data_dir=backend_dir / "data",
                raw_data_dir=raw_dir,
                processed_dir=processed_dir,
                artifacts_dir=artifacts_dir,
                logs_dir=logs_dir,
                database_path=backend_dir / "data" / "app.db",
                movies_csv_path=raw_dir / "movies.csv",
                ratings_csv_path=raw_dir / "ratings_filtrado_nuevo.csv.gz",
                auto_retrain_interval_seconds=0,
            )

            ensure_database(settings)
            service = RecommendationService(settings)

            with get_connection(settings.database_path) as connection:
                user = user_service.create_user(
                    connection,
                    UserCreate(username="ana", display_name="Ana", password="secret12"),
                )
                user_service.record_like(connection, user.id, 1, True)
                strategy, recommendations = service.recommend_for_user(connection, user.id, limit=2)

            self.assertEqual(strategy, "genre-popularity")
            self.assertTrue(recommendations)
            self.assertEqual(recommendations[0]["id"], 2)


if __name__ == "__main__":
    unittest.main()
