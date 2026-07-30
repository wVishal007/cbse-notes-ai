from __future__ import annotations

import time

from src.cache.research_cache import get_cached, set_cached
from src.graph.state import NotesState, Section, SourceChunk
from src.tools.scraper import extract_from_pdf, extract_text
from src.tools.search import search_subtopic, to_source_chunks


def _build_queries(section: Section, state: NotesState) -> list[str]:
    base = (
        f"{state['subject']} {state['chapter']} "
        f"class {state['student_class']} NCERT {state['medium']}"
    )
    queries = [f"{section['heading']} {base}"]
    for sub in section.get("subheadings", []):
        queries.append(f"{sub} {base}")
    for concept in section.get("key_concepts", []):
        queries.append(f"{concept} {base}")
    return queries


def research_node(state: NotesState) -> dict:
    t0 = time.time()

    cached = get_cached(
        state["student_class"], state["subject"], state["chapter"], state["medium"]
    )
    if cached and "research" in cached:
        return {
            "research": cached["research"],
            "timing": {"research_cache_hit": time.time() - t0},
        }

    plan: list[Section] = state.get("plan", [])
    all_research: dict[str, list[SourceChunk]] = {}

    for section in plan:
        section_id = section["id"]
        queries = _build_queries(section, state)
        section_chunks: list[SourceChunk] = []

        for query in queries:
            results = search_subtopic(query, max_results=3, min_priority=1)
            chunks = to_source_chunks(results, section_id)
            section_chunks.extend(chunks)

            for r in results:
                url = r.get("link", "")
                if url.endswith(".pdf"):
                    text = extract_from_pdf(url)
                else:
                    text = extract_text(url)
                if text:
                    section_chunks.append(
                        SourceChunk(
                            text=text[:3000],
                            source_url=url,
                            domain=str(r.get("domain_priority", 0)),
                            relevance_score=0.8,
                        )
                    )

        all_research[section_id] = section_chunks

    set_cached(
        state["student_class"],
        state["subject"],
        state["chapter"],
        state["medium"],
        {"research": all_research, "plan": plan},
    )

    elapsed = time.time() - t0
    return {"research": all_research, "timing": {"research": elapsed}}
