from __future__ import annotations

from typing import Optional

import trafilatura


def extract_text(url: str) -> Optional[str]:
    try:
        downloaded = trafilatura.fetch_url(url)
        if downloaded is None:
            return None
        text = trafilatura.extract(downloaded, include_links=False, include_images=False)
        return text
    except Exception:
        return None


def extract_from_pdf(url: str) -> Optional[str]:
    try:
        import urllib.request
        import tempfile

        with urllib.request.urlopen(url, timeout=15) as response:
            data = response.read()

        import fitz

        with tempfile.NamedTemporaryFile(suffix=".pdf", delete=False) as tmp:
            tmp.write(data)
            tmp_path = tmp.name

        doc = fitz.open(tmp_path)
        text_parts = []
        for page in doc:
            text_parts.append(page.get_text())
        doc.close()

        import os
        os.unlink(tmp_path)

        return "\n".join(text_parts)
    except Exception:
        return None



