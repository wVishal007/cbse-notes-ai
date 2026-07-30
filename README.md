# CBSE Notes AI

Multi-agent LangGraph workflow that generates NCERT-aligned CBSE study notes as PDFs. Input a class, subject, chapter, and medium — get structured notes with practice questions in real-time via SSE streaming, with a download button when the PDF is ready.

---

## Quick Start

### Prerequisites

```bash
pip install -r requirements.txt
playwright install chromium
```

### 1. Set up API keys

```bash
cp .env.example .env
```

Fill in at least these keys in `.env`:

| Key | Needed for |
|-----|-----------|
| `MISTRAL_API_KEY` | Planner, Synthesizer |
| `GOOGLE_API_KEY` | Aggregator, Formatter, PYQ Agent (Gemini) |
| `NVIDIA_NIM_API_KEY` | Validator |
| `LANGCHAIN_API_KEY` | (Optional) LangSmith tracing |

### 2. Start the backend

```bash
cd project
uvicorn src.api.main:app --port 8000
```

### 3. Start the frontend (dev mode)

```bash
cd frontend
npm install
npm run dev        # Opens at http://localhost:5173
```

The Vite dev server proxies `/api/*` to the backend. Default proxy target is `http://localhost:8000` — edit `frontend/vite.config.ts` if your backend is on a different port.

### 4. Generate notes

Via the web UI: fill in the form and click **Generate Notes**.

Via CLI:
```bash
python -m src --class 10 --subject Science --chapter "Chemical Reactions and Equations"
```

Via API:
```bash
curl -X POST http://localhost:8001/api/generate-notes \
  -H "Content-Type: application/json" \
  -d '{"student_class":"10","subject":"Science","chapter":"Chemical Reactions and Equations","medium":"english"}'
```

---

## Architecture

### Agent Pipeline

```
┌──────────┐  POST /api/generate-notes
│  CLIENT  │  ──────────────────────►  ┌──────────────────────┐
│ (React)  │                           │  FastAPI Server       │
│  ◄───────┤  SSE /api/stream/{id}     │  - BackgroundTasks   │
│  Live    │  ◄──────────────────────  │  - Event queue        │
│  Notes   │  (events: node_complete,  │  - graph.stream()     │
│  Preview │   complete, error)        └───────┬──────────────┘
└──────────┘                                   │
                                               ▼
                               ┌───────────────────────────────┐
                               │   LangGraph StateGraph         │
                               │   (8 nodes, conditional edge)  │
                               └───────────────────────────────┘

Input (class, subject, chapter, medium)
  │
  ▼
┌──────────────────────┐
│ PLANNER              │
│ Mistral medium       │
│ → Section outline    │
└─────────┬────────────┘
          │
          ▼
┌──────────────────────┐
│ RESEARCH             │
│ DuckDuckGo search    │
│ + trafilatura scrape │
│ + PyMuPDF extract    │
│ → SourceChunks       │
│ (cached in SQLite)   │
└─────────┬────────────┘
          │
          ▼
┌──────────────────────┐
│ AGGREGATOR           │
│ Gemini 3.1 Flash Lite│
│ → Dedupe, merge,     │
│   flag conflicts     │
└─────────┬────────────┘
          │
          ▼
┌──────────────────────┐
│ SYNTHESIZER          │
│ Mistral medium       │
│ → Write notes per    │
│   section            │
└─────────┬────────────┘
          │
          ▼
┌──────────────────────┐
│ VALIDATOR            │
│ NVIDIA Nemotron 3    │
│ → Check NCERT scope, │
│   key terms, claims  │
└──┬──────────────┬────┘
   │              │
   │  (retry)     │  (pass or max retries)
   │  ◄───────────┤
   ▼              ▼
           ┌──────────────────────┐
           │ FORMATTER            │
           │ Gemini 3.5 Flash Lite│
           │ → Structured Markdown│
           └─────────┬────────────┘
                     │
                     ▼
           ┌──────────────────────┐
           │ PYQ AGENT            │
           │ Gemini 3.5 Flash Lite│
           │ → 5 CBSE practice    │
           │   Q&A (mixed types)  │
           └─────────┬────────────┘
                     │
                     ▼
           ┌──────────────────────┐
           │ PDF EXPORTER         │
           │ Playwright Chromium  │
           │ → A4 PDF with        │
           │   headers/footers    │
           └─────────┬────────────┘
                     │
                     ▼
              PDF file saved   ───►  /api/download/{job_id}
```

### SSE Event Stream

When the client connects to `GET /api/stream/{job_id}`, the server pushes these events:

| Event type | When | Data |
|------------|------|------|
| `node_complete` | After each node finishes | `node`, `content` (notes text for synthesizer/formatter/pyq_agent) |
| `complete` | All nodes done | `pdf_path`, `timing`, `needs_review` |
| `error` | Any exception | `message` |

The frontend appends content incrementally so the user sees notes appearing in real-time ("typewriter" effect). If the SSE connection drops, it automatically falls back to polling `GET /api/status/{job_id}`.

---

### Agent Model Assignment

| Node | Provider | Model | Role |
|------|----------|-------|------|
| Planner | Mistral | `mistral-medium` | NCERT-aligned section outline |
| Research | — | DuckDuckGo + scrapers | Web search & content extraction |
| Aggregator | Google Gemini | `models/gemini-3.1-flash-lite` | Deduplicate & merge research |
| Synthesizer | Mistral | `mistral-medium` | Write section notes |
| Validator | NVIDIA NIM | `nvidia/nemotron-3-ultra-550b-a55b` | CBSE scope validation |
| Formatter | Google Gemini | `models/gemini-3.5-flash-lite` | Markdown structuring |
| PYQ Agent | Google Gemini | `models/gemini-3.5-flash-lite` | Practice Q&A generation |
| PDF Exporter | — | Playwright Chromium | HTML → A4 PDF |

Override any per-node at runtime via environment variables:

```bash
PLANNER__PROVIDER=google
PLANNER__MODEL=models/gemini-3.5-flash-lite
```

---

## API Reference

| Method | Path | Description |
|--------|------|-------------|
| `POST` | `/api/generate-notes` | Start generation — returns `{job_id, status}` |
| `GET` | `/api/stream/{job_id}` | **SSE** — live events (`node_complete`, `complete`, `error`) |
| `GET` | `/api/status/{job_id}` | Poll — returns current job status |
| `GET` | `/api/download/{job_id}` | Download generated PDF |
| `GET` | `/health` | Returns `{"status": "ok"}` |

### Example: Full flow

```bash
# 1. Start generation
JOB=$(curl -s -X POST http://localhost:8001/api/generate-notes \
  -H "Content-Type: application/json" \
  -d '{"student_class":"10","subject":"Science","chapter":"Light Reflection and Refraction","medium":"english"}' \
  | jq -r '.job_id')

# 2. Stream events
curl -N http://localhost:8001/api/stream/$JOB

# 3. Or poll for status
curl -s http://localhost:8001/api/status/$JOB | jq

# 4. Download PDF when complete
curl -o notes.pdf http://localhost:8001/api/download/$JOB
```

### Request schema

```json
{
  "student_class": "10",
  "subject": "Science",
  "chapter": "Chemical Reactions and Equations",
  "medium": "english"
}
```

`medium` accepts `"english"` or `"hindi"`.

---

## Frontend

A single-page React application built with:

- **React 19** — functional components with hooks
- **Vite 6** — fast HMR dev server
- **Tailwind CSS 4** — utility-first responsive styling
- **Lucide React** — icon library

### State machine

```
idle ──(Submit)──► generating ──(SSE: complete)──► completed
                       │                                 │
                       │ (SSE: error)                     │ (Reset)
                       ▼                                 ▼
                    failed ────(Try Again)──────► idle
```

### Key components

| Component | Purpose |
|-----------|---------|
| `useSSEGeneration` | Core hook — connects SSE, manages state, falls back to polling |
| `NotesPreview` | Live Markdown preview with auto-scroll; CSS-animated content appearing |
| `ProgressTracker` | Compact agent status badges (horizontal chips) with progress bar |
| `ResultCard` | Download PDF button + collapsible timing breakdown |
| `NotesForm` | Mobile-first form (single column, 44px touch targets) |
| `HeroSection` | Landing hero with feature tags |
| `AgentNode` | Individual agent status icon |

### Development

```bash
cd frontend
npm run dev          # Dev server on :5173 with API proxy
npm run build        # Production build → dist/
npm run preview      # Preview production build
```

### Responsive design

- **Mobile (<640px)**: Single column, full-width inputs, sticky bottom on forms, compact chip agents
- **Tablet/Desktop (≥640px)**: Wider content area, horizontal form grids, side-by-side elements
- Built with Tailwind's `sm:`, `md:`, `lg:` breakpoints

---

## Features

- **SSE live streaming** — notes appear in real-time as each agent completes (no polling wait)
- **Dual delivery** — CLI (`python -m src`), REST API (FastAPI), and Web UI (React)
- **Hindi/English medium** — searches Hindi NCERT sources, generates notes in the chosen language
- **CBSE-pattern PYQs** — 5 questions per chapter (2 MCQ, 2 Short, 1 Long) with answers
- **NCERT scope validation** — automated fact-checking with retry loop (up to 2 rounds)
- **Professional PDF** — Playwright Chromium rendering, A4 format, headers/footers, Q&A cards
- **Research cache** — SQLite with 7-day TTL; avoids redundant searches for repeated chapters
- **LangSmith tracing** — every run tagged with class/subject/chapter/medium
- **Configurable model routing** — swap providers per node at runtime via env vars
- **Mobile-first UI** — responsive design from phone to desktop

---

## Configuration

### Required API Keys

Set these in `.env`:

| Variable | Provider | Nodes Using It |
|----------|----------|----------------|
| `MISTRAL_API_KEY` | Mistral | Planner, Synthesizer |
| `GOOGLE_API_KEY` | Google Gemini | Aggregator, Formatter, PYQ Agent |
| `NVIDIA_NIM_API_KEY` | NVIDIA NIM | Validator |
| `LANGCHAIN_API_KEY` | LangSmith | All (tracing) |

### Domain Allowlist

Research biases toward trusted CBSE sources. Edit `src/config/domain_allowlist.py`:

| Domain | Priority |
|--------|----------|
| ncert.nic.in | 5 (highest) |
| cbse.gov.in | 5 |
| diksha.gov.in | 4 |
| learncbse.in | 3 |
| Others | 1–2 |

### Override models per-node

```bash
PLANNER__PROVIDER=groq
PLANNER__MODEL=llama-3.3-70b-versatile
VALIDATOR__MODEL=nvidia/nemotron-3-ultra-550b-a55b
```

### Application settings

All configurable in `.env`:

```
MAX_RETRIES=2                # Validation retry attempts
CACHE_TTL_HOURS=168          # Research cache TTL (7 days)
LOG_LEVEL=INFO
```

---

## Project Structure

```
project/
├── src/
│   ├── __main__.py              # CLI entry point
│   ├── api/
│   │   ├── main.py              # FastAPI app + startup logs
│   │   └── routes.py            # 5 API endpoints + SSE streaming
│   ├── cache/
│   │   └── research_cache.py    # SQLite cache with TTL
│   ├── config/
│   │   ├── settings.py          # Pydantic settings + model map
│   │   └── domain_allowlist.py  # CBSE domain priority scoring
│   ├── graph/
│   │   ├── state.py             # TypedDict state schema
│   │   ├── builder.py           # LangGraph graph compilation
│   │   ├── edges.py             # Conditional routing (retry logic)
│   │   └── nodes/
│   │       ├── planner.py       # Section outline (Mistral)
│   │       ├── research.py      # Web search + scrape (8 nodes)
│   │       ├── aggregator.py    # Dedupe & merge (Gemini)
│   │       ├── synthesizer.py   # Note writing (Mistral)
│   │       ├── validator.py     # NCERT scope check (NVIDIA)
│   │       ├── formatter.py     # Markdown formatting (Gemini)
│   │       ├── pyq_agent.py     # Practice Q&A (Gemini)
│   │       └── pdf_exporter.py  # HTML→PDF (Playwright)
│   ├── models/
│   │   ├── model_router.py      # Node→provider mapping
│   │   └── clients/
│   │       ├── base.py          # Abstract LLM client + retry
│   │       ├── mistral.py       # Mistral API wrapper
│   │       ├── gemini.py        # Google Gemini wrapper
│   │       ├── groq.py          # Groq API wrapper
│   │       └── nvidia_nim.py    # NVIDIA NIM wrapper (OpenAI compat)
│   └── tools/
│       ├── search.py            # DuckDuckGo search
│       ├── scraper.py           # Web & PDF text extraction
│       └── pdf.py               # Playwright HTML→PDF
├── frontend/
│   ├── src/
│   │   ├── main.tsx             # React entry point
│   │   ├── App.tsx              # Root component (4-state machine)
│   │   ├── index.css            # Tailwind + custom animations
│   │   ├── types/index.ts       # TypeScript interfaces
│   │   ├── lib/api.ts           # API client functions
│   │   ├── hooks/
│   │   │   └── useSSEGeneration.ts # SSE + polling hook
│   │   └── components/
│   │       ├── HeroSection.tsx  # Landing hero
│   │       ├── NotesForm.tsx    # Input form (mobile-first)
│   │       ├── ProgressTracker.tsx # Compact agent badges
│   │       ├── NotesPreview.tsx # Live Markdown preview
│   │       ├── ResultCard.tsx   # Download + timing
│   │       ├── AgentNode.tsx    # Single agent status
│   │       ├── ui/
│   │       │   ├── button.tsx
│   │       │   ├── card.tsx
│   │       │   ├── input.tsx
│   │       │   ├── select.tsx
│   │       │   └── badge.tsx
│   │       └── layout/
│   │           ├── header.tsx
│   │           ├── footer.tsx
│   │           └── layout.tsx
│   ├── package.json
│   ├── vite.config.ts
│   └── tsconfig*.json
├── templates/
│   ├── notes_template.html      # Jinja2 PDF template
│   └── notes.css                # PDF styles
├── output/                      # Generated PDFs + research_cache.db
├── .env.example
├── requirements.txt
└── README.md
```

---

## Cost Estimate

Per chapter (~10 sections, no cache):

| Agent | Approx. tokens | Est. cost |
|-------|---------------|-----------|
| Planner | 2K | < $0.001 |
| Research | — (free API) | $0 |
| Aggregator | 4K | < $0.001 |
| Synthesizer | 20K | ~$0.001 |
| Validator | 8K | < $0.001 |
| Formatter | 15K | ~$0.001 |
| PYQ Agent | 5K | < $0.001 |
| **Total** | **~54K** | **~$0.003** |

With cache hit: ~$0.001 (formatter + synthesizer + PDF only).

---

## Roadmap

| Status | Feature |
|--------|---------|
| ✅ | Foundation: state schema, config, model clients |
| ✅ | All 8 agent nodes with retry loop |
| ✅ | PDF generation (Playwright Chromium) |
| ✅ | SSE streaming — live notes preview in frontend |
| ✅ | Mobile-first responsive UI |
| ✅ | Research cache (SQLite, 7-day TTL) |
| ✅ | Hindi/English medium support |
| ⬜ | Async job queue with persistent storage (beyond in-memory `_jobs`) |
| ⬜ | Eval dataset + LangSmith regression tests |
| ⬜ | Multi-chapter batch generation |

---

## License

MIT

