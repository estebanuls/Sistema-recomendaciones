"""HTTP server for the movie recommendation system."""

from __future__ import annotations

from dataclasses import dataclass
from functools import partial
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
import json
import mimetypes
import re
import traceback
from urllib.parse import parse_qs, urlparse

from pydantic import ValidationError

from backend.app.api import ApiError
from backend.app.api import admin, auth, interactions, movies, recommendations, users
from backend.app.core.config import Settings, get_settings
from backend.app.core.security import decode_access_token, extract_bearer_token
from backend.app.db.base import ensure_database
from backend.app.db.session import get_connection
from backend.app.services.metrics import build_overview
from backend.app.services.recommendation import RecommendationService
from backend.app.services.training import TrainingSupervisor
from backend.app.services.user_service import get_user_by_id
from backend.app.utils.logger import get_logger
from backend.ml.entrenamiento import ensure_pipeline_outputs


@dataclass(slots=True)
class Route:
    method: str
    pattern: re.Pattern[str]
    handler: object
    auth_required: bool = False


@dataclass(slots=True)
class AppContext:
    settings: Settings
    recommendation_service: RecommendationService
    training_supervisor: TrainingSupervisor | None
    logger: object


class ApplicationServer(ThreadingHTTPServer):
    def __init__(self, server_address, handler, *, context: AppContext):
        self.context = context
        super().__init__(server_address, handler)

    def server_close(self) -> None:
        if self.context.training_supervisor is not None:
            self.context.training_supervisor.stop()
        super().server_close()


def _json_bytes(payload: dict[str, object]) -> bytes:
    return json.dumps(payload, ensure_ascii=False).encode("utf-8")


def _read_json_body(handler: BaseHTTPRequestHandler) -> dict[str, object]:
    raw_length = handler.headers.get("Content-Length", "0")
    try:
        length = int(raw_length)
    except ValueError:
        raise ApiError(400, "Content-Length invalido.")
    if length <= 0:
        return {}
    raw_body = handler.rfile.read(length).decode("utf-8")
    try:
        return json.loads(raw_body)
    except json.JSONDecodeError as exc:
        raise ApiError(400, "El cuerpo debe ser JSON valido.") from exc


class ApplicationHandler(BaseHTTPRequestHandler):
    server_version = "MovieRecommender/1.0"

    def __init__(self, *args, context: AppContext, **kwargs):
        self.context = context
        super().__init__(*args, **kwargs)

    @property
    def routes(self) -> list[Route]:
        return [
            Route("GET", re.compile(r"^/api/health$"), self.health),
            Route("GET", re.compile(r"^/api/metrics/overview$"), self.metrics_overview),
            Route("POST", re.compile(r"^/api/auth/register$"), auth.register),
            Route("POST", re.compile(r"^/api/auth/login$"), auth.login),
            Route("GET", re.compile(r"^/api/auth/me$"), auth.me, auth_required=True),
            Route("GET", re.compile(r"^/api/movies$"), movies.list_movies),
            Route("GET", re.compile(r"^/api/movies/(?P<movie_id>\d+)$"), movies.get_movie),
            Route("GET", re.compile(r"^/api/users/profile$"), users.profile, auth_required=True),
            Route("POST", re.compile(r"^/api/interactions/rate$"), interactions.rate_movie, auth_required=True),
            Route("POST", re.compile(r"^/api/interactions/like$"), interactions.like_movie, auth_required=True),
            Route("GET", re.compile(r"^/api/interactions/history$"), interactions.history, auth_required=True),
            Route("GET", re.compile(r"^/api/recommendations$"), recommendations.list_recommendations, auth_required=True),
            Route("POST", re.compile(r"^/api/admin/retrain$"), admin.retrain, auth_required=True),
        ]

    def log_message(self, format_string: str, *args) -> None:
        self.context.logger.info("%s - %s", self.address_string(), format_string % args)

    def do_OPTIONS(self) -> None:
        self.send_response(204)
        self._send_default_headers("application/json; charset=utf-8")
        self.end_headers()

    def do_GET(self) -> None:
        self._dispatch_request()

    def do_POST(self) -> None:
        self._dispatch_request()

    def health(self, **_) -> tuple[int, dict[str, object]]:
        return 200, {
            "status": "ok",
            "project_name": self.context.settings.project_name,
            "model_ready": self.context.recommendation_service.model_ready,
        }

    def metrics_overview(self, *, connection, **_) -> tuple[int, dict[str, object]]:
        return 200, build_overview(
            connection=connection,
            settings=self.context.settings,
            recommendation_service=self.context.recommendation_service,
        )

    def _dispatch_request(self) -> None:
        parsed = urlparse(self.path)
        if not parsed.path.startswith("/api/"):
            self._serve_static(parsed.path)
            return

        try:
            route, path_params = self._match_route(parsed.path, self.command)
            query_params = parse_qs(parsed.query)
            body = _read_json_body(self) if self.command in {"POST", "PUT", "PATCH"} else {}
            current_user = None

            with get_connection(self.context.settings.database_path) as connection:
                if route.auth_required:
                    current_user = self._resolve_current_user(connection)
                status_code, payload = route.handler(
                    context=self.context,
                    connection=connection,
                    query_params=query_params,
                    path_params=path_params,
                    body=body,
                    current_user=current_user,
                )
            self._write_json(status_code, payload)
        except ApiError as exc:
            self._write_json(exc.status_code, {"detail": exc.detail})
        except ValidationError as exc:
            self._write_json(422, {"detail": json.loads(exc.json())})
        except Exception as exc:
            self.context.logger.error("Unhandled error: %s\n%s", exc, traceback.format_exc())
            self._write_json(500, {"detail": "Error interno del servidor."})

    def _match_route(self, path: str, method: str) -> tuple[Route, dict[str, str]]:
        for route in self.routes:
            if route.method != method:
                continue
            match = route.pattern.match(path)
            if match:
                return route, match.groupdict()
        raise ApiError(404, "Ruta no encontrada.")

    def _resolve_current_user(self, connection):
        token = extract_bearer_token(self.headers.get("Authorization"))
        if not token:
            raise ApiError(401, "Se requiere autenticacion.")
        try:
            payload = decode_access_token(token, self.context.settings.secret_key)
        except ValueError as exc:
            raise ApiError(401, str(exc)) from exc

        user = get_user_by_id(connection, int(payload["sub"]))
        if not user:
            raise ApiError(401, "Usuario no encontrado.")
        return user

    def _send_default_headers(self, content_type: str) -> None:
        self.send_header("Content-Type", content_type)
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Headers", "Authorization, Content-Type")
        self.send_header("Access-Control-Allow-Methods", "GET, POST, OPTIONS")
        self.send_header("Cache-Control", "no-store")

    def _write_json(self, status_code: int, payload: dict[str, object]) -> None:
        body = _json_bytes(payload)
        self.send_response(status_code)
        self._send_default_headers("application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def _serve_static(self, path: str) -> None:
        requested_path = path or "/"
        if requested_path == "/":
            file_path = self.context.settings.frontend_dir / "index.html"
        else:
            file_path = self.context.settings.frontend_dir / requested_path.lstrip("/")

        try:
            resolved = file_path.resolve(strict=True)
        except FileNotFoundError:
            self._write_json(404, {"detail": "Archivo no encontrado."})
            return

        frontend_root = self.context.settings.frontend_dir.resolve()
        if not resolved.is_relative_to(frontend_root):
            self._write_json(403, {"detail": "Acceso denegado."})
            return

        mime_type, _ = mimetypes.guess_type(str(resolved))
        content_type = mime_type or "application/octet-stream"
        content = resolved.read_bytes()
        self.send_response(200)
        self._send_default_headers(content_type)
        self.send_header("Content-Length", str(len(content)))
        self.end_headers()
        self.wfile.write(content)


def create_server(settings: Settings | None = None) -> ThreadingHTTPServer:
    settings = settings or get_settings()
    if settings.auto_retrain_on_startup:
        ensure_pipeline_outputs(settings)
    ensure_database(settings)
    context = AppContext(
        settings=settings,
        recommendation_service=RecommendationService(settings),
        training_supervisor=None,
        logger=get_logger(settings.logs_dir),
    )
    training_supervisor = TrainingSupervisor(
        settings=settings,
        recommendation_service=context.recommendation_service,
        logger=context.logger,
    )
    context.training_supervisor = training_supervisor
    handler = partial(ApplicationHandler, context=context)
    server = ApplicationServer((settings.host, settings.port), handler, context=context)
    training_supervisor.start()
    return server


def run(settings: Settings | None = None) -> None:
    settings = settings or get_settings()
    server = create_server(settings)
    logger = get_logger(settings.logs_dir)
    logger.info("Servidor iniciado en http://%s:%s", settings.host, settings.port)
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        logger.info("Servidor detenido por el usuario.")
    finally:
        server.server_close()


if __name__ == "__main__":
    run()
