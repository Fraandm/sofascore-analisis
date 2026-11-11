"""API HTTP local para consultar el historial desde otras herramientas.

Escucha únicamente en 127.0.0.1. No está pensada para exponerse a Internet.
"""

from __future__ import annotations

import json
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from threading import Thread
from typing import Any, Dict, Optional
from urllib.parse import parse_qs, urlparse

from .storage import HistoryStore


class LocalAPIServer:
    def __init__(
        self,
        store: HistoryStore,
        host: str = "127.0.0.1",
        port: int = 8765,
    ) -> None:
        self.store = store
        self.host = host
        self.port = port
        self._httpd: Optional[ThreadingHTTPServer] = None
        self._thread: Optional[Thread] = None

    @property
    def url(self) -> str:
        if self._httpd is not None:
            host, port = self._httpd.server_address[:2]
            return f"http://{host}:{port}"
        return f"http://{self.host}:{self.port}"

    @property
    def running(self) -> bool:
        return self._httpd is not None

    def start(self, port: Optional[int] = None) -> str:
        if self._httpd is not None:
            return self.url
        requested = self.port if port is None else int(port)
        last_error: Optional[BaseException] = None
        attempts = [requested] if requested == 0 else list(
            range(requested, requested + 10)
        )
        store = self.store

        for candidate in attempts:
            try:
                httpd = ThreadingHTTPServer(
                    (self.host, candidate), self._handler(store)
                )
            except OSError as exc:
                last_error = exc
                continue
            self._httpd = httpd
            self._thread = Thread(
                target=httpd.serve_forever,
                kwargs={"poll_interval": 0.2},
                daemon=True,
            )
            self._thread.start()
            return self.url
        raise OSError(
            f"No se pudo abrir la API local: {last_error or 'puerto ocupado'}"
        )

    def stop(self) -> None:
        httpd, thread = self._httpd, self._thread
        self._httpd = None
        self._thread = None
        if httpd is not None:
            httpd.shutdown()
            httpd.server_close()
        if thread is not None and thread.is_alive():
            thread.join(timeout=1.5)

    @staticmethod
    def _handler(store: HistoryStore):
        class Handler(BaseHTTPRequestHandler):
            server_version = "SofaScoreLocalAPI/1.0"

            def log_message(self, _format, *_args):  # noqa: A003
                return

            def _send(self, payload: Any, status: int = 200) -> None:
                body = json.dumps(
                    payload, ensure_ascii=False, indent=2, default=str
                ).encode("utf-8")
                self.send_response(status)
                self.send_header(
                    "Content-Type", "application/json; charset=utf-8"
                )
                self.send_header("Content-Length", str(len(body)))
                self.send_header("Cache-Control", "no-store")
                self.end_headers()
                self.wfile.write(body)

            def do_GET(self):  # noqa: N802
                parsed = urlparse(self.path)
                query = parse_qs(parsed.query)
                try:
                    if parsed.path in ("/", "/api"):
                        self._send(
                            {
                                "name": "SofaScore local API",
                                "endpoints": [
                                    "/api/health",
                                    "/api/matches?query=&status=&limit=",
                                    "/api/predictions?limit=",
                                    "/api/accuracy",
                                ],
                                "note": "Uso personal. Solo escucha en 127.0.0.1.",
                            }
                        )
                        return
                    if parsed.path == "/api/health":
                        self._send(
                            {
                                "status": "ok",
                                "predictions": store.count_predictions(),
                                "accuracy": store.accuracy(),
                            }
                        )
                        return
                    if parsed.path == "/api/matches":
                        limit = int((query.get("limit") or ["200"])[0])
                        self._send(
                            {
                                "matches": store.list_matches(
                                    query=(query.get("query") or [""])[0],
                                    status=(query.get("status") or [""])[0],
                                    limit=max(1, min(1000, limit)),
                                )
                            }
                        )
                        return
                    if parsed.path == "/api/predictions":
                        limit = int((query.get("limit") or ["200"])[0])
                        self._send(
                            {
                                "predictions": store.list_predictions(
                                    limit=max(1, min(1000, limit))
                                )
                            }
                        )
                        return
                    if parsed.path == "/api/accuracy":
                        self._send(store.accuracy())
                        return
                    self._send({"error": "not_found"}, 404)
                except (ValueError, TypeError) as exc:
                    self._send({"error": "bad_request", "detail": str(exc)}, 400)
                except Exception as exc:  # noqa: BLE001 - API local
                    self._send({"error": "internal_error", "detail": str(exc)}, 500)

            def do_POST(self):  # noqa: N802
                self._send({"error": "method_not_allowed"}, 405)

        return Handler
