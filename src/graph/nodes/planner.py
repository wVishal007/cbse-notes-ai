from __future__ import annotations

import json
import time
from typing import Optional

from src.graph.state import NotesState, Section
from src.models.model_router import create_client, get_model_for_node

PLANNER_SYSTEM_PROMPT = """You are a CBSE curriculum expert. Given a class, subject, chapter, and medium,
produce a detailed section outline aligned with the NCERT textbook structure.

Output ONLY valid JSON in this exact format:
[
  {{
    "id": "sec-1",
    "heading": "Section Heading",
    "level": 1,
    "parent_id": null,
    "subheadings": ["Subheading 1", "Subheading 2"],
    "key_concepts": ["Concept 1", "Concept 2"]
  }}
]

Rules:
- level 1 = main section (16pt in output)
- level 2 = subsection (14pt)
- level 3 = sub-subsection (12pt)
- Cover ALL key topics from the NCERT chapter
- Include an introduction section and a summary section
- Each section id must be unique and sequential
- key_concepts should list 2-5 key terms/definitions to cover
- CRITICAL: every key_concept must appear in EXACTLY ONE section. Do not assign the same
  event, law, person, treaty, or term to more than one section's key_concepts list, even if
  it is relevant to both — pick the single best-fitting section for it. Downstream sections
  are written independently, so overlap here directly causes duplicate content in the notes.
- Order sections chronologically/logically so later sections can briefly reference earlier
  ones by name instead of re-explaining them.
- Respond with ONLY the JSON array, no other text
"""


def planner_node(state: NotesState) -> dict:
    provider, model = get_model_for_node("planner")
    client = create_client("planner")

    user_prompt = (
        f"Class: {state['student_class']}\n"
        f"Subject: {state['subject']}\n"
        f"Chapter: {state['chapter']}\n"
        f"Medium: {state['medium']}\n\n"
        f"Create a detailed NCERT-aligned section outline for this chapter."
    )

    t0 = time.time()
    raw = client.invoke(PLANNER_SYSTEM_PROMPT, user_prompt)
    elapsed = time.time() - t0

    sections: list[Section] = []
    if raw:
        try:
            cleaned = raw.strip()
            if cleaned.startswith("```"):
                cleaned = cleaned.split("\n", 1)[1].rsplit("\n", 1)[0]
            sections = json.loads(cleaned)
        except (json.JSONDecodeError, KeyError):
            sections = _fallback_plan(state)

    sections = _dedupe_key_concepts(sections or _fallback_plan(state))

    return {
        "plan": sections,
        "timing": {"planner": elapsed},
    }


def _dedupe_key_concepts(sections: list[Section]) -> list[Section]:
    seen: set[str] = set()
    for section in sections:
        unique_concepts = []
        for concept in section.get("key_concepts", []):
            key = concept.strip().lower()
            if key and key not in seen:
                seen.add(key)
                unique_concepts.append(concept)
        section["key_concepts"] = unique_concepts
    return sections


def _fallback_plan(state: NotesState) -> list[Section]:
    return [
        Section(
            id="sec-1",
            heading=f"Introduction to {state['chapter']}",
            level=1,
            parent_id=None,
            subheadings=["Overview", "Key Questions"],
            key_concepts=[f"{state['subject']} basics", "Chapter objectives"],
        ),
        Section(
            id="sec-2",
            heading="Main Content",
            level=1,
            parent_id=None,
            subheadings=["Core Concepts", "Important Definitions"],
            key_concepts=["Core topics"],
        ),
        Section(
            id="sec-3",
            heading="Summary",
            level=1,
            parent_id=None,
            subheadings=["Key Takeaways"],
            key_concepts=["Revision points"],
        ),
    ]
