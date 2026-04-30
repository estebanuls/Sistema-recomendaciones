"""Prepare filtered datasets and sparse matrices from raw files."""
from __future__ import annotations

from pathlib import Path
import json

import numpy as np
import pandas as pd


BASE_DIR = Path(__file__).resolve().parents[1]
DATA_RAW = BASE_DIR / "data" / "raw" / "ratings_filtrado_nuevo.csv.gz"
DATA_OUT_DIR = BASE_DIR / "data" / "processed"


def build_matrix_artifacts(
    csv_path: Path = DATA_RAW,
    output_dir: Path = DATA_OUT_DIR,
) -> dict[str, object]:
    if not csv_path.exists():
        raise FileNotFoundError(f"No se encontro el archivo de ratings: {csv_path}")

    output_dir.mkdir(parents=True, exist_ok=True)
    frame = pd.read_csv(
        csv_path,
        dtype={
            "userId": "int32",
            "movieId": "int32",
            "rating": "float32",
            "timestamp": "int64",
        },
    )

    user_ids = np.sort(frame["userId"].unique())
    movie_ids = np.sort(frame["movieId"].unique())
    user_to_idx = {int(user_id): index for index, user_id in enumerate(user_ids.tolist())}
    movie_to_idx = {int(movie_id): index for index, movie_id in enumerate(movie_ids.tolist())}

    frame["user_idx"] = frame["userId"].map(user_to_idx).astype("int32")
    frame["movie_idx"] = frame["movieId"].map(movie_to_idx).astype("int32")

    matrix = np.zeros((len(user_ids), len(movie_ids)), dtype=np.float32)
    matrix[
        frame["user_idx"].to_numpy(dtype=np.int32),
        frame["movie_idx"].to_numpy(dtype=np.int32),
    ] = frame["rating"].to_numpy(dtype=np.float32)

    np.save(output_dir / "matrix.npy", matrix)
    np.savez_compressed(
        output_dir / "ratings_triplets.npz",
        user_idx=frame["user_idx"].to_numpy(dtype=np.int32),
        movie_idx=frame["movie_idx"].to_numpy(dtype=np.int32),
        ratings=frame["rating"].to_numpy(dtype=np.float32),
        shape=np.array(matrix.shape, dtype=np.int32),
    )

    stats = frame.groupby("movieId")["rating"].agg(["mean", "count"]).reset_index()
    stats.columns = ["movieId", "mean_rating", "rating_count"]
    stats["popularity_score"] = (
        stats["mean_rating"] * np.log1p(stats["rating_count"])
    ).astype(np.float32)
    stats.to_csv(output_dir / "movie_stats.csv", index=False)

    metadata = {
        "rows": int(len(frame)),
        "unique_users": int(len(user_ids)),
        "unique_movies": int(len(movie_ids)),
        "matrix_shape": [int(matrix.shape[0]), int(matrix.shape[1])],
        "density": float(np.count_nonzero(matrix) / matrix.size),
    }
    (output_dir / "metadata.json").write_text(
        json.dumps(metadata, indent=2, ensure_ascii=False),
        encoding="utf-8",
    )
    (output_dir / "user_map.json").write_text(
        json.dumps({index: user_id for index, user_id in enumerate(user_ids.tolist())}, ensure_ascii=False),
        encoding="utf-8",
    )
    (output_dir / "movie_map.json").write_text(
        json.dumps({index: movie_id for index, movie_id in enumerate(movie_ids.tolist())}, ensure_ascii=False),
        encoding="utf-8",
    )

    return metadata
