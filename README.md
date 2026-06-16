# Sistema de Recomendaciones de Peliculas

MVP completo para recomendaciones sobre un subconjunto de MovieLens 25M filtrado a `5.000 usuarios x 5.000 peliculas`.

## Que incluye

- Backend HTTP en Python estandar, sin depender de FastAPI ni SQLAlchemy.
- Persistencia SQLite para usuarios, historial, ratings y likes.
- Pipeline reproducible de preprocesamiento y entrenamiento SVD usando `numpy` y `pandas`.
- Frontend web estatico servido por el mismo backend.
- Recomendacion hibrida:
  - `catalog-popularity` cuando el usuario no tiene interacciones.
  - `genre-popularity` hasta alcanzar `5` interacciones.
  - `latent-svd` cuando ya existe senal suficiente y el modelo esta entrenado.
- Hash de contrasenas con `bcrypt` costo `12` y bloqueo temporal tras `3` intentos fallidos.
- Reentrenamiento automatico al iniciar el servidor y supervision periodica cuando cambian los archivos fuente del dataset.
- Reporte de evaluacion del modelo con `RMSE` y `Precision@10`.
- Tests automatizados con `unittest`.

## Estructura

- [backend/app](backend/app) API, auth, SQLite, servicios y servidor HTTP.
- [backend/ml](backend/ml) preprocesamiento, entrenamiento y motor de recomendacion.
- [frontend](frontend) interfaz web.
- [scripts](scripts) entradas simples para correr servidor y entrenamiento.
- [tests](tests) pruebas unitarias e integracion.
- [docs](docs) notas de arquitectura y operacion.
- [docs/manual_usuario.md](docs/manual_usuario.md) guia de uso de la interfaz y despliegue basico.

## Requisitos

- Python 3.11 o superior
- Dependencias:

```bash
pip install -r backend/requirements.txt
```

## Ejecutar la app

```bash
python scripts/run_server.py
```

Luego abre:

- [http://127.0.0.1:8000](http://127.0.0.1:8000)
- [http://127.0.0.1:8000/login.html](http://127.0.0.1:8000/login.html)

## Despliegue con Docker

1. Ajusta las variables de entorno a partir de `.env.example`.
2. Ejecuta:

```bash
docker compose up --build
```

3. Abre:

- [http://127.0.0.1:8000](http://127.0.0.1:8000)

## Entrenar el modelo

El sistema funciona sin artefactos entrenados, pero cae a recomendaciones por popularidad y genero. Para activar SVD:

```bash
python scripts/run_training.py --k 32
```

Eso genera:

- `backend/data/processed/matrix.npy`
- `backend/data/processed/ratings_triplets.npz`
- `backend/data/processed/movie_stats.csv`
- `backend/data/artifacts/u_matrix.npy`
- `backend/data/artifacts/s_weights.npy`
- `backend/data/artifacts/vt_matrix.npy`

## Ejecutar pruebas

```bash
python -m unittest discover -s tests
```

## Verificacion orientada a requisitos

- `tests/test_api.py`: flujo principal de autenticacion, interacciones e historial.
- `tests/test_modelo.py`: artefactos del pipeline, SVD y metricas.
- `tests/test_recomendador.py`: cold start y fallback por genero.
- `tests/test_requirements.py`: verificaciones alineadas al plan general.

## Flujo principal del usuario

1. Registrarse o iniciar sesion.
2. Buscar peliculas por titulo o genero.
3. Marcar `Me gusta / No me gusta` y guardar ratings.
4. Consultar recomendaciones y revisar historial.
5. Ver perfil con generos preferidos y actividad reciente.

## Endpoints utiles

- `GET /api/health`
- `GET /api/metrics/overview`
- `GET /api/recommendations`
- `POST /api/admin/retrain`

## Notas importantes

- Si no ejecutas entrenamiento manual, el sistema sigue siendo usable.
- El catalogo operativo queda restringido a las `5.000` peliculas del subconjunto filtrado.
- El backend sirve tambien el frontend, asi que no hace falta un servidor aparte para la interfaz.