from __future__ import annotations

from typing import Literal, Optional

from pydantic import BaseModel, Field


class GenerateNotesRequest(BaseModel):
    student_class: str = Field(..., description="Class number (1-12)")
    subject: str = Field(..., description="Subject name (e.g. Science, Maths)")
    chapter: str = Field(..., description="Chapter name")
    medium: Literal["english", "hindi"] = "english"


class GenerateNotesResponse(BaseModel):
    job_id: str
    status: str
    message: str


class JobStatusResponse(BaseModel):
    job_id: str
    status: str
    pdf_path: Optional[str] = None
    error: Optional[str] = None
    timing: Optional[dict] = None
