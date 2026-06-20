# Arivu.AI — Full Specification & Requirements Document
## Voice-Enabled AI Teaching Assistant
### Connecting Dreams Foundation — Round 2 Technical Assignment (Option A)

> **Document Status:** FINAL SPEC — ready for implementation  
> **Deadline:** June 20, 2026  
> **Product Name:** Arivu.AI  
> **Malayalam meaning:** Arivu (അറിവ്) = Knowledge  
> **Tagline:** *"Your co-pilot in the classroom."*

---

## Table of Contents

1. [Product Overview](#1-product-overview)
2. [Evaluation Criteria Mapping](#2-evaluation-criteria-mapping)
3. [Architecture Overview](#3-architecture-overview)
4. [Technology Stack (Final Decisions)](#4-technology-stack-final-decisions)
5. [UI/UX Specification](#5-uiux-specification)
6. [Feature Specifications](#6-feature-specifications)
   - 6.1 Live Concept Simplification
   - 6.2 Voice-Triggered Quizzing
   - 6.3 Bilingual Dictation & Translation
   - 6.4 Hands-Free Activity Guide
7. [Shared Pipeline Specification](#7-shared-pipeline-specification)
8. [RAG / Knowledge Base Specification](#8-rag--knowledge-base-specification)
9. [Language & Localization Specification](#9-language--localization-specification)
10. [Session Management](#10-session-management)
11. [API & Prompt Design](#11-api--prompt-design)
12. [File & Folder Structure](#12-file--folder-structure)
13. [Deployment & Hosting](#13-deployment--hosting)
14. [Deliverables Checklist](#14-deliverables-checklist)
15. [Build Sequence & Phases](#15-build-sequence--phases)

---

## 1. Product Overview

### 1.1 What It Is

Arivu.AI is a browser-based, voice-first AI co-pilot for Indian government school teachers. It runs in Chrome on the teacher's classroom laptop, with output projected to a screen, projector, or interactive smart board visible to the whole class.

The teacher speaks naturally in any mix of English, Hindi, or Malayalam. The system listens, understands intent, generates educational content, and displays it on screen — all within 3–5 seconds, no typing required.

### 1.2 What It Is NOT

- **Not a replacement for the teacher.** The teacher stays in charge. The AI prepares and displays material; the teacher decides when and how to use it.
- **Not a replacement for SAMAGRA or NCERT portals.** Those are planned content libraries. Arivu.AI handles the unplanned, spontaneous moments that libraries cannot anticipate.
- **Not an AI that addresses students directly.** All AI output goes to the teacher's screen first. Students see what the teacher projects.

### 1.3 Core Problem Statement

> Indian government school classrooms now have display hardware (projectors, laptops, smart boards). The bottleneck is no longer the screen — it's whether an overloaded teacher can use that screen usefully, on the spot, mid-lesson, in the language they naturally speak, without stopping to type or browse menus.

Arivu.AI solves that bottleneck.

### 1.4 Evaluation Alignment

| Criterion | Weight | How Arivu.AI scores |
|---|---|---|
| Technical | 40% | Shared pipeline, RAG grounding, multilingual STT/TTS, Mermaid diagrams, PDF export |
| Empathy / UX | 30% | Co-pilot framing, dual-mode display, projector-optimized typography, no friction voice UX |
| AI / Prompt Design | 30% | Intent router, grade-calibrated generation, multilingual output, thumbs-down regeneration |

---

## 2. Evaluation Criteria Mapping

### Technical (40%)
- STT → Intent Router → LLM → Renderer → TTS pipeline: fully implemented, not mocked
- RAG grounding against NCERT Class 8–12 corpus: real retrieval, not hardcoded answers
- Mermaid diagram generation rendered client-side (no external image dependency)
- Wikipedia image pre-fetch for enriched concept display
- PDF session export: real jsPDF generation, not a screenshot
- Gemini API integration with Flash model (reliable free-tier throughput)
- Dual-mode UI: teacher control view + full-screen projector-optimized display

### Empathy/UX (30%)
- No mandatory account/login to use the app
- One-click entry from the landing page
- Push-to-talk with spacebar fallback (hands-free for a teacher holding chalk)
- Switchable dark/light theme optimized for projector conditions
- All 4 features accessible from a single voice command — no mode switching required
- "Show to class" optional preview gate reinforces teacher control
- Thumbs up/down feedback loop

### AI/Prompt Design (30%)
- Intent classification from natural multilingual speech (not keyword triggers)
- Grade level inferred from teacher's phrasing, not a manual setting
- Output language mirrors teacher's input language automatically
- Concept explanations calibrated to NCERT syllabus level via RAG
- Quiz questions drawn from NCERT content to ensure curriculum alignment
- Fallback to Gemini's trained knowledge if RAG returns no match

---

## 3. Architecture Overview

```
┌─────────────────────────────────────────────────────────┐
│                   BROWSER (Chrome)                       │
│                                                         │
│  ┌─────────────────────────────────────────────────┐   │
│  │              TEACHER VIEW (Control)              │   │
│  │  • Mic button (push-to-talk / spacebar)         │   │
│  │  • Live transcript display                      │   │
│  │  • AI output preview pane                       │   │
│  │  • Thumbs up/down controls                      │   │
│  │  • "Project to Class" button                    │   │
│  │  • Theme toggle / settings panel                │   │
│  │  • Session history sidebar                      │   │
│  └─────────────────────────────────────────────────┘   │
│                          ↕ (same tab / separate window) │
│  ┌─────────────────────────────────────────────────┐   │
│  │           DISPLAY VIEW (Projector Mode)          │   │
│  │  • Large-font rendered content                  │   │
│  │  • Mermaid diagram / image / MCQ cards / timer  │   │
│  │  • Arivu.AI subtle watermark                    │   │
│  └─────────────────────────────────────────────────┘   │
└─────────────────────────────────────────────────────────┘
         │ Web Speech API (STT)          │ gTTS (TTS)
         │ browser-native                │ via backend
         ▼                               ▼
┌─────────────────────────────────────────────────────────┐
│                BACKEND (FastAPI on Render)               │
│                                                         │
│  POST /api/process   ← receives transcript + session    │
│       ↓                                                 │
│  Intent Router (Gemini Flash)                           │
│       ↓                                                 │
│  ┌──────────┬──────────┬──────────────┬──────────────┐  │
│  │ Feature  │ Feature  │ Feature      │ Feature      │  │
│  │ 1:       │ 2:       │ 3:           │ 4:           │  │
│  │ Concept  │ Quiz     │ Bilingual    │ Activity     │  │
│  │ Simplify │ Generate │ Dictation    │ Guide        │  │
│  └──────────┴──────────┴──────────────┴──────────────┘  │
│       ↓                                                 │
│  RAG Retrieval (ChromaDB, NCERT corpus)                 │
│       ↓                                                 │
│  Content Generation (Gemini Flash)                      │
│       ↓                                                 │
│  Response: { type, content, mermaid?, imageUrl?,        │
│             questions?, steps?, duration? }             │
│                                                         │
│  POST /api/tts   ← text → gTTS audio                   │
│  POST /api/export ← session → PDF                       │
└─────────────────────────────────────────────────────────┘
```

### Data Flow Summary
1. Teacher holds spacebar (or clicks mic button) → Web Speech API records
2. On release → transcript sent to `/api/process` with session context
3. Backend: Intent Router classifies (Gemini Flash) → extracts intent + parameters
4. Backend: RAG retrieves relevant NCERT chunks → injected into content prompt
5. Backend: Gemini Flash generates output in detected language
6. Response JSON returned to frontend → rendered as appropriate UI component
7. Teacher sees preview in control view → optionally sends to projector display
8. On thumbs down → frontend re-calls `/api/process` with `regenerate: true` flag

---

## 4. Technology Stack (Final Decisions)

### 4.1 Why these choices

| Constraint | Decision Made |
|---|---|
| ₹0 running cost | Entire stack is free-tier or browser-native |
| Works on Vercel | Frontend static files on Vercel; Python backend on Render free tier |
| Supports Malayalam/Hindi/English STT | Web Speech API (hi-IN, ml-IN, en-IN) — Chrome native, no API key |
| Real-time classroom use | Gemini Flash (10–15 RPM free tier) — NOT Pro (2–5 RPM, too slow) |
| No touch dependency | Browser app works on laptop + projector without any board-specific APIs |

> **Note on Gemini model choice:** The original plan specified Flash for intent routing + Pro for content generation. After researching free-tier limits, Gemini 2.5 Pro has only 2–5 RPM on the free tier, which would cause 429 errors in a live demo. **Final decision: Gemini 2.5 Flash for both intent routing AND content generation.** Flash is sufficiently capable for this task and has 10–15 RPM — reliable enough for classroom use.

### 4.2 Final Stack Table

| Layer | Technology | Notes |
|---|---|---|
| **Frontend** | Vanilla HTML + CSS + JavaScript | No framework dependency; fast load, full layout control |
| **Backend** | Python 3.11 + FastAPI | Lightweight, async, easy to deploy on Render |
| **LLM** | Gemini 2.5 Flash (Google AI Studio free tier) | Intent routing + content generation + translation |
| **STT** | Web Speech API (browser-native) | `recognition.lang` set dynamically: `hi-IN`, `ml-IN`, `en-IN` |
| **TTS** | gTTS (Python, via `/api/tts` endpoint) | Called when teacher enables audio output |
| **RAG vector store** | ChromaDB (in-memory / persistent local) | Runs inside the FastAPI backend on Render |
| **Embedding model** | `text-embedding-004` (Google, free tier) | For NCERT chunk embeddings |
| **Diagram rendering** | Mermaid.js (CDN, client-side) | No server dependency for diagrams |
| **Image enrichment** | Wikipedia REST API (free) | `https://en.wikipedia.org/api/rest_v1/page/summary/{topic}` |
| **PDF export** | jsPDF (client-side JS library) | Session history → downloadable PDF |
| **Frontend hosting** | Vercel (free tier) | Static files, instant deployment from GitHub |
| **Backend hosting** | Render (free tier, Python) | FastAPI server, persistent ChromaDB |
| **Source control** | GitHub (public repo) | Required deliverable |

### 4.3 Environment Variables Required
```
GEMINI_API_KEY=             # Google AI Studio free API key
CHROMA_PERSIST_DIR=./data/chroma   # ChromaDB storage path on Render
```

---

## 5. UI/UX Specification

### 5.1 Screen Architecture — Dual-Mode Design

**Recommendation (approved):** Two modes within a single browser session.

| Mode | Description | How to Enter |
|---|---|---|
| **Teacher Control View** | Default view. Contains mic, controls, preview pane, history, settings. | Default on page load after session start |
| **Projector Display View** | Full-screen, large-font, no controls visible. This is what students see. | Teacher clicks "Project" button — opens new browser tab/window in full-screen |

Implementation detail: The "Project" button opens `arivu.ai/display?session=<id>` in a new window. The teacher keeps the control view on the laptop screen, drags the display window to the projector output. Both windows communicate via `localStorage` polling or `BroadcastChannel` API (browser-native, no WebSocket needed).

### 5.2 Landing Page

URL: `arivu.ai/` (or Vercel deployment URL)

**Sections:**
1. **Hero** — Product name + tagline + one-line description + CTA button ("Start Teaching →")
2. **Problem** — 2–3 sentences about the real classroom problem (from Section 1.3)
3. **Features** — 4 feature cards (icons + short description each)
4. **How It Works** — 3-step visual: Speak → AI Processes → Projects to Class
5. **Zero Cost Promise** — "₹0 to run. Works in any Chrome browser. No installation."
6. **Footer** — GitHub link, CDF attribution, built by [name]

### 5.3 Session Start Screen

URL: `arivu.ai/app`

A single modal/card overlaying the app:
- **Grade selector** — dropdown: Class 8 / Class 9 / Class 10 / Class 11 / Class 12 (default: Class 10)
- **Subject selector** — dropdown: Science / Mathematics / History / Geography / Political Science / Economics / English (default: Science)
- Note: *"Grade and subject help Arivu.AI calibrate explanations. You can also just say them aloud mid-session and the system will update."*
- **"Begin Session" button** → enters Teacher Control View

> Why a session start screen even though grade is also auto-inferred from speech? It sets a default context so the first command works immediately without the teacher having to state grade. The teacher can override by speaking at any time.

### 5.4 Teacher Control View Layout

```
┌──────────────────────────────────────────────────────┐
│  🎓 Arivu.AI    [Class 10 · Science]   [☀/🌙] [≡]  │  ← Top bar
├──────────────────────────────────────────────────────┤
│                                                      │
│  ┌────────────────────────┐  ┌─────────────────────┐ │
│  │   LIVE TRANSCRIPT      │  │   SESSION HISTORY   │ │
│  │                        │  │                     │ │
│  │  "Explain photosyn-    │  │  09:32 · Concept    │ │
│  │   thesis to class 9"   │  │  09:28 · Quiz       │ │
│  │                        │  │  09:15 · Translate  │ │
│  │  [Language: Malayalam] │  │                     │ │
│  └────────────────────────┘  │  [📄 Export PDF]    │ │
│                               └─────────────────────┘ │
│  ┌──────────────────────────────────────────────────┐ │
│  │              AI OUTPUT PREVIEW                   │ │
│  │                                                  │ │
│  │  [Feature badge: CONCEPT]                        │ │
│  │  Topic: Photosynthesis · Grade: 9 · Lang: ML     │ │
│  │                                                  │ │
│  │  [Mermaid diagram / MCQ cards / dual-text / etc] │ │
│  │                                                  │ │
│  │  👍  👎         [🖥️ Project to Class →]         │ │
│  └──────────────────────────────────────────────────┘ │
│                                                      │
│  ┌──────────────────────────────────────────────────┐ │
│  │   🎤  Hold SPACE or click to speak               │ │
│  │       [████████████████░░░░░░] Recording...      │ │
│  └──────────────────────────────────────────────────┘ │
└──────────────────────────────────────────────────────┘
```

### 5.5 Projector Display View Layout

Full-screen. No controls. Designed for visibility at 8–10 meters.

```
┌──────────────────────────────────────────────────────┐
│                                                      │
│   [Feature badge top-right: CONCEPT / QUIZ / etc]   │
│                                                      │
│         [MAIN CONTENT AREA]                          │
│         • Mermaid diagram (large)                    │
│         • OR: Wikipedia image + text                 │
│         • OR: MCQ cards                              │
│         • OR: Dual-language text panels              │
│         • OR: Steps list + countdown timer           │
│                                                      │
│                                          arivu.ai ·  │
└──────────────────────────────────────────────────────┘
```

Typography specs for projector view:
- Minimum body font: 28px
- Heading font: 48–64px
- Font family: `'Noto Sans'` (covers Devanagari + Malayalam + Latin in one font)
- Line height: 1.6
- High contrast: white text on dark background (dark mode default for projector)
- Malayalam/Devanagari text must render correctly — Noto Sans covers both scripts

### 5.6 Voice Input UX

**Primary:** Hold **Spacebar** → speak → release → processes  
**Secondary:** Click mic button on screen → same behavior  
**Visual feedback:**
- Button/indicator turns red + pulsing animation while recording
- Live waveform or "Recording…" text shown
- On release: "Processing…" spinner
- On response: content appears in preview pane

**Language detection:** `SpeechRecognition` is initialized with `lang = 'hi-IN'` by default. The system will attempt to detect which language was spoken from the transcript text (using Gemini in the intent router prompt). If Malayalam characters appear in a transcript, `lang` is switched to `ml-IN` for the next recognition session. English is always mixed in regardless of `lang` setting.

**Practical note:** The Web Speech API requires the `lang` property set BEFORE starting recognition. The system uses a language detector on the previous transcript to predict the next one's language. On session start, teachers can tap a language indicator to manually override if auto-detection fails.

### 5.7 Themes

| Theme | Background | Text | Primary Accent | Use case |
|---|---|---|---|---|
| **Dark** (projector default) | `#0f1117` | `#f0f0f0` | `#7c6af7` (indigo) | Classroom projection — less glare |
| **Light** (prep/home use) | `#fafafa` | `#1a1a2e` | `#4f46e5` (indigo) | Daytime, bright room |

Theme toggle: Sun/Moon icon top-right. Preference saved to `localStorage`.

### 5.8 Settings Panel (≡ menu)

- **Preview mode toggle** — off by default. When ON, content does not auto-appear in projector view; teacher must click "Project to Class" first.
- **TTS output toggle** — on/off. When on, AI responses are also read aloud via gTTS audio.
- **Language override** — manual override for STT language if auto-detection is struggling.
- **Clear session** — resets all history for a new class.

---

## 6. Feature Specifications

### 6.1 Feature 1 — Live Concept Simplification

**Priority:** Hero Feature (most depth, most polish)

#### Trigger Examples
- "Explain photosynthesis to class 9"
- "Photosynthesis ka matlab kya hai — grade 8 ke liye"
- "Photosynthesisine kurichu class 9 nu explain cheyyuka" (Malayalam)
- "What is osmosis, explain simply"
- "Newton's second law — visual banao"

#### Intent Router Output (JSON)
```json
{
  "intent": "concept_simplification",
  "topic": "photosynthesis",
  "grade": 9,
  "subject": "science",
  "language": "ml",
  "diagram_requested": true
}
```

#### Processing Steps
1. RAG retrieval: query ChromaDB for NCERT chunks matching topic + grade + subject
2. Wikipedia image fetch: `GET https://en.wikipedia.org/api/rest_v1/page/summary/{topic}` → extract `thumbnail.source`
3. Content generation: Gemini Flash with NCERT context injected → returns structured JSON
4. Diagram decision: if concept has clear process/hierarchy → Mermaid; if concrete object → Wikipedia image preferred

#### Gemini Prompt Template (Concept Simplification)
```
You are Arivu.AI, an educational co-pilot for Indian school teachers.

CONTEXT FROM NCERT TEXTBOOK (Class {grade}, {subject}):
{ncert_chunks}

TASK: Generate a classroom explanation of "{topic}" for Class {grade} students.

OUTPUT LANGUAGE: {language} (use natural code-mixing with English for technical terms — this is how Indian teachers actually speak)

OUTPUT FORMAT (strict JSON):
{
  "explanation": "2–3 paragraph explanation in {language}, calibrated to Class {grade} level. Use simple analogies. Technical terms in English are OK and expected.",
  "key_points": ["bullet 1", "bullet 2", "bullet 3", "bullet 4", "bullet 5"],
  "mermaid_diagram": "A valid Mermaid.js flowchart or mindmap diagram string. Use graph TD for processes, mindmap for concept maps. Keep node labels short (max 4 words). Example: graph TD\n A[Sunlight] --> B[Chlorophyll absorbs]\n B --> C[Glucose produced]",
  "analogy": "One memorable real-life analogy in {language}",
  "grade_calibration_note": "One sentence confirming how this is calibrated for Class {grade}"
}

RULES:
- Never include text outside the JSON object
- Mermaid must be syntactically valid (test with simple flowchart first)
- Key points must be in {language}
- Technical terms (photosynthesis, chlorophyll, etc.) stay in English even in Malayalam/Hindi output
- If NCERT context is provided, ground explanation in it; do not contradict syllabus
```

#### UI Component — Concept Display

**Teacher Control View Preview:**
- Feature badge: `CONCEPT · Class 9 · Science · Malayalam`
- Explanation text (scrollable)
- Key points as bullet list
- Mermaid diagram rendered (if valid) OR Wikipedia image (with caption)
- Analogy highlighted in a colored box
- 👍 / 👎 buttons + "Project to Class →"

**Projector Display View:**
- Large heading: topic name
- Mermaid diagram (full width, centered) OR Wikipedia image
- Key points list below (large font)
- Analogy at bottom in italics
- Language watermark: "Class 9 · Science · Arivu.AI"

#### Fallback Behavior
- If Mermaid parse fails → show explanation text only, no diagram
- If Wikipedia image returns 404 → show no image (graceful)
- If RAG returns no matches → Gemini uses its own knowledge + adds disclaimer: "[Generated from general knowledge — verify with NCERT textbook]"

---

### 6.2 Feature 2 — Voice-Triggered Quizzing

**Priority:** Hero Feature

#### Trigger Examples
- "Give me 5 MCQ on photosynthesis"
- "3 true false questions on Newton's laws"
- "2 short answer questions on the French Revolution"
- "Quiz banao — 5 MCQ — chapter 3"
- "Photosynthesisninte quiz — 5 MCQ" (Malayalam)
- "Now quiz the class on this topic"

#### Intent Router Output (JSON)
```json
{
  "intent": "quiz_generation",
  "topic": "photosynthesis",
  "grade": 9,
  "subject": "science",
  "language": "ml",
  "quiz_type": "mcq",
  "question_count": 5
}
```

**Quiz type parsing:**
- "MCQ" / "multiple choice" → `mcq` (4 options each)
- "True/False" / "True ya False" / "sathyasandham" → `true_false`
- "Short answer" / "short question" / "oru vaakya" → `short_answer`
- Default (no type mentioned) → `mcq`, count = 5

#### Gemini Prompt Template (Quiz)
```
You are Arivu.AI, an educational co-pilot for Indian school teachers.

CONTEXT FROM NCERT TEXTBOOK (Class {grade}, {subject}):
{ncert_chunks}

TASK: Generate {count} {quiz_type} questions on "{topic}" for Class {grade}.

OUTPUT LANGUAGE: {language} (technical terms stay in English)

OUTPUT FORMAT (strict JSON):
{
  "questions": [
    {
      "number": 1,
      "question": "question text in {language}",
      "type": "mcq",
      "options": ["A) ...", "B) ...", "C) ...", "D) ..."],
      "correct_answer": "A",
      "explanation": "one sentence explanation of correct answer in {language}"
    }
  ],
  "topic": "{topic}",
  "grade": {grade},
  "total_questions": {count}
}

For true_false: omit "options", set correct_answer to "True" or "False"
For short_answer: omit "options" and "correct_answer", include "model_answer" instead

RULES:
- Questions must be curriculum-appropriate for Class {grade}
- Ground in NCERT context if provided
- Mix difficulty: 2 easy, 2 medium, 1 hard (for 5 questions)
- Never duplicate questions from the same session (session history provided below)
```

#### UI Component — Quiz Display

**Teacher Control View Preview:**
- Feature badge: `QUIZ · 5 MCQ · Class 9 · Science`
- All 5 question cards shown (compact view)
- Each card: question text + options (answers hidden by default)
- "Show answers" toggle per card (teacher reveals when ready)
- 👍 / 👎 + "Project to Class →"

**Projector Display View:**
- Shows questions ONE AT A TIME
- Large question number + question text
- Options listed (A, B, C, D) without answer highlighted
- "Next Question" button (teacher clicks on laptop — pushes to display via BroadcastChannel)
- After teacher clicks "Reveal Answer" → correct option highlighted in green
- Bottom progress: "Question 2 of 5"

#### State Management for Quiz
```javascript
// Quiz state object
{
  questions: [...],
  currentIndex: 0,
  revealed: [false, false, false, false, false],
  mode: 'projector' | 'preview'
}
```
BroadcastChannel message types: `NEXT_QUESTION`, `REVEAL_ANSWER`, `RESET_QUIZ`

---

### 6.3 Feature 3 — Bilingual Dictation & Translation

**Priority:** Functional (complete but lighter polish)

#### Trigger Examples
- "Translate: The mitochondria is the powerhouse of the cell"
- "Yeh sentence Malayalam mein likhke dikao: Water is composed of hydrogen and oxygen"
- "Translate this: [teacher dictates the sentence]"
- "Ee vaakyam Malayalam il kaanikkuka: [sentence]"

#### How Input Works
The teacher speaks the command AND the sentence to be translated in one utterance:
- Pattern: `[translate command] [colon / pause] [sentence]`
- The intent router extracts both the command intent and the sentence content from the full transcript

#### Intent Router Output (JSON)
```json
{
  "intent": "bilingual_translation",
  "source_text": "The mitochondria is the powerhouse of the cell",
  "source_language": "en",
  "target_language": "ml",
  "display_mode": "side_by_side"
}
```

Target language logic:
- If teacher speaks in English → translate to session language (Malayalam or Hindi)
- If teacher speaks in Malayalam → translate to English
- If teacher speaks in Hindi → translate to English and/or Malayalam depending on session language

#### Gemini Prompt Template (Translation)
```
You are Arivu.AI, a bilingual educational assistant for Indian classrooms.

TASK: Translate the following text accurately.
SOURCE TEXT: {source_text}
SOURCE LANGUAGE: {source_language}
TARGET LANGUAGE: {target_language}

OUTPUT FORMAT (strict JSON):
{
  "original_text": "{source_text}",
  "original_language": "{source_language}",
  "translated_text": "accurate translation in {target_language}",
  "target_language": "{target_language}",
  "transliteration": "romanized pronunciation guide for non-native speakers (optional, only for Malayalam output)",
  "notes": "any translation notes (e.g., 'mitochondria has no standard Malayalam word — kept as-is')"
}

RULES:
- Scientific/technical terms with no standard translation → keep in English
- Provide transliteration only for Malayalam output (helps teachers pronounce)
- Keep sentence structure natural in the target language — not word-for-word
```

#### UI Component — Bilingual Display

**Teacher Control View Preview:**
- Feature badge: `TRANSLATE · English → Malayalam`
- Two text boxes side by side: left = original, right = translated
- Transliteration shown below Malayalam text in gray italic
- Translation notes (if any) in a small info box
- 👍 / 👎 + "Project to Class →"

**Projector Display View:**
- Two large panels, side by side
- Left panel: Original text (large font, language label at top)
- Right panel: Translated text (large font, language label at top)
- Transliteration below right panel
- Both panels use `font-family: 'Noto Sans'` for correct script rendering

---

### 6.4 Feature 4 — Hands-Free Activity Guide

**Priority:** Functional (complete but lighter polish)

#### Trigger Examples
- "Start a 10-minute group activity on the water cycle"
- "Give me a 5-minute pair activity on Newton's laws"
- "Activity shuru karo — 8 minutes — French Revolution discussion"
- "10 minute koottam activity — photosynthesis" (Malayalam)

#### Intent Router Output (JSON)
```json
{
  "intent": "activity_guide",
  "topic": "water cycle",
  "grade": 9,
  "subject": "science",
  "language": "ml",
  "duration_minutes": 10,
  "activity_type": "group"
}
```

Activity type parsing:
- "group" / "koottam" → group activity (4–6 students)
- "pair" / "jodi" → pair activity (2 students)
- "individual" → individual task
- Default → group activity

#### Gemini Prompt Template (Activity Guide)
```
You are Arivu.AI, an educational co-pilot for Indian school teachers.

TASK: Generate a classroom activity guide on "{topic}" for Class {grade} students.
DURATION: {duration_minutes} minutes
ACTIVITY TYPE: {activity_type}
OUTPUT LANGUAGE: {language}

OUTPUT FORMAT (strict JSON):
{
  "activity_title": "Title of the activity in {language}",
  "topic": "{topic}",
  "duration_minutes": {duration_minutes},
  "activity_type": "{activity_type}",
  "steps": [
    {
      "step_number": 1,
      "title": "Short step title in {language}",
      "instruction": "Clear instruction for students in {language}",
      "duration_seconds": 120,
      "teacher_note": "Optional hint for teacher (in English for clarity)"
    }
  ],
  "materials_needed": ["list of materials, if any"],
  "expected_outcome": "What students should have learned/produced"
}

RULES:
- Steps must sum to exactly {duration_minutes} minutes total
- Each step should be concrete and actionable (not vague)
- Step instructions written FOR students (direct), teacher_notes written FOR teacher
- No special materials required beyond chalk, paper, textbook
- Maximum 6 steps (keep it simple for one-class-period)
```

#### UI Component — Activity Guide Display

**Teacher Control View Preview:**
- Feature badge: `ACTIVITY · 10 min · Group · Class 9`
- Step list (compact cards): step number + title + duration
- Timer control: "Start Timer" button
- 👍 / 👎 + "Project to Class →"

**Projector Display View:**
- Top: Activity title + "Group Activity — 10 minutes"
- Center: Current step card (large) — step number, title, full instruction
- Bottom-left: Step progress indicator (Step 2 of 5)
- Bottom-right: Countdown timer (MM:SS format, large font)
- Timer behavior:
  - Starts when teacher clicks "Start" in control view (via BroadcastChannel)
  - Counts down for current step's duration
  - On step complete: timer pauses, next step card slides in, teacher advances manually
  - At 0:00 on final step: "Activity Complete! 🎉" message shown

Timer State Object:
```javascript
{
  steps: [...],
  currentStep: 0,
  timeRemaining: 120, // seconds
  running: false,
  complete: false
}
```

---

## 7. Shared Pipeline Specification

### 7.1 Intent Router — Detailed

The intent router is a Gemini Flash call that takes the raw transcript and session context and returns a structured classification.

**Input to intent router:**
```json
{
  "transcript": "Explain photosynthesis to class 9 in Malayalam",
  "session_context": {
    "current_grade": 10,
    "current_subject": "science",
    "previous_topic": "cell biology",
    "session_language": "ml"
  }
}
```

**Intent Router Prompt:**
```
You are the intent router for Arivu.AI, a voice-controlled educational assistant for Indian teachers.

AVAILABLE INTENTS:
1. concept_simplification — teacher wants an explanation of a concept with a visual
2. quiz_generation — teacher wants quiz questions generated
3. bilingual_translation — teacher wants text translated and displayed in two languages
4. activity_guide — teacher wants a timed classroom activity generated
5. unclear — cannot determine intent

SESSION CONTEXT:
Current grade: {current_grade}
Current subject: {current_subject}
Previous topic: {previous_topic}
Session language: {session_language}

TRANSCRIPT: "{transcript}"

Detect the language spoken. Infer grade and subject from transcript if stated; otherwise use session defaults.

OUTPUT (strict JSON, no other text):
{
  "intent": "concept_simplification | quiz_generation | bilingual_translation | activity_guide | unclear",
  "topic": "extracted topic or null",
  "grade": number or null,
  "subject": "extracted subject or null",
  "language": "en | hi | ml",
  "confidence": 0.0–1.0,
  "quiz_type": "mcq | true_false | short_answer | null",
  "question_count": number or null,
  "source_text": "text to translate (if bilingual_translation) or null",
  "duration_minutes": number or null,
  "activity_type": "group | pair | individual | null",
  "additional_params": {}
}
```

**Fallback:** If `intent = "unclear"` or `confidence < 0.5`, frontend shows: *"I didn't quite catch that. Try: 'Explain [topic] to Class [grade]' or 'Give me 5 MCQ on [topic]'"*

### 7.2 API Endpoint Specification

#### `POST /api/process`
**Request:**
```json
{
  "transcript": "string",
  "session": {
    "grade": 9,
    "subject": "science",
    "language": "ml",
    "previous_topic": "cell biology",
    "history": ["previous topic 1", "previous topic 2"]
  },
  "regenerate": false
}
```
**Response:**
```json
{
  "intent": "concept_simplification",
  "detected_language": "ml",
  "topic": "photosynthesis",
  "grade": 9,
  "content": {
    "explanation": "...",
    "key_points": [...],
    "mermaid_diagram": "graph TD\n A --> B",
    "analogy": "...",
    "wikipedia_image_url": "https://...",
    "wikipedia_image_caption": "..."
  },
  "timestamp": "2026-06-12T09:30:00Z",
  "session_id": "abc123"
}
```

#### `POST /api/tts`
**Request:** `{ "text": "string", "language": "ml | hi | en" }`  
**Response:** Audio file (MP3) stream  
**Library:** `gTTS(text, lang='ml')` → returns audio bytes

#### `POST /api/export`
**Request:** `{ "session": { "history": [...] } }`  
**Response:** JSON with session data; PDF generation happens client-side using jsPDF

#### `GET /api/health`
**Response:** `{ "status": "ok", "chroma_ready": true, "gemini_ready": true }`

---

## 8. RAG / Knowledge Base Specification

### 8.1 Corpus

**Primary:** NCERT textbooks, Classes 8–12  
**Subjects to index:** Science, Mathematics, History (Social Science), Geography, Political Science, Economics, English (core grammar concepts)  
**Source:** Download from `ncert.nic.in/textbook.php` (official, free) OR use `KadamParth/Ncert_dataset` on HuggingFace (Classes 6–12, pre-extracted text)

> **Recommended:** HuggingFace dataset `KadamParth/Ncert_dataset` — text already extracted, no PDF parsing needed. Verify coverage before indexing.

**SAMAGRA portal:** Assess if content is freely downloadable during implementation. If not, skip for V1 — NCERT covers the curriculum adequately.

### 8.2 Chunking Strategy

```
1. Split each chapter into chunks of ~500 tokens
2. Overlap: 50 tokens between chunks (for context continuity)
3. Metadata per chunk:
   {
     "class": 9,
     "subject": "science",
     "chapter": "Cell — The Unit of Life",
     "chapter_number": 5,
     "book": "NCERT Science Class 9",
     "text": "..."
   }
```

### 8.3 Embedding & Storage

```python
# Embedding model
from google.generativeai import embed_content

def embed(text):
    result = embed_content(
        model="models/text-embedding-004",
        content=text,
        task_type="retrieval_document"
    )
    return result['embedding']

# ChromaDB collection
collection = chroma_client.create_collection(
    name="ncert_corpus",
    metadata={"hnsw:space": "cosine"}
)
```

### 8.4 Retrieval

```python
def retrieve(query, grade, subject, n_results=5):
    query_embedding = embed(query)
    results = collection.query(
        query_embeddings=[query_embedding],
        n_results=n_results,
        where={"$and": [{"class": grade}, {"subject": subject}]}
    )
    return results['documents'][0]  # list of chunk texts
```

### 8.5 Indexing Script

Location: `backend/scripts/build_index.py`  
Run once at deployment setup or via Render build hook.  
Estimated index size: ~50MB for Classes 8–12 across 7 subjects.  
Estimated build time: ~15 minutes (with free-tier embedding rate limits).

---

## 9. Language & Localization Specification

### 9.1 Supported Languages

| Language | BCP-47 Code | Web Speech API | gTTS | Gemini |
|---|---|---|---|---|
| English (Indian) | `en-IN` | ✅ | ✅ | ✅ |
| Hindi | `hi-IN` | ✅ | ✅ (`hi`) | ✅ |
| Malayalam | `ml-IN` | ✅ | ✅ (`ml`) | ✅ |

### 9.2 Language Auto-Detection Logic

```javascript
function detectLanguage(transcript) {
  // Check for Malayalam Unicode range: 0D00–0D7F
  const malayalamPattern = /[\u0D00-\u0D7F]/;
  // Check for Devanagari (Hindi) Unicode range: 0900–097F
  const hindiPattern = /[\u0900-\u097F]/;
  
  if (malayalamPattern.test(transcript)) return 'ml';
  if (hindiPattern.test(transcript)) return 'hi';
  return 'en';
}
```

If Malayalam characters detected in transcript → next recognition session uses `lang = 'ml-IN'`.  
If Devanagari detected → `lang = 'hi-IN'`.  
Otherwise → `lang = 'en-IN'`.

The `lang` setting for Web Speech API affects the recognition language. Code-mixing (Hinglish, Manglish) is handled on the Gemini side — the intent router is explicitly prompted to handle mixed-language input.

### 9.3 Output Language Rules

- AI output language = language detected in teacher's input
- Technical/scientific terms remain in English regardless of output language
- Malayalam output uses Noto Sans Malayalam for correct script rendering
- Hindi output uses Noto Sans Devanagari

### 9.4 Font Loading

```html
<link rel="preconnect" href="https://fonts.googleapis.com">
<link href="https://fonts.googleapis.com/css2?family=Noto+Sans:wght@400;600;700&family=Noto+Sans+Malayalam:wght@400;600;700&family=Noto+Sans+Devanagari:wght@400;600;700&display=swap" rel="stylesheet">
```

CSS font stack:
```css
body {
  font-family: 'Noto Sans', 'Noto Sans Malayalam', 'Noto Sans Devanagari', sans-serif;
}
```

---

## 10. Session Management

### 10.1 Session Object (localStorage)

```javascript
const session = {
  id: "uuid-v4",
  startedAt: "ISO timestamp",
  grade: 10,
  subject: "science",
  language: "ml",
  history: [
    {
      timestamp: "ISO timestamp",
      intent: "concept_simplification",
      topic: "photosynthesis",
      transcript: "...",
      response: { ... },
      rating: 1  // 1 = thumbs up, -1 = thumbs down, 0 = no rating
    }
  ]
}
```

### 10.2 Session History UI

- Right sidebar in Teacher Control View
- Each entry: `[time] · [Feature type] · [Topic]`
- Click an entry → re-loads that output in the preview pane
- "Export PDF" button at bottom of history

### 10.3 PDF Export

Using `jsPDF` (client-side JavaScript library, CDN):
```javascript
function exportSession(session) {
  const doc = new jsPDF();
  doc.setFont("helvetica");
  doc.text(`Arivu.AI Session — ${session.startedAt}`, 10, 10);
  doc.text(`Grade: ${session.grade} | Subject: ${session.subject}`, 10, 20);
  
  session.history.forEach((item, i) => {
    doc.addPage();
    doc.text(`${i+1}. ${item.intent} — ${item.topic}`, 10, 20);
    // Add content based on intent type
  });
  
  doc.save(`arivu-session-${session.id}.pdf`);
}
```

> **Note on Indic script in PDF:** jsPDF's default helvetica font does not support Malayalam/Devanagari. For V1: export English content and transliterations in the PDF. Malayalam/Hindi text in the session → exported as romanized transliteration with a note. Mark this as a known limitation in README.

### 10.4 Thumbs Up / Down

- 👎 (thumbs down) → frontend re-calls `/api/process` with `regenerate: true`
- Backend adds `regenerate: true` to the prompt: "The previous response was rated unsatisfactory. Generate a different, improved response."
- If rated 👎 twice on same topic → add note in response: "Try being more specific — e.g., say 'explain photosynthesis light reactions to class 10'"

---

## 11. API & Prompt Design

### 11.1 Gemini API Configuration

```python
import google.generativeai as genai

genai.configure(api_key=os.environ["GEMINI_API_KEY"])

# Intent router — needs to be fast
intent_model = genai.GenerativeModel(
    model_name="gemini-2.5-flash",
    generation_config={
        "temperature": 0.1,  # low temp for classification
        "response_mime_type": "application/json"
    }
)

# Content generation — needs to be creative but accurate
content_model = genai.GenerativeModel(
    model_name="gemini-2.5-flash",
    generation_config={
        "temperature": 0.4,
        "response_mime_type": "application/json",
        "max_output_tokens": 2048
    }
)
```

### 11.2 Rate Limiting Strategy

Gemini 2.5 Flash free tier: ~10–15 RPM.
A typical classroom session: 1 command every 2–3 minutes.  
Peak: teacher demos quickly → max 3–4 calls/minute.  
This is well within free-tier limits for demo use.

Implement basic retry with exponential backoff:
```python
import time

def call_gemini_with_retry(prompt, max_retries=3):
    for attempt in range(max_retries):
        try:
            return content_model.generate_content(prompt)
        except Exception as e:
            if "429" in str(e) and attempt < max_retries - 1:
                time.sleep(2 ** attempt)  # 1s, 2s, 4s
            else:
                raise
```

### 11.3 JSON Response Validation

All Gemini responses are expected as JSON (using `response_mime_type: application/json`). Still validate:
```python
import json

def safe_parse_json(response_text):
    try:
        return json.loads(response_text)
    except json.JSONDecodeError:
        # Strip markdown code blocks if Gemini added them
        cleaned = response_text.strip().removeprefix("```json").removesuffix("```").strip()
        return json.loads(cleaned)
```

### 11.4 Wikipedia Image Fetch

```python
import httpx

async def fetch_wikipedia_image(topic: str) -> dict:
    url = f"https://en.wikipedia.org/api/rest_v1/page/summary/{topic.replace(' ', '_')}"
    async with httpx.AsyncClient() as client:
        r = await client.get(url, timeout=5.0)
        if r.status_code == 200:
            data = r.json()
            return {
                "image_url": data.get("thumbnail", {}).get("source"),
                "caption": data.get("description", ""),
                "extract": data.get("extract", "")[:300]
            }
    return {"image_url": None, "caption": None, "extract": None}
```

---

## 12. File & Folder Structure

```
arivu-ai/
├── README.md                    # Public-facing README (deliverable)
├── SPEC.md                      # This document
├── RESEARCH.md                  # Research notes
│
├── frontend/                    # Deployed to Vercel
│   ├── index.html               # Landing page
│   ├── app.html                 # Main app (Teacher Control View)
│   ├── display.html             # Projector Display View
│   ├── css/
│   │   ├── main.css             # Design system + variables
│   │   ├── landing.css          # Landing page styles
│   │   ├── app.css              # Teacher view styles
│   │   └── display.css          # Projector view styles
│   ├── js/
│   │   ├── stt.js               # Web Speech API wrapper
│   │   ├── session.js           # Session state management
│   │   ├── api.js               # Backend API calls
│   │   ├── renderer.js          # Component rendering (Mermaid, MCQ, etc.)
│   │   ├── broadcast.js         # BroadcastChannel for control↔display sync
│   │   ├── export.js            # jsPDF session export
│   │   └── app.js               # Main app controller
│   └── assets/
│       └── logo.svg             # Arivu.AI logo
│
├── backend/                     # Deployed to Render
│   ├── main.py                  # FastAPI app entrypoint
│   ├── requirements.txt
│   ├── .env.example
│   ├── api/
│   │   ├── process.py           # POST /api/process
│   │   ├── tts.py               # POST /api/tts
│   │   ├── export.py            # POST /api/export (session data)
│   │   └── health.py            # GET /api/health
│   ├── core/
│   │   ├── intent_router.py     # Gemini Flash intent classification
│   │   ├── concept.py           # Feature 1: Concept Simplification
│   │   ├── quiz.py              # Feature 2: Quiz Generation
│   │   ├── translation.py       # Feature 3: Bilingual Translation
│   │   ├── activity.py          # Feature 4: Activity Guide
│   │   ├── rag.py               # ChromaDB retrieval
│   │   └── wikipedia.py         # Wikipedia image fetch
│   ├── prompts/
│   │   ├── intent_router.txt
│   │   ├── concept_simplification.txt
│   │   ├── quiz_generation.txt
│   │   ├── translation.txt
│   │   └── activity_guide.txt
│   └── scripts/
│       ├── build_index.py       # NCERT corpus → ChromaDB index
│       └── download_ncert.py    # Download NCERT PDFs from HuggingFace
│
└── data/                        # NCERT corpus + ChromaDB (backend, Render disk)
    ├── ncert/                   # Raw NCERT text chunks (JSON)
    └── chroma/                  # ChromaDB persistent storage
```

---

## 13. Deployment & Hosting

### 13.1 Frontend — Vercel

1. Push `frontend/` to GitHub
2. Connect repo to Vercel
3. Set output directory: `frontend/`
4. No build step required (pure HTML/CSS/JS)
5. Set environment variable: `VITE_BACKEND_URL=https://arivu-ai-backend.onrender.com`
6. Actually: since no build step, inject backend URL as a JS constant in `api.js`

**Vercel config (`vercel.json`):**
```json
{
  "rewrites": [
    { "source": "/app", "destination": "/app.html" },
    { "source": "/display", "destination": "/display.html" }
  ]
}
```

### 13.2 Backend — Render

1. Push `backend/` to GitHub
2. Create new Render Web Service
3. Runtime: Python 3.11
4. Build command: `pip install -r requirements.txt && python scripts/build_index.py`
5. Start command: `uvicorn main:app --host 0.0.0.0 --port $PORT`
6. Set environment variables: `GEMINI_API_KEY`, `CHROMA_PERSIST_DIR=/opt/render/project/src/data/chroma`
7. Free tier: 512MB RAM, spins down after 15 min inactivity (cold start ~30s)

**CORS config in FastAPI:**
```python
from fastapi.middleware.cors import CORSMiddleware

app.add_middleware(
    CORSMiddleware,
    allow_origins=["https://arivu-ai.vercel.app", "http://localhost:3000"],
    allow_methods=["*"],
    allow_headers=["*"]
)
```

### 13.3 Render Cold Start Warning

Free-tier Render services sleep after 15 minutes of inactivity. Cold start takes ~25–35 seconds. 

**Mitigation for demo:** Add a "Wake up server" call that the landing page makes on load (`GET /api/health`). Show a "Warming up... (~20s)" message on the landing page if the health check takes >5s.

---

## 14. Deliverables Checklist

| Deliverable | Spec Reference | Done? |
|---|---|---|
| Live URL | Vercel deployment | [ ] |
| Public GitHub repo | All code, public | [ ] |
| README.md | See format below | [ ] |
| Video walkthrough (max 3 mins) | See Section 1.4 for script | [ ] |

### 14.1 README.md Required Sections (per CDF brief)

```markdown
# Arivu.AI — Voice-Enabled AI Teaching Assistant

## What it is
## Live Demo
## Tech Stack
## Architecture Diagram
## Prompt Design (explain intent router + content prompts)
## Localization (explain multilingual support: hi-IN, ml-IN, en-IN)
## How to run locally
## Environment variables
## Known limitations
## Built for: Connecting Dreams Foundation Round 2
```

### 14.2 Video Script (3 minutes)

| Time | Content |
|---|---|
| 0:00–0:20 | Problem hook: "Every day, an Indian teacher faces a question they can't answer in the class language, mid-lesson, with no time to search." |
| 0:20–0:50 | Demo: Concept Simplification — teacher speaks, Mermaid diagram appears, "Project to Class" |
| 0:50–1:20 | Demo: Quiz — same topic, "Give me 5 MCQ", cards appear, answer reveal |
| 1:20–1:40 | Demo: Translation — teacher dictates, side-by-side bilingual display |
| 1:40–2:00 | Demo: Activity Guide — 10-minute activity, timer starts |
| 2:00–2:30 | Architecture: one pipeline, four features, Gemini Flash, NCERT RAG, ₹0 cost |
| 2:30–3:00 | CDF alignment: "Arivu.AI doesn't replace the teacher — it gives them 10 more minutes of teaching time in every class." |

---

## 15. Build Sequence & Phases

Build in this exact order. Each phase produces something testable before the next phase begins.

### Phase 1 — Foundation (Day 1–2)
- [ ] Create GitHub repo `arivu-ai`, public
- [ ] Set up folder structure (Section 12)
- [ ] Build landing page (`index.html`) — static, no backend needed
- [ ] Build session start screen modal
- [ ] Implement Web Speech API wrapper (`stt.js`) — test with console.log
- [ ] Set up FastAPI skeleton with health endpoint
- [ ] Deploy both to Vercel (frontend) + Render (backend) — get live URLs early
- [ ] Verify: can open URL, see landing page, click to app, press spacebar, see transcript in console

### Phase 2 — Shared Pipeline (Day 2–3)
- [ ] Implement intent router (`intent_router.py`) — test with 20 sample transcripts
- [ ] Implement `/api/process` endpoint (routes to placeholder handlers initially)
- [ ] Build `api.js` frontend module — send transcript, receive JSON
- [ ] Build basic `renderer.js` — displays raw JSON for now
- [ ] Test: speak → transcript → intent classified → JSON returned → displayed raw

### Phase 3 — RAG Index (Day 3)
- [ ] Download NCERT corpus (HuggingFace dataset or manual download for 3–4 subjects)
- [ ] Write and run `build_index.py` — chunk, embed, store in ChromaDB
- [ ] Implement `rag.py` retrieval function
- [ ] Test: query "photosynthesis" → returns relevant NCERT chunks

### Phase 4 — Hero Features (Day 4–5)
- [ ] Implement Feature 1: Concept Simplification (`concept.py` + Mermaid renderer + Wikipedia fetch)
- [ ] Implement Feature 2: Quiz Generation (`quiz.py` + MCQ card UI + BroadcastChannel reveal)
- [ ] Build projector display view (`display.html`) — BroadcastChannel connection working
- [ ] Test full flow: speak concept → diagram on projector / speak quiz → cards on projector

### Phase 5 — Functional Features (Day 5–6)
- [ ] Implement Feature 3: Bilingual Translation (`translation.py` + dual-pane UI)
- [ ] Implement Feature 4: Activity Guide (`activity.py` + countdown timer UI)
- [ ] Test all 4 features end-to-end with Malayalam and Hindi input

### Phase 6 — Polish & UX (Day 6–7)
- [ ] Dark/light theme toggle
- [ ] Session history sidebar
- [ ] Thumbs up/down + regeneration
- [ ] PDF export (jsPDF)
- [ ] gTTS integration for TTS
- [ ] Render cold-start warm-up call from landing page
- [ ] Mobile-responsive landing page
- [ ] Projector typography tuning (font size, contrast, Noto Sans)

### Phase 7 — Deliverables (Day 7–8)
- [ ] Write README.md (all required sections)
- [ ] Final deployment check: Vercel + Render both live, CORS clean
- [ ] Record 3-minute video walkthrough
- [ ] Submit GitHub repo + live URL

---

*Document prepared: June 2026*  
*Stack: Gemini 2.5 Flash · ChromaDB · FastAPI · Vercel · Render · Web Speech API · gTTS · Mermaid.js · jsPDF*  
*Total running cost: ₹0*
