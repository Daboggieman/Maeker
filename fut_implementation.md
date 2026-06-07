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

## Notes
- The current code already has a good modular structure for `VideoCreator`, `Manager`, and `OutroMaker`; the implementation should preserve the existing async flow while making state and config explicit.
- The biggest risk is doubling down on per-job state file behavior; ensure `platform` and `video_file` are always stored consistently.
- The implementation should avoid altering core business logic in the first pass, and instead focus on configuration and robust failure handling.
