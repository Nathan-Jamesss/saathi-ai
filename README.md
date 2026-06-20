# Saathi.AI — Voice-Enabled AI Teaching Assistant

> **Saathi** (साथी) = Companion in Hindi  
> *"Your co-pilot in the classroom."*

Built for Connecting Dreams Foundation Round 2 · Deadline: June 20, 2026

---

## What it is

Saathi.AI is a browser-based, voice-first AI co-pilot for Indian government school teachers. The teacher speaks naturally in English, Hindi, or Malayalam. The system listens, classifies intent, retrieves NCERT curriculum content, generates a response using Gemini 2.5 Flash, and projects it to the classroom screen — all within 3–5 seconds, no typing required.

**It does NOT replace the teacher.** It gives them 10 more minutes of teaching time per class.

## Live Demo

- **Frontend:** https://saathi-ai.vercel.app
- **Backend API:** https://saathi-ai-backend.onrender.com/api/health

> **Note:** The Render free-tier backend sleeps after 15 min inactivity. The landing page will show a warm-up message (~20s) if it's waking up.

## Tech Stack

| Layer | Technology |
|---|---|
| Frontend | Vanilla HTML + CSS + JavaScript (no framework) |
| Backend | Python 3.11 + FastAPI |
| LLM | Gemini 2.5 Flash (Google AI Studio free tier) |
| STT | Web Speech API (browser-native, Chrome) |
| TTS | gTTS (Python, via `/api/tts`) |
| RAG Vector Store | ChromaDB (persistent, embedded in FastAPI) |
| Embedding Model | `text-embedding-004` (Google, free tier) |
| Diagram Rendering | Mermaid.js (CDN, client-side) |
| Image Enrichment | Wikipedia REST API (free) |
| PDF Export | jsPDF (client-side) |
| Frontend Hosting | Vercel (free tier) |
| Backend Hosting | Render (free tier) |

**Total running cost: ₹0**

## Architecture Diagram

```
BROWSER (Chrome)
┌─────────────────────────────────────────────────────┐
│  Teacher Control View                                │
│  Mic (spacebar) → Live Transcript → Preview Pane     │
│  Session History Sidebar → Export PDF                │
│             ↕ BroadcastChannel                       │
│  Projector Display View (new window)                 │
│  Large-font content · Mermaid diagrams · Timer       │
└─────────────────────────────────────────────────────┘
         │ Web Speech API (STT)         │ gTTS (TTS)
         ▼                              ▼
FASTAPI BACKEND (Render)
┌─────────────────────────────────────────────────────┐
│  POST /api/process                                   │
│    → Intent Router (Gemini Flash, temp=0.1)          │
│    → RAG Retrieval (ChromaDB + text-embedding-004)   │
│    → Feature Handler (Gemini Flash, temp=0.4–0.5)    │
│    → Wikipedia image fetch (async)                   │
│    → JSON response                                   │
│  POST /api/tts  →  gTTS audio stream                 │
│  GET  /api/health                                    │
└─────────────────────────────────────────────────────┘
```

## Prompt Design

### Intent Router
A Gemini Flash call with `temperature=0.1` (low, for classification accuracy). The prompt includes session context (grade, subject, previous topic) so the model can infer missing parameters from speech. Handles English, Hindi, Malayalam, and code-mixed input.

Output: strict JSON with `intent`, `topic`, `grade`, `language`, `confidence`, and feature-specific params.

### Content Generation Prompts (per feature)

| Feature | Temperature | Key Design Decisions |
|---|---|---|
| Concept Simplification | 0.4 | Grade-calibrated; NCERT context injected; Mermaid diagram in output; code-mixing allowed |
| Quiz Generation | 0.5 | Difficulty mix (40/40/20); NCERT-grounded; deduplicated against session history |
| Translation | 0.2 | Keeps technical terms in English; transliteration for Malayalam only |
| Activity Guide | 0.5 | Steps must sum to exact duration; max 6 steps; student-facing vs teacher-facing instructions split |

All prompts use `response_mime_type: application/json` for reliable structured output.

## Localization

| Language | STT (Web Speech API) | TTS (gTTS) | Gemini Output |
|---|---|---|---|
| English (Indian) | `en-IN` | `en` | ✅ |
| Hindi | `hi-IN` | `hi` | ✅ |
| Malayalam | `ml-IN` | `ml` | ✅ |

**Auto-detection:** Unicode range check on transcript text. Malayalam (U+0D00–U+0D7F) → switch to `ml-IN`. Devanagari (U+0900–U+097F) → `hi-IN`. The teacher can also manually override via the language indicator or settings panel.

**Font:** Noto Sans covers Latin, Devanagari, and Malayalam in a single font family — no separate font loading per language.

## How to Run Locally

### Backend
```bash
cd backend
pip install -r requirements.txt
cp .env.example .env
# Edit .env with your GEMINI_API_KEY

# (Optional) Build NCERT index
python scripts/download_ncert.py
python scripts/build_index.py

# Start server
uvicorn main:app --reload --port 8000
```

### Frontend
```bash
# Option 1: Live Server (VS Code extension)
# Open frontend/index.html with Live Server

# Option 2: Python
cd frontend
python -m http.server 5500
# Open http://localhost:5500
```

Update `frontend/js/api.js` — change `BACKEND_URL` to `http://localhost:8000`.

## Environment Variables

| Variable | Description | Default |
|---|---|---|
| `GEMINI_API_KEY` | Google AI Studio API key (required) | — |
| `CHROMA_PERSIST_DIR` | ChromaDB storage path | `./data/chroma` |

## Known Limitations

1. **Chrome only** — Web Speech API is not supported in Firefox or Safari.
2. **Malayalam/Hindi in PDF** — jsPDF's built-in fonts don't support Indic scripts. Malayalam/Hindi text is not included in PDF exports (English content and transliterations are exported instead).
3. **Render cold start** — Free-tier backend sleeps after 15 min. First request after sleep takes ~25–35s.
4. **RAG requires index build** — If `build_index.py` hasn't run, the system falls back to Gemini's general knowledge (still functional, but not NCERT-grounded).
5. **Rate limits** — Gemini 2.5 Flash free tier: ~10–15 RPM. Suitable for classroom use (1 command every 2–3 min), not for rapid automated testing.

## File Structure

```
saathi-ai/
├── frontend/          → Deployed to Vercel
│   ├── index.html     Landing page
│   ├── app.html       Teacher Control View
│   ├── display.html   Projector Display View
│   ├── css/           Design system + page styles
│   └── js/            STT, session, API, renderer, broadcast, export, app
├── backend/           → Deployed to Render
│   ├── main.py        FastAPI entrypoint + CORS
│   ├── api/           /process, /tts, /export, /health
│   ├── core/          intent_router, concept, quiz, translation, activity, rag, wikipedia
│   ├── prompts/       Prompt templates (5 features)
│   └── scripts/       build_index.py, download_ncert.py
└── data/
    ├── ncert/         Raw NCERT text chunks (JSON)
    └── chroma/        ChromaDB persistent storage
```

## Built for

**Connecting Dreams Foundation Round 2** — Option A: AI Teaching Assistant  
Built by Nathan James · June 2026

---

*Stack: Gemini 2.5 Flash · ChromaDB · FastAPI · Vercel · Render · Web Speech API · gTTS · Mermaid.js · jsPDF · Total cost: ₹0*
