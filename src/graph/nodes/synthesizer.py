from __future__ import annotations

import time

from src.graph.state import NotesState
from src.models.clients.mistral import MistralClient
from src.models.model_router import get_model_for_node

SYNTHESIZER_PROMPT = """You are a CBSE NCERT notes writer. Write clear, accurate study notes for students.

Rules:
- Write in {medium}
- Rewrite concepts in your own words — do NOT copy paragraphs verbatim from source
- Cover all key concepts listed
- Use simple language appropriate for Class {student_class}
- Include definitions, explanations, and examples where relevant
- Use proper section structure with headings
- Bold key terms with **double asterisks**

Format each section as:
## Section Heading
**Key Term:** explanation

Additional context here.

Additional instructions from validator: {validator_feedback}
"""


def synthesizer_node(state: NotesState) -> dict:
    provider, model = get_model_for_node("synthesizer")
    client = MistralClient(model=model)

    plan = state.get("plan", [])
    research = state.get("research", {})
    retry_count = state.get("retry_count", 0)
    validation_report = state.get("validation_report")
    validator_feedback = ""
    if validation_report and not validation_report.get("passed", True):
        validator_feedback = validation_report.get("feedback", "")

    draft_notes: dict[str, str] = {}
    t0 = time.time()

    for section in plan:
        section_id = section["id"]
        section_research = research.get(section_id, "")
        if isinstance(section_research, list):
            research_text = "\n\n".join(
                c["text"] for c in section_research[:5]
            )
        else:
            research_text = str(section_research)

        heading_level = section["level"]
        heading_prefix = "#" * heading_level

        system_prompt = SYNTHESIZER_PROMPT.format(
            medium=state["medium"],
            student_class=state["student_class"],
            validator_feedback=validator_feedback,
        )

        user_prompt = (
            f"Section: {section['heading']}\n\n"
            f"Key concepts to cover: {', '.join(section.get('key_concepts', []))}\n\n"
            f"Research material:\n{research_text[:5000]}\n\n"
            f"Write the notes for this section using {heading_prefix} as the heading marker."
        )

        result = client.invoke(system_prompt, user_prompt)
        if result:
            draft_notes[section_id] = result

    elapsed = time.time() - t0
    return {
        "draft_notes": draft_notes,
        "retry_count": retry_count + 1,
        "timing": {"synthesizer": elapsed},
    }
