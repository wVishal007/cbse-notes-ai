from __future__ import annotations

import time

from src.graph.state import NotesState
from src.models.clients.gemini import GeminiClient
from src.models.model_router import get_model_for_node

AGGREGATOR_PROMPT = """You are a research aggregator. Given research chunks for a CBSE chapter section,
your job is to:
1. Remove duplicate information
2. Merge related content into coherent paragraphs
3. Flag any conflicting facts
4. Keep only information relevant to the CBSE NCERT syllabus

Output the merged, deduplicated content as clean text suitable for a note-taking agent."""


def aggregator_node(state: NotesState) -> dict:
    provider, model = get_model_for_node("aggregator")
    client = GeminiClient(model=model)

    research = state.get("research", {})
    aggregated: dict[str, str] = {}
    t0 = time.time()

    for section_id, chunks in research.items():
        combined = "\n\n".join(
            f"[Source: {c['source_url']}]\n{c['text']}" for c in chunks[:10]
        )
        user_prompt = (
            f"Aggregate these research chunks for section '{section_id}':\n\n{combined[:8000]}"
        )
        result = client.invoke(AGGREGATOR_PROMPT, user_prompt)
        aggregated[section_id] = result or ""

    elapsed = time.time() - t0
    # Store aggregated text in a field for the synthesizer to consume
    return {"research": aggregated, "timing": {"aggregator": elapsed}}
