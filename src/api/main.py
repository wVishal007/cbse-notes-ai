from __future__ import annotations

import os
import sys
from pathlib import Path

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

from src.api.routes import router
from src.config.settings import DEFAULT_MODEL_MAP, get_settings

app = FastAPI(
    title="CBSE Notes AI",
    description="Multi-agent workflow for generating CBSE NCERT-aligned study notes",
    version="1.0.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(router, prefix="/api")

FRONTEND_DIST = Path(__file__).resolve().parent.parent.parent / "frontend" / "dist"
INDEX_HTML = FRONTEND_DIST / "index.html"


@app.on_event("startup")
async def startup():
    settings = get_settings()

    print("=" * 50, file=sys.stderr)
    print("  CBSE Notes AI -- Starting up", file=sys.stderr)
    print("=" * 50, file=sys.stderr)

    print("\n  Resolved Model Map:", file=sys.stderr)
    for node, (provider, model) in DEFAULT_MODEL_MAP.items():
        override_provider = os.environ.get(f"{node.upper()}__PROVIDER")
        override_model = os.environ.get(f"{node.upper()}__MODEL")
        p = override_provider or provider
        m = override_model or model
        flag = " (env override)" if (override_provider or override_model) else ""
        print(f"    {node:20s} -> {p:15s} / {m}{flag}", file=sys.stderr)
    print(file=sys.stderr)

    key_status = {
        "Mistral": bool(settings.mistral_api_key),
        "Google": bool(settings.google_api_key),
        "Groq": bool(settings.groq_api_key),
        "NVIDIA NIM": bool(settings.nvidia_nim_api_key),
    }
    for name, ok in key_status.items():
        print(f"  [{'+' if ok else 'x'}] {name} API key: {'SET' if ok else 'MISSING'}", file=sys.stderr)

    ls_key = bool(settings.langchain_api_key)
    print(f"  [{'x' if not ls_key else '+'}] LangSmith tracing: {'ENABLED' if (ls_key and settings.langchain_tracing_v2) else 'DISABLED'}", file=sys.stderr)
    print("=" * 50, file=sys.stderr)
    print(file=sys.stderr)


@app.get("/health")
async def health():
    return {"status": "ok"}


if FRONTEND_DIST.exists():
    app.mount("/assets", StaticFiles(directory=str(FRONTEND_DIST / "assets")), name="assets")

    @app.exception_handler(404)
    async def spa_fallback(_request: Request, _exc: Exception):
        path = _request.url.path
        if path.startswith("/api/") or path == "/health":
            from fastapi.exceptions import HTTPException
            raise HTTPException(status_code=404)
        return FileResponse(str(INDEX_HTML))
