"""SVD model training utilities."""
from __future__ import annotations

from pathlib import Path
import json

import numpy as np


def randomized_svd(
    matrix: np.ndarray,
    k: int = 32,
    n_oversamples: int = 8,
    n_iter: int = 2,
    random_state: int = 42,
) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    if matrix.ndim != 2:
        raise ValueError("La matriz de entrada debe ser bidimensional.")

    rows, columns = matrix.shape
    rank = min(k + n_oversamples, rows, columns)
    generator = np.random.default_rng(random_state)
    omega = generator.standard_normal((columns, rank), dtype=np.float32)
    sample = matrix @ omega

    for _ in range(n_iter):
        sample = matrix @ (matrix.T @ sample)

    basis, _ = np.linalg.qr(sample, mode="reduced")
    reduced = basis.T @ matrix
    reduced_u, singular_values, vt = np.linalg.svd(reduced, full_matrices=False)
    u = basis @ reduced_u

    return (
        u[:, : min(k, u.shape[1])].astype(np.float32),
        singular_values[: min(k, singular_values.shape[0])].astype(np.float32),
        vt[: min(k, vt.shape[0]), :].astype(np.float32),
    )

def train_svd(matrix_path: Path, k: int = 32) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    if not matrix_path.exists():
        raise FileNotFoundError(f"No se encontro la matriz en {matrix_path}")
    matrix = np.load(matrix_path).astype(np.float32)
    return randomized_svd(matrix=matrix, k=k)


def save_model_artifacts(
    u: np.ndarray,
    sigma: np.ndarray,
    vt: np.ndarray,
    folder_path: Path,
) -> None:
    folder_path.mkdir(parents=True, exist_ok=True)
    np.save(folder_path / "u_matrix.npy", u.astype(np.float32))
    np.save(folder_path / "s_weights.npy", sigma.astype(np.float32))
    np.save(folder_path / "vt_matrix.npy", vt.astype(np.float32))

    manifest = {
        "u_shape": list(u.shape),
        "sigma_shape": list(sigma.shape),
        "vt_shape": list(vt.shape),
        "latent_factors": int(sigma.shape[0]),
    }
    (folder_path / "manifest.json").write_text(
        json.dumps(manifest, indent=2, ensure_ascii=False),
        encoding="utf-8",
    )


def load_model_artifacts(folder_path: Path) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    return (
        np.load(folder_path / "u_matrix.npy").astype(np.float32),
        np.load(folder_path / "s_weights.npy").astype(np.float32),
        np.load(folder_path / "vt_matrix.npy").astype(np.float32),
    )


if __name__ == "__main__":
    backend_dir = Path(__file__).resolve().parents[1]
    matrix_path = backend_dir / "data" / "processed" / "matrix.npy"
    artifacts_path = backend_dir / "data" / "artifacts"
    matrices = train_svd(matrix_path=matrix_path, k=32)
    save_model_artifacts(*matrices, folder_path=artifacts_path)
    print(f"Artefactos generados en {artifacts_path}")