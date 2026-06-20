# Saathi.AI — Your co-pilot in the classroom

> **Saathi** (साथी) = companion. A voice-first AI helper for Indian government school teachers.
> Speak in English, Hindi, or Malayalam. Saathi listens, builds the lesson, and puts it on the class screen in seconds.

Built for **Connecting Dreams Foundation, Round 2** (Option A).

---

## Live links (open these)

| Link | What it is |
|---|---|
| **https://frontend-vert-ten-18.vercel.app** | **Main app — open this first.** The landing page, then click "Launch app". |
| https://frontend-vert-ten-18.vercel.app/app.html | **Teacher screen.** Where the teacher speaks or types commands. |
| https://frontend-vert-ten-18.vercel.app/display.html | **Projector screen.** The big clean screen the students see. |
| https://saathi-ai-hfqi.onrender.com/api/health | Backend health check (should say `ok`). Judges don't need this; the app uses it. |
| https://github.com/Nathan-Jamesss/saathi-ai | Source code. |

> First command may take ~30 seconds if the free backend was idle (it shows "Waking the server"). A scheduled ping keeps it awake, so normally it's instant. Best viewed in **Chrome**.

---

## Why are there TWO screens (teacher + projector)?

This is the core idea, so here it is plainly:

- A real classroom has **two displays**: the teacher's laptop, and the projector/smart-board the whole class sees.
- The **teacher screen** (`app.html`) has the controls — the mic, the preview, the buttons. This stays on the teacher's laptop. Students never see the messy control panel.
- The **projector screen** (`display.html`) is clean and huge — just the diagram, the quiz, the timer. No buttons, no clutter. This is dragged onto the projector.

The teacher decides *what* and *when* to show. They preview an answer privately, then tap "Project to class" and it appears on the big screen. They are always in control.

The two screens talk to each other instantly inside the browser (BroadcastChannel) — no internet round-trip needed between them. So when the teacher clicks "Next question", the projector changes immediately.

**In short:** teacher screen = the cockpit, projector screen = what the passengers see.

---

## What happens when a teacher speaks (simple flow)

```
   Teacher speaks: "explain photosynthesis to class 9"
                 |
                 v
   [1] Browser turns voice into text (Web Speech API)
                 |
                 v
   [2] Text sent to the backend
                 |
                 v
   [3] Intent Router (Gemini): "what does the teacher want?"
        -> decides: concept / quiz / translation / activity
                 |
                 v
   [4] RAG: find matching NCERT textbook content (ChromaDB)
                 |
                 v
   [5] Content generation (Gemini): build the answer
        + grab a real image (Wikipedia / Wikimedia)
        + build a diagram (Mermaid)
                 |
                 v
   [6] Answer shown on the TEACHER screen (preview)
                 |
                 v
   [7] Teacher taps "Project to class"
                 |
                 v
   [8] Answer appears BIG on the PROJECTOR screen
```

All of this takes about 3 to 5 seconds. No typing.

---

## The four features

All four are triggered by **just speaking** — no mode switching, no menus.

| # | Say this | What appears |
|---|---|---|
| **1. Live Concept Simplification** | "explain photosynthesis to class 9" | Explanation in simple language + a diagram + a real photo + key points |
| **2. Voice-Triggered Quizzing** | "give me 5 MCQ on photosynthesis" | Quiz questions; teacher reveals answers one by one on the projector |
| **3. Bilingual Dictation & Translation** | "translate to Malayalam: water is essential" | The sentence side by side, English and Malayalam, with pronunciation |
| **4. Hands-Free Activity Guide** | "10 minute group activity on the water cycle" | Step-by-step guide with a countdown timer running on the projector |

**The two required features (Option A): #1 Live Concept Simplification and #2 Voice-Triggered Quizzing.** Features #3 and #4 are built and working as a bonus.

---

## Why this exists

India has around **25 crore** school children but not enough teachers — over **10 lakh** teaching posts lie empty. In many government schools one teacher handles 40 to 60 students at once. There's no time to stop mid-lesson, search, and explain a doubt that's not in the textbook.

Saathi takes that load off. It does the fetch-and-display grunt work in seconds, in the teacher's own language, so the teacher can focus on the part only a human can do.

**It does not replace the teacher. It is a companion that lightens the burden.**

---

## Tech stack

| Layer | Technology |
|---|---|
| Frontend | Vanilla HTML + CSS + JavaScript (no framework), hosted on **Vercel** |
| Backend | Python 3.11 + **FastAPI**, hosted on **Render** |
| AI model | **Gemini 2.5 Flash** (intent routing + content generation) |
| Speech to text | Web Speech API (browser-native) |
| Text to speech | Browser voices (natural, language-matched) with gTTS fallback |
| Knowledge base (RAG) | **ChromaDB** over NCERT Class 6–12 text |
| Embeddings | `gemini-embedding-001` |
| Diagrams | Mermaid.js (client-side) |
| Images | Wikipedia REST + Wikimedia Commons |
| PDF export | jsPDF (client-side) |
| Background visual | Custom WebGL shader (vanilla) |

**Running cost: effectively ₹0** (free tiers + a rotating pool of free API keys).

---

## Prompt design (short version)

- **Intent Router** — Gemini at low temperature (0.1) for accurate classification. Gets session context (grade, subject, language) so it can fill in missing details from natural speech. Handles mixed languages (Hinglish, Manglish). Returns strict JSON.
- **Per-feature generation** — separate prompts, each grounded in retrieved NCERT content, calibrated to the class grade, output in the language the teacher spoke. Technical terms stay in English even in Malayalam/Hindi output (how real teachers talk).

## Localization

Detects the language from the transcript (Unicode range check): Malayalam → `ml-IN`, Devanagari → `hi-IN`, else `en-IN`. The reply, the voice, and the on-screen text all match the language spoken. Noto Sans renders all three scripts.

## Reliability notes

- **7 API keys rotate automatically.** When one hits the free daily quota, the app switches to the next — no downtime mid-demo.
- **Backend kept awake** by a GitHub Action pinging it every 10 minutes, so the free server never sleeps.

---

## Run locally

**Backend**
```bash
cd backend
pip install -r requirements.txt
cp .env.example .env          # add GEMINI_API_KEYS=key1,key2,...
uvicorn main:app --reload --port 8000
```

**Frontend**
```bash
cd frontend
python -m http.server 3000    # open http://localhost:3000
```
The frontend auto-uses `localhost:8000` when run locally, and the live Render backend when deployed.

**Environment variables**

| Variable | What |
|---|---|
| `GEMINI_API_KEYS` | One or more Google AI Studio keys, comma-separated (rotates on quota) |
| `CHROMA_PERSIST_DIR` | ChromaDB path (default `./data/chroma`) |

## Known limitations

1. **Chrome recommended** — Web Speech voice input is Chrome-native. A type-a-command box is provided as a fallback for any browser.
2. **Malayalam TTS** — uses the device's Malayalam voice if present; otherwise a more robotic gTTS fallback.
3. **PDF export** — Indic scripts fall back to transliteration (jsPDF font limitation).
4. **Free-tier quota** — the rotating key pool handles normal demo load; very heavy rapid testing can still exhaust all keys for the day.

---

Built by Nathan James for Connecting Dreams Foundation, Round 2.
