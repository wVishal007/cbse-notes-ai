from __future__ import annotations

import time
from concurrent.futures import ThreadPoolExecutor, as_completed

from src.cache.research_cache import get_cached, set_cached
from src.graph.state import NotesState, Section, SourceChunk
from src.tools.scraper import (
    extract_from_pdf,
    extract_text,
)
from src.tools.search import search_subtopic, to_source_chunks

MAX_WORKERS = 6
MAX_QUERIES_PER_SECTION = 4


def _build_queries(section: Section, state: NotesState) -> list[str]:
    base = (
        f"{state['subject']} {state['chapter']} "
        f"class {state['student_class']} NCERT {state['medium']}"
    )
    queries = [f"{section['heading']} {base}"]
    for concept in section.get("key_concepts", [])[:3]:
        queries.append(f"{concept} {base}")
    return queries[:MAX_QUERIES_PER_SECTION]


def _run_query(query: str) -> list[dict]:
    results = search_subtopic(query, max_results=3, min_priority=1)
    enriched: list[dict] = []
    for r in results:
        url = r.get("link", "")
        try:
            text = extract_from_pdf(url) if url.endswith(".pdf") else extract_text(url)
        except Exception:
            text = ""
        enriched.append({**r, "scraped_text": text})
    return enriched


def research_node(state: NotesState) -> dict:
    t0 = time.time()

    cached = get_cached(
        state["student_class"], state["subject"], state["chapter"], state["medium"]
    )
    if cached and "research" in cached:
        return {
            "research": cached["research"],
            "images": cached.get("images", {}),
            "timing": {"research_cache_hit": time.time() - t0},
        }

    plan: list[Section] = state.get("plan", [])

    query_to_sections: dict[str, list[str]] = {}
    for section in plan:
        for query in _build_queries(section, state):
            query_to_sections.setdefault(query, []).append(section["id"])

    all_research: dict[str, list[SourceChunk]] = {sec["id"]: [] for sec in plan}

    with ThreadPoolExecutor(max_workers=MAX_WORKERS) as pool:
        future_to_query = {
            pool.submit(_run_query, query): query for query in query_to_sections
        }
        for future in as_completed(future_to_query):
            query = future_to_query[future]
            try:
                results = future.result()
            except Exception:
                results = []

            section_ids = query_to_sections[query]
            for section_id in section_ids:
                chunks = to_source_chunks(results, section_id)
                all_research[section_id].extend(chunks)
                for r in results:
                    text = r.get("scraped_text", "")
                    if text:
                        all_research[section_id].append(
                            SourceChunk(
                                text=text[:3000],
                                source_url=r.get("link", ""),
                                domain=str(r.get("domain_priority", 0)),
                                relevance_score=0.8,
                            )
                        )

    set_cached(
        state["student_class"],
        state["subject"],
        state["chapter"],
        state["medium"],
        {"research": all_research, "plan": plan},
    )

    elapsed = time.time() - t0
    return {"research": all_research, "timing": {"research": elapsed}}
