from __future__ import annotations

import json
import logging
import re
import time

from src.graph.state import NotesState, QA
from src.models.model_router import create_client, get_model_for_node

logger = logging.getLogger(__name__)

PYQ_SYSTEM_PROMPT = """You are a CBSE exam question expert. Generate practice questions that follow the CBSE
previous-year question paper pattern but are original (not exact copies).

Output ONLY valid JSON array (no markdown fences, no extra text):
[
  {{
    "question": "What is ...?",
    "answer": "- Point one\\n- Point two\\n- Point three",
    "marks": 2,
    "section_id": "sec-1",
    "question_type": "Short"
  }}
]

Format answers as bullet points using "- " at the start of each point.
Question types: "MCQ" (1 mark), "Short" (2-3 marks), "Long" (5 marks), "Case-based" (4 marks)
Generate 8 questions per chapter: 2 MCQs, 3 Short, 2 Long, 1 Case-based."""


def _parse_json(text: str) -> list[dict] | None:
    clean = text.strip()
    if clean.startswith("```"):
        clean = clean.split("\n", 1)[1].rsplit("\n", 1)[0].strip()
    try:
        parsed = json.loads(clean)
        if isinstance(parsed, list):
            return parsed
    except json.JSONDecodeError:
        pass
    m = re.search(r"```(?:json)?\s*(\[[\s\S]*?\])\s*```", text)
    if m:
        try:
            parsed = json.loads(m.group(1))
            if isinstance(parsed, list):
                return parsed
        except json.JSONDecodeError:
            pass
    return None


def _parse_fallback(text: str) -> list[QA]:
    qas: list[QA] = []
    blocks = re.split(r"\*{0,2}Q\d+[\s.\):]+", text)
    if len(blocks) < 2:
        blocks = re.split(r"(?:^|\n)\d+[\s.\)]+", text)
    for block in blocks[1:]:
        if not block.strip():
            continue
        lines = block.strip().split("\n")
        question = lines[0].strip()
        answer_lines: list[str] = []
        for line in lines[1:]:
            stripped = line.strip()
            if re.match(r"\*{0,2}(?:Answer|Ans)[\s:.]*\*{0,2}", stripped, re.IGNORECASE):
                answer_text = re.sub(r"\*{0,2}(?:Answer|Ans)[\s:.]*\*{0,2}\s*", "", stripped, flags=re.IGNORECASE)
                if answer_text:
                    answer_lines.append(answer_text)
            elif answer_lines or stripped:
                answer_lines.append(stripped)
        answer = " ".join(answer_lines).strip()
        marks = 2
        marks_m = re.search(r"(\d+)\s*mark", block, re.IGNORECASE)
        if marks_m:
            marks = int(marks_m.group(1))
        q_type = "Short"
        if "MCQ" in block or "Objective" in block or marks == 1:
            q_type = "MCQ"
        elif marks >= 5:
            q_type = "Long"
        if question and answer:
            qas.append(QA(question=question, answer=answer, marks=marks, section_id="", question_type=q_type))
    return qas


def pyq_agent_node(state: NotesState) -> dict:
    _, _ = get_model_for_node("pyq_agent")
    client = create_client("pyq_agent")

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
        f"Generate 8 CBSE-pattern practice questions (2 MCQs, 3 Short, 2 Long, 1 Case-based) with bullet-point answers."
    )

    raw = client.invoke(PYQ_SYSTEM_PROMPT, user_prompt)
    elapsed = time.time() - t0

    pyqs: list[QA] = []
    if raw:
        parsed = _parse_json(raw)
        if parsed:
            pyqs = parsed
        else:
            fallback = _parse_fallback(raw)
            if fallback:
                logger.info("PYQ agent: JSON parse failed, regex fallback extracted %d QAs", len(fallback))
                pyqs = fallback
            else:
                logger.warning("PYQ agent: all parsing methods failed for response (%.200s)", raw)

    return {"pyqs": pyqs, "timing": {"pyq_agent": elapsed}}
