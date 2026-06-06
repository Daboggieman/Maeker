# Maeker Studio — Senior Developer Audit

---

## 🔴 Bugs (Will Break Things)

### 1. `video_creator.py` line 11 — Hardcoded path to a different machine
```python
self.base_dir = base_dir or os.getenv("BASE_DIR", "c:\\Users\\RAPH-EXT\\maker")
```
The fallback is another person's machine path. If `BASE_DIR` is not set in `.env`, every file write goes to a non-existent directory and crashes. **Fix:** Default to the script's own directory.
```python
self.base_dir = base_dir or os.getenv("BASE_DIR", os.path.dirname(os.path.abspath(__file__)))
```

---

### 2. `manager.py` line 377 — `platform` is never passed to `_run_production` from `run_job`
```python
video_file = await self._run_production(topic, script, job_id, music=music)
# ↑ platform is silently dropped — always defaults to "youtube_short"
```
The `--platform youtube` argument you pass via CLI has no effect on new jobs. **Fix:**
```python
video_file = await self._run_production(topic, script, job_id, music=music, platform=platform)
```
Also: `self.state["platform"]` is never set in `run_job`, so a resumed job also can't read it.

---

### 3. `manager.py` line 332 — Fragile "Error" string check on the script
```python
if not isinstance(script, str) or "Error" in script:
    raise Exception("Script generation failed after retries.")
```
If the generated script legitimately contains the word "Error" (e.g. "The Error of Napoleon's judgment..."), the whole job halts. **Fix:** Check the return value from `route_request` being `None` instead, since that's the actual failure signal.

---

### 4. `script_generator.py` line 100 — Python comment leaks into the LLM prompt
```python
{script[:800]}  # type: ignore
```
The string `# type: ignore` is literally sent to the LLM inside the prompt. This is a stray comment that ended up inside an f-string. **Fix:** Remove it.

---

### 5. `manager.py` lines 465–467 — Wrong resume completion check
```python
for s in self.state["scenes"]:
    if "audio" in s and "image" in s:
        completed_count = completed_count + 1
```
Scenes are stored in `self.state["scenes"]` as raw LLM output — they don't have `"audio"` or `"image"` keys. Those are in `self.state["scene_assets"]`. This counter is always 0 and is never even used. Dead/broken code.

---

### 6. `outro_maker.py` line 17 — Outro path evaluated at import time
```python
OUTRO_PATH = os.path.join(os.getenv("ASSETS_DIR", "assets"), "outro", "maeker_outro.mp4")
```
This runs before `load_dotenv()` is called in any module. If `ASSETS_DIR` is in `.env`, it won't be picked up here — the outro always saves to `assets/outro/`. **Fix:** Move this into `OutroMaker.__init__()`.

---

### 7. `voice_engine.py` — `generate_voice` uses `requests.post` (sync) inside an async function
```python
async def generate_voice(self, text, output_path, ...):
    ...
    response = requests.post(url, json=data, headers=headers, timeout=60)
```
A synchronous 60-second HTTP call blocks the entire event loop. This stalls all other async tasks while waiting for ElevenLabs. **Fix:** Wrap in `asyncio.to_thread()`.

---

## 🟠 Potential Issues (Will Hurt You Under Load or Edge Cases)

### 8. `manager.py` — Log file handler leaks on every job
```python
file_handler = logging.FileHandler(log_file, encoding='utf-8')
logger.addHandler(file_handler)
```
A new handler is added every time `run_job` or `resume_job` is called, but it's never removed or closed. Run 5 jobs in one session and you have 5 open file handles writing to 5 log files simultaneously. **Fix:** Store the handler and remove it at the end of the job with `logger.removeHandler(handler); handler.close()`.

---

### 9. `video_creator.py` — `ffmpeg concat` with no re-encoding fails on mismatched streams
```python
subprocess.run(["ffmpeg", "-y", "-f", "concat", "-safe", "0",
    "-i", concat_file_path, "-c", "copy", output_path], check=True, ...)
```
`-c copy` (stream copy) requires all input clips to have identical codecs, timebase, and resolution. If any scene clip was rendered slightly differently (e.g. different audio sample count), ffmpeg will produce a broken or silent video. Given scenes are rendered individually with MoviePy, this is a real risk. **Fix:** Add `-c:v libx264 -c:a aac` for safe re-encoding on the final concat pass.

---

### 10. `video_creator.py` — stderr suppressed on all ffmpeg calls
```python
stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL
```
When ffmpeg fails, you get `CalledProcessError` with no message about *why*. Debugging production failures becomes a guessing game. **Fix:** Capture stderr and log it on error.
```python
result = subprocess.run([...], capture_output=True, text=True)
if result.returncode != 0:
    logger.error(f"ffmpeg error: {result.stderr}")
```

---

### 11. `llm_router.py` line 116 — Mutates the shared messages list
```python
messages[0]["content"] += "\nReturn strictly as JSON without markdown blocks."
```
`messages` is passed in by reference. If `_execute_openrouter` is called after a Groq retry with the same list, this mutation persists and the appended instruction keeps growing on every retry. **Fix:** Work on a copy: `msg = [{"role": m["role"], "content": m["content"]} for m in messages]`.

---

### 12. `video_creator.py` — Image generation has a hardcoded 3.5s sleep per scene
```python
time.sleep(3.5)
```
With 15 scenes, that's 52 seconds of pure sleep before any API call. Combined with the ElevenLabs 1.5s sleep, a 15-scene job wastes ~75 seconds doing nothing. **Fix:** Only sleep after a failure, not before every single attempt.

---

### 13. `manager.py` — `_save_state()` called inside `_state_lock` but `_notify()` also calls MongoDB sync
`_notify()` triggers `db.save_content_metadata(self.state)` (a sync MongoDB write) without holding the lock. Calling `_notify()` concurrently from multiple scene tasks could write partially-updated state to MongoDB.

---

### 14. `outro_maker.py` — Outro is always 1920×1080 regardless of platform
```python
WIDTH, HEIGHT = 1920, 1080
```
If your main video is 720×1280 (TikTok/Shorts), the outro is a completely different resolution and `append_outro` has to resize it. The resize via MoviePy re-encodes everything and looks poor. **Fix:** Pass the target dimensions into `build_outro()`.

---

## 🟡 Code Quality & Improvements

### 15. Mixed logging — `print()` vs `logger`
`video_creator.py` and `voice_engine.py` use raw `print()`. `manager.py` uses the `logger`. This means video and voice messages never appear in the rotating log file — only in the console. Standardize everything to use `logging.getLogger(__name__)`.

---

### 16. `script_generator.py` — Only 4 categories in `category_prompts`, no Bible in README
```python
category_prompts = {"Bible": ..., "History": ..., "News": ..., "General": ...}
```
The `run_job.bat` offers 10 categories (History, Politics, Culture, Crime, Society, Science, Technology, Business, Biography, Other) but the script generator only has 4 system prompts. All others silently fall through to the `"General"` prompt. This isn't necessarily wrong but is likely unintentional — Politics and Crime content probably needs different prompting.

---

### 17. `maker_studio.py` — `--no-outro` flag is parsed but silently ignored
```python
if args.no_outro:
    manager.outro = None  # disable outro rendering
```
`manager.outro` is set to `None`, but in `_run_production` the outro is called as:
```python
outro_path = await asyncio.to_thread(self.outro.build_outro)
```
This will crash with `AttributeError: 'NoneType' object has no attribute 'build_outro'` if `--no-outro` is passed. **Fix:** Add a guard in `_run_production`.

---

### 18. `.env` — `PIXABAY_API_KEY` is used in code but not documented
`video_creator.py` line 105 reads `PIXABAY_API_KEY` for background music, but it's not in the `.env` template or the README table. Users will miss it.

---

### 19. `manager.py` — `_log_bat_file()` dumps the entire bat file to the log every single run
This is ~6KB of batch script logged to `maker.log` on every job. It's noise that makes the log harder to read and serves no operational purpose. Should be removed or put behind a debug flag.

---

### 20. `video_creator.py` — No cleanup of `temp_cache_*.mp4` files on failure
If `assemble_multi_scene_video` fails after writing `temp_combined`, it's cleaned up (line 427–428). But on `CalledProcessError` that happens after the temp file is created, the `except` block returns `None` before cleanup. Stale temp files accumulate in `renders/`.

---

## Summary Table

| # | File | Severity | Issue |
|---|------|----------|-------|
| 1 | `video_creator.py` | 🔴 Bug | Hardcoded path to another machine |
| 2 | `manager.py` | 🔴 Bug | `platform` arg dropped — always youtube_short |
| 3 | `manager.py` | 🔴 Bug | `"Error" in script` kills valid scripts |
| 4 | `script_generator.py` | 🔴 Bug | `# type: ignore` comment inside f-string sent to LLM |
| 5 | `manager.py` | 🔴 Bug | Resume completion check reads wrong dict keys |
| 6 | `outro_maker.py` | 🔴 Bug | `OUTRO_PATH` evaluated before `.env` is loaded |
| 7 | `voice_engine.py` | 🔴 Bug | Sync HTTP call blocks async event loop |
| 8 | `manager.py` | 🟠 Issue | Log handler leak per job run |
| 9 | `video_creator.py` | 🟠 Issue | `-c copy` concat fails on mismatched streams |
| 10 | `video_creator.py` | 🟠 Issue | ffmpeg stderr suppressed — silent failures |
| 11 | `llm_router.py` | 🟠 Issue | Shared messages list mutated in-place |
| 12 | `video_creator.py` | 🟠 Issue | Unconditional 3.5s sleep per image attempt |
| 13 | `manager.py` | 🟠 Issue | MongoDB sync outside state lock |
| 14 | `outro_maker.py` | 🟠 Issue | Outro hardcoded to 1920×1080 |
| 15 | Multiple | 🟡 Quality | Mixed `print()` / `logger` — voice/video logs missing from file |
| 16 | `script_generator.py` | 🟡 Quality | 6 of 10 bat categories have no specific prompt |
| 17 | `maker_studio.py` | 🔴 Bug | `--no-outro` crashes with AttributeError |
| 18 | `.env` | 🟡 Quality | `PIXABAY_API_KEY` undocumented |
| 19 | `manager.py` | 🟡 Quality | Entire bat file logged every run |
| 20 | `video_creator.py` | 🟡 Quality | Temp files not cleaned up on assembly failure |
