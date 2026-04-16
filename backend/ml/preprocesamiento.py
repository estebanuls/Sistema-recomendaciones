#"""Prepare filtered datasets and sparse matrices from raw files."""
#codigo para el proceso de matriz dispersa
import os
import json
import pandas as pd
from scipy.sparse import save_npz
from scipy.sparse import csr_matrix

#Rutas absolitas (doble guion bajo __file__)
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

#Cambiado a .csv.gz
DATA_RAW = os.path.join(BASE_DIR, "data", "raw", "ratings_filtrado_nuevo.csv.gz")
DATA_OUT = os.path.join(BASE_DIR, "data", "processed", "matriz.npz")

def construir_matriz(csv_path=DATA_RAW, out_path=DATA_OUT):
    if not os.path.exists(csv_path):
        print(f"Error: No se encuentra el archivo {csv_path}")
        return
    print(f"Cargando dataset comprimido (.gz): {csv_path}...")
    
    # Pandas detecta y descomprime el .gz al vuelo
    df = pd.read_csv(csv_path)

    user_ids = df['userId'].unique()
    movie_ids = df['movieId'].unique()

    user_to_idx = {uid: i for i, uid in enumerate(user_ids)}
    movie_to_idx = {mid: i for i, mid in enumerate(movie_ids)}

    df['user_idx'] = df['userId'].map(user_to_idx)
    df['movie_idx'] = df['movieId'].map(movie_to_idx)

    matriz = csr_matrix(
        (df['rating'], (df['user_idx'], df['movie_idx'])),
        shape=(len(user_ids), len(movie_ids))
    )

    # Crear carpeta processed si no existe
    os.makedirs(os.path.dirname(out_path), exist_ok=True)

    #Guarda matriz comprimida
    save_npz(out_path, matriz)

    # Guardar mapeos
    processed_dir = os.path.dirname(out_path)
    idx_to_user = {int(i): int(uid) for uid, i in user_to_idx.items()}
    idx_to_movie = {int(i): int(mid) for mid, i in movie_to_idx.items()}

    with open(os.path.join(processed_dir, "user_map.json"), "w") as f:
        json.dump(idx_to_user, f)
    with open(os.path.join(processed_dir, "movie_map.json"), "w") as f:
        json.dump(idx_to_movie, f)

    print(f"¡Éxito! Matriz generada con forma: {matriz.shape}")
    return matriz

if __name__ == "__main__": # Doble guion bajo name
    construir_matriz()
