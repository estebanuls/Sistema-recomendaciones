"""SVD model training and persistence utilities."""
from __future__ import annotations
from pathlib import Path
import numpy as np
import os
from scipy.sparse import load_npz
from scipy.sparse.linalg import svds

def train_svd(matrix_path: Path, k: int = 20) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    """
    Carga la matriz dispersa y aplica Descomposición en Valores Singulares (SVD).
    
    Args:
        matrix_path: Ruta al archivo .npz generado en el preprocesamiento.
        k: Número de factores latentes (dimensiones).
        
    Returns:
        Matrices U, Sigma y Vt ordenadas por importancia.
    """
    if not os.path.exists(matrix_path):
        raise FileNotFoundError(f"No se encontró la matriz en: {matrix_path}")

    print(f"--- Iniciando entrenamiento SVD (k={k}) ---")
    
    # 1. Cargar la matriz dispersa generada por el script de Esteban
    matrix = load_npz(matrix_path).asfptype()
    
    # 2. Calcular SVD truncado
    # U: Relación Usuarios-Conceptos
    # Sigma: Importancia de cada concepto
    # Vt: Relación Películas-Conceptos
    u, sigma, vt = svds(matrix, k=k)
    
    # 3. Ordenar resultados (svds devuelve los valores de menor a mayor)
    # Los ordenamos de mayor a menor para priorizar los rasgos más relevantes
    order = np.argsort(sigma)[::-1]
    
    u = u[:, order]
    sigma = sigma[order]
    vt = vt[order, :]
    
    print("✓ Entrenamiento completado con éxito.")
    return u, sigma, vt

def save_model_artifacts(u: np.ndarray, sigma: np.ndarray, vt: np.ndarray, folder_path: Path):
    """
    Guarda las matrices resultantes en la carpeta de artifacts para su uso en la API.
    """
    os.makedirs(folder_path, exist_ok=True)
    
    np.save(folder_path / "u_matrix.npy", u)
    np.save(folder_path / "s_weights.npy", sigma)
    np.save(folder_path / "vt_matrix.npy", vt)
    
    print(f"✓ Artefactos del modelo guardados en: {folder_path}")

def load_model_artifacts(folder_path: Path) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    """
    Carga los archivos .npy para realizar recomendaciones sin volver a entrenar.
    """
    u = np.load(folder_path / "u_matrix.npy")
    sigma = np.load(folder_path / "s_weights.npy")
    vt = np.load(folder_path / "vt_matrix.npy")
    
    return u, sigma, vt

if __name__ == "__main__":
    BASE_DIR = Path(__file__).resolve().parents[2]

    matrix_path = BASE_DIR / "backend" / "data" / "processed" / "matriz.npz"
    artifacts_path = BASE_DIR / "backend" / "data" / "artifacts"

    print("Matrix path:", matrix_path)
    print("Artifacts path:", artifacts_path)

    u, sigma, vt = train_svd(matrix_path, k=20)
    save_model_artifacts(u, sigma, vt, artifacts_path)