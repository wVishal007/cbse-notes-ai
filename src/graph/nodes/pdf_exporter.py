from __future__ import annotations

import time
from datetime import datetime
from pathlib import Path

from src.graph.state import NotesState
from src.tools.pdf import export_pdf, render_html_with_mindmap

OUTPUT_DIR = Path(__file__).resolve().parent.parent.parent.parent / "output"


def _format_pyqs(pyqs: list[dict]) -> str:
    if not pyqs:
        return "<p>No practice questions generated.</p>"

    parts = ["<h2>Practice Questions (CBSE Pattern)</h2>"]
    for i, qa in enumerate(pyqs, 1):
        q_type = qa.get("question_type", "Short")
        marks = qa.get("marks", 2)
        badge = f"<span class='badge badge-{q_type.lower()}'>{q_type} | {marks} mark{'s' if marks > 1 else ''}</span>"
        answer = qa.get("answer", "")
        points = [ln.strip().lstrip("- *") for ln in answer.split("\n") if ln.strip().startswith(("- ", "* "))]
        if points:
            answer_html = "<ul>" + "".join(f"<li>{p}</li>" for p in points) + "</ul>"
        else:
            answer_html = f"<p class='answer'>{answer}</p>"
        parts.append(
            f"<div class='qa-card'>"
            f"<p class='q-number'>Q{i}.</p>"
            f"{badge}"
            f"<p class='question'>{qa.get('question', '')}</p>"
            f"<div class='answer-block'>"
            f"<p class='answer-label'>Answer</p>"
            f"{answer_html}"
            f"</div></div>"
        )
    return "\n".join(parts)


def pdf_exporter_node(state: NotesState) -> dict:
    t0 = time.time()

    output_filename = (
        f"Class{state['student_class']}_{state['subject']}_{state['chapter']}"
        f"_{state['medium']}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.pdf"
    )
    output_path = str(OUTPUT_DIR / output_filename)
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    formatted = state.get("formatted_notes", "")
    pyqs = state.get("pyqs", [])
    mindmap_svg = state.get("mindmap_svg", "")

    pyqs_html = _format_pyqs(pyqs)

    template_vars = {
        "title": f"{state['subject']} — Class {state['student_class']}",
        "subtitle": f"Chapter: {state['chapter']}",
        "medium": state["medium"].title(),
    }

    html_content = render_html_with_mindmap(
        formatted, pyqs_html, mindmap_svg, template_vars
    )
    export_pdf(html_content, output_path)

    elapsed = time.time() - t0
    return {
        "pdf_path": output_path,
        "timing": {"pdf_exporter": elapsed},
    }
