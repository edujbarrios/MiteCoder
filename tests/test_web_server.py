from __future__ import annotations

import threading
from http.server import ThreadingHTTPServer
from pathlib import Path
from urllib.request import urlopen

import pytest

from mitecoder.web.server import WebApplication, make_handler


def application(tmp_path: Path) -> WebApplication:
    repository = tmp_path / "repo"
    repository.mkdir()
    (repository / "main.py").write_text("value = 1\n", encoding="utf-8")
    config = tmp_path / "config.yaml"
    config.write_text("profile: test\n", encoding="utf-8")
    model = tmp_path / "model.gguf"
    model.write_bytes(b"model")
    return WebApplication(repository, config, model)


def test_lists_reads_and_writes_workspace_files(tmp_path: Path) -> None:
    app = application(tmp_path)

    assert app.tree() == [
        {"path": "main.py", "size": (tmp_path / "repo" / "main.py").stat().st_size}
    ]
    assert app.read_file("main.py") == "value = 1\n"
    app.write_file("main.py", "value = 2\n")

    assert app.read_file("main.py") == "value = 2\n"


def test_web_editor_cannot_escape_workspace(tmp_path: Path) -> None:
    app = application(tmp_path)

    with pytest.raises(Exception, match="escapes workspace"):
        app.read_file("../config.yaml")


def test_opens_another_existing_codebase(tmp_path: Path) -> None:
    app = application(tmp_path)
    other = tmp_path / "other"
    other.mkdir()
    (other / "app.py").write_text("ready = True\n", encoding="utf-8")

    project = app.open_repository(str(other))

    assert project["root"] == str(other.resolve())
    assert app.tree() == [{"path": "app.py", "size": (other / "app.py").stat().st_size}]


def test_rejects_missing_codebase(tmp_path: Path) -> None:
    app = application(tmp_path)

    with pytest.raises(ValueError, match="existing directory"):
        app.open_repository(str(tmp_path / "missing"))


def test_folder_picker_lists_only_directories(tmp_path: Path) -> None:
    app = application(tmp_path)
    folder = app.workspace.root / "package"
    folder.mkdir()

    result = app.directories()

    assert result["path"] == str(app.workspace.root)
    assert result["folders"] == [{"name": "package", "path": str(folder.resolve())}]


def test_web_server_only_binds_to_localhost(tmp_path: Path) -> None:
    from mitecoder.web.server import serve

    app = application(tmp_path)
    with pytest.raises(ValueError, match="localhost"):
        serve(app.workspace.root, app.config_path, app.model_path, host="0.0.0.0", port=0)


def test_static_responses_include_local_security_headers(tmp_path: Path) -> None:
    app = application(tmp_path)
    server = ThreadingHTTPServer(("127.0.0.1", 0), make_handler(app))
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    try:
        with urlopen(f"http://127.0.0.1:{server.server_port}/", timeout=5) as response:
            assert response.status == 200
            assert response.headers["X-Content-Type-Options"] == "nosniff"
            assert response.headers["X-Frame-Options"] == "DENY"
            assert "default-src 'self'" in response.headers["Content-Security-Policy"]
            assert response.headers["Cache-Control"] == "no-store"
            page = response.read().decode("utf-8")
            assert 'id="chat-messages"' in page
            assert 'id="chat-attach"' in page
            assert 'id="editor"' in page
        with urlopen(
            f"http://127.0.0.1:{server.server_port}/app.bundle", timeout=5
        ) as response:
            assert response.headers["Content-Type"] == "application/javascript; charset=utf-8"
    finally:
        server.shutdown()
        server.server_close()
        thread.join(timeout=5)
