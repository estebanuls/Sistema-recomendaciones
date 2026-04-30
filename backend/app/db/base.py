""" base."""
from __future__ import annotations

from pathlib import Path
import csv
import math

import pandas as pd

from backend.app.core.config import Settings
from backend.app.db.session import get_connection


SCHEMA_STATEMENTS = (
    """
    CREATE TABLE IF NOT EXISTS users (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        username TEXT NOT NULL UNIQUE,
        display_name TEXT NOT NULL,
        password_hash TEXT NOT NULL,
        is_admin INTEGER NOT NULL DEFAULT 0,
        failed_login_attempts INTEGER NOT NULL DEFAULT 0,
        blocked_until TEXT,
        created_at TEXT NOT NULL
    );
    """,
    """
    CREATE TABLE IF NOT EXISTS movies (
        id INTEGER PRIMARY KEY,
        title TEXT NOT NULL,
        genres TEXT NOT NULL,
        mean_rating REAL NOT NULL DEFAULT 0,
        rating_count INTEGER NOT NULL DEFAULT 0,
        popularity_score REAL NOT NULL DEFAULT 0
    );
    """,
    """
    CREATE TABLE IF NOT EXISTS interactions (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id INTEGER NOT NULL,
        movie_id INTEGER NOT NULL,
        rating REAL,
        liked INTEGER,
        source TEXT NOT NULL DEFAULT 'app',
        created_at TEXT NOT NULL,
        updated_at TEXT NOT NULL,
        UNIQUE(user_id, movie_id),
        FOREIGN KEY(user_id) REFERENCES users(id) ON DELETE CASCADE,
        FOREIGN KEY(movie_id) REFERENCES movies(id) ON DELETE CASCADE
    );
    """,
    "CREATE INDEX IF NOT EXISTS idx_movies_title ON movies(title);",
    "CREATE INDEX IF NOT EXISTS idx_interactions_user ON interactions(user_id);",
    "CREATE INDEX IF NOT EXISTS idx_interactions_movie ON interactions(movie_id);",
)

USER_COLUMNS = {
    "is_admin": "ALTER TABLE users ADD COLUMN is_admin INTEGER NOT NULL DEFAULT 0;",
    "failed_login_attempts": "ALTER TABLE users ADD COLUMN failed_login_attempts INTEGER NOT NULL DEFAULT 0;",
    "blocked_until": "ALTER TABLE users ADD COLUMN blocked_until TEXT;",
}


def _compute_movie_stats_from_processed(processed_dir: Path) -> pd.DataFrame | None:
    stats_path = processed_dir / "movie_stats.csv"
    if not stats_path.exists():
        return None
    return pd.read_csv(stats_path)


def _compute_movie_stats_from_raw(ratings_csv_path: Path) -> pd.DataFrame:
    frame = pd.read_csv(
        ratings_csv_path,
        usecols=["movieId", "rating"],
        dtype={"movieId": "int32", "rating": "float32"},
    )
    grouped = frame.groupby("movieId")["rating"].agg(["mean", "count"]).reset_index()
    grouped.columns = ["movieId", "mean_rating", "rating_count"]
    grouped["popularity_score"] = (
        grouped["mean_rating"] * grouped["rating_count"].apply(lambda value: math.log1p(value))
    )
    return grouped


def _load_allowed_movie_ids(settings: Settings) -> set[int]:
    stats = _compute_movie_stats_from_processed(settings.processed_dir)
    if stats is not None:
        return {int(movie_id) for movie_id in stats["movieId"].tolist()}

    ratings = pd.read_csv(
        settings.ratings_csv_path,
        usecols=["movieId"],
        dtype={"movieId": "int32"},
    )
    return {int(movie_id) for movie_id in ratings["movieId"].unique().tolist()}


def _load_movies_catalog(connection, settings: Settings) -> None:
    allowed_movie_ids = _load_allowed_movie_ids(settings)
    current_rows = connection.execute("SELECT id FROM movies").fetchall()
    current_ids = {int(row["id"]) for row in current_rows}

    removable_ids = sorted(current_ids - allowed_movie_ids)
    if removable_ids:
        chunk_size = 900
        for start in range(0, len(removable_ids), chunk_size):
            chunk = removable_ids[start : start + chunk_size]
            placeholders = ",".join("?" for _ in chunk)
            connection.execute(f"DELETE FROM movies WHERE id IN ({placeholders})", chunk)

    missing_ids = allowed_movie_ids - current_ids
    if not missing_ids and len(current_ids) == len(allowed_movie_ids):
        return

    with settings.movies_csv_path.open("r", encoding="utf-8", newline="") as handle:
        reader = csv.DictReader(handle)
        rows = [
            (int(row["movieId"]), row["title"], row["genres"] or "Unknown", 0.0, 0, 0.0)
            for row in reader
            if int(row["movieId"]) in allowed_movie_ids and int(row["movieId"]) in missing_ids
        ]
    if rows:
        connection.executemany(
            """
            INSERT INTO movies (id, title, genres, mean_rating, rating_count, popularity_score)
            VALUES (?, ?, ?, ?, ?, ?)
            """,
            rows,
        )


def _update_movie_stats(connection, settings: Settings) -> None:
    populated = connection.execute(
        "SELECT COUNT(*) AS total FROM movies WHERE rating_count > 0"
    ).fetchone()["total"]
    if populated:
        return

    stats = _compute_movie_stats_from_processed(settings.processed_dir)
    if stats is None:
        stats = _compute_movie_stats_from_raw(settings.ratings_csv_path)

    rows = [
        (
            float(row["mean_rating"]),
            int(row["rating_count"]),
            float(row["popularity_score"]),
            int(row["movieId"]),
        )
        for row in stats.to_dict(orient="records")
    ]
    connection.executemany(
        """
        UPDATE movies
        SET mean_rating = ?, rating_count = ?, popularity_score = ?
        WHERE id = ?
        """,
        rows,
    )


def ensure_database(settings: Settings) -> None:
    settings.logs_dir.mkdir(parents=True, exist_ok=True)
    with get_connection(settings.database_path) as connection:
        for statement in SCHEMA_STATEMENTS:
            connection.execute(statement)
        current_columns = {
            row["name"] for row in connection.execute("PRAGMA table_info(users);").fetchall()
        }
        for column_name, alter_statement in USER_COLUMNS.items():
            if column_name not in current_columns:
                connection.execute(alter_statement)
        _load_movies_catalog(connection, settings)
        _update_movie_stats(connection, settings)