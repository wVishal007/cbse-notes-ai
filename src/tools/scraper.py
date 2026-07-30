from __future__ import annotations

import base64
import io
from pathlib import Path
from typing import Optional

import fitz
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


def extract_images_from_pdf(url: str) -> list[dict]:
    import os
    import tempfile
    import urllib.request

    try:
        with urllib.request.urlopen(url, timeout=15) as response:
            data = response.read()
    except Exception:
        return []

    with tempfile.NamedTemporaryFile(suffix=".pdf", delete=False) as tmp:
        tmp_path = tmp.name
        tmp.write(data)

    images: list[dict] = []
    try:
        doc = fitz.open(tmp_path)
        for page_num in range(len(doc)):
            page = doc[page_num]
            pixmaps = page.get_images(full=True)
            for idx, img in enumerate(pixmaps[:3]):
                xref = img[0]
                base_img = doc.extract_image(xref)
                img_bytes = base_img["image"]
                ext = base_img["ext"]
                if ext not in ("png", "jpeg", "jpg"):
                    continue
                b64 = base64.b64encode(img_bytes).decode("utf-8")
                images.append({
                    "b64": b64,
                    "ext": ext,
                    "page_num": page_num + 1,
                    "caption": f"Diagram {len(images) + 1} (Page {page_num + 1})",
                })
        doc.close()
    except Exception:
        pass
    finally:
        os.unlink(tmp_path)

    return images
