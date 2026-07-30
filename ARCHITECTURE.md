# CBSE Notes AI — Architecture

## 1. System Overview

Multi-agent pipeline that generates NCERT-aligned CBSE study notes as A4 PDFs.

**Input:** `student_class`, `subject`, `chapter`, `medium` (`english`/`hindi`), `note_mode` (`short`/`detailed`)

**Output:** A4 PDF containing:
- Title block (subject, class, chapter, medium)
- Mermaid mindmap (chapter concept map)
- Structured notes (per-section, NCERT-aligned)
- Practice questions (8 CBSE-pattern Q&As with bullet-point answers)

**Interface:** React SPA (Vite) → FastAPI REST API → LangGraph agent pipeline

---

## 2. Project Structure

```
project/
├── src/
│   ├── __main__.py                 # CLI entry point (python -m src)
│   ├── api/
│   │   ├── main.py                 # FastAPI app factory + startup logs
│   │   └── routes.py               # 5 endpoints + SSE streaming + job queue
│   ├── cache/
│   │   └── research_cache.py       # SQLite cache with 7-day TTL, schema v3
│   ├── config/
│   │   ├── settings.py             # Pydantic Settings + DEFAULT_MODEL_MAP
│   │   └── domain_allowlist.py     # CBSE domain priority scoring for search
│   ├── graph/
│   │   ├── state.py                # NotesState TypedDict (20 fields)
│   │   ├── builder.py              # StateGraph construction + compilation
│   │   ├── edges.py                # Conditional edge: route_after_validation
│   │   └── nodes/
│   │       ├── planner.py          # Section outline (Gemini)
│   │       ├── research.py         # Web search + scrape (DuckDuckGo + trafilatura)
│   │       ├── mindmap.py          # Mermaid mindmap (Playwright + CDN)
│   │       ├── aggregator.py       # Deduplicate & merge research (Gemini)
│   │       ├── synthesizer.py      # Write notes per section (Gemini, 2-model RR)
│   │       ├── validator.py        # NCERT scope validation (Gemini, chunked)
│   │       ├── formatter.py        # Markdown formatting + dedup (Gemini)
│   │       ├── pyq_agent.py        # 8 CBSE-pattern Q&As (Gemini)
│   │       └── pdf_exporter.py     # HTML→PDF (Playwright)
│   ├── models/
│   │   ├── model_router.py         # create_client() factory + get_model_for_node()
│   │   └── clients/
│   │       ├── base.py             # LLMClient abstract class + retry loop
│   │       ├── gemini.py           # Google Gemini (genai SDK)
│   │       ├── groq.py             # Groq (OpenAI-compat SDK)
│   │       ├── mistral.py          # Mistral (mistralai SDK)
│   │       ├── nvidia_nim.py       # NVIDIA NIM (OpenAI-compat SDK)
│   │       └── openai.py           # OpenAI (OpenAI SDK)
│   └── tools/
│       ├── search.py               # DuckDuckGo search + to_source_chunks()
│       ├── scraper.py              # trafilatura extract_text() + PDF text extraction
│       ├── mermaid.py              # Mermaid definition → SVG via Playwright CDN
│       └── pdf.py                  # render_html_with_mindmap() + export_pdf()
├── frontend/
│   ├── src/
│   │   ├── main.tsx                # React entry
│   │   ├── App.tsx                 # Root: 4-state machine (idle→generating→completed|failed)
│   │   ├── index.css               # Tailwind v4 + custom animations
│   │   ├── types/index.ts          # GeneratePayload, JobStatus, AgentStage
│   │   ├── lib/api.ts              # generateNotes(), pollStatus(), getDownloadUrl()
│   │   ├── hooks/
│   │   │   └── useSSEGeneration.ts # EventSource + polling fallback
│   │   └── components/
│   │       ├── HeroSection.tsx     # Landing hero with feature tags
│   │       ├── NotesForm.tsx       # Class/subject/chapter/medium/note_mode form
│   │       ├── ProgressTracker.tsx # Compact agent badges + progress bar
│   │       ├── NotesPreview.tsx    # Live markdown preview with auto-scroll
│   │       ├── ResultCard.tsx      # Download PDF + timing breakdown
│   │       └── ui/                 # button, card, input, select, badge
│   ├── package.json
│   ├── vite.config.ts              # Proxy /api→backend
│   └── tsconfig*.json
├── templates/
│   ├── notes_template.html         # Jinja2 PDF template
│   └── notes.css                   # PDF stylesheet (warm academic palette)
├── output/                         # Generated PDFs + research_cache.db
├── clear.py                        # Cache + output cleaner
├── requirements.txt
├── .env.example
├── README.md
└── ARCHITECTURE.md                 # This file
```

---

## 3. Tech Stack

| Layer | Technology | Version |
|-------|-----------|---------|
| Language | Python | 3.11+ |
| Graph orchestration | LangGraph | latest |
| API server | FastAPI | latest |
| LLM SDKs | google-genai, groq, mistralai, openai | latest |
| Web scraping | trafilatura, duckduckgo-search | latest |
| PDF extraction | PyMuPDF (fitz) | latest |
| PDF generation | Playwright (Chromium) | latest |
| HTML templating | Jinja2 | latest |
| Markdown | markdown | latest |
| Validation | Pydantic v2 | latest |
| Schema cache | SQLite | stdlib |
| **Frontend** | | |
| Framework | React | 19 |
| Build tool | Vite | 6 |
| Styling | Tailwind CSS | 4 |
| Icons | Lucide React | latest |
| State | useState + useRef | built-in |
| HTTP | fetch + EventSource | built-in |

---

## 4. Pipeline Graph

```
POST /api/generate-notes
         │
         ▼
┌──────────────────────────────────────────────────────────────────┐
│                    LangGraph StateGraph                          │
│                                                                  │
│  planner ───────────────────────────────────────────────────────┐│
│    │ (plan: list[Section])                                      ││
│    │                                                            ││
│    ├──────────────────┐                                         ││
│    ▼                  ▼                                         ││
│  mindmap_generator  research  (parallel)                        ││
│    │                  │                                         ││
│    └──────┬───────────┘                                         ││
│           ▼                                                     ││
│         aggregator                                              ││
│           │ (aggregated_research: dict)                         ││
│           ▼                                                     ││
│         synthesizer  ──── 5 parallel threads,                   ││
│           │              round-robin across 2 Gemini models     ││
│           │ (draft_notes: dict)                                 ││
│           ▼                                                     ││
│         validator  ──── chunked validation (6× ~9K chars)      ││
│          ╱       ╲                                              ││
│         ╱         ╲                                             ││
│   (retry)      (pass/max)                                       ││
│      │             │                                            ││
│      ◄──── ────────┤                                            ││
│                    ▼                                            ││
│                 formatter                                       ││
│                    │ (formatted_notes: str)                      ││
│                    ▼                                            ││
│                 pyq_agent                                       ││
│                    │ (pyqs: list[QA], 8 questions)              ││
│                    ▼                                            ││
│                 pdf_exporter                                    ││
│                    │ (pdf_path: str)                             ││
│                    ▼                                            ││
│                   END                                           ││
└──────────────────────────────────────────────────────────────────┘
         │
         ▼
  PDF saved to output/  ←──  GET /api/download/{job_id}
  SSE stream via        ──→  GET /api/stream/{job_id}
```

**Parallelism:**
- `mindmap_generator` + `research` run concurrently (fan-out from `planner`, fan-in to `aggregator`)
- `synthesizer` uses `ThreadPoolExecutor(5)` for parallel section writes
- `research` uses `ThreadPoolExecutor(6)` for parallel web queries

**Conditional edge:**
- `validator` → `synthesizer` (retry, up to `max_retries=2`)
- `validator` → `formatter` (pass or max retries exhausted)

---

## 5. Node Deep Dives

### 5.1 Planner

| Property | Value |
|----------|-------|
| **File** | `src/graph/nodes/planner.py` |
| **Provider** | Google Gemini |
| **Model** | `models/gemini-3.1-flash-lite` |
| **Input** | `student_class`, `subject`, `chapter`, `medium` |
| **Output** | `plan: list[Section]` |
| **Prompt** | NCERT-aligned section outline → JSON array of sections |
| **Detail** | Reads `note_mode`: if `"detailed"`, appends granular outline instruction |

Each `Section`:
```python
{
    "id": "sec-1",
    "heading": "Introduction to Chemical Reactions",
    "level": 1,
    "parent_id": None,
    "subheadings": ["Types of Reactions", "Balancing Equations"],
    "key_concepts": ["Chemical equation", "Reactants", "Products"],
}
```

### 5.2 Mindmap Generator

| Property | Value |
|----------|-------|
| **File** | `src/graph/nodes/mindmap.py` |
| **Provider** | — (local, Playwright) |
| **Input** | `plan: list[Section]` |
| **Output** | `mindmap_svg: str` |
| **Process** | Builds Mermaid mindmap definition from section hierarchy → renders via Playwright + `mermaid@11.4.1` CDN → returns SVG outerHTML |

### 5.3 Research

| Property | Value |
|----------|-------|
| **File** | `src/graph/nodes/research.py` |
| **Provider** | — (DuckDuckGo + trafilatura) |
| **Input** | `plan`, `student_class`, `subject`, `chapter`, `medium` |
| **Output** | `research: dict[str, list[SourceChunk]]` |
| **Cache** | SQLite, keyed by `{schema_version}\|{class}\|{subject}\|{chapter}\|{medium}`, 7-day TTL |
| **Process** | 4 queries per section (heading + 3 key concepts) → 6 parallel workers → text extracted via trafilatura or PyMuPDF |

### 5.4 Aggregator

| Property | Value |
|----------|-------|
| **File** | `src/graph/nodes/aggregator.py` |
| **Provider** | Google Gemini |
| **Model** | `models/gemini-3.1-flash-lite` |
| **Input** | `research: dict`, `plan: list[Section]` |
| **Output** | `aggregated_research: dict[str, str]` |
| **Prompt** | Merges duplicate chunks, flags contradictions, returns one coherent text per section |

### 5.5 Synthesizer

| Property | Value |
|----------|-------|
| **File** | `src/graph/nodes/synthesizer.py` |
| **Provider** | Google Gemini (round-robin across 2 models) |
| **Models** | `models/gemini-3.1-flash-lite`, `models/gemini-3.5-flash-lite` |
| **Input** | `aggregated_research`, `plan`, `note_mode`, `validation_report` (retries) |
| **Output** | `draft_notes: dict[str, str]` |
| **Parallelism** | `ThreadPoolExecutor(5)` — one thread per section |
| **Model distribution** | Round-robin: `clients[i % 2]` → sections 1,3,5 on 3.1; 2,4 on 3.5 |
| **Detail** | Reads `note_mode`: if `"detailed"`, appends depth instruction (2-3× content, examples, step-by-step) |

### 5.6 Validator

| Property | Value |
|----------|-------|
| **File** | `src/graph/nodes/validator.py` |
| **Provider** | Google Gemini |
| **Model** | `models/gemini-3.1-flash-lite` |
| **Input** | `draft_notes: dict`, `plan: list[Section]` |
| **Output** | `validation_report: ValidationResult`, `needs_review: bool`, `retry_count: int` |
| **Chunking** | `CHUNK_SIZE = 9000` characters → ~6 chunks for a full chapter |
| **Rate limiting** | `RateLimitError` caught per-chunk → logs warning, marks chunk as passed |
| **Retry loop** | If `not passed` and `retry_count < max_retries` → edge back to synthesizer with feedback |

### 5.7 Formatter

| Property | Value |
|----------|-------|
| **File** | `src/graph/nodes/formatter.py` |
| **Provider** | Google Gemini |
| **Model** | `models/gemini-3.5-flash-lite` |
| **Input** | `draft_notes: dict`, `plan: list[Section]` |
| **Output** | `formatted_notes: str` |
| **Prompt** | Deduplicates repeated facts across sections, reformats to structured Markdown, plain-language pass |

### 5.8 PYQ Agent

| Property | Value |
|----------|-------|
| **File** | `src/graph/nodes/pyq_agent.py` |
| **Provider** | Google Gemini |
| **Model** | `models/gemini-3.5-flash-lite` |
| **Input** | `formatted_notes: str`, `plan: list[Section]` |
| **Output** | `pyqs: list[QA]` (8 questions) |
| **Types** | 2 MCQ (1 mark), 3 Short (2-3 marks), 2 Long (5 marks), 1 Case-based (4 marks) |
| **Answers** | Bullet-point format (`"- "` delimited), rendered as `<ul><li>` in PDF |
| **Parsing** | 3-stage fallback: direct JSON → markdown-fenced JSON → regex extraction from text |

### 5.9 PDF Exporter

| Property | Value |
|----------|-------|
| **File** | `src/graph/nodes/pdf_exporter.py` |
| **Provider** | — (Playwright Chromium) |
| **Input** | `formatted_notes`, `pyqs`, `mindmap_svg`, template vars |
| **Output** | `pdf_path: str` |
| **Process** | Markdown → HTML → Jinja2 template with mindmap SVG + Q&A cards → Playwright `page.pdf()` → A4 with headers/footers |

---

## 6. State Schema

Full `NotesState` TypedDict (defined in `src/graph/state.py`):

```python
class NotesState(TypedDict):
    # --- Input ---
    student_class: str                # "10"
    subject: str                      # "Science"
    chapter: str                      # "Chemical Reactions and Equations"
    medium: Literal["english", "hindi"]
    note_mode: Literal["short", "detailed"]

    # --- Pipeline outputs ---
    plan: list[Section]               # Section outline (planner)
    mindmap_svg: Optional[str]        # Mermaid SVG (mindmap_generator)
    research: dict[str, str]          # Raw source chunks per section ID (research)
    aggregated_research: dict[str, str]  # Merged research per section (aggregator)
    draft_notes: dict[str, str]       # Per-section notes (synthesizer)
    formatted_notes: str              # Full formatted document (formatter)
    pyqs: list[QA]                    # Practice questions (pyq_agent)

    # --- Validation ---
    retry_count: int                  # Current validation retry count
    max_retries: int                  # Maximum retries (default 2)
    needs_review: bool                # True if retries exhausted but validation still failed
    validation_report: Optional[ValidationResult]

    # --- Output ---
    pdf_path: Optional[str]           # Absolute path to generated PDF

    # --- Meta ---
    errors: list[str]                 # Error messages collected during run
    timing: Annotated[dict[str, float], merge_timing]  # Per-node elapsed times (auto-merged for parallel nodes)
```

**Sub-types:**

```python
class Section(TypedDict):
    id: str; heading: str; level: int
    parent_id: Optional[str]
    subheadings: list[str]; key_concepts: list[str]

class QA(TypedDict):
    question: str; answer: str; marks: int
    section_id: str; question_type: str     # "MCQ"|"Short"|"Long"|"Case-based"

class ValidationResult(TypedDict):
    passed: bool
    missing_key_terms: list[str]
    hallucinated_claims: list[str]
    scope_violations: list[str]
    feedback: str
```

---

## 7. Request Flow (End-to-End)

```
CLIENT (React)                    FASTAPI                          LANGGRAPH
     │                               │                                │
     │ POST /api/generate-notes       │                                │
     │ {class,subject,chapter,        │                                │
     │  medium,note_mode}             │                                │
     │──────────────────────────────►│                                │
     │                               │  Create job_id                  │
     │◄── {job_id, status:"processing"}│                                │
     │                               │                                │
     │ GET /api/stream/{job_id}       │                                │
     │──────────────────────────────►│                                │
     │                               │  Start background task          │
     │                               │  ┌──────────────────────────┐  │
     │                               │  │ _run_generation()        │  │
     │                               │  │  graph.stream(state)     │  │
     │                               │  │    .stream() yields:     │  │
     │                               │  │  step 1: {"planner": ...}│  │
     │  SSE: node_complete           │  │  step 2: {"research":...}│  │
     │◄─── {node:"planner",...}──────│  │           +              │  │
     │  SSE: node_complete           │  │  step 2: {"mindmap":...} │  │
     │◄─── {node:"research",...}─────│  │  step 3: {"aggregator"}: │  │
     │  SSE: node_complete           │  │  ...                      │  │
     │◄─── ...                       │  │  step N: {"pdf_exporter"}│  │
     │                               │  └──────────────────────────┘  │
     │  SSE: complete                │                                │
     │◄─── {pdf_path, timing}────────│                                │
     │                               │                                │
     │ GET /api/download/{job_id}     │                                │
     │──────────────────────────────►│                                │
     │◄── FileResponse (PDF)────────│                                │
```

**SSE event types:**

| Event | Data | When |
|-------|------|------|
| `node_complete` | `{node, content, timestamp}` | After each node finishes |
| `complete` | `{pdf_path, timing, needs_review}` | All nodes done |
| `error` | `{message}` | Any exception |

**Polling fallback:** If SSE disconnects, frontend polls `GET /api/status/{job_id}` every 2s until `completed` or `failed`.

---

## 8. Model Routing

### Default Model Map

Defined in `src/config/settings.py`:

```python
DEFAULT_MODEL_MAP = {
    "planner":       ("google", "models/gemini-3.1-flash-lite"),
    "aggregator":    ("google", "models/gemini-3.1-flash-lite"),
    "synthesizer":   ("google", "models/gemini-3.1-flash-lite"),  # + 3.5 round-robin in code
    "validator":     ("google", "models/gemini-3.1-flash-lite"),
    "pyq_agent":     ("google", "models/gemini-3.5-flash-lite"),
    "formatter":     ("google", "models/gemini-3.5-flash-lite"),
}
```

### Runtime Override

Any node can be redirected via environment variables:
```bash
SYNTHESIZER__PROVIDER=groq
SYNTHESIZER__MODEL=llama-3.1-8b-instant
```

### Provider Clients

| Provider | Client class | API Key | SDK |
|----------|-------------|---------|-----|
| `google` | `GeminiClient` | `GOOGLE_API_KEY` | `google-genai` |
| `groq` | `GroqClient` | `GROQ_API_KEY` | `groq` (OpenAI compat) |
| `mistral` | `MistralClient` | `MISTRAL_API_KEY` | `mistralai` |
| `nvidia_nim` | `NvidiaNIMClient` | `NVIDIA_NIM_API_KEY` | `openai` (OpenAI compat) |
| `openai` | `OpenAIClient` | `OPENAI_API_KEY` | `openai` |

All clients extend `LLMClient` (abstract base class in `base.py`) which provides:
- Retry loop with exponential backoff (`max_retries`, `base_delay` × 2^attempt)
- `RateLimitError` — caught downstream for graceful degradation (validator skips chunk)

---

## 9. Note Modes

| Aspect | `"short"` (default) | `"detailed"` |
|--------|--------------------|--------------|
| **Planner** | Standard NCERT section outline (8-12 sections) | More granular: 1-2 extra subsections per topic |
| **Synthesizer** | Current behavior: clear, detailed, covers key concepts | 2-3× content: real-world examples, step-by-step explanations, detailed comparisons |
| **Validator** | Same scope check | Same scope check |
| **Formatter** | Same dedup + format | Same dedup + format |
| **PYQs** | Same 8 questions | Same 8 questions |

---

## 10. Rate Limit & Error Handling

### Rate Limits

Both Gemini and Groq have free-tier rate limits:

| Provider | Limit | Mitigation |
|----------|-------|-----------|
| Gemini 3.1 Flash Lite | 15 req/min | Round-robin synthesizer across 2 models |
| Gemini 3.5 Flash Lite | 15 req/min | Only 2-3 req per run (synthesizer + formatter + pyq) |
| Groq 8B | 6000 TPM | Only used when explicitly configured |

### Error Handling Strategy

```
Planner ──► LLM  ──► RateLimitError? ──► base.py retry loop (2×, exponential backoff)
Research ──► DuckDuckGo ──► Exception? ──► logged, empty results returned
Synthesizer ──► ThreadPoolExecutor ──► RateLimitError? ──► propagates up, run fails
Validator ──► Gemini (chunked) ──► RateLimitError? ──► per-chunk: logged "skipping", proceeds
                                                      without that chunk's validation
Validation retry ──► loop back to synthesizer ──► max 2 retries
PDF Exporter ──► Playwright ──► greenlet error? ──► fixed by per-call sync_playwright()
```

### Validation Retry Loop

```
synthesizer
    │
    ▼
validator ──► passed=true? ──► formatter
    │
    └──► passed=false && retry_count < max_retries?
              │
              ▼
         synthesizer (with validator feedback in prompt)
              │
              ▼
         validator
              │
              └──► passed=false && retry_count >= max_retries?
                        │
                        ▼
                   needs_review=true
                        │
                        ▼
                   formatter (continues regardless)
```

---

## 11. Research Cache

**File:** `src/cache/research_cache.py`

**Backend:** SQLite at `output/research_cache.db`

**Schema:**
```sql
CREATE TABLE research_cache (
    key_hash TEXT PRIMARY KEY,       -- SHA-256 of cache key
    data_json TEXT NOT NULL,         -- JSON blob: {research: dict, plan: list}
    created_at REAL NOT NULL         -- Unix timestamp
);
```

**Cache key:** `SHA256("{SCHEMA_VERSION}|{class}|{subject}|{chapter}|{medium}")`

- `SCHEMA_VERSION = 3` — bumped to invalidate old entries (image removal, data format changes)
- Case-insensitive: `subject` and `chapter` lowercased before hashing

**TTL:** `CACHE_TTL_HOURS` (default 168 = 7 days, configurable in `.env`)

**Write-through policy:** Research is cached on first miss. Subsequent identical requests (same class/subject/chapter/medium) return cached data immediately, skipping all web searches.

---

## 12. Frontend Architecture

### Component Tree

```
<App>
  <Layout>
    <Toaster />                          # Toast notifications

    # State: idle
    <HeroSection />                      # Landing hero + feature tags
    <NotesForm                           # Input form
      onSubmit={startGeneration}
      fields: class, subject, chapter, medium, note_mode
    />

    # State: generating / completed / failed
    <button onClick={reset}>Back</button>
    <ProgressTracker                     # Agent status badges + progress bar
      agents={[planner, research, ..., pdf_exporter]}
    />
    <NotesPreview                        # Live markdown preview
      content (accumulated SSE content)
      isGenerating
    />
    <ResultCard />                       # Download PDF + timing breakdown (completed only)
    <ErrorCard />                        # "Try Again" (failed only)
```

### State Machine

```
idle ──(Submit)──► generating ──(SSE: complete)──► completed
                        │
                        │ (SSE: error)
                        ▼
                     failed ──(Try Again)──► idle
```

### SSE Hook (`useSSEGeneration`)

Manages 4 state variables:
- `state: GenerationState` — `idle | generating | completed | failed`
- `content: string` — accumulated markdown from all `node_complete` events
- `agents: AgentStage[]` — 9 agents with `pending | running | completed | failed` status
- `result: GenerateResult` — `{pdf_path, timing, needsReview}` from `complete` event

**Flow:**
1. `startGeneration(payload)` → `POST /api/generate-notes` → get `job_id`
2. Open `EventSource(/api/stream/{job_id})`
3. On each `node_complete`: append content, mark agent completed
4. On `complete`: set state to `completed`, close EventSource
5. On `error`: set state to `failed`
6. On connectivity error: fall back to polling `GET /api/status/{job_id}` every 2s

### Markdown Rendering

`NotesPreview` uses a regex-based renderer (no library dependency):
```
### Heading → <h3>, ## → <h2>, # → <h1>
**bold** → <strong>, *italic* → <em>
> quote → <blockquote>
- list → <li>
\n\n → paragraph break
```

---

## 13. API Reference

### POST /api/generate-notes

Start note generation (returns immediately with `job_id`).

**Request:**
```json
{
  "student_class": "10",
  "subject": "Science",
  "chapter": "Chemical Reactions and Equations",
  "medium": "english",
  "note_mode": "short"
}
```

**Response:**
```json
{
  "job_id": "a1b2c3d4-e5f6-...",
  "status": "processing"
}
```

### GET /api/stream/{job_id}

Server-Sent Events stream. Returns `text/event-stream`.

**Events:**
```
data: {"type":"node_complete","node":"planner","content":"- Introduction\n- ...","timestamp":...}

data: {"type":"node_complete","node":"synthesizer","content":"## Section 1\n**Key Term:** ...","timestamp":...}

data: {"type":"complete","pdf_path":"output/Class10_...pdf","timing":{"planner":1.2,...},"needs_review":false}

data: {"type":"error","message":"..."}
```

### GET /api/status/{job_id}

Poll for job status (fallback when SSE disconnects).

**Response:**
```json
{
  "job_id": "...",
  "status": "processing|completed|failed|not_found",
  "pdf_path": null,
  "error": null,
  "timing": null,
  "needs_review": false
}
```

### GET /api/download/{job_id}

Download the generated PDF. `Content-Type: application/pdf`.

### GET /health

Health check. Returns `{"status": "ok"}`.

---

## 14. Configuration

### Environment Variables (.env)

| Variable | Required | Default | Purpose |
|----------|----------|---------|---------|
| `GOOGLE_API_KEY` | ✅ | — | Gemini API access |
| `GROQ_API_KEY` | ❌ | — | Groq API access |
| `MISTRAL_API_KEY` | ❌ | — | Mistral API access |
| `NVIDIA_NIM_API_KEY` | ❌ | — | NVIDIA NIM API access |
| `OPENAI_API_KEY` | ❌ | — | OpenAI API access |
| `LANGCHAIN_API_KEY` | ❌ | — | LangSmith tracing |
| `LANGCHAIN_PROJECT` | ❌ | `cbse-notes-ai` | LangSmith project name |
| `MAX_RETRIES` | ❌ | `2` | Validation retry attempts |
| `CACHE_TTL_HOURS` | ❌ | `168` | Research cache TTL (7 days) |
| `LOG_LEVEL` | ❌ | `INFO` | Logging level |

### Per-Node Model Overrides

Set any node's provider/model at runtime:
```bash
PLANNER__PROVIDER=groq
PLANNER__MODEL=llama-3.1-8b-instant
VALIDATOR__MODEL=models/gemini-3.5-flash-lite
SYNTHESIZER__PROVIDER=google
SYNTHESIZER__MODEL=models/gemini-2.0-flash
```

### Domain Allowlist

`src/config/domain_allowlist.py` biases research toward trusted CBSE sources:

| Domain | Priority |
|--------|----------|
| `ncert.nic.in` | 5 (highest) |
| `cbse.gov.in` | 5 |
| `diksha.gov.in` | 4 |
| `learncbse.in` | 3 |
| Others | 1-2 |

---

## 15. Design Decisions

### Why LangGraph over direct orchestration?

- **State management**: Shared `NotesState` TypedDict across all nodes — no manual message passing
- **Conditional edges**: Validator retry loop via `add_conditional_edges` — no custom loop logic
- **Streaming**: `graph.stream()` yields per-node output as it completes — drives SSE directly
- **Parallelism**: Fan-out edges (`planner→mindmap`, `planner→research`) handled natively

### Why two Gemini models for synthesizer?

Gemini free tier limits to 15 requests/minute per model. The synthesizer launches 5 parallel section writes. Distributing round-robin across `gemini-3.1-flash-lite` and `gemini-3.5-flash-lite` keeps each model under 3 req/burst, well within the 15/min limit.

### Why Playwright for PDF?

- Renders Mermaid SVG via CDN (requires a browser JS engine)
- Full CSS support (Flexbox, @page, page-break)
- Header/footer templates with page numbering
- `page.pdf()` produces proper A4 output with print backgrounds

### Why sync_playwright() per call?

LangGraph's internal greenlet-based execution conflicts with Playwright's sync API when using a persistent browser singleton. Creating a fresh `sync_playwright()` context per call ensures browser creation and usage happen in the same greenlet context, avoiding `Cannot switch to a different thread` errors.

### Why SSE over WebSocket?

- Simpler: HTTP-based, no upgrade handshake, works through standard proxies
- Browser-native `EventSource` API — no library needed
- Auto-reconnect behavior built into `EventSource`
- HTTP/2 compatible (multiple SSE streams over one connection)
- Fallback to polling is trivial (standard `fetch` + `setInterval`)

### Why images were removed?

The image pipeline (PDF extraction + web search + base64 embedding) added ~15s to wall-clock time, complex failure paths, and bloated the PDF HTML. The value was minimal for CBSE notes — students primarily need text content, diagrams from NCERT are available separately. Removing images simplified the codebase and reduced generation time without impacting note quality.

### Why answers are bullet points?

CBSE answer keys use point-wise marking. Bullet-point answers make the evaluation criteria explicit, help students learn structured answer writing, and are more scannable in both the preview and PDF.
