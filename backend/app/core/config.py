"""Application settings loaded from environment variables."""

from __future__ import annotations

from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path
import os


ROOT_DIR = Path(__file__).resolve().parents[3]
BACKEND_DIR = ROOT_DIR / "backend"
FRONTEND_DIR = ROOT_DIR / "frontend"


@dataclass(slots=True)
class Settings:
    project_name: str
    environment: str
    host: str
    port: int
    secret_key: str
    token_ttl_minutes: int
    bcrypt_rounds: int
    login_block_minutes: int
    max_login_attempts: int
    min_cold_start_interactions: int
    default_recommendation_count: int
    auto_retrain_on_startup: bool
    auto_retrain_interval_seconds: int
    latent_factors: int
    root_dir: Path
    backend_dir: Path
    frontend_dir: Path
    data_dir: Path
    raw_data_dir: Path
    processed_dir: Path
    artifacts_dir: Path
    logs_dir: Path
    database_path: Path
    movies_csv_path: Path
    ratings_csv_path: Path


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    data_dir = BACKEND_DIR / "data"
    return Settings(
        project_name=os.getenv("PROJECT_NAME", "MovieLens Recommender"),
        environment=os.getenv("APP_ENV", "development"),
        host=os.getenv("APP_HOST", "127.0.0.1"),
        port=int(os.getenv("APP_PORT", "8000")),
        secret_key=os.getenv("APP_SECRET_KEY", "dev-secret-change-me"),
        token_ttl_minutes=int(os.getenv("TOKEN_TTL_MINUTES", "1440")),
        bcrypt_rounds=max(12, int(os.getenv("BCRYPT_ROUNDS", "12"))),
        login_block_minutes=int(os.getenv("LOGIN_BLOCK_MINUTES", "15")),
        max_login_attempts=int(os.getenv("MAX_LOGIN_ATTEMPTS", "3")),
        min_cold_start_interactions=int(os.getenv("MIN_COLD_START_INTERACTIONS", "5")),
        default_recommendation_count=int(os.getenv("DEFAULT_RECOMMENDATION_COUNT", "10")),
        auto_retrain_on_startup=os.getenv("AUTO_RETRAIN_ON_STARTUP", "true").lower() not in {"0", "false", "no"},
        auto_retrain_interval_seconds=int(os.getenv("AUTO_RETRAIN_INTERVAL_SECONDS", "300")),
        latent_factors=int(os.getenv("LATENT_FACTORS", "32")),
        root_dir=ROOT_DIR,
        backend_dir=BACKEND_DIR,
        frontend_dir=FRONTEND_DIR,
        data_dir=data_dir,
        raw_data_dir=data_dir / "raw",
        processed_dir=data_dir / "processed",
        artifacts_dir=data_dir / "artifacts",
        logs_dir=BACKEND_DIR / "logs",
        database_path=data_dir / "app.db",
        movies_csv_path=data_dir / "raw" / "movies.csv",
        ratings_csv_path=data_dir / "raw" / "ratings_filtrado_nuevo.csv.gz",
    )
