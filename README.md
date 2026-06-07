# Maeker Studio v2

### AI-Powered Video Production Suite — Rebuilt for Reliability

This is the `maeker-v2` repository: a refreshed version of the original Maker Studio pipeline. v2 emphasizes safer resume behavior, platform-aware render sizing, better logging, cleaner asset caching, and a more configurable production workflow.

It still turns a single topic into a full multi-scene narrated video for **YouTube**, **TikTok**, or **News**, but now with stronger recovery, more predictable output, and a clearer path toward scalable automation.

---

## Quick Start

Double-click **`run_job.bat`** and follow the interactive prompts:

1. **Enter your topic** — any subject, as long or short as you like
2. **Pick a category** — numbered menu (History, Politics, Culture, Crime, etc.)
3. **Choose a voice** — live list of up to 50 bold narrative voices from ElevenLabs, ranked by quality
4. **Choose Platform** — outputs dynamically crop and sequence for either TikTok (`9:16`) or YouTube (`16:9`)
5. **Confirm** — review your selections and press `Y` to start production

Output lands in `/assets/renders/` as a ready-to-upload `.mp4` featuring neatly blended crossfaded scenes.

---

## What’s New in v2

- Platform-aware image and scene sizing for `9:16` and `16:9` outputs
- Stronger resume support and recovered scene assembly
- More consistent logging and error visibility across the pipeline
- Improved `.env`/secret handling and GitHub-safe repo practice
- A clearer roadmap toward profile-based rendering and debug-friendly builds

---

## Architecture

Maker Studio is a **Native Python** system. Python handles all heavy computation, scheduling, and rendering natively.

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

## AI Stack

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

## Directory Structure

```
maeker-v2/
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

## Manual CLI Usage

```powershell
# Basic production run (defaults to youtube_short 9:16)
.\venv\Scripts\python maker_studio.py --topic "Your Topic" --category "History" --produce

# With specific voice and background music
.\venv\Scripts\python maker_studio.py --topic "Your Topic" --category "History" --voice "George" --music --produce

# Target specific platform (youtube 16:9, tiktok 9:16, youtube_short 9:16)
.\venv\Scripts\python maker_studio.py --topic "Your Topic" --platform "youtube" --produce
```

---

## Environment Variables (`.env`)

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

## Production Pipeline (per job)

1. **Script Generation** — LLM writes a detailed, fact-rich narrative script for the topic
2. **Fact Checking** — Secondary LLM pass verifies dates, events, and claims
3. **Hook Generation** — Generates 3 viral hook variations for Shorts/TikTok
4. **Compliance Check** — Screens for YouTube policy violations
5. **Dynamic Scene Breakdown** — Script is split into ~15-second cinematic scenes to maximize viewer engagement without blowing through API limits.
6. **Asset Generation** (per scene, in parallel-ready chunked loops):
   - ElevenLabs narration MP3 → Edge TTS on failure
   - Pollinations image (flux → zimage → imagen-4 failover)
   - Dynamic Subtitles — Split perfectly line-by-line, perfectly timed to the TTS audio.
7. **Video Assembly** — MoviePy seamlessly stitches the clips with 1-second **crossfades**, rendering scenes in memory-friendly batches of 5 to prevent OOM errors, formatted precisely via `--platform`.
8. **Save to DB** — Atomic JSON `.tmp` writes ensure Job State recovery never corrupts, and the final metadata is sent to MongoDB Atlas.

---

## �️ Roadmap

See [`55.txt`](./55.txt) for the full phased roadmap.

| Phase                                                | Status         |
| ---------------------------------------------------- | -------------- |
| Phase 1 — Hybrid Infrastructure                      | Complete       |
| Phase 2 — AI Creative Engine                         | Complete       |
| Phase 3 — Production Pipeline + Interactive Launcher | Complete       |
| Phase 4 — Scalability & Audit                        | In Progress    |
| Phase 5 — Cinematic Expansion + Voice Cloning        | Planned        |

---

## V2 Improvement Plan

- Stabilize the core pipeline with stronger resume, platform-aware rendering, and safer ffmpeg assembly.
- Standardize logging and surface ffmpeg/audio failures clearly in the job log.
- Add runtime profiles for `fast`, `standard`, `quality`, and `debug` builds.
- Harden `.env` handling and keep secrets out of repo history.
- Expand CLI options for `--platform`, `--profile`, and `--no-outro`.

---



_Built by Daboggieman — Maeker Studio v2_
