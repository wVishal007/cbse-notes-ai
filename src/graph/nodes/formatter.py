from __future__ import annotations

import time

from src.graph.state import NotesState
from src.models.model_router import create_client, get_model_for_node

FORMATTER_PROMPT = """You are the final editor for a CBSE study notes document. The sections below were
written independently by different passes, so the same topic may have been explained more
than once in different sections. Format the notes into structured Markdown AND fix that.

Formatting rules:
- # Main Title → 16pt (use # for chapter title only)
- ## Section Heading → 14pt
- ### Subsection Heading → 12pt
- **Bold** all key terms and definitions
- Use bullet lists (-) for enumerations
- Use numbered lists (1.) for sequences/steps
- Use tables for comparisons where appropriate
- Add horizontal rules (---) between major sections

Deduplication rules (do this pass carefully — check the WHOLE document, not just adjacent
sections):
- If the same event, law, person, term, or fact is explained in more than one section, keep
  the fullest, clearest explanation in the section where it fits best, and in every other
  place replace the repeated explanation with a short one-line cross-reference instead
  (e.g. "See **Zollverein** under 'Economic Nationalism' above.")
- Do NOT delete a section's unique content — only remove genuine repeats of the same fact.
- Do not invent, add, or change any fact that wasn't already present in the source notes.

Plain-language pass:
- While reformatting, simplify any sentence longer than ~25 words or any unnecessarily
  dense/academic phrasing into shorter, clearer sentences — without losing meaning.

Output the FULL formatted document."""


def formatter_node(state: NotesState) -> dict:
    _, _ = get_model_for_node("formatter")
    client = create_client("formatter")

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
