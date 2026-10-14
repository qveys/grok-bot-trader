"""API HTTP du gardien pour Grok Bot — stdlib uniquement.

Deux endpoints, token Bearer obligatoire :
  GET  /wake      -> 200 + contexte texte si un réveil est en attente, sinon 204
  POST /decision  -> le JSON de décision du bot ; mis en file, traité par la boucle

À exposer derrière un reverse proxy TLS (Caddy, nginx). Jamais en HTTP nu sur Internet.
"""
from __future__ import annotations

import hmac
import json
import logging
import queue
import threading
from dataclasses import dataclass, field
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

log = logging.getLogger("api")

MAX_BODY = 64 * 1024


@dataclass
class Mailbox:
    """Boîte partagée entre la boucle du gardien et le serveur HTTP."""
    token: str
    lock: threading.Lock = field(default_factory=threading.Lock)
    pending_wake_id: str | None = None
    pending_context: str = ""
    decisions: "queue.Queue[dict]" = field(default_factory=queue.Queue)

    # --- côté gardien
    def open_wake(self, wake_id: str, context: str) -> None:
        with self.lock:
            self.pending_wake_id = wake_id
            self.pending_context = context

    def close_wake(self) -> None:
        with self.lock:
            self.pending_wake_id = None
            self.pending_context = ""

    def current_wake(self) -> str | None:
        with self.lock:
            return self.pending_wake_id

    # --- côté serveur
    def snapshot(self) -> tuple[str | None, str]:
        with self.lock:
            return self.pending_wake_id, self.pending_context


class _Handler(BaseHTTPRequestHandler):
    mailbox: Mailbox = None  # injecté par serve()

    def log_message(self, fmt, *args):  # journal via logging, pas stderr
        log.debug(fmt, *args)

    def _authorized(self) -> bool:
        auth = self.headers.get("Authorization", "")
        expected = f"Bearer {self.mailbox.token}"
        return hmac.compare_digest(auth.encode(), expected.encode())

    def _send(self, code: int, body: bytes = b"", content_type: str = "text/plain; charset=utf-8") -> None:
        self.send_response(code)
        self.send_header("Content-Type", content_type)
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        if body:
            self.wfile.write(body)

    def do_GET(self):
        if not self._authorized():
            return self._send(401)
        if self.path != "/wake":
            return self._send(404)
        wake_id, context = self.mailbox.snapshot()
        if not wake_id:
            return self._send(204)
        self._send(200, context.encode("utf-8"))

    def do_POST(self):
        if not self._authorized():
            return self._send(401)
        if self.path != "/decision":
            return self._send(404)
        length = int(self.headers.get("Content-Length", "0"))
        if length <= 0 or length > MAX_BODY:
            return self._send(413)
        raw = self.rfile.read(length)
        try:
            decision = json.loads(raw.decode("utf-8"))
            assert isinstance(decision, dict)
        except (ValueError, AssertionError):
            return self._send(400, b"JSON invalide")
        wake_id, _ = self.mailbox.snapshot()
        if not wake_id:
            return self._send(409, b"Aucun r\xc3\xa9veil en attente")
        if decision.get("decision_id") != wake_id:
            return self._send(409, f"decision_id attendu : {wake_id}".encode("utf-8"))
        self.mailbox.decisions.put(decision)
        self._send(202, b"Re\xc3\xa7u, en cours de validation")


def serve(mailbox: Mailbox, host: str, port: int) -> ThreadingHTTPServer:
    _Handler.mailbox = mailbox
    server = ThreadingHTTPServer((host, port), _Handler)
    thread = threading.Thread(target=server.serve_forever, name="api", daemon=True)
    thread.start()
    log.info("API du gardien sur %s:%d", host, port)
    return server
