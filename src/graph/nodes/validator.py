from __future__ import annotations

import json
import time

from src.graph.state import NotesState, ValidationResult
from src.models.clients.nvidia_nim import NvidiaNIMClient
from src.models.model_router import get_model_for_node

VALIDATOR_PROMPT = """You are a CBSE NCERT syllabus validator. Check the following notes for:
1. **Missing key terms** — important NCERT terms from the chapter that are not covered
2. **Hallucinated claims** — facts not supported by NCERT curriculum for this class/subject
3. **Scope violations** — content outside the CBSE syllabus for this class/subject

Output ONLY valid JSON:
{{
  "passed": true,
  "missing_key_terms": [],
  "hallucinated_claims": [],
  "scope_violations": [],
  "feedback": "Brief feedback on what to improve"
}}

When NOT passed, feedback should be specific: mention exactly which concepts need rewriting and why."""


def validator_node(state: NotesState) -> dict:
    provider, model = get_model_for_node("validator")
    client = NvidiaNIMClient(model=model)

    draft_notes = state.get("draft_notes", {})
    all_notes = "\n\n".join(draft_notes.values())
    plan = state.get("plan", [])

    all_key_concepts = set()
    for section in plan:
        all_key_concepts.update(section.get("key_concepts", []))

    t0 = time.time()
    user_prompt = (
        f"Class: {state['student_class']}\n"
        f"Subject: {state['subject']}\n"
        f"Chapter: {state['chapter']}\n"
        f"Medium: {state['medium']}\n\n"
        f"Key concepts that MUST be covered: {', '.join(all_key_concepts)}\n\n"
        f"Notes to validate:\n{all_notes[:8000]}"
    )

    raw = client.invoke(VALIDATOR_PROMPT, user_prompt)
    elapsed = time.time() - t0

    validation: ValidationResult = {"passed": False, "missing_key_terms": [], "hallucinated_claims": [], "scope_violations": [], "feedback": "Validation parsing failed"}
    if raw:
        try:
            cleaned = raw.strip()
            if cleaned.startswith("```"):
                cleaned = cleaned.split("\n", 1)[1].rsplit("\n", 1)[0]
            validation = json.loads(cleaned)
        except (json.JSONDecodeError, KeyError):
            pass

    needs_review = not validation.get("passed", False) and state.get("retry_count", 0) >= state.get("max_retries", 2)
    return {
        "validation_report": validation,
        "needs_review": needs_review,
        "timing": {"validator": elapsed},
    }
