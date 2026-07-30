from __future__ import annotations
import atexit
from pathlib import Path

import markdown
from jinja2 import Environment, FileSystemLoader, select_autoescape
from playwright.sync_api import Browser, Playwright, sync_playwright

TEMPLATES_DIR = Path(__file__).resolve().parent.parent.parent / "templates"

_playwright: Playwright | None = None
_browser: Browser | None = None


def _get_browser() -> Browser:
    global _playwright, _browser
    if _browser is None:
        _playwright = sync_playwright().start()
        _browser = _playwright.chromium.launch()
        atexit.register(_cleanup)
    return _browser


def _cleanup() -> None:
    global _playwright, _browser
    if _browser:
        _browser.close()
        _browser = None
    if _playwright:
        _playwright.stop()
        _playwright = None


def markdown_to_html(md_text: str) -> str:
    return markdown.markdown(
        md_text,
        extensions=["tables", "fenced_code", "sane_lists"],
    )


def render_html(formatted_notes: str, pyqs_html: str, template_vars: dict | None = None) -> str:
    env = Environment(
        loader=FileSystemLoader(str(TEMPLATES_DIR)),
        autoescape=select_autoescape(["html", "xml"]),
    )
    template = env.get_template("notes_template.html")

    body_html = markdown_to_html(formatted_notes)

    return template.render(
        notes_body=body_html,
        pyqs_body=pyqs_html,
        **(template_vars or {}),
    )


def export_pdf(html_content: str, output_path: str) -> str:
    browser = _get_browser()
    page = browser.new_page()
    try:
        page.set_content(html_content, wait_until="domcontentloaded")
        page.pdf(
            path=output_path,
            format="A4",
            margin={"top": "0.8in", "bottom": "0.8in", "left": "1in", "right": "1in"},
            display_header_footer=True,
            header_template="<div style='font-size:8pt;color:#666;text-align:center;width:100%;padding:0 1in;'>CBSE Notes AI</div>",
            footer_template="<div style='font-size:8pt;color:#666;text-align:center;width:100%;padding:0 1in;'>Page <span class='pageNumber'></span> of <span class='totalPages'></span></div>",
            print_background=True,
        )
    finally:
        page.close()
    return output_path
