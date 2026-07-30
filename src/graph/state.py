from __future__ import annotations

from typing import Literal, Optional, TypedDict


class Section(TypedDict):
    id: str
    heading: str
    level: int
    parent_id: Optional[str]
    subheadings: list[str]
    key_concepts: list[str]


class SourceChunk(TypedDict):
    text: str
    source_url: str
    domain: str
    relevance_score: float


class QA(TypedDict):
    question: str
    answer: str
    marks: int
    section_id: str
    question_type: str


class ValidationResult(TypedDict):
    passed: bool
    missing_key_terms: list[str]
    hallucinated_claims: list[str]
    scope_violations: list[str]
    feedback: str


class NotesState(TypedDict):
    student_class: str
    subject: str
    chapter: str
    medium: Literal["english", "hindi"]

    plan: list[Section]
    research: dict[str, str]
    aggregated_research: dict[str, str]
    draft_notes: dict[str, str]
    formatted_notes: str
    pyqs: list[QA]

    retry_count: int
    max_retries: int
    needs_review: bool

    validation_report: Optional[ValidationResult]

    pdf_path: Optional[str]

    errors: list[str]
    timing: dict[str, float]
