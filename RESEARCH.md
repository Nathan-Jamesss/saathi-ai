# Project Research & Planning Document
## Connecting Dreams Foundation — Round 2 Technical Assignment
### Option A: Voice-Enabled AI Teaching Assistant

---

## 1. The Assignment (Original Brief, As-Is)

> **Connecting Dreamyes Foundation Round 2 — Technical Assignment**
> Build practical, human-centered AI tools that solve real-world problems.
>
> CDF is looking for talented builders to develop practical, human-centered digital solutions. This round is a project-based assignment designed to validate your ability to build functional AI-based tools that solve grassroots challenges.

### Option A — Voice-Enabled AI Teaching Assistant

> **Context:** A teacher in a Haryana government school needs a hands-free AI co-pilot for live classroom sessions. The school has a smart board; students speak a mix of Hindi and English (Hinglish).
>
> **Task:** Build a voice-based prototype that generates educational support via voice commands and projects visuals on the smart board.
>
> **Requirements (Choose 2):**
> - Live Concept Simplification — Conversational Hinglish explanation with projected visuals.
> - Voice-Triggered Quizzing — Verbal quiz announcements with visual display.
> - Bilingual Dictation & Translation — Transcribe/translate textbook content and display both.
> - Hands-Free Activity Guide — Verbal instructions with on-screen timer/guide.

### Option B — Multilevel Natural Farming Consultant (not pursued)

> **Context:** Farmers transitioning to natural farming need instant access to organic pest control, crop rotation, seed selection, finances, weather and market intelligence via a voice-first mobile interface.
>
> **Task:** Build a functional prototype of a Voice-Based Natural Farming Consultant.
>
> **Requirements (Choose 2):**
> - Disease Identification & Treatment — Identify issues and suggest organic remedies.
> - Seed & Financial Guidance — Planting recommendations and government subsidy info.
> - Weather & Market Intelligence — Real-time/dummy regional weather and crop market prices.
> - Natural Farming Education — Explain multilevel cropping strategies.

### Common Guidelines

> **Technical Constraints:** STT/TTS audio pipeline; simple web interface (Streamlit, Gradio) optimized for smart board or mobile; RAG or strict prompt guardrails for farming accuracy.
>
> **Deliverables:** Live URL · Public GitHub repo · README (tech stack, prompt design, localization) · Video walkthrough (max 3 mins).
>
> **Deadline:** June 20 | **Evaluation:** Technical 40% · Empathy/UX 30% · AI/Prompt 30%

**Decision: Pursuing Option A.** Two features were initially considered (per the "Choose 2" instruction), but the team is attempting all four as a single shared pipeline with two "hero" (deep-polish) features and two "lighter" (functional) features — see Section 6.

---

## 2. Who Is Connecting Dreams Foundation (CDF)?

### 2.1 Organization basics

- **Legal status:** [Connecting Dreams Foundation](https://www.connecting-dreams.org/) is a non-profit registered and licensed under Section 25 of the Companies Act, 1956, Government of India.
- **Headquarters:** #196 F, 2nd Floor, Savitri Nagar, near Panchsheel Park Metro Station, Delhi - 110012, India.
- **Contact:** info@connecting-dreams.org · +91 9899748528
- **LinkedIn:** [linkedin.com/company/connecting-dreams-foundation](https://www.linkedin.com/company/connecting-dreams-foundation/about/) (~10,745 followers)
- **Tagline:** "Connecting 10 Million SDG Dreams by 2025"
- **Mandate:** To architect social transformational interventions and campaigns using technology that create positive impact across the globe.
- **Mission/Vision (CDF chapters):** Empowerment of youth and women in rural India through Connectivity and Entrepreneurship; bridging the gap between rural and urban India through sustainable business models.
- **Key recurring people:** Amit Tuteja, Simi Mishra (appear across most CDF programs, posts, and chapters).
- **Operating model:** Works through college/university chapters (e.g., SRCC, SBSC, Ramjas) and field programs across the 17 UN Sustainable Development Goals (SDGs).

### 2.2 Track record / scale (from CDF's own website)

- 13+ Years of Trust & Impact
- 27 Lakh+ lives positively impacted through trained leaders
- 50+ schools or institutions engaged
- 1,25,000+ grassroots leaders trained across rural India
- 100+ partners and institutions
- 250+ rural changemakers supported

### 2.3 "The Need" — CDF's own framing of India's problems

CDF frames India's development challenge as fundamentally a **leadership challenge**, broken into six areas:

| Area | Stated Problem |
|---|---|
| **Schools** | Learning outcomes and life skills gaps limit future readiness. |
| **Youth** | Millions lack access to opportunities, mentorship and purpose. |
| **Enterprises** | Livelihoods need innovation, markets and business resilience. |
| **Panchayats** | Local governance needs stronger participation and planning. |
| **Climate** | Communities face climate risks without enough local solutions. |
| **NGOs** | Grassroots organizations need capacity, tools and networks. |

### 2.4 What CDF Does — Four Leadership Verticals

1. **Education and Future Leadership** — Building confident, ethical and future-ready young leaders.
2. **Enterprise and Livelihood Leadership** — Strengthening livelihoods and enterprises for inclusive growth.
3. **Rural Leadership and Governance** — Empowering communities and panchayats for participatory development.
4. **Climate and Sustainability Leadership** — Promoting climate resilience and sustainable living solutions.

### 2.5 Operating Philosophy — 3C and 5C Models

**3C Model:**
1. **Collect Dreams** — Listen deeply and understand real needs.
2. **Create Solutions** — Co-create practical, local and scalable solutions.
3. **Change Lives** — Empower changemakers to create lasting impact.

**5C Model** (expanded version):
1. **Clarify Vision** — Define purpose and priorities.
2. **Collect Dreams** — Engage and listen widely.
3. **Create Solutions** — Design and test local solutions.
4. **Change Lives** — Enable action and transform lives.
5. **Crystallise Impact** — Capture learning and scale impact.

> **Why this matters for the project:** The README/pitch for this hackathon should echo this language — start from the teacher's real constraint, then show the solution as co-created around that constraint, not as a tech-first imposition. CDF evaluators will likely be listening for this "listen first" framing given it's their entire methodology.

### 2.6 CDF's "AI for Development" Program

This is the most directly relevant part of CDF's existing work to this assignment. CDF runs a dedicated AI program with five tracks:

1. AI for Teachers & Classrooms ← **Option A maps here**
2. AI for Youth Changemakers
3. AI for Civil Society Organisations
4. AI for Rural Entrepreneurs ← Option B would map here
5. AI for Panchayats & Local Governance

This confirms Option A (Voice-Enabled AI Teaching Assistant) is not a hypothetical exercise — it sits squarely inside an active CDF program area ("AI for Teachers & Classrooms").

---

## 3. Ground Reality: Government School Classrooms — Kerala Focus

The brief's example scenario ("a Haryana government school," "Hinglish") describes one regional instance of a national pattern. This project's research deliberately centers on **Kerala** instead, since Kerala represents the most mature state-level digital classroom infrastructure in the country and offers the clearest picture of what a "fully resourced" Indian government classroom looks like — a strong reference model that generalizes well to the rest of India as other states catch up. All findings below are documented with the goal of a **state-agnostic design** (see Section 4), with Kerala as the primary research anchor.

> **Note on governance context:** Kerala's government changed in May 2026. **V. D. Satheesan (Indian National Congress, leading the UDF coalition) was sworn in as the 13th Chief Minister of Kerala on 18 May 2026**, succeeding Pinarayi Vijayan after the UDF won 102 of 140 seats in the 2026 Kerala Legislative Assembly election, ending the CPI(M)-led LDF's decade-long rule. The KITE/SAMAGRA infrastructure described below was built and largely deployed under the previous government (2016–2026); it remains the operational infrastructure in schools today and is treated here as the current ground reality, independent of which administration is in office.

### 3.1 KITE (Kerala Infrastructure and Technology for Education)

- Originally founded as **IT@School** in 2001–02; became a fully state-government-owned company in **2017**, renamed **KITE**.
- Implementing agency for Kerala's **Public Education Rejuvenation Mission**, funded by KIIFB (Kerala Infrastructure Investment Fund Board).
- Scope has expanded over two decades from basic ICT infrastructure to: teacher capacity building, ICT content development, e-governance systems, **AI training for teachers**, deployment of robotic kits for students, and AI curriculum integration.
- Runs "Little Kites" IT Club — over 1 lakh (100,000) student members trained in animation and related tech skills.

### 3.2 Hi-Tech School Project — Hardware Deployed

- **Kerala became the first state in India to have high-tech classrooms in ALL public schools** (announced/completed ~2020, CM Pinarayi Vijayan).
- **45,000 classrooms across 4,752 schools** converted to "Hi-Tech" status under the Hi-Tech School Project (2016–2019), funded with **Rs 493.50 crore** from KIIFB.
- The 4,752 schools include Govt & Aided High Schools, Higher Secondary Schools, and Vocational Higher Secondary Schools.
- **Each Hi-Tech classroom is equipped with:**
  - 1 laptop
  - Ceiling-mounted multimedia projector
  - HDMI cables and faceplates
  - Whiteboard / projection screen
  - USB speakers
  - High-speed broadband internet
  - Access to the SAMAGRA Resource Portal
- **Each of the 4,752 schools additionally received:** a 42-inch LED TV, a Full HD webcam, and a DSLR camera, networked via a central server in an IT lab for information sharing.
- The **Hi-Tech Lab Project** subsequently extended similar (if scaled-down) upgrades to **11,257 primary schools**.
- Cumulative figures: **Over 4,50,000 (450,000) ICT devices** deployed to government and government-aided schools statewide, all supported by broadband, a 5-year warranty, and maintenance infrastructure (call centre, web portal, annual maintenance contracts).
- Official cumulative count (per Deccan Herald, all 16,030 public schools in Kerala): **3,74,274 IT equipment items**, including 1,19,055 laptops and 69,944 multimedia projectors.

> **Key takeaway for hardware assumptions:** In Kerala — and very likely as the *direction of travel* for other states — the standard classroom AV setup is **laptop + ceiling projector + projection screen/whiteboard + speakers + broadband**, NOT necessarily a touchscreen "smart board" in the interactive-touch sense. Interactive touch boards are a minority case. Designing for "a browser window projected onto a screen via a laptop" covers both Kerala's standard setup AND any school that does have an actual interactive smart board (since the board would just display the same browser window). This generalizes the solution and removes a hardware-specific dependency.

### 3.3 SAMAGRA Resource Portal — Detailed Breakdown

**What it is:** SAMAGRA is an online learning/content platform developed entirely by KITE, with academic support from SCERT (State Council of Educational Research and Training), Kerala. It was built to supplement the Hi-Tech School Project — i.e., "now that schools have the hardware, here's the content to put on it."

**URL:** samagra.kite.kerala.gov.in (also accessible via samagra.itschool.gov.in)

**What's in it:**
- Digital resources for **all subjects, Class 1 to Class 12** — videos, animations, audios, simulations, interactive content (formats mentioned include .pdb, .ggb, .swf, .gif), and images.
- **Unit plans and micro-planning** for every chapter (i.e., lesson-plan-level content, not just media).
- **eTextbooks in four mediums: Malayalam, English, Tamil, and Kannada** — allows students to study even without a physical textbook.
- **Multi-level logins**: separate access levels for Teachers, Public, and Administrators.
- **Teacher-contributed content**: teachers upload videos, images, and interactive files; students access without restriction, filterable by subject → chapter → topic.
- **Discussion forums**: teachers can post doubts/questions regardless of location, for asynchronous community help.
- **"Learning Room"**: videos, audios, presentations, interactives, and simulations aligned to curriculum learning objectives; supports self-directed learning and self-assessment via interactive online quizzes with instant feedback.
- **"Samagra Plus" Question Bank**: 6,500+ questions across subjects (Physics, Chemistry, Mathematics, Economics, Accountancy, Botany, Zoology, Computerised Accounting, Business Studies) for Higher Secondary students — browsable by medium/class/subject/chapter, each with a "View Answer" option. Includes a question-paper preparation module.
- **Edutainment / E-Resources for Kids** sections — recreational + pedagogically designed digital resources, particularly used during holiday periods.
- **Samagra Plus podcast**: audio content covering literature — novel discussions, poem recitations, narrations of language-subject content.

**How a teacher uses it (current workflow):** Login → navigate menus → select medium, standard (class), subject, chapter, topic → submit → browse/download/play the relevant resource. This is a **prepare-ahead, browse-and-select** model.

### 3.4 Honest comparison: SAMAGRA vs. the proposed tool

This comparison is included deliberately and honestly, because an evaluator familiar with Kerala's edtech landscape will ask "why not just use SAMAGRA?" — and the answer needs to be clear-eyed, not oversold.

| | **SAMAGRA** | **Proposed Voice Teaching Assistant** |
|---|---|---|
| **Interaction model** | Click-based browsing: select medium → class → subject → chapter → topic → open resource | Voice command: teacher speaks naturally, system responds |
| **When it's used** | Before class, during prep time | During class, in the moment |
| **Best for** | Planned lessons, pre-curated high-quality media (videos, simulations, full lesson plans) | Spontaneous/reactive needs — a student asks an unexpected question, teacher wants an instant quiz, teacher needs a quick translation on the spot |
| **Content depth** | Deep — professionally produced videos, simulations, full question banks | Shallow but fast — AI-generated on the fly, lower production quality but zero prep time |
| **"AI" component** | None in the core portal (KITE separately runs AI *training* for teachers, but SAMAGRA itself is a content library, not an AI system) | Core — voice understanding, multilingual generation, intent routing |
| **Hands-free** | No — requires keyboard/mouse navigation through menus | Yes — by design |

**Honest conclusion:** This is **not a replacement for SAMAGRA**, and should not be pitched as one. SAMAGRA is a rich, pre-built content **library** that a teacher prepares from. The proposed tool is a **real-time voice layer for the spontaneous moments a library can't anticipate** — the question a student asks mid-lesson, the need for an instant 5-question check-in, a quick on-the-spot translation of a textbook line. The realistic framing is: *"A teacher already has SAMAGRA (or equivalent state content) open in one tab for planned content. This tool lives in another tab for everything that comes up unplanned."*

This also reframes the "AI for Teachers & Classrooms" gap correctly: KITE's current AI involvement is **training teachers to use AI tools generally** — it is not (per available information) AI embedded into the classroom content delivery itself. That is the actual gap this project occupies.

---

## 4. Reframing the Problem (Generalized, Not Region-Locked)

### 4.1 Why "Hinglish-only" was too narrow

The brief's wording ("Hindi and English / Hinglish") describes the *most common* national pattern but not the *only* one. The underlying pattern that's actually true everywhere in India is:

> **Every Indian classroom code-switches between a regional/local language and English**, especially for technical, scientific, and exam-relevant vocabulary. The specific regional language varies by state — Kerala's SAMAGRA portal itself provides eTextbooks in four mediums (Malayalam, English, Tamil, and Kannada), illustrating that even a single state's content ecosystem already spans multiple languages — but the *code-switching behavior itself* is the constant.

Designing strictly for "Hindi + English" would make the tool unusable in Kerala, Tamil Nadu, Karnataka, West Bengal, etc. — a large majority of the country. The corrected design treats the **regional language as a configurable parameter**, with English code-mixing supported in all cases.

### 4.2 Why "smart board" was too narrow

As established in Section 3.2, the dominant real-world setup — including in Kerala, the most digitally advanced state — is **laptop + projector + screen**, not necessarily a touchscreen interactive board. Designing specifically for "smart board integration" (implying touch input, proprietary board software, or board-specific APIs) would be:
- Less general (excludes the laptop+projector majority case)
- More fragile (dependent on board-specific hardware/software)
- Unnecessary (the actual requirement is just *visual output the class can see*)

**Corrected design assumption:** The deliverable is a **browser-based web application**, opened on whatever device (laptop/PC) is connected to the classroom's display (projector, TV, or interactive board — all of which just show whatever is on the connected device's screen). No board-specific integration, no touch dependency. This is simultaneously more general AND simpler to build.

### 4.3 Restating the core problem (final version)

> Indian government schools — across states — have made substantial investments in classroom display hardware (digital boards, projectors, laptops). Execution gaps mean some of this hardware is underused or non-functional, but **where it works, the bottleneck is no longer "is there a screen?" — it's "can an overloaded teacher use that screen for something useful, on the spot, mid-lesson, in the language mix they naturally speak, without stopping to type or browse a menu?"**
>
> Existing digital content libraries (SAMAGRA and equivalents) solve the "prepared content" half of this. They do not solve the "spontaneous, in-the-moment, voice-driven" half. That gap — combined with a national teacher shortage that leaves individual teachers covering more ground than they reasonably can — is the actual problem this project addresses.

---

## 5. Design Philosophy: Co-Pilot, Not Replacement

An early framing risk identified during planning: a tool that "explains concepts to students" or "quizzes the class" in an AI voice could easily read as **replacing the teacher** rather than assisting them. This is both a poor pitch (CDF's entire model is about empowering human leaders/changemakers, not automating them away) and arguably bad pedagogy (the human relationship between teacher and student is not something AI should be inserted into as a substitute).

**Corrected framing — the tool is a co-pilot:**

- The **teacher remains the one teaching**. The AI does not address students directly as an autonomous "voice of authority."
- The teacher **asks** for something and **decides** when/whether to use it — like reaching for chalk, a textbook, or a wall map. It is a tool reached for, not an agent acting independently.
- AI output is primarily **visual** (diagrams, text, quiz cards, timers) for the teacher to *use* while *they* explain — not a recorded "lecture" played to students.
- TTS (text-to-speech) is a secondary/optional channel (e.g., reading out a translated phrase), not the primary interaction model.
- Each feature should be understood as **saving teacher prep time**, not **performing the teaching task**:

| Feature | NOT this framing | YES this framing |
|---|---|---|
| Concept Simplification | "AI explains the concept to students" | "AI instantly pulls up a diagram/explanation *for the teacher* to use while *they* explain it" |
| Voice-Triggered Quizzing | "AI quizzes the class" | "AI generates quiz questions instantly so the teacher doesn't spend evening hours writing them" |
| Bilingual Dictation & Translation | "AI translates for students" | "AI displays bilingual text so the teacher doesn't have to hand-write both versions on the board" |
| Hands-Free Activity Guide | "AI runs the activity" | "AI displays the instructions + timer so the teacher doesn't have to repeat steps or watch the clock" |

A UI implication of this: before any content goes "live" on the projected display, the teacher should see a preview and explicitly confirm (e.g., a "Show to class" button) — reinforcing that the teacher is always in control and the AI is preparing material *for* them, not broadcasting independently.

A naming implication: working names considered include **"Teacher's Co-Pilot"** or **"Smart Board Assistant"** — names that foreground "assistant to the teacher" rather than "AI teacher."

---

## 6. Feature Scope Decisions

### 6.1 All four requirements, via one shared pipeline

The brief asks to "Choose 2" of four requirements. After analysis, the team is attempting **all four**, on the basis that they are not four separate systems but **four "skills" sitting on top of one shared pipeline**:

```
🎤 Voice input (push-to-talk; teacher pre-selects their regional language)
        ↓
   Speech-to-Text (handles regional language + English code-mixing)
        ↓
   Intent Router (LLM call — classifies which of the 4 skills is being requested,
                   and extracts relevant parameters: topic, grade, etc.)
        ↓
   ┌───────────────┬────────────────┬─────────────────────┬────────────────────┐
   │ 1. Concept     │ 2. Quiz        │ 3. Bilingual         │ 4. Activity Guide   │
   │    Simplifier  │    Generator   │    Dictation/        │    Generator        │
   │  (LLM + RAG)   │  (LLM + RAG)   │    Translation       │  (LLM)              │
   │                │                │  (Translation model) │                     │
   └───────────────┴────────────────┴─────────────────────┴────────────────────┘
        ↓
   Custom Web Renderer (diagrams / MCQ cards / dual-language text panels / timers)
        ↓
   Text-to-Speech (optional secondary output, regional language voice)
```

The genuinely new work per feature is limited to: (a) a prompt template, and (b) a UI component (diagram view, MCQ card, dual-text panel, timer). STT, the intent router, the RAG layer, the rendering shell, and TTS are shared infrastructure built once.

### 6.2 Depth allocation given the timeline (deadline: June 20)

Given the constraint of building all four within the available time, the team has allocated depth as follows:

- **Hero feature 1 — Live Concept Simplification.** Highest AI/prompt complexity (regional-language generation, grade-level calibration, syllabus grounding via RAG, diagram generation). This is where the 30% AI/Prompt score is primarily earned, and it's the strongest empathy story (directly maps to CDF's stated "Schools: learning outcomes" problem).
- **Hero feature 2 — Voice-Triggered Quizzing.** Completes the teach→test pedagogical loop with Hero 1, and reuses ~90% of Hero 1's pipeline (same STT, same LLM+RAG approach, same renderer shell) — so the marginal build cost is low relative to the payoff of a complete demo narrative (explain a concept → immediately quiz on it).
- **Functional, lighter polish — Bilingual Dictation & Translation.** Reuses the shared pipeline; the new work is primarily a translation call and a dual-pane display component.
- **Functional, lighter polish — Hands-Free Activity Guide.** Reuses the shared pipeline; the new work is primarily a step-sequencing prompt and a timer UI component.

### 6.3 Why Concept Simplification + Quizzing were the strongest pair (if only 2 were chosen)

For reference, the original "pick 2" analysis (before the decision to attempt all 4) concluded:

1. They form a **complete pedagogical loop** — teach, then test — which makes for a clean, continuous demo video.
2. Concept Simplification is the **hardest AI problem** of the four (regional-language generation, grade calibration, syllabus grounding, visual generation) — most relevant to the 30% AI/Prompt criterion.
3. Quizzing **reuses ~90% of the same pipeline** as Concept Simplification — nearly "free" as a second feature.
4. **Strongest empathy alignment** with CDF's stated problem #1 (school learning outcomes) and with the national teacher-shortage reality (instant formative assessment without manual grading-register work).

---

## 7. Technical Stack

### 7.1 Constraint: Fully free (₹0 running cost)

Priority was explicitly set as **cost over "fully Indian-sovereign" branding** — i.e., even though India-specific AI providers (e.g., Sarvam AI) offer strong Indian-language coverage, their paid tiers were deprioritized in favor of a zero-cost stack, both for hackathon practicality (unlimited demo/testing without burning credits) and for the stronger sustainability pitch: *"deployable in any government school with zero recurring cost."*

(Sarvam AI was researched in depth as a potential paid option — see Section 7.4 for reference, in case a future paid tier becomes relevant for a production version.)

### 7.2 Gemini API — confirmed core LLM

**Gemini API access is confirmed available for this project** and serves as the reasoning/generation core of the entire pipeline. Gemini's free tier is the basis for:

- **Intent routing** — classifying which of the 4 skills (Concept Simplification, Quiz, Translation/Dictation, Activity Guide) a teacher's voice command maps to, and extracting parameters (topic, grade level, language).
- **Content generation** — concept explanations, quiz questions, activity steps, all generated in the teacher's chosen regional language with English code-mixing where natural.
- **RAG-grounded responses** — retrieval-augmented generation against the NCERT corpus (Section 7.3) to keep content syllabus-accurate and reduce hallucination.
- **Translation** — Gemini's multilingual capability covers the Bilingual Dictation & Translation feature directly, avoiding a separate translation API dependency.

Using one model (Gemini) across intent routing, content generation, RAG, and translation keeps the architecture simple — one API key, one set of prompt/response conventions, one place to tune for reliability — while staying within free-tier limits for a hackathon-scale prototype.

### 7.3 Final free stack

| Layer | Choice | Why |
|---|---|---|
| **Speech-to-Text (STT)** | Browser **Web Speech API** | Free, built into Chrome, supports major Indian languages (Hindi, Malayalam, Tamil, Telugu, Bengali, Marathi, etc.), no API key needed |
| **STT backup/offline** | **Whisper (open-source)** | Free, runs locally or via free Hugging Face inference; reasonable code-mixing handling as a fallback |
| **LLM (intent routing + content generation + RAG)** | **Gemini (free tier)** | Generous free limits, strong multilingual reasoning, team already has GCP familiarity |
| **Text-to-Speech (TTS)** | Browser **Web Speech API (SpeechSynthesis)** | Free, built-in, has Indian language voices |
| **TTS backup** | **gTTS** | Free, decent Indian language coverage |
| **Translation** | **Gemini** (or Google Translate free tier) | Gemini translates well and avoids adding another service dependency |
| **RAG corpus** | **NCERT textbook PDFs** | Free, public, common foundation across most state boards (CBSE directly; most state boards align closely). Avoids needing to build 28 separate state-board corpora for a prototype. State-board-specific corpora (e.g., SAMAGRA's Malayalam/Tamil/Kannada eTextbooks) noted as a future extension. |
| **Frontend / display** | **Custom web app, built from scratch** | Full control over layout for projector/large-screen visibility (large fonts, high contrast); no framework lock-in to Streamlit/Gradio defaults |

Total stack cost: **₹0** — everything is browser-native or free-tier.

### 7.4 Reference: Sarvam AI (researched, not used — for future/production reference)

[Sarvam AI](https://www.sarvam.ai/) was evaluated as a potential Indian-language speech stack:

- **Company:** Founded 2023, Bengaluru, by IIT Madras alumni Vivek Raghavan and Pratyush Kumar. Backed by India's IndiaAI Mission. Positioned as India's "sovereign AI infrastructure" — models trained on Indian data, hosted on Indian servers, INR pricing.
- **STT (Saaras v3):** Covers 22 Indian languages, code-mixing support (Hinglish/Tanglish), <150ms time-to-first-token in fast streaming mode, speaker diarization, word-level timestamps.
- **TTS (Bulbul v3):** 25+ voices across 11 Indian languages, real-time streaming, emotion control.
- **Translation (Mayura):** Open-weights model, 22 Indian languages, structured long-form text.
- **Pricing:** STT ~₹30/hour (~Rs 1.5/min in some listings), TTS ~₹15–30 per 10K characters, Translation ~₹20 per 10K characters. ₹1,000 free credits on signup; paid plans range up to ₹50,000 with bonus credits.
- **Stated target users:** "The 800 million+ Indians more comfortable in Hindi, Tamil, Telugu, Bengali, Kannada, Gujarati, Marathi, Malayalam, Odia, or Punjabi than in English" — i.e., exactly the demographic this project targets, including Malayalam (Kerala).

**Why not used for the prototype:** The ₹1,000 free credit would be consumed quickly during iterative development/testing, and the explicit priority set for this project was zero cost over Indian-provider branding. Documented here so the choice is traceable and so Sarvam can be revisited if/when a production deployment with a real budget is considered — its Indian-language depth (especially code-mixing handling) is genuinely strong and may outperform Web Speech API in noisy real classroom audio conditions.

---

## 8. Open Items / Next Steps

- [ ] Finalize repo structure and scaffold the shared pipeline (STT → Intent Router → 4 skills → Renderer → TTS)
- [ ] Build and test Intent Router prompt (classification + parameter extraction across 4 skills, multilingual input)
- [ ] Build Concept Simplifier prompt + RAG retrieval against NCERT corpus (Hero feature 1)
- [ ] Build diagram/visual generation approach for Concept Simplifier output
- [ ] Build Quiz Generator prompt + MCQ card UI (Hero feature 2)
- [ ] Build Bilingual Dictation/Translation flow + dual-pane UI
- [ ] Build Activity Guide flow + timer UI
- [ ] Verify Web Speech API language coverage in target browser for all major Indian languages to be demoed (confirm Malayalam, Tamil, Telugu, Bengali, Marathi, etc. work in practice, not just in documentation)
- [ ] Design "preview before show to class" UI pattern (co-pilot framing — Section 5)
- [ ] Write final public README (tech stack, prompt design, localization notes) per deliverable requirements
- [ ] Record 3-minute video walkthrough
- [ ] Deploy to a live URL
- [ ] Publish public GitHub repo

---

## 9. Source Links

- CDF Website: https://www.connecting-dreams.org/
- CDF LinkedIn: https://www.linkedin.com/company/connecting-dreams-foundation/about/
- KITE Kerala (SAMAGRA-related pages): https://kite.kerala.gov.in/
- SAMAGRA Portal: https://samagra.kite.kerala.gov.in/
- Sarvam AI: https://www.sarvam.ai/
