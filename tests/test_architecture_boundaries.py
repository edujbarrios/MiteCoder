from __future__ import annotations

import ast
from pathlib import Path

ROOT = Path(__file__).parents[1]
BACKEND = ROOT / "backend" / "src" / "mitecoder"


def _import_roots(path: Path) -> set[str]:
    tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
    roots: set[str] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            roots.update(alias.name.split(".", 1)[0] for alias in node.names)
        elif isinstance(node, ast.ImportFrom) and node.module:
            roots.add(node.module.split(".", 1)[0])
    return roots


def test_repository_has_explicit_application_boundaries() -> None:
    assert (ROOT / "backend" / "src" / "mitecoder").is_dir()
    assert (ROOT / "cli" / "src" / "mitecoder_cli").is_dir()
    assert (ROOT / "frontend" / "src" / "app.ts").is_file()
    assert not (ROOT / "src").exists()
    assert not (ROOT / "app.ts").exists()


def test_backend_does_not_depend_on_cli() -> None:
    offenders = [
        path.relative_to(ROOT).as_posix()
        for path in BACKEND.rglob("*.py")
        if path.name != "__main__.py" and "mitecoder_cli" in _import_roots(path)
    ]
    assert offenders == []


def test_frontend_has_no_javascript_source_files() -> None:
    assert list((ROOT / "frontend").rglob("*.js")) == []


def test_generated_frontend_assets_are_packaged() -> None:
    static = BACKEND / "web" / "static"
    assert {path.name for path in static.iterdir()} == {"app.bundle", "index.html", "styles.css"}
