from __future__ import annotations

import json
from pathlib import Path

from mitecoder.repository.scanner import inspect_workspace
from mitecoder.repository.workspace import Workspace
from mitecoder.retrieval.lexical import LexicalRetrieval
from mitecoder.tools.file_tools import ReadFileTool, SearchCodeTool


def make_notebook(path: Path) -> None:
    path.write_text(
        json.dumps(
            {
                "cells": [
                    {
                        "cell_type": "markdown",
                        "metadata": {},
                        "source": ["# Experiment\n", "Predict customer churn."],
                    },
                    {
                        "cell_type": "code",
                        "metadata": {},
                        "source": ["learning_rate = 0.01\n", "print(learning_rate)"],
                        "outputs": [{"output_type": "stream", "text": ["0.01"]}],
                    },
                ],
                "metadata": {"private_token": "must not become context"},
                "nbformat": 4,
                "nbformat_minor": 5,
            }
        ),
        encoding="utf-8",
    )


def test_notebook_cells_are_retrieved_as_readable_context(tmp_path: Path) -> None:
    notebook = tmp_path / "experiment.ipynb"
    make_notebook(notebook)
    workspace = Workspace(tmp_path)

    items = LexicalRetrieval().retrieve("learning_rate", workspace)
    read = ReadFileTool(workspace).execute({"path": "experiment.ipynb"})
    search = SearchCodeTool(workspace).execute({"query": "customer churn"})

    assert items and "--- code cell 2 ---" in items[0].content
    assert "learning_rate = 0.01" in read.output
    assert "private_token" not in read.output
    assert "experiment.ipynb" in search.output
    assert inspect_workspace(workspace).languages == {"Jupyter Notebook": 1}
