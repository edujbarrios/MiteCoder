"""Dependency-free localhost web server for the offline coding agent."""

from __future__ import annotations

import json
import mimetypes
import threading
from http import HTTPStatus
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from typing import Any
from urllib.parse import parse_qs, urlparse

from mitecoder.config.loader import load_config
from mitecoder.inference.factory import create_backend
from mitecoder.repository.workspace import Workspace
from mitecoder.runtime import run_agent
from mitecoder.tools.git_diff import GitDiffTool
from mitecoder.tools.run_tests import RunTestsTool

STATIC_ROOT = Path(__file__).with_name("static")


class WebApplication:
    def __init__(self, repository: Path, config_path: Path, model_path: Path) -> None:
        self.workspace = Workspace(repository)
        self.config_path = config_path.resolve()
        self.model_path = model_path.resolve()
        self.run_lock = threading.Lock()
        self.workspace_lock = threading.RLock()

    def project(self) -> dict[str, Any]:
        config = load_config(self.config_path)
        return {
            "name": self.workspace.root.name,
            "root": str(self.workspace.root),
            "model": self.model_path.name,
            "commands": list(config.testing.commands),
            "profile": config.profile,
            "threads": config.inference.threads,
            "context_length": config.inference.context_length,
            "max_ram_mb": config.runtime.max_ram_mb,
        }

    def open_repository(self, repository: str) -> dict[str, Any]:
        if self.run_lock.locked():
            raise RuntimeError("Cannot change project while the agent is running")
        candidate = Path(repository).expanduser().resolve()
        if not candidate.is_dir():
            raise ValueError("Repository must be an existing directory")
        with self.workspace_lock:
            self.workspace = Workspace(candidate)
        return self.project()

    def directories(self, path: str | None = None) -> dict[str, Any]:
        current = Path(path).expanduser().resolve() if path else self.workspace.root
        if not current.is_dir():
            raise ValueError("Folder does not exist")
        folders: list[dict[str, str]] = []
        try:
            children = sorted(current.iterdir(), key=lambda item: item.name.lower())
        except PermissionError as exc:
            raise ValueError("Folder cannot be read") from exc
        for child in children:
            try:
                excluded = {"$RECYCLE.BIN", "System Volume Information"}
                if child.is_dir() and not child.is_symlink() and child.name not in excluded:
                    folders.append({"name": child.name, "path": str(child.resolve())})
            except (OSError, PermissionError):
                continue
        parent = current.parent if current.parent != current else None
        return {
            "path": str(current),
            "parent": str(parent) if parent else None,
            "folders": folders,
        }

    def tree(self) -> list[dict[str, Any]]:
        with self.workspace_lock:
            return [
                {"path": self.workspace.relative(path), "size": path.stat().st_size}
                for path in self.workspace.iter_files()
            ]

    def read_file(self, path: str) -> str:
        return self.workspace.read_text(path)

    def write_file(self, path: str, content: str) -> None:
        target = self.workspace.resolve(path, must_exist=True)
        if not target.is_file() or target.stat().st_size > 2_000_000:
            raise ValueError("Only existing files smaller than 2 MB can be edited")
        if len(content.encode("utf-8")) > 2_000_000:
            raise ValueError("File content exceeds 2 MB")
        target.write_text(content, encoding="utf-8")

    def run(self, task: str) -> dict[str, Any]:
        if not task.strip() or len(task) > 4000:
            raise ValueError("Task must contain between 1 and 4000 characters")
        if not self.run_lock.acquire(blocking=False):
            raise RuntimeError("The agent is already running")
        try:
            config = load_config(self.config_path)
            backend = create_backend(config.inference, self.model_path)
            result, artifact = run_agent(task.strip(), self.workspace, config, backend)
            return result.as_dict() | {"artifacts": str(artifact) if artifact else None}
        finally:
            self.run_lock.release()

    def run_command(self, index: int) -> dict[str, Any]:
        config = load_config(self.config_path)
        if not 0 <= index < len(config.testing.commands):
            raise ValueError("Configured command index is invalid")
        if not self.run_lock.acquire(blocking=False):
            raise RuntimeError("The workspace is already running a task")
        try:
            result = RunTestsTool(
                self.workspace, config.testing.commands, config.testing.timeout_seconds
            ).execute({"index": index})
            return {
                "command": config.testing.commands[index],
                "success": result.success,
                "output": result.output,
                "returncode": result.metadata.get("returncode"),
            }
        finally:
            self.run_lock.release()

    def diff(self) -> dict[str, Any]:
        result = GitDiffTool(self.workspace).execute({})
        return {"success": result.success, "diff": result.output}


def make_handler(application: WebApplication) -> type[BaseHTTPRequestHandler]:
    class Handler(BaseHTTPRequestHandler):
        server_version = "MiteCoderWeb/0.1"

        def do_GET(self) -> None:  # noqa: N802
            parsed = urlparse(self.path)
            if parsed.path == "/api/project":
                self._json(application.project())
                return
            if parsed.path == "/api/tree":
                self._json({"files": application.tree()})
                return
            if parsed.path == "/api/diff":
                self._json(application.diff())
                return
            if parsed.path == "/api/directories":
                path = parse_qs(parsed.query).get("path", [None])[0]
                try:
                    self._json(application.directories(path))
                except (OSError, ValueError) as exc:
                    self._error(HTTPStatus.BAD_REQUEST, str(exc))
                return
            if parsed.path == "/api/file":
                path = parse_qs(parsed.query).get("path", [""])[0]
                try:
                    self._json({"path": path, "content": application.read_file(path)})
                except (OSError, ValueError) as exc:
                    self._error(HTTPStatus.BAD_REQUEST, str(exc))
                return
            self._static(parsed.path)

        def do_PUT(self) -> None:  # noqa: N802
            if urlparse(self.path).path != "/api/file":
                self._error(HTTPStatus.NOT_FOUND, "Not found")
                return
            try:
                data = self._body()
                application.write_file(str(data.get("path", "")), str(data.get("content", "")))
                self._json({"saved": True})
            except (OSError, ValueError, json.JSONDecodeError) as exc:
                self._error(HTTPStatus.BAD_REQUEST, str(exc))

        def do_POST(self) -> None:  # noqa: N802
            path = urlparse(self.path).path
            if path == "/api/project":
                try:
                    data = self._body()
                    self._json(application.open_repository(str(data.get("path", ""))))
                except RuntimeError as exc:
                    self._error(HTTPStatus.CONFLICT, str(exc))
                except (OSError, ValueError, json.JSONDecodeError) as exc:
                    self._error(HTTPStatus.BAD_REQUEST, str(exc))
                return
            if path == "/api/terminal":
                try:
                    data = self._body()
                    self._json(application.run_command(int(data.get("index", -1))))
                except RuntimeError as exc:
                    self._error(HTTPStatus.CONFLICT, str(exc))
                except (OSError, TypeError, ValueError, json.JSONDecodeError) as exc:
                    self._error(HTTPStatus.BAD_REQUEST, str(exc))
                return
            if path != "/api/run":
                self._error(HTTPStatus.NOT_FOUND, "Not found")
                return
            try:
                data = self._body()
                self._json(application.run(str(data.get("task", ""))))
            except RuntimeError as exc:
                self._error(HTTPStatus.CONFLICT, str(exc))
            except (OSError, ValueError, json.JSONDecodeError) as exc:
                self._error(HTTPStatus.BAD_REQUEST, str(exc))

        def log_message(self, format: str, *args: object) -> None:
            return

        def _body(self) -> dict[str, Any]:
            length = int(self.headers.get("Content-Length", "0"))
            if length > 2_100_000:
                raise ValueError("Request body is too large")
            value = json.loads(self.rfile.read(length).decode("utf-8"))
            if not isinstance(value, dict):
                raise ValueError("JSON body must be an object")
            return value

        def _json(self, value: Any, status: HTTPStatus = HTTPStatus.OK) -> None:
            payload = json.dumps(value, ensure_ascii=False).encode("utf-8")
            self.send_response(status)
            self.send_header("Content-Type", "application/json; charset=utf-8")
            self.send_header("Content-Length", str(len(payload)))
            self.send_header("Cache-Control", "no-store")
            self._security_headers()
            self.end_headers()
            self.wfile.write(payload)

        def _error(self, status: HTTPStatus, message: str) -> None:
            self._json({"error": message}, status)

        def _static(self, request_path: str) -> None:
            relative = "index.html" if request_path in {"", "/"} else request_path.lstrip("/")
            candidate = (STATIC_ROOT / relative).resolve()
            try:
                candidate.relative_to(STATIC_ROOT.resolve())
            except ValueError:
                self._error(HTTPStatus.NOT_FOUND, "Not found")
                return
            if not candidate.is_file():
                self._error(HTTPStatus.NOT_FOUND, "Not found")
                return
            payload = candidate.read_bytes()
            content_type = (
                "application/javascript"
                if candidate.suffix == ".bundle"
                else mimetypes.guess_type(candidate.name)[0] or "application/octet-stream"
            )
            self.send_response(HTTPStatus.OK)
            self.send_header("Content-Type", f"{content_type}; charset=utf-8")
            self.send_header("Content-Length", str(len(payload)))
            self.send_header("Cache-Control", "no-store")
            self._security_headers()
            self.end_headers()
            self.wfile.write(payload)

        def _security_headers(self) -> None:
            self.send_header("Content-Security-Policy", "default-src 'self'; img-src 'self' data:")
            self.send_header("Referrer-Policy", "no-referrer")
            self.send_header("X-Content-Type-Options", "nosniff")
            self.send_header("X-Frame-Options", "DENY")

    return Handler


def serve(
    repository: Path,
    config_path: Path,
    model_path: Path,
    host: str = "127.0.0.1",
    port: int = 8765,
) -> None:
    if host not in {"127.0.0.1", "localhost", "::1"}:
        raise ValueError("The offline web interface can only bind to localhost")
    application = WebApplication(repository, config_path, model_path)
    server = ThreadingHTTPServer((host, port), make_handler(application))
    print("MiteCoder web workspace")
    print(f"Repository: {application.workspace.root}")
    print(f"Model: {application.model_path}")
    print(f"Open: http://{host}:{port}")
    print("Press Ctrl+C to stop.")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        server.server_close()
