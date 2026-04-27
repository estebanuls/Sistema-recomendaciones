#codigo
#librerias ha usar
from scipy.sparse import csr_matrix
from scipy import sparse
import pandas as pd
import os

nombre_archivo = 'archivo dataset' #aqui se necesita el archivo
sparse.save_npz(nombre_archivo, sparse_matrix)

# Ver cuánto pesa el archivo en el disco
tamaño = os.path.getsize(nombre_archivo) / (1024 * 1024)#pregunta cuanto pesa el archivo guardado y conbierte los bites ah mega (convergencia)
print(f"Archivo guardado: {nombre_archivo}")
print(f"Peso en disco: {tamaño:.2f} MB")

#iniciar la carga de la base de datos
df = pd.read_csv('archivo dataset')

#Crear categorías para manejar los IDs como índices
# Esto mapea los IDs originales a rangos de 0 a N-1
user_u = list(df.userId.unique())
movie_u = list(df.movieId.unique())

data = df['rating'].tolist()
row = df.userId.astype('category').cat.codes
col = df.movieId.astype('category').cat.codes

#Se construye la matriz dispersa (formato CSR)
sparse_matrix = csr_matrix((data, (row, col)), shape=(len(user_u), len(movie_u)))

print(f"Dimensiones de la matriz: {sparse_matrix.shape}")
print(f"Elementos no nulos: {sparse_matrix.nnz}")




