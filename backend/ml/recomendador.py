"""Base SVD Recommender Engine."""
import json
import numpy as np
from pathlib import Path
from backend.ml.modelo import load_model_artifacts

# Configuración de rutas (Ajustar según la estructura de Esteban)
BASE_DIR = Path(__file__).parent.parent
ARTIFACTS_DIR = BASE_DIR / "data" / "artifacts"
PROCESSED_DIR = BASE_DIR / "data" / "processed"

class SVDRecommender:
    def __init__(self):
        # 1. Cargar las matrices entrenadas por Leandro
        self.u, self.sigma, self.vt = load_model_artifacts(ARTIFACTS_DIR)
        
        # 2. Cargar el mapeo de usuarios de Esteban (JSON)
        with open(PROCESSED_DIR / "user_map.json", "r") as f:
            user_map_raw = json.load(f)
            # El JSON es { "indice": "id_real" }, lo invertimos para buscar por ID real
            self.user_to_idx = {int(uid): int(idx) for idx, uid in user_map_raw.items()}
            
        # 3. Cargar el mapeo de películas de Esteban (JSON)
        with open(PROCESSED_DIR / "movie_map.json", "r") as f:
            self.movie_map = json.load(f) # { "indice": "id_real" }

    def get_recommendations(self, user_id: int, top_n: int = 10):
        """
        Calcula las mejores N películas para un usuario usando el producto punto de SVD.
        """
        if user_id not in self.user_to_idx:
            # Por ahora, si no existe el usuario, lanzamos un error o lista vacía
            # Bernardo manejará el Cold Start aquí después.
            return []

        user_idx = self.user_to_idx[user_id]

        # --- El Corazón del Algoritmo ---
        # Predicción: $r_{ui} = (U_u \cdot \Sigma) \cdot V^T$
        # Multiplicamos el vector del usuario por los pesos (sigma) 
        # y luego hacemos producto punto con la matriz de películas (Vt)
        user_features = self.u[user_idx, :] * self.sigma
        scores = user_features @ self.vt

        # Obtener los índices de las películas con mayores puntajes
        best_movie_indices = np.argsort(scores)[::-1]

        # Mapear esos índices de matriz a IDs reales de películas
        recommendations = []
        for i in range(top_n):
            idx = str(best_movie_indices[i])
            movie_id = self.movie_map.get(idx)
            if movie_id:
                recommendations.append(int(movie_id))

        return recommendations

# Para probar que funcione:
if __name__ == "__main__":
    recommender = SVDRecommender()
    # Cambia el 1 por un ID de usuario que sepas que está en tu dataset
    print(f"Top 10 para usuario 1: {recommender.get_recommendations(user_id=1)}")
