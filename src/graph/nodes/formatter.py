from __future__ import annotations

import time

from src.graph.state import NotesState
from src.models.clients.gemini import GeminiClient
from src.models.model_router import get_model_for_node

FORMATTER_PROMPT = """You are a document formatter for CBSE study notes. Format the following raw notes into
structured Markdown with proper hierarchy.

Rules:
- # Main Title → 16pt (use # for chapter title only)
- ## Section Heading → 14pt
- ### Subsection Heading → 12pt
- **Bold** all key terms and definitions
- Use bullet lists (-) for enumerations
- Use numbered lists (1.) for sequences/steps
- Use tables for comparisons where appropriate
- Add horizontal rules (---) between major sections
- Keep the content exactly as provided — only change formatting and structure

Output the FULL formatted document."""


def formatter_node(state: NotesState) -> dict:
    provider, model = get_model_for_node("formatter")
    client = GeminiClient(model=model)

    draft_notes = state.get("draft_notes", {})
    plan = state.get("plan", [])
    raw_text_parts = []

    raw_text_parts.append(f"# {state['subject']} — Class {state['student_class']}: {state['chapter']}\n")

    for section in plan:
        section_id = section["id"]
        content = draft_notes.get(section_id, "")
        if content:
            raw_text_parts.append(content)

    raw_text = "\n\n---\n\n".join(raw_text_parts)

    t0 = time.time()
    user_prompt = (
        f"Format these CBSE study notes for Class {state['student_class']} {state['subject']} "
        f"Chapter '{state['chapter']}' in {state['medium']}:\n\n{raw_text}"
    )
    result = client.invoke(FORMATTER_PROMPT, user_prompt)
    elapsed = time.time() - t0

    return {
        "formatted_notes": result or raw_text,
        "timing": {"formatter": elapsed},
    }
