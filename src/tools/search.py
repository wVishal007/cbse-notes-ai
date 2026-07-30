from __future__ import annotations

from typing import Optional

from langchain_community.tools import DuckDuckGoSearchResults

from src.config.domain_allowlist import get_domain_priority
from src.graph.state import SourceChunk

_SEARCH = DuckDuckGoSearchResults(num_results=5, source="web")


def search_subtopic(
    query: str, max_results: int = 5, min_priority: int = 0
) -> list[dict]:
    raw = _SEARCH.invoke(query)
    results: list[dict] = []
    seen_urls: set[str] = set()

    if isinstance(raw, str):
        import re

        snippets = re.split(r"(?=snippet:)", raw)
        for snippet in snippets:
            title_match = re.search(r"title:\s*(.*?)(?=,\s*snippet:)", snippet)
            snippet_match = re.search(r"snippet:\s*(.*?)(?=,\s*link:)", snippet)
            link_match = re.search(r"link:\s*(https?://\S+)", snippet)

            title = title_match.group(1).strip() if title_match else ""
            body = snippet_match.group(1).strip() if snippet_match else ""
            link = link_match.group(1).strip().rstrip(")") if link_match else ""

            if link and link not in seen_urls:
                seen_urls.add(link)
                priority = get_domain_priority(link)
                if priority >= min_priority:
                    results.append({
                        "title": title,
                        "snippet": body,
                        "link": link,
                        "domain_priority": priority,
                    })

    return results[:max_results]


def to_source_chunks(
    results: list[dict], section_id: str
) -> list[SourceChunk]:
    chunks: list[SourceChunk] = []
    for r in results:
        chunks.append(
            SourceChunk(
                text=f"{r.get('title', '')}\n{r.get('snippet', '')}",
                source_url=r.get("link", ""),
                domain=str(r.get("domain_priority", 0)),
                relevance_score=float(r.get("domain_priority", 0)) / 5.0,
            )
        )
    return chunks
