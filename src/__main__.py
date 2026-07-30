from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from src.graph.builder import graph
from src.graph.state import NotesState


def main():
    parser = argparse.ArgumentParser(
        description="Generate CBSE NCERT-aligned study notes"
    )
    parser.add_argument("--class", dest="student_class", required=True, help="Class (1-12)")
    parser.add_argument("--subject", required=True, help="Subject name")
    parser.add_argument("--chapter", required=True, help="Chapter name")
    parser.add_argument(
        "--medium", default="english", choices=["english", "hindi"], help="Language medium"
    )
    parser.add_argument("--open", action="store_true", help="Open PDF after generation")

    args = parser.parse_args()

    initial_state: NotesState = {
        "student_class": args.student_class,
        "subject": args.subject,
        "chapter": args.chapter,
        "medium": args.medium,
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

    print(f" Generating notes for Class {args.student_class} {args.subject} - {args.chapter} ({args.medium})")
    print()

    result = graph.invoke(
        initial_state,
        {"configurable": {"thread_id": f"cli_{args.student_class}_{args.subject}_{args.chapter}"}},
    )

    pdf_path = result.get("pdf_path")
    timing = result.get("timing", {})

    if pdf_path:
        print(f" PDF saved to: {pdf_path}")
        if args.open:
            import subprocess
            subprocess.Popen(["start", pdf_path], shell=True)
    else:
        print(" PDF generation failed.")
        errors = result.get("errors", [])
        if errors:
            print(f"Errors: {errors}")

    print()
    print("Timing breakdown:")
    for node, elapsed in timing.items():
        print(f"  {node}: {elapsed:.2f}s")

    needs_review = result.get("needs_review", False)
    if needs_review:
        print(" Note: This output needs human review (validation failed after max retries).")


if __name__ == "__main__":
    main()