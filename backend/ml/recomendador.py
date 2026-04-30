"""Base SVD recommender engine."""

from __future__ import annotations

from pathlib import Path
import json

import numpy as np

from backend.ml.modelo import load_model_artifacts


class SVDRecommender:
    def __init__(self, artifacts_dir: Path, processed_dir: Path):
        self.artifacts_dir = artifacts_dir
        self.processed_dir = processed_dir
        self.ready = False
        self.item_embeddings: np.ndarray | None = None
        self.movie_id_to_index: dict[int, int] = {}
        self.index_to_movie_id: dict[int, int] = {}
        self.reload()

    def reload(self) -> None:
        self.ready = False
        self.item_embeddings = None
        self.movie_id_to_index = {}
        self.index_to_movie_id = {}

        required_files = (
            self.artifacts_dir / "s_weights.npy",
            self.artifacts_dir / "vt_matrix.npy",
            self.processed_dir / "movie_map.json",
        )
        if not all(path.exists() for path in required_files):
            return

        _, sigma, vt = load_model_artifacts(self.artifacts_dir)
        movie_map = json.loads((self.processed_dir / "movie_map.json").read_text(encoding="utf-8"))
        self.index_to_movie_id = {int(index): int(movie_id) for index, movie_id in movie_map.items()}
        self.movie_id_to_index = {movie_id: index for index, movie_id in self.index_to_movie_id.items()}
        self.item_embeddings = (vt.T * sigma).astype(np.float32)
        self.ready = True

    def score_from_preferences(
        self,
        preferences: dict[int, float],
        excluded_movie_ids: set[int] | None = None,
        limit: int = 20,
    ) -> list[tuple[int, float]]:
        if not self.ready or self.item_embeddings is None:
            return []

        vectors: list[np.ndarray] = []
        weights: list[float] = []
        for movie_id, weight in preferences.items():
            movie_index = self.movie_id_to_index.get(int(movie_id))
            if movie_index is None:
                continue
            vectors.append(self.item_embeddings[movie_index])
            weights.append(float(weight))

        if not vectors:
            return []

        weight_array = np.asarray(weights, dtype=np.float32)
        vector_matrix = np.vstack(vectors)
        denominator = float(np.abs(weight_array).sum())
        if denominator == 0:
            return []

        profile = (vector_matrix * weight_array[:, None]).sum(axis=0) / denominator
        scores = self.item_embeddings @ profile

        for movie_id in excluded_movie_ids or set():
            movie_index = self.movie_id_to_index.get(int(movie_id))
            if movie_index is not None:
                scores[movie_index] = -np.inf

        best_indices = np.argsort(scores)[::-1]
        results: list[tuple[int, float]] = []
        for index in best_indices:
            score = float(scores[index])
            if not np.isfinite(score):
                continue
            movie_id = self.index_to_movie_id.get(int(index))
            if movie_id is None:
                continue
            results.append((movie_id, score))
            if len(results) >= limit:
                break
        return results
