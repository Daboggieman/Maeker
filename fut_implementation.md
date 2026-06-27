# Future Implementation Plan

## Objective
Implement all high and medium priority fixes from `audit.md`, and add configurable "levels" for rendering, quality, and behavior so the pipeline can adapt to very different use cases (fast draft, quality render, mobile vertical, debugging, etc.).

---

## Scope
This plan covers:
- High priority bug fixes (critical runtime failures and incorrect behavior)
- Medium priority issues (reliability, logging, config, and UX)
- Additional configurability for different operational levels
- A clear implementation roadmap and recommended file-level changes

---

## Priority Fix Groups

### High Priority Fixes

1. `video_creator.py` — remove hardcoded fallback `BASE_DIR`
   - Fix `self.base_dir` fallback to `os.path.dirname(os.path.abspath(__file__))` instead of a fixed path.
   - Ensure all asset directories use the resolved base.

2. `manager.py` — preserve `platform` when launching jobs
   - Pass `platform` through `run_job()` into `_run_production()`.
   - Save `self.state["platform"]` so resume can preserve the intended format.

3. `manager.py` — robust script generation failure detection
   - Replace `"Error" in script` checks with explicit `None` or exception handling.
   - Fail only on real generation errors, not on valid content containing the word "Error".

4. `script_generator.py` — remove stray `# type: ignore` in LLM prompt
   - Fix prompt construction so the actual prompt sent to the LLM does not contain code comments.

5. `manager.py` — resume logic should use `scene_assets`, not raw `scenes`
   - Fix the resume completion counter and cache existence checks to inspect `self.state["scene_assets"]`.

6. `outro_maker.py` — evaluate `ASSETS_DIR` after `.env` load
   - Move `OUTRO_PATH` resolution into runtime initialization.
   - Ensure `ASSETS_DIR` from `.env` is respected.

7. `voice_engine.py` — avoid blocking async event loop with sync HTTP
   - Wrap `requests.post()` in `asyncio.to_thread()` or use an async HTTP client.

8. `manager.py` — close file handlers after each job
   - Remove and close the job-specific log handler in `_cleanup_log_handler()`.
   - Prevent handle leaks across multiple jobs.

9. `video_creator.py` — avoid ffmpeg concat failures by re-encoding
   - Use `-c:v libx264 -c:a aac` for final concat instead of `-c copy`.
   - Always use a codec-safe ffmpeg command for generated segments.

10. `video_creator.py` — propagate ffmpeg stderr to logger
    - Capture stderr and log it when ffmpeg returns non-zero.
    - Remove `stdout=subprocess.DEVNULL` suppression or retain it with explicit stderr logging.

11. `llm_router.py` — avoid mutating shared `messages`
    - Copy the messages list before appending instructions.
    - Keep retry logic side-effect-free.

12. `video_creator.py` — stop sleeping unconditionally between image calls
    - Sleep only on retry/failure, not before every image generation attempt.

13. `manager.py` — avoid `db.save_content_metadata()` outside the state lock
    - Ensure state writes and notification writes happen in a consistent, locked context or are explicitly sequenced.

14. `outro_maker.py` — make outro resolution match the main video target
    - Allow `build_outro()` to accept a target width/height.
    - Resize the outro only when necessary, not by default.

15. `maker_studio.py` — fix `--no-outro` handling
    - Guard `self.outro` from `None` in `_run_production()` before calling `build_outro()`.


### Medium Priority Fixes

1. Mixed `print()` and `logger` usage
   - Standardize on the centralized `MakerStudio` logger across all modules.
   - Ensure console and file outputs are both captured if configured.

2. `outro_maker.py` default hardcoded render dimensions
   - Make outro dimensions configurable by platform or project settings.

3. `PIXABAY_API_KEY` is undocumented
   - Document the environment variable in `.env.example` and README.

4. `manager.py` logs the whole batch file every run
   - Remove or wrap this under a debug flag.

5. Temp files not cleaned up on ffmpeg failure
   - Clean `temp_combined` and any partial caches on failure.

6. Consolidate render size and image generation resolution
   - Ensure image size matches target video format and platform.

7. Improve resume logs and failure semantics
   - If resume completes without producing a file, mark status as `Error` or `Incomplete`, not `Complete`.

---

## Configurability Enhancements

### Goals
Enable three configurability levels:
- **Basic**: a small set of runtime profiles and safe defaults for everyday use.
- **Advanced**: configuration by platform, resolution, output quality, retry policy, and subtitle style.
- **Expert/Debug**: full control over logging, encoding presets, `ffmpeg` flags, and diagnostic output.

### Recommended Configurable Domains

1. **Platform / Output shape**
   - `youtube_short`, `tiktok`, `youtube`, `instagram_story`, `portrait`, `landscape`
   - Map to target resolutions and aspect ratios.

2. **Video quality profile**
   - `fast`, `standard`, `quality`, `max`
   - Controls `ffmpeg` preset, bitrate, threads, optional re-encoding, and whether subtitles are anti-aliased.

3. **Subtitle style & placement**
   - `bottom`, `lower_center`, `center`, `top`, with margin values.
   - `font_size`, `font_family`, `box_opacity`, `stroke_width`, `line_break_mode`.

4. **Audio / music behavior**
   - `music: off|ambient|score`
   - volume scaling, `stream_loop` behavior, and fallback when music download fails.

5. **Retry & backoff**
   - `image_retry`, `voice_retry`, `api_backoff_mult`, `max_attempts`
   - separate profiles for LLM, image API, and voice generation.

6. **Logging / diagnostics**
   - `log_level`, `debug_mode`, `ffmpeg_debug`, `job_tracing`
   - optionally write a `debug_manifest` for each job.

7. **Asset caching**
   - `cache_assets: true/false`
   - `cache_dir`, `cache_cleanup_policy`, `resume_strategy`.

8. **Render scale**
   - `target_resolution`, `scale_factor`, and whether to generate vertical assets from the start.

---

## Recommended Implementation Architecture

### 1. Add a config module
Create `config.py` or `settings.py` with:
- `ConfigProfile` enum (`fast`, `standard`, `quality`, `debug`)
- `PlatformSpec` dict mapping `platform -> width,height,aspect_ratio`
- `JobSettings` dataclass with fields like `platform`, `quality_profile`, `subtitle_position`, `music`, `outro`, `log_level`, `retry_policy`
- `load_config()` that reads from `.env`, CLI args, and defaults.

### 2. Centralize logging
- Move logger setup into `maker_studio.py` or `manager.py` initializer.
- Use `logging.getLogger("MakerStudio")` everywhere.
- Ensure module-level loggers inherit the root `MakerStudio` handler.
- Add a `debug` flag for verbose ffmpeg stdout/stderr.

### 3. Make `VideoCreator` config-driven
- Accept `VideoCreatorConfig` in `__init__`.
- Use profile-driven `ffmpeg` flags and `ImageClip` parameters.
- Parameterize subtitle position, font, and margin.
- Clean temporary files in finally blocks.

### 4. Make `Manager` platform-aware
- Persist `platform` in job state.
- Use `PlatformSpec` to choose image generation size and user-facing resolution.
- Add `--platform` / `--profile` CLI flags in `maker_studio.py`.

### 5. Fix async and retry logic
- Convert blocking API calls in `voice_engine.py` to `asyncio.to_thread()`.
- Only sleep on retry failure in image generation.
- Add a reusable retry helper in `manager.py` or `utils.py`.

### 6. Improve `resume_job()` semantics
- Verify whether a resumed job produces a final video.
- If assembly fails, leave state as `Error`/`Incomplete`.
- Add state flags like `needs_assembly` and `video_file`.

### 7. Document environment and profiles
- Add `.env.example` values for `PIXABAY_API_KEY`, `POLLINATIONS_API_KEY`, `BASE_DIR`, `PROFILE`, `LOG_LEVEL`, etc.
- Update `README.md` with profile usage and example commands.

### 8. Add targeted tests
- Add unit tests for `script_generator`, `llm_router`, `config`, and `video_creator` path handling.
- Add scenario tests for profile-based artifact generation (mocked if necessary).

---

## Implementation Roadmap

### Phase 1 — Core stability fixes
1. Fix `video_creator.py` base path and `ffmpeg` behavior.
2. Fix `manager.py` platform propagation and resume state handling.
3. Fix `voice_engine.py` async blocking call.
4. Fix `outro_maker.py` env path and resolution handling.
5. Fix `script_generator.py` stray prompt comment.
6. Fix `llm_router.py` message mutation.
7. Fix `maker_studio.py` `--no-outro` guard.
8. Standardize logging across modules.

### Phase 2 — Medium reliability and cleanup
1. Add stderr logging and temp file cleanup.
2. Remove batch-file noise from logs or gate it.
3. Document required env variables.
4. Make image generation resolution align with video platform.
5. Improve state locking and save behavior.
6. Add quality/fast mode profiles.

### Phase 3 — Configurability and UX
1. Add config module and runtime profiles.
2. Expose platform/quality/profile options in CLI.
3. Parameterize subtitle style and placement.
4. Add caching controls and cleanup policies.
5. Add `producer`/`render` profiles for vastly different pipelines.

### Phase 4 — Tests and docs
1. Add tests for config loading, prompt generation, and ffmpeg path handling.
2. Add README examples for `PROFILE=fast`, `PROFILE=quality`, `--platform=tiktok`, `--no-outro`, and `DEBUG=true`.
3. Add an `audit.md` follow-up status section.

---

## Example Profiles

### `fast`
- 720p or 720×1280 output
- `ffmpeg` preset `ultrafast`
- low retry/backoff
- no outro or minimal outro
- subtitles simple and small

### `standard`
- 1080p / standard quality
- `ffmpeg` preset `medium`
- moderate retry/backoff
- normal outro and music
- subtitles lower center

### `quality`
- 1080p+ output
- `ffmpeg` preset `slow`
- full audio quality and filtering
- high-quality outro matching resolution
- advanced subtitle style with larger font and softer background

### `debug`
- `log_level=DEBUG`
- no cache skipping or resume
- keep temp files for inspection
- store all diagnostic commands and ffmpeg stderr

---

## Feature 1: Dual Video Generation Mode (Image vs. Video)

### Overview
Currently, the pipeline only generates videos from static images provided by an image generation AI. Add capability for users to choose between:
- **Image Mode**: Current behavior — generates static images and creates video by sequencing with transitions
- **Video Mode**: Generates short video scenes from a video generation AI and concatenates them with ffmpeg

### Requirements
1. **Startup Prompt**: At job initiation, prompt the user to select video mode:
   - `"Choose video generation mode: [1] Image-based (default) [2] Video-based"`
   - Store selection in job state as `self.state["video_mode"]`

2. **Conditional Pipeline**:
   - **Image Mode**: Use existing `script_generator.py` → image generation → `video_creator.py` flow
   - **Video Mode**: Use `script_generator.py` → video scene generation (new API integration) → scene concatenation with ffmpeg

3. **Scene Assets**: For video mode, download and organize video scenes similar to current image organization:
   - `assets/video_scenes/{job_id}/` directory structure
   - Store video metadata (duration, resolution, fps) in state

4. **Concatenation**: Use ffmpeg to combine video scenes:
   - Ensure all scenes are re-encoded to match target resolution and codec (avoid copy-paste concat failures)
   - Preserve audio from scenes or replace with generated narration/music

5. **State & Resume**: Persist `video_mode` in job state so resume operations work correctly for both modes

### Implementation Notes
- Modify `manager.py` to prompt for mode selection before scene generation
- Add conditional branches in `_run_production()` based on `self.state["video_mode"]`
- Create new module `video_scene_generator.py` for video AI API integration
- Update `video_creator.py` to handle both image and video input sources

---

## Feature 2: Externalized Prompt Files

### Overview
Replace all hardcoded prompts in the codebase with editable configuration files. Users should be able to modify prompts without touching code.

### Requirements
1. **Prompt File Structure**:
   - Create `prompts/` directory in project root
   - Subdirectories: `prompts/image-mode/` and `prompts/video-mode/`
   - Each section gets its own named file:
     - `script_generation.txt` — prompt for generating video scripts
     - `image_generation.txt` — prompt for image generation (image mode)
     - `video_scene_generation.txt` — prompt for video scene generation (video mode)
     - `compliance_check.txt` — prompt for compliance engine
     - `fact_check.txt` — prompt for fact checker
     - (Add any other sections from the codebase)

2. **File Naming Convention**:
   - Clear, descriptive names
   - Use underscores for multi-word names
   - Include a comment header in each file explaining its purpose

3. **Loading Mechanism**:
   - Create `prompt_loader.py` module to read and cache prompt files at runtime
   - Load prompts at job start, not on every generation attempt
   - Support variable substitution (e.g., `{topic}`, `{tone}`, `{language}`)

4. **Error Handling**:
   - If a prompt file is missing, log error and use a safe fallback
   - Provide warnings if prompt files are not found

5. **Both Modes**: Maintain separate prompt folders so users can customize prompts for image vs. video generation independently

### Implementation Notes
- Create `.prompts.json` or `.prompts_manifest` for versioning/tracking
- Consider adding a `--reload-prompts` flag to force re-load during development
- Document prompt syntax and available variables in each file header

---

## Feature 3: Comprehensive Configurability

### Overview
Move all hardcoded parameters and settings to `.env` and `config.py` so users can customize behavior without editing code.

### Configurable Parameters

#### Video Output & Format
- `TARGET_RESOLUTION` — default video resolution (e.g., `1080x1920`, `1280x720`)
- `TARGET_FPS` — frames per second (e.g., `30`, `60`)
- `VIDEO_BITRATE` — encoding bitrate (e.g., `5000k`, `10000k`)
- `VIDEO_DURATION_MIN` — minimum video length in seconds (e.g., `30`)
- `VIDEO_DURATION_MAX` — maximum video length in seconds (e.g., `120`)
- `VIDEO_DURATION_ESTIMATED` — estimated typical duration (e.g., `60`)
- `OUTRO_DURATION` — outro video length in seconds (e.g., `5`)
- `FFMPEG_PRESET` — encoding speed (`ultrafast`, `fast`, `medium`, `slow`, `veryslow`)

#### Platform-Specific Formats
- `YOUTUBE_FORMAT` — resolution for long-form YouTube (e.g., `1920x1080`)
- `YOUTUBE_SHORT_FORMAT` — resolution for YouTube Shorts (e.g., `1080x1920`)
- `TIKTOK_FORMAT` — TikTok resolution (e.g., `1080x1920`)
- `INSTAGRAM_FORMAT` — Instagram Reels resolution (e.g., `1080x1920`)

#### Content Settings
- `CONTENT_RATING` — audience level (`children`, `teenager`, `adult`, `everyone`)
- `COMPLIANCE_ENABLED` — whether to run compliance checks (`true`/`false`)
- `FACT_CHECK_ENABLED` — whether to run fact checking (`true`/`false`)

#### AI Models & API Keys
- `IMAGE_GEN_MODEL` — image generation service (e.g., `pollinations`, `dall-e`, `midjourney`)
- `IMAGE_GEN_API_KEY` — API key for image service
- `VIDEO_GEN_MODEL` — video generation service (e.g., `runway`, `genmo`, `pika`)
- `VIDEO_GEN_API_KEY` — API key for video service
- `LLM_MODEL` — language model (e.g., `gpt-4`, `claude-3`, `groq`)
- `LLM_API_KEY` — LLM API key
- `VOICE_ENGINE` — text-to-speech provider (e.g., `google`, `elevenlabs`, `azure`)
- `VOICE_API_KEY` — TTS API key
- `PIXABAY_API_KEY` — existing Pixabay key (document this)

#### Generation Parameters
- `IMAGE_RETRY_COUNT` — max retries for image generation (e.g., `3`)
- `IMAGE_RETRY_BACKOFF` — backoff multiplier (e.g., `2`)
- `VOICE_RETRY_COUNT` — max retries for voice generation
- `API_TIMEOUT_SECONDS` — timeout for API calls (e.g., `60`)

#### Asset Caching
- `CACHE_ASSETS` — enable asset caching (`true`/`false`)
- `CACHE_DIR` — custom cache directory path
- `CACHE_CLEANUP_ON_ERROR` — delete cache if generation fails (`true`/`false`)
- `KEEP_TEMP_FILES` — retain temporary files for debugging (`true`/`false`)

#### Logging & Debugging
- `LOG_LEVEL` — logging verbosity (`DEBUG`, `INFO`, `WARNING`, `ERROR`)
- `DEBUG_MODE` — enable debug mode (`true`/`false`)
- `FFMPEG_DEBUG` — log ffmpeg command and output (`true`/`false`)
- `LOG_FILE_PATH` — custom log file location

#### Base Paths
- `BASE_DIR` — project root directory (auto-detected if not set)
- `ASSETS_DIR` — assets storage directory
- `OUTPUT_DIR` — final video output directory

### Implementation Strategy

**Option A (Recommended)**: `.env` + `config.py`
- Store all parameters in `.env`
- Create `config.py` with:
  - `ConfigProfile` class loading from `.env`
  - Type validation and defaults
  - Helper methods for resolving paths and format specs
  - `load_config()` function called at startup
- Use `python-dotenv` to parse `.env` at runtime

**Option B**: `.env` only
- All parameters in `.env` with defaults in fallback logic
- Less structured but simpler

**Option C**: YAML configuration file
- Single `config.yaml` for all settings (more readable)
- Parse with `pyyaml`
- May be overkill if `.env` is already standardized

**Recommendation**: Use **Option A** (`.env` + `config.py`) for:
- Clear separation of secrets (`.env`) and business logic (`config.py`)
- Type safety and validation
- Easy `.env.example` distribution for GitHub
- Backward compatibility with existing environment setup

### Files to Create/Update
1. Create `.env.example`:
   ```
   # Video Output
   TARGET_RESOLUTION=1080x1920
   TARGET_FPS=30
   VIDEO_BITRATE=5000k
   VIDEO_DURATION_MIN=30
   VIDEO_DURATION_MAX=120
   VIDEO_DURATION_ESTIMATED=60
   OUTRO_DURATION=5
   FFMPEG_PRESET=medium

   # Platforms
   YOUTUBE_FORMAT=1920x1080
   YOUTUBE_SHORT_FORMAT=1080x1920
   TIKTOK_FORMAT=1080x1920
   INSTAGRAM_FORMAT=1080x1920

   # Content
   CONTENT_RATING=everyone
   COMPLIANCE_ENABLED=true
   FACT_CHECK_ENABLED=true

   # AI Models
   IMAGE_GEN_MODEL=pollinations
   IMAGE_GEN_API_KEY=your_key_here
   VIDEO_GEN_MODEL=runway
   VIDEO_GEN_API_KEY=your_key_here
   LLM_MODEL=gpt-4
   LLM_API_KEY=your_key_here
   VOICE_ENGINE=elevenlabs
   VOICE_API_KEY=your_key_here
   PIXABAY_API_KEY=your_key_here

   # Generation
   IMAGE_RETRY_COUNT=3
   IMAGE_RETRY_BACKOFF=2
   VOICE_RETRY_COUNT=3
   API_TIMEOUT_SECONDS=60

   # Caching
   CACHE_ASSETS=true
   CACHE_DIR=./assets/cache
   CACHE_CLEANUP_ON_ERROR=false
   KEEP_TEMP_FILES=false

   # Logging
   LOG_LEVEL=INFO
   DEBUG_MODE=false
   FFMPEG_DEBUG=false
   LOG_FILE_PATH=./logs/maker_studio.log

   # Paths
   BASE_DIR=./
   ASSETS_DIR=./assets
   OUTPUT_DIR=./output
   ```

2. Create `config.py`:
   ```python
   import os
   from typing import Optional
   from dataclasses import dataclass
   from dotenv import load_dotenv

   load_dotenv()

   @dataclass
   class VideoConfig:
       resolution: str
       fps: int
       bitrate: str
       duration_min: int
       duration_max: int
       duration_estimated: int
       outro_duration: int
       ffmpeg_preset: str

   @dataclass
   class ModelConfig:
       image_gen_model: str
       image_gen_api_key: str
       video_gen_model: str
       video_gen_api_key: str
       llm_model: str
       llm_api_key: str
       voice_engine: str
       voice_api_key: str
       pixabay_api_key: str

   @dataclass
   class AppConfig:
       video: VideoConfig
       models: ModelConfig
       log_level: str
       debug_mode: bool
       cache_assets: bool
       # ... etc

       @staticmethod
       def from_env():
           # Load from environment variables
           pass
   ```

3. Update all modules to import from `config.py`:
   - Replace `HARDCODED_VALUE` with `config.video.resolution`, etc.
   - Pass `config` object to functions that need it

### Potential Issues & Alternatives
- **Issue**: Too many `.env` variables (100+)?
  - **Solution**: Group related configs into sections; use `config.py` validation layer to keep `.env` tidy
- **Issue**: Runtime config changes (hot-reload)?
  - **Solution**: Not in scope for Phase 1; document as "requires job restart"
- **Issue**: Secrets management (API keys in `.env`)?
  - **Solution**: Recommend `.env` in `.gitignore`; use `.env.example` for distribution; document setup in README

---

## Feature 4: Telegram Notification System

### Overview
Send completed videos to a Telegram bot for remote access. Users can download rendered videos from anywhere using the bot.

### Requirements
1. **Telegram Bot Setup**:
   - Create a Telegram bot (via BotFather)
   - Store bot token in `.env`: `TELEGRAM_BOT_TOKEN`
   - Store user/chat ID in `.env`: `TELEGRAM_CHAT_ID` or `TELEGRAM_USER_ID`

2. **Notification Trigger**:
   - After successful video render, check if `TELEGRAM_BOT_TOKEN` is set
   - Send video file to configured Telegram chat

3. **Message Content**:
   - Video file
   - Job metadata:
     - Job ID / name
     - Duration
     - Topic / title
     - Render time
     - Platform (YouTube, TikTok, etc.)
     - Video mode (Image-based or Video-based)

4. **Error Handling**:
   - If send fails, log error but don't block final output
   - Implement retry logic (max 3 attempts)
   - Support sending video URL if file is too large (for Telegram's 50MB limit)

5. **Optional**: Add command to download video stats or re-send last video

### Implementation Notes
- Create `telegram_notifier.py` module with `TelegramNotifier` class
- Use `python-telegram-bot` library
- Send in `_cleanup_job()` or after successful `video_creator` completion
- Add env variables:
  - `TELEGRAM_ENABLED` (`true`/`false`)
  - `TELEGRAM_BOT_TOKEN`
  - `TELEGRAM_CHAT_ID`
- Consider adding a `--no-telegram` CLI flag to skip notification

### Integration Points
- In `manager.py` `_run_production()`: After video is successfully written, call `telegram_notifier.send_video()`
- In `maker_studio.py`: Add `--notify-telegram` flag

---

## Notes
- The current code already has a good modular structure for `VideoCreator`, `Manager`, and `OutroMaker`; the implementation should preserve the existing async flow while making state and config explicit.
- The biggest risk is doubling down on per-job state file behavior; ensure `platform` and `video_file` are always stored consistently.
- The implementation should avoid altering core business logic in the first pass, and instead focus on configuration and robust failure handling.
- The four new features (dual video mode, prompt externalization, configurability, and Telegram notifications) should be implemented in phases to maintain code stability and allow for iterative testing.
