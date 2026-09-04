from __future__ import annotations

import json
import mimetypes
import os
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from .config import load_env
from .domain import ParkingReading
from .repository import MemoryReadingRepository, SupabaseReadingRepository

ROOT = Path(__file__).resolve().parent.parent
STATIC = ROOT / "static"
load_env(ROOT / ".env")


@dataclass
class Response:
    status: int
    body: bytes
    content_type: str = "application/json; charset=utf-8"


def json_response(status: int, payload: Any) -> Response:
    return Response(status, json.dumps(payload, ensure_ascii=False).encode("utf-8"))


def build_repository():
    url = os.getenv("SUPABASE_URL")
    key = os.getenv("SUPABASE_SECRET_KEY") or os.getenv("SUPABASE_SERVICE_ROLE_KEY")
    if url and key:
        return SupabaseReadingRepository(url, key)
    return MemoryReadingRepository()


class ParkingApplication:
    def __init__(self, repository=None, ingest_key: str | None = None) -> None:
        self.repository = repository or build_repository()
        self.ingest_key = ingest_key if ingest_key is not None else os.getenv("PARKING_INGEST_KEY", "")

    def dispatch(
        self,
        method: str,
        path: str,
        headers: dict[str, str] | None = None,
        body: bytes = b"",
    ) -> Response:
        headers = {key.lower(): value for key, value in (headers or {}).items()}
        if method == "GET" and path == "/api/health":
            configured = bool(
                os.getenv("SUPABASE_URL")
                and (os.getenv("SUPABASE_SECRET_KEY") or os.getenv("SUPABASE_SERVICE_ROLE_KEY"))
            )
            return json_response(200, {"status": "ok", "database": "supabase" if configured else "memory"})
        if method == "GET" and path == "/api/readings/latest":
            try:
                reading = self.repository.latest()
                return json_response(200, {"reading": reading})
            except Exception:
                return json_response(503, {"error": "Nao foi possivel consultar o banco de dados."})
        if method == "POST" and path == "/api/readings":
            if not self.ingest_key:
                return json_response(503, {"error": "Chave de ingestao nao configurada."})
            if headers.get("x-ingest-key") != self.ingest_key:
                return json_response(401, {"error": "Chave de ingestao invalida."})
            try:
                payload = json.loads(body or b"{}")
                reading = ParkingReading.from_payload(payload)
                saved = self.repository.save(reading)
                return json_response(201, {"reading": saved})
            except (KeyError, TypeError, ValueError, json.JSONDecodeError) as error:
                return json_response(422, {"error": str(error)})
            except Exception:
                return json_response(503, {"error": "Nao foi possivel persistir a leitura."})
        if method == "GET" and (path == "/" or path.startswith("/static/")):
            candidate = ROOT / "index.html" if path == "/" else STATIC / path.removeprefix("/static/")
            candidate = candidate.resolve()
            if path != "/" and STATIC.resolve() not in candidate.parents:
                return json_response(404, {"error": "Arquivo nao encontrado."})
            if candidate.is_file():
                mime = mimetypes.guess_type(candidate.name)[0] or "application/octet-stream"
                return Response(200, candidate.read_bytes(), f"{mime}; charset=utf-8")
        return json_response(404, {"error": "Rota nao encontrada."})


def create_asgi_app(application: ParkingApplication | None = None):
    parking = application or ParkingApplication()

    async def app(scope, receive, send):
        if scope["type"] != "http":
            return
        chunks = []
        more = True
        while more:
            message = await receive()
            chunks.append(message.get("body", b""))
            more = message.get("more_body", False)
        headers = {
            key.decode("latin-1"): value.decode("latin-1")
            for key, value in scope.get("headers", [])
        }
        response = parking.dispatch(
            scope["method"], scope["path"], headers, b"".join(chunks)
        )
        await send({"type": "http.response.start", "status": response.status, "headers": [(b"content-type", response.content_type.encode("latin-1")), (b"cache-control", b"no-store")]})
        await send({"type": "http.response.body", "body": response.body})

    return app


app = create_asgi_app()
