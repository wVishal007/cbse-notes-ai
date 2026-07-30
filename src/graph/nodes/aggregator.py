from __future__ import annotations

import time
from concurrent.futures import ThreadPoolExecutor, as_completed

from src.graph.state import NotesState, Section
from src.models.clients.gemini import GeminiClient

MAX_WORKERS = 5

AGGREGATOR_PROMPT = """You are a research aggregator for one section of a CBSE chapter.
Given research chunks for THIS section only, your job is to:
1. Remove duplicate information within these chunks
2. Merge related content into coherent paragraphs, in plain, simple English
3. Flag any conflicting facts
4. Keep only information relevant to the CBSE NCERT syllabus for this section's topic
5. If a chunk is clearly about a DIFFERENT section (see "Other sections in this chapter"
   below), ignore it — that topic will be covered elsewhere, do not include it here.

Output the merged, deduplicated content as clean text suitable for a note-taking agent."""


def _aggregate_section(
    client: GeminiClient, section_id: str, heading: str, other_headings: list[str], combined: str
) -> tuple[str, str]:
    other_sections_note = (
        "Other sections in this chapter (do NOT cover their topics here): "
        + ", ".join(other_headings)
        if other_headings
        else ""
    )
    user_prompt = (
        f"This section: '{heading}'\n{other_sections_note}\n\n"
        f"Aggregate these research chunks for this section only:\n\n{combined[:8000]}"
    )
    result = client.invoke(AGGREGATOR_PROMPT, user_prompt)
    return section_id, result or ""


def aggregator_node(state: NotesState) -> dict:
    _pool = [
        GeminiClient("models/gemini-3.5-flash-lite"),
        GeminiClient("gemma-4-26b-a4b-it"),
        GeminiClient("gemma-4-26b-a4b-it"),
    ]

    research = state.get("research", {})
    plan: list[Section] = state.get("plan", [])
    heading_by_id = {s["id"]: s["heading"] for s in plan}

    aggregated: dict[str, str] = {}
    t0 = time.time()

    with ThreadPoolExecutor(max_workers=MAX_WORKERS) as executor:
        futures = []
        for i, (section_id, chunks) in enumerate(research.items()):
            client = _pool[i % len(_pool)]
            time.sleep(i * 0.15)
            combined = "\n\n".join(
                f"[Source: {c['source_url']}]\n{c['text']}" for c in chunks[:10]
            )
            other_headings = [h for sid, h in heading_by_id.items() if sid != section_id]
            heading = heading_by_id.get(section_id, section_id)
            futures.append(
                executor.submit(_aggregate_section, client, section_id, heading, other_headings, combined)
            )

        for future in as_completed(futures):
            section_id, result = future.result()
            aggregated[section_id] = result

    elapsed = time.time() - t0
    return {"aggregated_research": aggregated, "timing": {"aggregator": elapsed}}
