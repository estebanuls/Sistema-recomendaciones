from __future__ import annotations

import unittest

import numpy as np
import pandas as pd

from backend.ml.modelo import save_model_artifacts, train_svd
from backend.ml.preprocesamiento import build_matrix_artifacts
from backend.ml.recomendador import SVDRecommender
from backend.ml.entrenamiento import evaluate_model
from tests.helpers import workspace_temp_dir


class TestModelo(unittest.TestCase):
    def test_pipeline_generates_artifacts_and_scores(self) -> None:
        with workspace_temp_dir("modelo") as root:
            csv_path = root / "ratings.csv"
            processed_dir = root / "processed"
            artifacts_dir = root / "artifacts"

            frame = pd.DataFrame(
                [
                    {"userId": 1, "movieId": 10, "rating": 5.0, "timestamp": 1},
                    {"userId": 1, "movieId": 20, "rating": 4.5, "timestamp": 2},
                    {"userId": 2, "movieId": 10, "rating": 4.5, "timestamp": 3},
                    {"userId": 2, "movieId": 20, "rating": 4.0, "timestamp": 4},
                    {"userId": 3, "movieId": 30, "rating": 5.0, "timestamp": 5},
                    {"userId": 3, "movieId": 20, "rating": 4.0, "timestamp": 6},
                ]
            )
            frame.to_csv(csv_path, index=False)

            metadata = build_matrix_artifacts(csv_path=csv_path, output_dir=processed_dir)
            self.assertEqual(metadata["unique_users"], 3)
            self.assertEqual(metadata["unique_movies"], 3)

            u, sigma, vt = train_svd(processed_dir / "matrix.npy", k=2)
            self.assertEqual(u.shape[1], 2)
            self.assertEqual(vt.shape[0], 2)
            self.assertTrue(np.all(sigma > 0))

            save_model_artifacts(u, sigma, vt, artifacts_dir)
            recommender = SVDRecommender(artifacts_dir=artifacts_dir, processed_dir=processed_dir)
            scores = recommender.score_from_preferences(
                preferences={10: 1.0},
                excluded_movie_ids={10},
                limit=2,
            )

            self.assertTrue(recommender.ready)
            self.assertTrue(scores)
            self.assertNotEqual(scores[0][0], 10)

            evaluation = evaluate_model(processed_dir, k=2)
            self.assertIn("rmse", evaluation)
            self.assertIn("precision_at_10", evaluation)


if __name__ == "__main__":
    unittest.main()
