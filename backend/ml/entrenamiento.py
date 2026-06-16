"""Pipeline orchestration for preprocessing, evaluation and SVD training."""

from __future__ import annotations

import argparse
from datetime import datetime, timezone
import json

import numpy as np

from backend.app.core.config import get_settings
from backend.ml.modelo import randomized_svd, save_model_artifacts, train_svd
from backend.ml.preprocesamiento import build_matrix_artifacts


def _utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _load_triplets(processed_dir):
    triplets = np.load(processed_dir / "ratings_triplets.npz")
    return (
        triplets["user_idx"].astype(np.int32),
        triplets["movie_idx"].astype(np.int32),
        triplets["ratings"].astype(np.float32),
        tuple(int(value) for value in triplets["shape"]),
    )


def _split_triplets_by_user(
    user_idx: np.ndarray,
    movie_idx: np.ndarray,
    ratings: np.ndarray,
    *,
    holdout_ratio: float = 0.1,
    positive_threshold: float = 4.0,
    seed: int = 42,
):
    total = user_idx.shape[0]
    train_mask = np.ones(total, dtype=bool)
    test_mask = np.zeros(total, dtype=bool)
    train_seen_by_user: dict[int, list[int]] = {}
    positive_test_by_user: dict[int, set[int]] = {}

    order = np.argsort(user_idx, kind="stable")
    sorted_users = user_idx[order]
    boundaries = np.flatnonzero(np.diff(sorted_users)) + 1
    groups = np.split(order, boundaries)
    rng = np.random.default_rng(seed)

    for group in groups:
        if group.size == 0:
            continue
        user = int(user_idx[group[0]])
        train_seen_by_user[user] = movie_idx[group].tolist()
        if group.size < 2:
            continue

        test_count = min(group.size - 1, max(1, int(round(group.size * holdout_ratio))))
        chosen = rng.choice(group, size=test_count, replace=False)
        train_mask[chosen] = False
        test_mask[chosen] = True
        train_seen_by_user[user] = movie_idx[group[train_mask[group]]].tolist()

        positives = {
            int(movie_idx[position])
            for position in chosen
            if float(ratings[position]) >= positive_threshold
        }
        if positives:
            positive_test_by_user[user] = positives

    return train_mask, test_mask, train_seen_by_user, positive_test_by_user


def _build_matrix(shape: tuple[int, int], user_idx, movie_idx, ratings):
    matrix = np.zeros(shape, dtype=np.float32)
    matrix[user_idx, movie_idx] = ratings
    return matrix


def _compute_rmse(u, sigma, vt, user_idx, movie_idx, ratings) -> float:
    if user_idx.size == 0:
        return 0.0
    user_features = u[user_idx] * sigma
    item_features = vt[:, movie_idx].T
    predictions = np.sum(user_features * item_features, axis=1)
    predictions = np.clip(predictions, 0.5, 5.0)
    return float(np.sqrt(np.mean((predictions - ratings) ** 2)))


def _compute_precision_at_k(
    u,
    sigma,
    vt,
    train_seen_by_user: dict[int, list[int]],
    positive_test_by_user: dict[int, set[int]],
    *,
    k: int = 10,
) -> float:
    if not positive_test_by_user:
        return 0.0

    precision_scores: list[float] = []
    total_movies = vt.shape[1]
    for user_idx, positives in positive_test_by_user.items():
        user_features = u[user_idx] * sigma
        scores = user_features @ vt
        seen_movies = train_seen_by_user.get(user_idx, [])
        if seen_movies:
            scores[np.asarray(seen_movies, dtype=np.int32)] = -np.inf
        best_items = np.argsort(scores)[::-1][: min(k, total_movies)]
        hits = sum(1 for movie in best_items if int(movie) in positives)
        precision_scores.append(hits / float(k))

    return float(np.mean(precision_scores)) if precision_scores else 0.0


def evaluate_model(processed_dir, *, k: int = 32) -> dict[str, object]:
    user_idx, movie_idx, ratings, shape = _load_triplets(processed_dir)
    train_mask, test_mask, train_seen_by_user, positive_test_by_user = _split_triplets_by_user(
        user_idx,
        movie_idx,
        ratings,
    )

    train_matrix = _build_matrix(
        shape,
        user_idx[train_mask],
        movie_idx[train_mask],
        ratings[train_mask],
    )
    u, sigma, vt = randomized_svd(train_matrix, k=k)
    rmse = _compute_rmse(
        u,
        sigma,
        vt,
        user_idx[test_mask],
        movie_idx[test_mask],
        ratings[test_mask],
    )
    precision_at_10 = _compute_precision_at_k(
        u,
        sigma,
        vt,
        train_seen_by_user,
        positive_test_by_user,
        k=10,
    )

    return {
        "generated_at": _utc_now(),
        "holdout_ratio": 0.1,
        "positive_threshold": 4.0,
        "test_interactions": int(test_mask.sum()),
        "evaluated_users_precision": int(len(positive_test_by_user)),
        "rmse": round(rmse, 6),
        "precision_at_10": round(precision_at_10, 6),
    }


def is_training_required(settings) -> bool:
    required_paths = [
        settings.processed_dir / "matrix.npy",
        settings.processed_dir / "ratings_triplets.npz",
        settings.processed_dir / "movie_stats.csv",
        settings.processed_dir / "metadata.json",
        settings.processed_dir / "user_map.json",
        settings.processed_dir / "movie_map.json",
        settings.artifacts_dir / "u_matrix.npy",
        settings.artifacts_dir / "s_weights.npy",
        settings.artifacts_dir / "vt_matrix.npy",
        settings.artifacts_dir / "evaluation_metrics.json",
    ]
    if not all(path.exists() for path in required_paths):
        return True

    source_mtime = max(
        settings.movies_csv_path.stat().st_mtime,
        settings.ratings_csv_path.stat().st_mtime,
    )
    outputs_mtime = min(path.stat().st_mtime for path in required_paths)
    return source_mtime > outputs_mtime


def run_pipeline(settings=None, k: int = 32, skip_preprocessing: bool = False) -> dict[str, object]:
    settings = settings or get_settings()
    metadata = {}
    if not skip_preprocessing:
        metadata = build_matrix_artifacts(
            csv_path=settings.ratings_csv_path,
            output_dir=settings.processed_dir,
        )

    evaluation = evaluate_model(settings.processed_dir, k=k)
    u, sigma, vt = train_svd(matrix_path=settings.processed_dir / "matrix.npy", k=k)
    save_model_artifacts(u, sigma, vt, settings.artifacts_dir)

    (settings.artifacts_dir / "evaluation_metrics.json").write_text(
        json.dumps(evaluation, indent=2, ensure_ascii=False),
        encoding="utf-8",
    )
    training_report = {
        "generated_at": _utc_now(),
        "preprocessing": metadata,
        "latent_factors": int(min(k, sigma.shape[0])),
        "artifacts_dir": str(settings.artifacts_dir),
        "evaluation": evaluation,
    }
    (settings.artifacts_dir / "training_report.json").write_text(
        json.dumps(training_report, indent=2, ensure_ascii=False),
        encoding="utf-8",
    )
    return training_report


def ensure_pipeline_outputs(settings, force: bool = False) -> dict[str, object]:
    if force or is_training_required(settings):
        return run_pipeline(settings=settings, k=settings.latent_factors, skip_preprocessing=False)

    report_path = settings.artifacts_dir / "training_report.json"
    if report_path.exists():
        return json.loads(report_path.read_text(encoding="utf-8"))
    return {
        "generated_at": _utc_now(),
        "latent_factors": settings.latent_factors,
        "artifacts_dir": str(settings.artifacts_dir),
    }


def main() -> None:
    parser = argparse.ArgumentParser(description="Preprocesa el dataset y entrena el modelo SVD.")
    parser.add_argument("--k", type=int, default=32, help="Numero de factores latentes.")
    parser.add_argument(
        "--skip-preprocessing",
        action="store_true",
        help="Usa una matriz previamente generada en backend/data/processed/matrix.npy.",
    )
    args = parser.parse_args()
    result = run_pipeline(settings=get_settings(), k=args.k, skip_preprocessing=args.skip_preprocessing)
    print(json.dumps(result, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()
