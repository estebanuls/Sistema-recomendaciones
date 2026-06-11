from __future__ import annotations

from dataclasses import replace
import json
import os
import unittest

import pandas as pd

from backend.app.core.config import get_settings
from backend.app.db.base import ensure_database
from backend.app.db.session import get_connection
from backend.app.schemas.user import UserCreate
from backend.app.services.recommendation import RecommendationService
from backend.app.services.training import TrainingSupervisor
from backend.app.services import user_service
from backend.ml.entrenamiento import ensure_pipeline_outputs, run_pipeline
from tests.helpers import workspace_temp_dir


class _NullLogger:
    def info(self, *args, **kwargs) -> None:
        return None

    def error(self, *args, **kwargs) -> None:
        return None


class TestRequirements(unittest.TestCase):
    def build_settings(self, prefix: str, *, bcrypt_rounds: int = 12):
        context = workspace_temp_dir(prefix)
        root = context.__enter__()
        self.addCleanup(context.__exit__, None, None, None)

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
                {"movieId": 1, "title": "Toy Mission", "genres": "Animation|Adventure"},
                {"movieId": 2, "title": "Toy Return", "genres": "Animation|Comedy"},
                {"movieId": 3, "title": "Steel Night", "genres": "Action|Thriller"},
            ]
        )
        ratings = pd.DataFrame(
            [
                {"userId": 10, "movieId": 1, "rating": 5.0, "timestamp": 1},
                {"userId": 11, "movieId": 2, "rating": 4.0, "timestamp": 2},
                {"userId": 12, "movieId": 3, "rating": 3.0, "timestamp": 3},
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
            bcrypt_rounds=bcrypt_rounds,
            auto_retrain_interval_seconds=0,
        )
        return settings

    def test_srs_rf_003_retrains_automatically_after_dataset_change(self) -> None:
        settings = self.build_settings("rf003")
        ensure_pipeline_outputs(settings, force=True)
        report_path = settings.artifacts_dir / "training_report.json"
        first_mtime = report_path.stat().st_mtime_ns

        frame = pd.read_csv(settings.ratings_csv_path, compression="gzip")
        frame.loc[len(frame)] = {"userId": 13, "movieId": 2, "rating": 4.5, "timestamp": 4}
        frame.to_csv(settings.ratings_csv_path, index=False, compression="gzip")
        os.utime(settings.ratings_csv_path, ns=(first_mtime + 5_000_000_000, first_mtime + 5_000_000_000))

        supervisor = TrainingSupervisor(
            settings=settings,
            recommendation_service=RecommendationService(settings),
            logger=_NullLogger(),
        )
        triggered = supervisor.poll_once()

        self.assertTrue(triggered)
        self.assertGreater(report_path.stat().st_mtime_ns, first_mtime)

    def test_srs_rf_004_new_user_receives_cold_start_recommendations(self) -> None:
        settings = self.build_settings("rf004")
        ensure_database(settings)
        service = RecommendationService(settings)

        with get_connection(settings.database_path) as connection:
            user = user_service.create_user(
                connection,
                UserCreate(username="ana", display_name="Ana", password="secret12"),
                settings,
            )
            strategy, recommendations = service.recommend_for_user(connection, user.id, limit=10)

        self.assertEqual(strategy, "catalog-popularity")
        self.assertTrue(recommendations)

    def test_srs_rf_005_training_generates_rmse_and_precision_report(self) -> None:
        settings = self.build_settings("rf005")
        report = run_pipeline(settings=settings, k=2)
        evaluation_path = settings.artifacts_dir / "evaluation_metrics.json"

        self.assertIn("evaluation", report)
        self.assertIn("rmse", report["evaluation"])
        self.assertIn("precision_at_10", report["evaluation"])
        self.assertTrue(evaluation_path.exists())

        evaluation = json.loads(evaluation_path.read_text(encoding="utf-8"))
        self.assertIn("rmse", evaluation)
        self.assertIn("precision_at_10", evaluation)

    def test_srs_rs_002_password_hash_keeps_minimum_bcrypt_cost_12(self) -> None:
        settings = self.build_settings("rs002", bcrypt_rounds=10)
        ensure_database(settings)

        with get_connection(settings.database_path) as connection:
            user_service.create_user(
                connection,
                UserCreate(username="mati", display_name="Mati", password="secret12"),
                settings,
            )
            row = connection.execute(
                "SELECT password_hash FROM users WHERE username = ?",
                ("mati",),
            ).fetchone()

        self.assertTrue(str(row["password_hash"]).startswith("$2"))
        self.assertIn("$12$", str(row["password_hash"]))
