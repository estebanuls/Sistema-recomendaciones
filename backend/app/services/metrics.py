"""Basic recommendation metrics helpers."""

from __future__ import annotations

import json


def build_overview(connection, settings, recommendation_service) -> dict[str, object]:
    users = connection.execute("SELECT COUNT(*) AS total FROM users").fetchone()["total"]
    movies = connection.execute("SELECT COUNT(*) AS total FROM movies").fetchone()["total"]
    interactions = connection.execute(
        "SELECT COUNT(*) AS total FROM interactions"
    ).fetchone()["total"]

    metadata = {}
    metadata_path = settings.processed_dir / "metadata.json"
    if metadata_path.exists():
        metadata = json.loads(metadata_path.read_text(encoding="utf-8"))

    evaluation = {}
    evaluation_path = settings.artifacts_dir / "evaluation_metrics.json"
    if evaluation_path.exists():
        evaluation = json.loads(evaluation_path.read_text(encoding="utf-8"))

    artifacts = {
        "matrix": (settings.processed_dir / "matrix.npy").exists(),
        "triplets": (settings.processed_dir / "ratings_triplets.npz").exists(),
        "movie_stats": (settings.processed_dir / "movie_stats.csv").exists(),
        "u_matrix": (settings.artifacts_dir / "u_matrix.npy").exists(),
        "s_weights": (settings.artifacts_dir / "s_weights.npy").exists(),
        "vt_matrix": (settings.artifacts_dir / "vt_matrix.npy").exists(),
        "evaluation_metrics": evaluation_path.exists(),
    }

    return {
        "project_name": settings.project_name,
        "environment": settings.environment,
        "users": users,
        "movies": movies,
        "interactions": interactions,
        "model_ready": recommendation_service.model_ready,
        "artifacts": artifacts,
        "dataset": metadata,
        "evaluation": evaluation,
        "min_cold_start_interactions": settings.min_cold_start_interactions,
        "default_recommendation_count": settings.default_recommendation_count,
    }