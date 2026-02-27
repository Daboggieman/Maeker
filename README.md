# maker Studio - Free-First Automation Suite

An advanced content automation system designed for YouTube, TikTok, and News platforms. Built with a focus on high accuracy and zero-cost infrastructure.

## 🚀 The "Free Stack" Architecture

- **Orchestration**: Self-hosted **n8n** (visual control & scheduling).
- **Intelligence**: **DeepSeek / Gemini / Ollama** (state-of-the-art script generation).
- **Voiceover**: **Edge-TTS** (FREE high-quality natural voices).
- **Media Engine**: **FFmpeg** (automated video assembly).
- **Database**: **MongoDB Atlas** (persistent project metadata).

## 📁 Directory Structure

- `/assets`: Voiceovers, render jobs, and placeholders.
- `/jobs/pending`: Temporary storage for active processing.
- `/venv`: Isolated Python environment with all required drivers.

## 🛠️ Usage

### 1. Setup

- Ensure `n8n` is installed and running.
- Copy `.env.template` to `.env` and fill in your API keys.

### 2. Running a Single Job

```powershell
.\venv\Scripts\python maker_studio.py --topic "Your Topic" --category "History/Bible/News" --produce
```

_Add `--json` if calling from n8n._

### 3. n8n Integration

Import `n8n_workflow_template.json` into your n8n dashboard to activate the automated feed loop.

## 📜 Roadmap

1. [x] Phase 1-4: Core Engine Development.
2. [ ] Phase 5: Cinematic expansion (SoraAI) and Celebrity narration (Speechify).

---

_Created by Antigravity Studio_
