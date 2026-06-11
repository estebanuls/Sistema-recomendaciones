"""User CRUD and interaction helpers."""
from __future__ import annotations

from collections import Counter
from datetime import datetime, timedelta, timezone

from backend.app.api import ApiError
from backend.app.core.security import hash_password, needs_password_rehash, verify_password
from backend.app.models.interaction import Interaction
from backend.app.models.user import User
from backend.app.schemas.user import UserCreate


def _utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _ensure_movie_exists(connection, movie_id: int) -> None:
    row = connection.execute("SELECT id FROM movies WHERE id = ?", (movie_id,)).fetchone()
    if not row:
        raise ApiError(404, "La pelicula indicada no existe en el catalogo.")


def _resolve_bcrypt_rounds(settings) -> int:
    if settings is None:
        return 12
    return max(12, int(settings.bcrypt_rounds))


def create_user(connection, payload: UserCreate, settings=None) -> User:
    exists = connection.execute(
        "SELECT id FROM users WHERE lower(username) = lower(?)",
        (payload.username,),
    ).fetchone()
    if exists:
        raise ApiError(409, "Ese nombre de usuario ya esta en uso.")

    created_at = _utc_now()
    password_hash = hash_password(payload.password, rounds=_resolve_bcrypt_rounds(settings))
    cursor = connection.execute(
        """
        INSERT INTO users (username, display_name, password_hash, failed_login_attempts, blocked_until, created_at)
        VALUES (?, ?, ?, 0, NULL, ?)
        """,
        (payload.username, payload.display_name, password_hash, created_at),
    )
    row = connection.execute(
        "SELECT id, username, display_name, created_at FROM users WHERE id = ?",
        (cursor.lastrowid,),
    ).fetchone()
    return User.from_row(row)


def _parse_iso_datetime(value: str | None) -> datetime | None:
    if not value:
        return None
    return datetime.fromisoformat(value)


def authenticate_user(connection, username: str, password: str, settings) -> User:
    row = connection.execute(
        """
        SELECT id, username, display_name, created_at, is_admin, password_hash, failed_login_attempts, blocked_until
        FROM users
        WHERE lower(username) = lower(?)
        """,
        (username.strip(),),
    ).fetchone()
    if not row:
        raise ApiError(401, "Credenciales invalidas.")

    blocked_until = _parse_iso_datetime(row.get("blocked_until"))
    now = datetime.now(timezone.utc)
    if blocked_until and blocked_until > now:
        raise ApiError(
            429,
            f"Cuenta bloqueada temporalmente hasta {blocked_until.astimezone(timezone.utc).isoformat()}",
        )

    stored_hash = str(row["password_hash"])
    if not verify_password(password, stored_hash):
        failed_attempts = int(row.get("failed_login_attempts") or 0) + 1
        blocked_value = None
        if failed_attempts >= settings.max_login_attempts:
            blocked_value = (now + timedelta(minutes=settings.login_block_minutes)).isoformat()
            failed_attempts = 0
        connection.execute(
            """
            UPDATE users
            SET failed_login_attempts = ?, blocked_until = ?
            WHERE id = ?
            """,
            (failed_attempts, blocked_value, row["id"]),
        )
        connection.commit()
        if blocked_value:
            raise ApiError(429, "Cuenta bloqueada temporalmente por demasiados intentos fallidos.")
        raise ApiError(401, "Credenciales invalidas.")

    new_hash = stored_hash
    if needs_password_rehash(stored_hash):
        new_hash = hash_password(password, rounds=_resolve_bcrypt_rounds(settings))
    connection.execute(
        """
        UPDATE users
        SET password_hash = ?, failed_login_attempts = 0, blocked_until = NULL
        WHERE id = ?
        """,
        (new_hash, row["id"]),
    )
    connection.commit()
    return User.from_row(row)


def get_user_by_id(connection, user_id: int) -> User | None:
    row = connection.execute(
        "SELECT id, username, display_name, created_at, is_admin FROM users WHERE id = ?",
        (user_id,),
    ).fetchone()
    if not row:
        return None
    return User.from_row(row)


def record_rating(connection, user_id: int, movie_id: int, rating: float) -> Interaction:
    _ensure_movie_exists(connection, movie_id)
    timestamp = _utc_now()
    current = connection.execute(
        "SELECT * FROM interactions WHERE user_id = ? AND movie_id = ?",
        (user_id, movie_id),
    ).fetchone()

    if current:
        connection.execute(
            """
            UPDATE interactions
            SET rating = ?, updated_at = ?
            WHERE id = ?
            """,
            (rating, timestamp, current["id"]),
        )
        interaction_id = int(current["id"])
    else:
        cursor = connection.execute(
            """
            INSERT INTO interactions (user_id, movie_id, rating, liked, source, created_at, updated_at)
            VALUES (?, ?, ?, NULL, 'app', ?, ?)
            """,
            (user_id, movie_id, rating, timestamp, timestamp),
        )
        interaction_id = int(cursor.lastrowid)

    row = connection.execute(
        """
        SELECT i.*, m.title AS movie_title, m.genres AS movie_genres
        FROM interactions i
        JOIN movies m ON m.id = i.movie_id
        WHERE i.id = ?
        """,
        (interaction_id,),
    ).fetchone()
    return Interaction.from_row(row)


def record_like(connection, user_id: int, movie_id: int, liked: bool) -> Interaction:
    _ensure_movie_exists(connection, movie_id)
    timestamp = _utc_now()
    current = connection.execute(
        "SELECT * FROM interactions WHERE user_id = ? AND movie_id = ?",
        (user_id, movie_id),
    ).fetchone()

    if current:
        connection.execute(
            """
            UPDATE interactions
            SET liked = ?, updated_at = ?
            WHERE id = ?
            """,
            (1 if liked else 0, timestamp, current["id"]),
        )
        interaction_id = int(current["id"])
    else:
        cursor = connection.execute(
            """
            INSERT INTO interactions (user_id, movie_id, rating, liked, source, created_at, updated_at)
            VALUES (?, ?, NULL, ?, 'app', ?, ?)
            """,
            (user_id, movie_id, 1 if liked else 0, timestamp, timestamp),
        )
        interaction_id = int(cursor.lastrowid)

    row = connection.execute(
        """
        SELECT i.*, m.title AS movie_title, m.genres AS movie_genres
        FROM interactions i
        JOIN movies m ON m.id = i.movie_id
        WHERE i.id = ?
        """,
        (interaction_id,),
    ).fetchone()
    return Interaction.from_row(row)


def list_user_interactions(connection, user_id: int, limit: int = 50) -> list[Interaction]:
    rows = connection.execute(
        """
        SELECT i.*, m.title AS movie_title, m.genres AS movie_genres
        FROM interactions i
        JOIN movies m ON m.id = i.movie_id
        WHERE i.user_id = ?
        ORDER BY i.updated_at DESC
        LIMIT ?
        """,
        (user_id, limit),
    ).fetchall()
    return [Interaction.from_row(row) for row in rows]


def get_user_profile(connection, user_id: int) -> dict[str, object]:
    user = get_user_by_id(connection, user_id)
    if not user:
        raise ApiError(404, "Usuario no encontrado.")

    interactions = list_user_interactions(connection, user_id, limit=500)
    liked_count = sum(1 for item in interactions if item.liked is True)
    rated_count = sum(1 for item in interactions if item.rating is not None)
    genre_counter: Counter[str] = Counter()

    for item in interactions:
        positive_signal = (item.rating is not None and item.rating >= 3.5) or item.liked is True
        if positive_signal and item.movie_genres:
            genre_counter.update(
                genre
                for genre in item.movie_genres.split("|")
                if genre and genre != "(no genres listed)"
            )

    favorite_genres = [genre for genre, _ in genre_counter.most_common(5)]
    return {
        "user": user.to_public_dict(),
        "liked_count": liked_count,
        "rated_count": rated_count,
        "history_count": len(interactions),
        "favorite_genres": favorite_genres,
        "recent_history": [item.to_public_dict() for item in interactions[:10]],
    }
