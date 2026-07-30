from __future__ import annotations

import re
import time

from src.graph.state import NotesState
from src.tools.mermaid import render_mermaid

_SPECIAL_CHARS = re.compile(r'[\(\)\[\]\{\}\#"\/:@;]')


def _qq(text: str) -> str:
    if _SPECIAL_CHARS.search(text):
        escaped = text.replace('"', '\\"')
        return f'"{escaped}"'
    return text


def _build_mindmap_definition(state: NotesState) -> str:
    chapter = state["chapter"]
    plan = state.get("plan", [])

    lines = ["mindmap", f"  root(({_qq(chapter)}))"]
    for section in plan:
        heading = _qq(section["heading"])
        level = section.get("level", 1)
        indent = "  " * (level + 1)
        lines.append(f"{indent}{heading}")
        for sub in section.get("subheadings", []):
            lines.append(f"{indent}  {_qq(sub)}")
    return "\n".join(lines)


def mindmap_generator(state: NotesState) -> dict:
    t0 = time.time()

    definition = _build_mindmap_definition(state)
    svg = render_mermaid(definition)

    elapsed = time.time() - t0
    return {
        "mindmap_svg": svg,
        "timing": {"mindmap_generator": elapsed},
    }
