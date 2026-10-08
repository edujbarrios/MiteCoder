from __future__ import annotations

from pathlib import Path

from mitecoder.repository.workspace import Workspace
from mitecoder.retrieval.lexical import LexicalRetrieval


def test_generic_question_receives_workspace_overview(tmp_path: Path) -> None:
    (tmp_path / "README.md").write_text(
        "# Weather service\nProvides local forecasts.\n", encoding="utf-8"
    )
    (tmp_path / "service.py").write_text("def forecast():\n    return 'sunny'\n", encoding="utf-8")

    items = LexicalRetrieval(max_files=2).retrieve("What does this folder do?", Workspace(tmp_path))

    assert [item.path for item in items] == ["README.md", "service.py"]
    assert all(item.reason == "workspace_overview" for item in items)


def test_generated_and_temporary_directories_are_not_context(tmp_path: Path) -> None:
    (tmp_path / "main.py").write_text("ready = True\n", encoding="utf-8")
    for name in ("dist", "build", "runs", "benchmark-results", ".test-wheel"):
        folder = tmp_path / name
        folder.mkdir()
        (folder / "noise.py").write_text("secret_noise = True\n", encoding="utf-8")

    paths = [Workspace(tmp_path).relative(path) for path in Workspace(tmp_path).iter_files()]

    assert paths == ["main.py"]


def test_binary_files_are_not_added_to_overview(tmp_path: Path) -> None:
    (tmp_path / "README.md").write_text("Useful context\n", encoding="utf-8")
    (tmp_path / "artifact.bin").write_bytes(b"binary\x00payload")

    items = LexicalRetrieval().retrieve("summarize this folder", Workspace(tmp_path))

    assert [item.path for item in items] == ["README.md"]


def test_lexical_retrieval_supports_unicode_queries(tmp_path: Path) -> None:
    (tmp_path / "diseño.md").write_text(
        "La función calcula una predicción meteorológica.\n", encoding="utf-8"
    )

    items = LexicalRetrieval().retrieve("¿Dónde está la predicción?", Workspace(tmp_path))

    assert items[0].path == "diseño.md"
    assert items[0].reason.startswith("term_hits=2")
