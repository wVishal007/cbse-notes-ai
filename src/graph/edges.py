from __future__ import annotations

from typing import Literal

from src.graph.state import NotesState


def route_after_validation(state: NotesState) -> Literal["synthesizer", "format_pyq"]:
    validation = state.get("validation_report")
    retry_count = state.get("retry_count", 0)
    max_retries = state.get("max_retries", 2)

    if (
        validation is None
        or (not validation.get("passed", False) and retry_count < max_retries)
    ):
        return "synthesizer"

    if validation and not validation.get("passed", False):
        return "format_pyq"

    return "format_pyq"

