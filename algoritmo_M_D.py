#codigo
#librerias ha usar
from scipy.sparse import csr_matrix
from scipy import sparse
import pandas as pd
import os

nombre_archivo = 'archivo dataset' #aqui se necesita el archivo

#iniciar la carga de la base de datos
df = pd.read_csv('archivo dataset')
