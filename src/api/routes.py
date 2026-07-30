from __future__ import annotations

import asyncio
import json
import os
import sys
import threading
import time
import traceback
import uuid
from pathlib import Path
from typing import Literal

from fastapi import APIRouter, BackgroundTasks, HTTPException
from fastapi.responses import FileResponse, StreamingResponse
from pydantic import BaseModel, Field

from src.graph.builder import graph as notes_graph
from src.graph.state import NotesState

router = APIRouter()

_jobs: dict[str, dict] = {}
_jobs_lock = threading.Lock()


def _push_event(job_id: str, event: dict):
    with _jobs_lock:
        job = _jobs.get(job_id)
        if job:
            job["events"].append(event)


def _extract_content(node_name: str, output: dict) -> str:
    if node_name == "synthesizer":
        notes = output.get("draft_notes", {})
        parts = []
        for sid in sorted(notes.keys()):
            parts.append(notes[sid])
        return "\n\n".join(parts)
    if node_name == "formatter":
        return output.get("formatted_notes", "")
    if node_name == "pyq_agent":
        qas = output.get("pyqs", [])
        lines = []
        for i, qa in enumerate(qas, 1):
            lines.append(f"**Q{i}.** {qa.get('question', '')}")
            lines.append(f"> {qa.get('answer', '')}")
            marks = qa.get("marks", 2)
            lines.append(f"*({qa.get('question_type', 'Short')} | {marks} mark{'s' if marks > 1 else ''})*")
            lines.append("")
        return "\n".join(lines)
    if node_name == "validator":
        report = output.get("validation_report", {})
        if report.get("passed", False):
            return "Validation passed"
        feedback = report.get("feedback", "")
        missing = report.get("missing_key_terms", [])
        if missing:
            feedback += f"\nMissing terms: {', '.join(missing)}"
        return feedback or "Validation completed"
    if node_name == "planner":
        plan = output.get("plan", [])
        return "\n".join(f"- {s['heading']}" for s in plan)
    return ""


OUTPUT_DIR = Path(__file__).resolve().parent.parent.parent / "output"


class GenerateRequest(BaseModel):
    student_class: str = Field(..., description="e.g. '10'")
    subject: str = Field(..., description="e.g. 'Science'")
    chapter: str = Field(..., description="e.g. 'Chemical Reactions and Equations'")
    medium: Literal["english", "hindi"] = "english"


class GenerateResponse(BaseModel):
    job_id: str
    status: str


class JobStatus(BaseModel):
    job_id: str
    status: str
    pdf_path: str | None = None
    error: str | None = None
    timing: dict[str, float] | None = None
    needs_review: bool = False


def _run_generation(job_id: str, request: GenerateRequest) -> None:
    try:
        initial_state: NotesState = {
            "student_class": request.student_class,
            "subject": request.subject,
            "chapter": request.chapter,
            "medium": request.medium,
            "plan": [],
            "research": {},
            "draft_notes": {},
            "formatted_notes": "",
            "pyqs": [],
            "retry_count": 0,
            "max_retries": 2,
            "needs_review": False,
            "validation_report": None,
            "pdf_path": None,
            "errors": [],
            "timing": {},
        }

        config = {"configurable": {"thread_id": job_id}}
        accumulated = dict(initial_state)

        for step in notes_graph.stream(initial_state, config):
            for node_name, output in step.items():
                t_node = time.time()
                for k, v in output.items():
                    accumulated[k] = v

                elapsed = time.time() - t_node
                status = "OK"
                content = _extract_content(node_name, output)
                print(f"[NODE] {node_name} -> {status} ({elapsed:.2f}s)", file=sys.stderr)

                _push_event(job_id, {
                    "type": "node_complete",
                    "node": node_name,
                    "content": content,
                    "timestamp": t_node,
                })

        pdf_path = accumulated.get("pdf_path")
        timing = accumulated.get("timing", {})
        needs_review = accumulated.get("needs_review", False)

        _push_event(job_id, {
            "type": "complete",
            "pdf_path": str(pdf_path) if pdf_path else None,
            "timing": timing,
            "needs_review": needs_review,
            "timestamp": time.time(),
        })

        with _jobs_lock:
            _jobs[job_id].update({
                "status": "completed",
                "pdf_path": str(pdf_path) if pdf_path else None,
                "timing": timing,
                "error": None,
                "needs_review": needs_review,
                "events": _jobs[job_id].get("events", []),
            })
    except Exception as e:
        print(f"[ERROR] Job {job_id} failed:", file=sys.stderr)
        traceback.print_exc()
        _push_event(job_id, {
            "type": "error",
            "message": str(e),
            "timestamp": time.time(),
        })
        with _jobs_lock:
            job = _jobs.get(job_id)
            if job:
                job.update({"status": "failed", "error": str(e)})


@router.post("/generate-notes", response_model=GenerateResponse)
async def generate_notes(request: GenerateRequest, background_tasks: BackgroundTasks):
    job_id = str(uuid.uuid4())
    _jobs[job_id] = {
        "status": "processing",
        "pdf_path": None,
        "timing": None,
        "error": None,
        "needs_review": False,
        "events": [],
    }
    background_tasks.add_task(_run_generation, job_id, request)
    return GenerateResponse(job_id=job_id, status="processing")


@router.get("/status/{job_id}", response_model=JobStatus)
async def get_status(job_id: str):
    with _jobs_lock:
        job = _jobs.get(job_id)
    if job is None:
        return JobStatus(job_id=job_id, status="not_found")
    return JobStatus(job_id=job_id, **{k: v for k, v in job.items() if k != "events"})


@router.get("/stream/{job_id}")
async def stream_events(job_id: str):
    async def event_generator():
        last_index = 0
        while True:
            with _jobs_lock:
                job = _jobs.get(job_id)
                if job is None:
                    yield "event: error\ndata: {\"message\":\"job not found\"}\n\n"
                    return
                events = job.get("events", [])

            while last_index < len(events):
                event = events[last_index]
                last_index += 1
                yield f"data: {json.dumps(event)}\n\n"
                if event["type"] in ("complete", "error"):
                    return

            await asyncio.sleep(0.1)

    return StreamingResponse(event_generator(), media_type="text/event-stream")


@router.get("/download/{job_id}")
async def download_pdf(job_id: str):
    with _jobs_lock:
        job = _jobs.get(job_id)
    if job is None:
        raise HTTPException(status_code=404, detail="Job not found")
    if job["status"] != "completed":
        raise HTTPException(status_code=400, detail="Job not yet completed")
    pdf_path = job.get("pdf_path")
    if not pdf_path or not os.path.exists(pdf_path):
        raise HTTPException(status_code=404, detail="PDF file not found")
    filename = Path(pdf_path).name
    return FileResponse(pdf_path, media_type="application/pdf", filename=filename)
