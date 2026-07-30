from __future__ import annotations

import logging

from playwright.sync_api import Page, sync_playwright

logger = logging.getLogger(__name__)

MERMAID_JS = "https://cdn.jsdelivr.net/npm/mermaid@11.4.1/dist/mermaid.min.js"


def _render_mermaid_on_page(page: Page, definition: str) -> str:
    html = (
        "<html><head>"
        f'<script src="{MERMAID_JS}"></script>'
        "</head><body>"
        '<div class="mermaid-wrapper" style="max-width:800px;margin:0 auto;">'
        f'<pre class="mermaid">{definition}</pre>'
        "</div>"
        "</body></html>"
    )
    page.set_content(html, wait_until="domcontentloaded")
    page.wait_for_function("typeof mermaid !== 'undefined'", timeout=20000)
    page.evaluate("""() => {
        mermaid.initialize({theme: 'neutral'});
        return mermaid.run({nodes: [document.querySelector('.mermaid')]});
    }""")
    page.wait_for_function(
        "document.querySelector('.mermaid svg g') !== null",
        timeout=15000,
    )
    outer = page.locator(".mermaid svg").evaluate("el => el.outerHTML")
    return outer


def render_mermaid(definition: str) -> str:
    with sync_playwright() as p:
        browser = p.chromium.launch()
        page = browser.new_page()
        try:
            svg = _render_mermaid_on_page(page, definition)
            return svg
        except Exception as exc:
            logger.error("mindmap render failed: %s", exc, exc_info=True)
            return ""
        finally:
            page.close()
            browser.close()
