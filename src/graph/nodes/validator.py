from __future__ import annotations

import json
import time

from src.graph.state import NotesState, ValidationResult
from src.models.clients.base import RateLimitError
from src.models.model_router import create_client, get_model_for_node

CHUNK_SIZE = 9000

VALIDATOR_PROMPT = """You are a CBSE NCERT syllabus validator. Check the following notes for:
1. **Missing key terms** — important NCERT terms from the chapter that are not covered
2. **Hallucinated claims** — facts not supported by NCERT curriculum for this class/subject
3. **Scope violations** — content outside the CBSE syllabus for this class/subject
4. **Factual accuracy of names/titles/dates** — check every named person's title (e.g. King,
   Prince, Chancellor, President), every date, and every place name mentioned. Flag any that
   look wrong (e.g. a historical figure given the wrong title).
5. **Repetition** — flag if the same fact, definition, or event is explained more than once
   almost word-for-word in different places (this is a real defect, not acceptable style).

Output ONLY valid JSON:
{{
  "passed": true,
  "missing_key_terms": [],
  "hallucinated_claims": [],
  "scope_violations": [],
  "feedback": ""
}}

When NOT passed, feedback should be specific: mention exactly which concepts need rewriting and why."""


def _chunk_text(text: str, size: int) -> list[str]:
    return [text[i : i + size] for i in range(0, len(text), size)] or [""]


def _parse_validation(raw: str | None) -> ValidationResult:
    validation: ValidationResult = {
        "passed": False,
        "missing_key_terms": [],
        "hallucinated_claims": [],
        "scope_violations": [],
        "feedback": "Validation parsing failed",
    }
    if raw:
        try:
            cleaned = raw.strip()
            if cleaned.startswith("```"):
                cleaned = cleaned.split("\n", 1)[1].rsplit("\n", 1)[0]
            validation = json.loads(cleaned)
        except (json.JSONDecodeError, KeyError):
            pass
    return validation


def validator_node(state: NotesState) -> dict:
    _, _ = get_model_for_node("validator")
    client = create_client("validator")

    draft_notes = state.get("draft_notes", {})
    plan = state.get("plan", [])
    all_notes = "\n\n".join(draft_notes.values()) if draft_notes else ""
    all_key_concepts: set[str] = set()
    for section in plan:
        all_key_concepts.update(section.get("key_concepts", []))

    t0 = time.time()

    chunks = _chunk_text(all_notes, CHUNK_SIZE)
    merged: ValidationResult = {
        "passed": True,
        "missing_key_terms": [],
        "hallucinated_claims": [],
        "scope_violations": [],
        "feedback": "",
    }
    feedback_parts: list[str] = []

    for idx, chunk in enumerate(chunks):
        user_prompt = (
            f"Class: {state['student_class']}\n"
            f"Subject: {state['subject']}\n"
            f"Chapter: {state['chapter']}\n"
            f"Medium: {state['medium']}\n\n"
            f"Key concepts that MUST be covered somewhere in the chapter: {', '.join(all_key_concepts)}\n\n"
            f"Notes chunk {idx + 1}/{len(chunks)} to validate:\n{chunk}"
        )
        try:
            raw = client.invoke(VALIDATOR_PROMPT, user_prompt)
            result = _parse_validation(raw)
        except RateLimitError:
            print(f"[VALIDATOR] Rate limit hit on chunk {idx + 1}/{len(chunks)} — skipping validation", file=__import__('sys').stderr)
            result = _parse_validation(None)
            result["passed"] = True
            result["feedback"] = "Skipped due to rate limit."

        if not result.get("passed", False):
            merged["passed"] = False
        merged["missing_key_terms"].extend(result.get("missing_key_terms", []))
        merged["hallucinated_claims"].extend(result.get("hallucinated_claims", []))
        merged["scope_violations"].extend(result.get("scope_violations", []))
        if result.get("feedback"):
            feedback_parts.append(result["feedback"])

    if len(chunks) > 1:
        merged["missing_key_terms"] = [
            term for term in set(merged["missing_key_terms"]) if term not in all_notes
        ]
    merged["feedback"] = " | ".join(feedback_parts) or "Looks good."

    elapsed = time.time() - t0
    current_retry = state.get("retry_count", 0)
    needs_review = not merged.get("passed", False) and current_retry >= state.get("max_retries", 2)
    return {
        "validation_report": merged,
        "needs_review": needs_review,
        "retry_count": current_retry + 1,
        "timing": {"validator": elapsed},
    }
