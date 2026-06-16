from __future__ import annotations

from dataclasses import replace
from http.client import HTTPConnection
import json
import threading
import unittest

import pandas as pd

from backend.app.core.config import get_settings
from backend.app.db.session import get_connection
from backend.app.main import create_server
from tests.helpers import workspace_temp_dir


class TestApi(unittest.TestCase):
    def setUp(self) -> None:
        self.temp_context = workspace_temp_dir("api")
        root = self.temp_context.__enter__()
        self.temp_dir = root
        backend_dir = root / "backend"
        raw_dir = backend_dir / "data" / "raw"
        processed_dir = backend_dir / "data" / "processed"
        artifacts_dir = backend_dir / "data" / "artifacts"
        frontend_dir = root / "frontend"
        private_dir = root / "frontend-private"
        logs_dir = backend_dir / "logs"

        for directory in (raw_dir, processed_dir, artifacts_dir, frontend_dir, private_dir, logs_dir):
            directory.mkdir(parents=True, exist_ok=True)

        (frontend_dir / "index.html").write_text("<!doctype html><title>home</title>", encoding="utf-8")
        (frontend_dir / "login.html").write_text("<!doctype html><title>login</title>", encoding="utf-8")
        (frontend_dir / "profile.html").write_text("<!doctype html><title>profile</title>", encoding="utf-8")
        (private_dir / "secret.txt").write_text("TOP-SECRET", encoding="utf-8")

        movies = pd.DataFrame(
            [
                {"movieId": 1, "title": "Toy Mission", "genres": "Animation|Adventure"},
                {"movieId": 2, "title": "Toy Return", "genres": "Animation|Comedy"},
                {"movieId": 3, "title": "Steel Night", "genres": "Action|Thriller"},
            ]
        )
        ratings = pd.DataFrame(
            [
                {"userId": 10, "movieId": 1, "rating": 5.0, "timestamp": 1},
                {"userId": 11, "movieId": 2, "rating": 4.0, "timestamp": 2},
                {"userId": 12, "movieId": 3, "rating": 3.0, "timestamp": 3},
            ]
        )
        movies.to_csv(raw_dir / "movies.csv", index=False)
        ratings.to_csv(raw_dir / "ratings_filtrado_nuevo.csv.gz", index=False, compression="gzip")

        base = get_settings()
        self.settings = replace(
            base,
            root_dir=root,
            backend_dir=backend_dir,
            frontend_dir=frontend_dir,
            data_dir=backend_dir / "data",
            raw_data_dir=raw_dir,
            processed_dir=processed_dir,
            artifacts_dir=artifacts_dir,
            logs_dir=logs_dir,
            database_path=backend_dir / "data" / "app.db",
            movies_csv_path=raw_dir / "movies.csv",
            ratings_csv_path=raw_dir / "ratings_filtrado_nuevo.csv.gz",
            host="127.0.0.1",
            port=0,
            auto_retrain_interval_seconds=0,
        )

        self.server = create_server(self.settings)
        self.thread = threading.Thread(target=self.server.serve_forever, daemon=True)
        self.thread.start()
        self.port = self.server.server_address[1]

    def tearDown(self) -> None:
        self.server.shutdown()
        self.server.server_close()
        self.thread.join(timeout=2)
        self.temp_context.__exit__(None, None, None)

    def request(self, method: str, path: str, body: dict[str, object] | None = None, token: str | None = None):
        connection = HTTPConnection("127.0.0.1", self.port, timeout=10)
        payload = json.dumps(body).encode("utf-8") if body is not None else None
        headers = {"Content-Type": "application/json"}
        if token:
            headers["Authorization"] = f"Bearer {token}"
        connection.request(method, path, body=payload, headers=headers)
        response = connection.getresponse()
        data = json.loads(response.read().decode("utf-8"))
        connection.close()
        return response.status, data

    def request_text(self, method: str, path: str):
        connection = HTTPConnection("127.0.0.1", self.port, timeout=10)
        connection.request(method, path)
        response = connection.getresponse()
        body = response.read().decode("utf-8")
        connection.close()
        return response.status, body

    def test_full_api_flow(self) -> None:
        status, register_payload = self.request(
            "POST",
            "/api/auth/register",
            {"username": "mati", "display_name": "Mati", "password": "secret12"},
        )
        self.assertEqual(status, 201)
        token = register_payload["access_token"]
        self.assertEqual(register_payload["user"]["username"], "mati")

        with get_connection(self.settings.database_path) as connection:
            row = connection.execute(
                "SELECT password_hash FROM users WHERE username = ?",
                ("mati",),
            ).fetchone()
        self.assertTrue(str(row["password_hash"]).startswith("$2"))

        status, me_payload = self.request("GET", "/api/auth/me", token=token)
        self.assertEqual(status, 200)
        self.assertEqual(me_payload["user"]["username"], "mati")

        status, movies_payload = self.request("GET", "/api/movies?query=toy&limit=5")
        self.assertEqual(status, 200)
        self.assertEqual(movies_payload["count"], 2)

        status, like_payload = self.request(
            "POST",
            "/api/interactions/like",
            {"movie_id": 1, "liked": True},
            token=token,
        )
        self.assertEqual(status, 200)
        self.assertTrue(like_payload["interaction"]["liked"])

        status, recommendations_payload = self.request("GET", "/api/recommendations?limit=5", token=token)
        self.assertEqual(status, 200)
        self.assertGreaterEqual(recommendations_payload["count"], 1)

        status, history_payload = self.request("GET", "/api/interactions/history?limit=5", token=token)
        self.assertEqual(status, 200)
        self.assertEqual(history_payload["count"], 1)

        status, invalid_history_payload = self.request(
            "GET",
            "/api/interactions/history?limit=foo",
            token=token,
        )
        self.assertEqual(status, 400)
        self.assertIn("limit", invalid_history_payload["detail"])

        status, invalid_rating = self.request(
            "POST",
            "/api/interactions/rate",
            {"movie_id": 1, "rating": 3.7},
            token=token,
        )
        self.assertEqual(status, 422)
        self.assertIn("0.5", str(invalid_rating["detail"]))

        status, overview_payload = self.request("GET", "/api/metrics/overview")
        self.assertEqual(status, 200)
        self.assertIn("evaluation", overview_payload)

    def test_static_file_traversal_is_blocked(self) -> None:
        status, body = self.request_text("GET", "/../frontend-private/secret.txt")
        self.assertEqual(status, 403)
        self.assertIn("Acceso denegado", body)

    def test_rating_validation_and_login_block(self) -> None:
        status, _ = self.request(
            "POST",
            "/api/auth/register",
            {"username": "lina", "display_name": "Lina", "password": "secret12"},
        )
        self.assertEqual(status, 201)

        for _ in range(2):
            status, _ = self.request(
                "POST",
                "/api/auth/login",
                {"username": "lina", "password": "mala"},
            )
            self.assertEqual(status, 401)

        status, blocked_payload = self.request(
            "POST",
            "/api/auth/login",
            {"username": "lina", "password": "mala"},
        )
        self.assertEqual(status, 429)
        self.assertIn("bloqueada", blocked_payload["detail"])


if __name__ == "__main__":
    unittest.main()
