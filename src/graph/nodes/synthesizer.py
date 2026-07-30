from __future__ import annotations

import time
from concurrent.futures import ThreadPoolExecutor, as_completed

from src.graph.state import NotesState, Section
from src.models.model_router import create_client, get_model_for_node

MAX_WORKERS = 5

SYNTHESIZER_PROMPT = """You are a CBSE NCERT notes writer. Write clear, accurate study notes for students.

Language rules (these matter more than sounding "academic"):
- Write in {medium}
- Use short sentences (aim for under 20 words each). One idea per sentence.
- Explain everything the way you would to a Class {student_class} student who is reading
  this topic for the first time — avoid dense, jargon-heavy phrasing.
- The FIRST time you use a technical term, define it in plain words immediately after it.
- Where useful, add a one-line everyday comparison or example to make an abstract idea concrete.
- Rewrite concepts in your own words — do NOT copy paragraphs verbatim from source
- Cover all key concepts listed below, and ONLY those — do not cover topics owned by other
  sections (listed below); if this section needs to mention one, refer to it briefly by name
  instead of re-explaining it (e.g. "as seen earlier in X" or "covered under Y").
- Use proper section structure with headings
- Bold key terms with **double asterisks**

Format each section as:
## Section Heading
**Key Term:** simple one-line explanation

Additional context in short sentences here.

Additional instructions from validator: {validator_feedback}
"""


def _synthesize_section(
    client: MistralClient,
    system_prompt: str,
    section: Section,
    research_text: str,
) -> tuple[str, str]:
    heading_level = section["level"]
    heading_prefix = "#" * heading_level
    user_prompt = (
        f"Section: {section['heading']}\n\n"
        f"Key concepts to cover: {', '.join(section.get('key_concepts', []))}\n\n"
        f"Research material:\n{research_text[:5000]}\n\n"
        f"Write the notes for this section using {heading_prefix} as the heading marker."
    )
    result = client.invoke(system_prompt, user_prompt)
    return section["id"], result or ""


def synthesizer_node(state: NotesState) -> dict:
    _, _ = get_model_for_node("synthesizer")

    plan = state.get("plan", [])
    research = state.get("research", {})
    aggregated = state.get("aggregated_research", {})

    validator = state.get("validation_report", {})
    validator_feedback = validator.get("feedback", "") if validator else ""
    if validator_feedback:
        validator_feedback = f"Previous validation requested: {validator_feedback}"

    draft_notes: dict[str, str] = {}
    t0 = time.time()

    heading_by_id = {s["id"]: s["heading"] for s in plan}
    concepts_by_id = {s["id"]: s.get("key_concepts", []) for s in plan}

    with ThreadPoolExecutor(max_workers=MAX_WORKERS) as pool:
        futures = []
        for section in plan:
            section_id = section["id"]
            agg_research = aggregated.get(section_id, "")
            if agg_research:
                research_text = str(agg_research)
            else:
                section_research = research.get(section_id, "")
                if isinstance(section_research, list):
                    research_text = "\n\n".join(c["text"] for c in section_research[:5])
                else:
                    research_text = str(section_research)

            other_topics = [
                f"{heading_by_id[sid]} ({', '.join(concepts_by_id[sid])})"
                for sid in heading_by_id
                if sid != section_id and concepts_by_id.get(sid)
            ]
            system_prompt = SYNTHESIZER_PROMPT.format(
                medium=state["medium"],
                student_class=state["student_class"],
                validator_feedback=validator_feedback,
            )
            if other_topics:
                system_prompt += "\nTopics owned by other sections: " + "; ".join(other_topics)

            client = create_client("synthesizer")
            futures.append(pool.submit(_synthesize_section, client, system_prompt, section, research_text))

        for future in as_completed(futures):
            section_id, result = future.result()
            if result:
                draft_notes[section_id] = result

    elapsed = time.time() - t0
    return {
        "draft_notes": draft_notes,
        "timing": {"synthesizer": elapsed},
    }
