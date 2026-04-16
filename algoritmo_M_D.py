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

