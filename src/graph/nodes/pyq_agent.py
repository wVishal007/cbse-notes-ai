from __future__ import annotations

import json
import time

from src.graph.state import NotesState, QA
from src.models.clients.gemini import GeminiClient
from src.models.model_router import get_model_for_node

PYQ_SYSTEM_PROMPT = """You are a CBSE exam question expert. Generate practice questions that follow the CBSE
previous-year question paper pattern but are original (not exact copies).

Output ONLY valid JSON array:
[
  {{
    "question": "What is ...?",
    "answer": "The answer ...",
    "marks": 2,
    "section_id": "sec-1",
    "question_type": "Short"
  }}
]

Question types: "MCQ" (1 mark), "Short" (2-3 marks), "Long" (5 marks), "Case-based" (4 marks)
Generate a mix: 2 MCQs, 2 Short, 1 Long per chapter."""


def pyq_agent_node(state: NotesState) -> dict:
    provider, model = get_model_for_node("pyq_agent")
    client = GeminiClient(model=model)

    draft_notes = state.get("draft_notes", {})
    all_notes = "\n\n".join(draft_notes.values())
    plan = state.get("plan", [])

    sections_text = "\n".join(f"- {s['heading']}: {', '.join(s.get('key_concepts', []))}" for s in plan)

    t0 = time.time()
    user_prompt = (
        f"Class: {state['student_class']}\n"
        f"Subject: {state['subject']}\n"
        f"Chapter: {state['chapter']}\n"
        f"Medium: {state['medium']}\n\n"
        f"Sections:\n{sections_text}\n\n"
        f"Chapter content:\n{all_notes[:6000]}\n\n"
        f"Generate 5 CBSE-pattern practice questions (2 MCQs, 2 Short, 1 Long) with answers."
    )

    raw = client.invoke(PYQ_SYSTEM_PROMPT, user_prompt)
    elapsed = time.time() - t0

    pyqs: list[QA] = []
    if raw:
        try:
            cleaned = raw.strip()
            if cleaned.startswith("```"):
                cleaned = cleaned.split("\n", 1)[1].rsplit("\n", 1)[0]
            pyqs = json.loads(cleaned)
        except (json.JSONDecodeError, KeyError):
            pass

    return {"pyqs": pyqs, "timing": {"pyq_agent": elapsed}}
