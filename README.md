# 🎬 Maker Studio

### AI-Powered Video Production Suite

An advanced, fully automated content production system for **YouTube**, **TikTok**, and **News** platforms. Maker Studio takes a single topic and produces a complete multi-scene narrated video — script, voiceover, images, and final render — with zero manual intervention after launch.

---

## ⚡ Quick Start

Double-click **`run_job.bat`** and follow the interactive prompts:

1. **Enter your topic** — any subject, as long or short as you like
2. **Pick a category** — numbered menu (History, Politics, Culture, Crime, etc.)
3. **Choose a voice** — live list of up to 50 bold male narrative voices from ElevenLabs, ranked by quality
4. **Confirm** — review your selections and press `Y` to start production

Output lands in `/assets/renders/` as a ready-to-upload `.mp4`.

---

## 🏗️ Architecture

Maker Studio is a **Hybrid Python + n8n** system. Python handles all heavy computation; n8n handles scheduling, webhooks, and approval workflows.

```
run_job.bat  ──►  maker_studio.py  ──►  manager.py (JobManager)
                                              │
                        ┌─────────────────────┼──────────────────────┐
                        ▼                     ▼                      ▼
               script_generator.py    voice_engine.py       video_creator.py
               (LLM script + scenes)  (ElevenLabs TTS)      (Pollinations img
                                                              + MoviePy render)
                        │
                        ▼
               fact_checker.py  ──►  compliance_engine.py  ──►  database_manager.py
```

---

## 🧠 AI Stack

| Layer                 | Primary                        | Fallback                             |
| --------------------- | ------------------------------ | ------------------------------------ |
| **Script Generation** | Groq `llama-3.3-70b-versatile` | OpenRouter `google/gemini-2.5-flash` |
| **Fact Checking**     | Groq `llama-3.3-70b-versatile` | OpenRouter `google/gemini-2.5-flash` |
| **Hook Generation**   | Groq `llama-3.3-70b-versatile` | —                                    |
| **Voice (TTS)**       | ElevenLabs `eleven_turbo_v2_5` | Edge TTS `en-US-ChristopherNeural`   |
| **Image Generation**  | Pollinations `flux`            | `zimage` → `imagen-4`                |
| **Video Assembly**    | MoviePy (multi-scene, 16:9)    | —                                    |
| **Database**          | MongoDB Atlas                  | —                                    |

---

## 📁 Directory Structure

```
maker/
├── run_job.bat               # Interactive launcher — double-click to start
├── pick_voice.py             # Fetches & ranks ElevenLabs voices for selection
├── maker_studio.py           # Entry point — CLI argument parser
├── manager.py                # JobManager — orchestrates the full pipeline
├── script_generator.py       # LLM script + scene breakdown
├── fact_checker.py           # Secondary LLM fact verification pass
├── compliance_engine.py      # YouTube policy compliance check
├── voice_engine.py           # ElevenLabs TTS (Edge TTS fallback)
├── video_creator.py          # Pollinations image gen + MoviePy video assembly
├── database_manager.py       # MongoDB Atlas persistence
├── .env                      # API keys and path config (never commit this)
├── assets/
│   ├── audio/<topic_slug>/   # Per-topic scene audio files
│   ├── images/<topic_slug>/  # Per-topic scene images
│   └── renders/              # Final output .mp4 files
├── jobs/                     # n8n job queue handoff folder
├── logs/maker.log            # Rotating log (5 × 10MB)
└── venv/                     # Isolated Python environment
```

---

## 🔧 Manual CLI Usage

```powershell
# Basic production run
.\venv\Scripts\python maker_studio.py --topic "Your Topic" --category "History" --produce

# With specific voice
.\venv\Scripts\python maker_studio.py --topic "Your Topic" --category "History" --voice "George" --produce

# JSON output (for n8n integration)
.\venv\Scripts\python maker_studio.py --topic "Your Topic" --produce --json
```

---

## 🔑 Environment Variables (`.env`)

| Variable               | Purpose                                    |
| ---------------------- | ------------------------------------------ |
| `GROQ_API_KEY`         | Primary LLM (Groq)                         |
| `OPENROUTER_API_KEY`   | Fallback LLM (OpenRouter)                  |
| `OPENROUTER_MODEL`     | Model name, e.g. `google/gemini-2.5-flash` |
| `ELEVENLABS_API_KEY`   | TTS voice generation                       |
| `POLLINATIONS_API_KEY` | Image generation                           |
| `GNEWS_API_KEY`        | News sourcing (for news category)          |
| `MONGODB_URI`          | MongoDB Atlas connection string            |
| `BASE_DIR`             | Absolute path to the maker root folder     |
| `ASSETS_DIR`           | Absolute path to the assets folder         |
| `JOBS_DIR`             | Absolute path to the jobs queue folder     |

---

## 🔄 Production Pipeline (per job)

1. **Script Generation** — LLM writes a detailed, fact-rich narrative script for the topic
2. **Fact Checking** — Secondary LLM pass verifies dates, events, and claims
3. **Hook Generation** — Generates 3 viral hook variations for Shorts/TikTok
4. **Compliance Check** — Screens for YouTube policy violations
5. **Scene Breakdown** — Script is split into individual cinematic scenes (narration + image prompt per scene)
6. **Asset Generation** (per scene, in parallel-ready loop):
   - 🎙️ ElevenLabs narration MP3 → Edge TTS on failure
   - 🖼️ Pollinations image (flux → zimage → imagen-4 failover)
7. **Video Assembly** — MoviePy concatenates all scene clips into a single `.mp4` with subtitles
8. **Save to DB** — Full job metadata and asset paths saved to MongoDB Atlas

---

## �️ Roadmap

See [`55.txt`](./55.txt) for the full phased roadmap.

| Phase                                                | Status         |
| ---------------------------------------------------- | -------------- |
| Phase 1 — Hybrid Infrastructure                      | ✅ Complete    |
| Phase 2 — AI Creative Engine                         | ✅ Complete    |
| Phase 3 — Production Pipeline + Interactive Launcher | ✅ Complete    |
| Phase 4 — Scalability & Audit                        | 🔲 Pending     |
| Phase 5 — Cinematic Expansion + Voice Cloning        | 🔄 In Progress |

---

## 🔌 n8n Integration

1. Install and run n8n locally
2. Import `n8n_workflow_template.json` into your n8n dashboard
3. The workflow sends topic + category to `maker_studio.py` via webhook, receives JSON results back
4. Add `--json` flag to CLI args in the n8n Execute Command node

---

_Built by Daboggieman — Maker Studio v3_
