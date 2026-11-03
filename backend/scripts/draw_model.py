"""Draws the data model from the SQLAlchemy models: `uv run python scripts/draw_model.py` (needs Graphviz's `dot`)."""

from pathlib import Path

from eralchemy import render_er

from app.models import Base

OUTPUT = Path(__file__).resolve().parents[2] / "docs"

if __name__ == "__main__":
    OUTPUT.mkdir(exist_ok=True)
    for extension in ("png", "svg"):
        render_er(Base.metadata, str(OUTPUT / f"data-model.{extension}"))
        print(f"docs/data-model.{extension}")
