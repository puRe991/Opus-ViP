"""Dependency-free HTTP server for the Opus-ViP MVP."""

from __future__ import annotations

import json
from http import HTTPStatus
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import parse_qs, urlparse

from .analysis import parse_transcript, rank_clips
from .storage import create_project, get_project, list_projects

WEB_ROOT = Path(__file__).resolve().parents[2] / "web"


class AppHandler(BaseHTTPRequestHandler):
    server_version = "OpusViP/0.1"

    def do_GET(self) -> None:  # noqa: N802 - stdlib API
        parsed = urlparse(self.path)
        if parsed.path == "/api/projects":
            self._json([project.__dict__ for project in list_projects()])
            return
        if parsed.path.startswith("/api/projects/"):
            try:
                self._json(get_project(parsed.path.rsplit("/", 1)[-1]).__dict__)
            except (FileNotFoundError, ValueError):
                self._json({"error": "project not found"}, HTTPStatus.NOT_FOUND)
            return
        self._static(parsed.path)

    def do_POST(self) -> None:  # noqa: N802 - stdlib API
        if self.path != "/api/analyze":
            self._json({"error": "not found"}, HTTPStatus.NOT_FOUND)
            return
        try:
            length = int(self.headers.get("Content-Length", "0"))
            if length > 5_000_000:
                raise ValueError("request too large")
            payload = json.loads(self.rfile.read(length) or b"{}")
            transcript = str(payload.get("transcript", ""))
            target_duration = int(payload.get("targetDuration", 45))
            segments = parse_transcript(transcript)
            clips = rank_clips(segments, target_duration=target_duration)
            project = create_project(str(payload.get("name", "New clip project")), transcript, clips)
            self._json(project.__dict__, HTTPStatus.CREATED)
        except (ValueError, json.JSONDecodeError) as exc:
            self._json({"error": str(exc)}, HTTPStatus.BAD_REQUEST)

    def log_message(self, format: str, *args: object) -> None:
        return

    def _static(self, path: str) -> None:
        relative = "index.html" if path in {"/", ""} else path.lstrip("/")
        target = (WEB_ROOT / relative).resolve()
        if WEB_ROOT not in target.parents and target != WEB_ROOT:
            self.send_error(HTTPStatus.FORBIDDEN)
            return
        if not target.exists() or target.is_dir():
            self.send_error(HTTPStatus.NOT_FOUND)
            return
        content_type = "text/html" if target.suffix == ".html" else "text/css" if target.suffix == ".css" else "application/javascript"
        body = target.read_bytes()
        self.send_response(HTTPStatus.OK)
        self.send_header("Content-Type", f"{content_type}; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def _json(self, body: object, status: HTTPStatus = HTTPStatus.OK) -> None:
        data = json.dumps(body, ensure_ascii=False).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(data)))
        self.end_headers()
        self.wfile.write(data)


def run(host: str = "127.0.0.1", port: int = 8000) -> None:
    ThreadingHTTPServer((host, port), AppHandler).serve_forever()


if __name__ == "__main__":
    run()
