"""Build the dependency-free web assets consumed by the Python package."""

from __future__ import annotations

from pathlib import Path
import shutil


ROOT = Path(__file__).resolve().parents[1]
PUBLIC = ROOT / "frontend" / "public"
STATIC = ROOT / "src" / "mitecoder" / "web" / "static"


def main() -> None:
    STATIC.mkdir(parents=True, exist_ok=True)
    for name in ("index.html", "styles.css"):
        shutil.copyfile(PUBLIC / name, STATIC / name)


if __name__ == "__main__":
    main()
