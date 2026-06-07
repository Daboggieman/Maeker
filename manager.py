import os
import re
import json
import uuid
import logging
import asyncio
import requests  # type: ignore
from logging.handlers import RotatingFileHandler
from database_manager import DatabaseManager  # type: ignore
from script_generator import ScriptGenerator  # type: ignore
from fact_checker import FactChecker  # type: ignore
from voice_engine import VoiceEngine  # type: ignore
from video_creator import VideoCreator  # type: ignore
from compliance_engine import ComplianceEngine  # type: ignore
from outro_maker import OutroMaker  # type: ignore
from youtube_uploader import YouTubeUploader  # type: ignore
from tiktok_uploader import TikTokUploader  # type: ignore

# Setup Centralized Logging
LOG_DIR = "logs"
os.makedirs(LOG_DIR, exist_ok=True)

logger = logging.getLogger("MakerStudio")
logger.setLevel(logging.INFO)

# Global Console Handler (always shows in CLI)
if not logger.handlers:
    console_handler = logging.StreamHandler()
    console_handler.setFormatter(logging.Formatter('%(message)s'))
    logger.addHandler(console_handler)

JOBS_DIR = "jobs"
os.makedirs(JOBS_DIR, exist_ok=True)

class JobManager:
    def __init__(self, status_callback=None):
        self.db = DatabaseManager()
        self.generator = ScriptGenerator()
        self.checker = FactChecker()
        self.v_engine = VoiceEngine()
        self.v_creator = VideoCreator()
        self.base_dir = self.v_creator.base_dir
        self.compliance = ComplianceEngine()
        self.outro = OutroMaker()
        self.state = {}
        self._state_lock = asyncio.Lock()
        self.scene_semaphore = asyncio.Semaphore(2)
        self.status_callback = status_callback

    def _log_bat_file(self):
        """Reads run_job.bat and records it in the current logger."""
        try:
            bat_path = os.path.join(self.base_dir, "run_job.bat")
            if os.path.exists(bat_path):
                with open(bat_path, "r", encoding="utf-8") as f:
                    content = f.read()
                logger.info(f"--- run_job.bat CONTENT ---\n{content}\n--- END run_job.bat ---")
        except Exception as e:
            logger.warning(f"Could not read/log run_job.bat: {e}")

    def _cleanup_log_handler(self):
        """Removes and closes the per-job log file handler to prevent handler accumulation."""
        handler = getattr(self, '_current_log_handler', None)
        if handler:
            try:
                logger.removeHandler(handler)
                handler.close()
            except Exception:
                pass
            self._current_log_handler = None

    def _notify(self, message, status="InProgress"):
        """Logs status updates and syncs state to MongoDB."""
        logger.info(f"JOB STATUS: {message}")
        self.state["status"] = status
        self.state["last_message"] = message

        if self.status_callback:
            try:
                if asyncio.iscoroutinefunction(self.status_callback):
                    # We are generally inside an async function like run_job
                    asyncio.create_task(self.status_callback(message))
                else:
                    self.status_callback(message)
            except Exception as e:
                logger.warning(f"Status callback failed: {e}")

        # Real-time Sync to MongoDB
        try:
            self.db.save_content_metadata(self.state)
        except Exception as e:
            logger.warning(f"MongoDB real-time sync failed: {e}")

    def _save_state(self):
        """Persists the current job state to jobs/{job_id}.json."""
        job_id = self.state.get("job_id")
        if not job_id:
            return
        state_path = os.path.join(JOBS_DIR, f"{job_id}.json")
        temp_path = os.path.join(JOBS_DIR, f"{job_id}.json.tmp")
        try:
            with open(temp_path, "w", encoding="utf-8") as f:
                json.dump(self.state, f, indent=2, default=str)
            os.replace(temp_path, state_path)
        except Exception as e:
            logger.warning(f"Could not save job state: {e}")

    def _load_state(self, job_id: str) -> dict:
        """Loads a job state from disk. Supports partial/prefix matching on job IDs."""
        state_path = os.path.join(JOBS_DIR, f"{job_id}.json")
        if os.path.exists(state_path):
            with open(state_path, "r", encoding="utf-8") as f:
                return json.load(f)

        # --- Prefix / fuzzy match ---
        try:
            all_files = [f for f in os.listdir(JOBS_DIR) if f.endswith(".json")]
        except OSError:
            all_files = []

        matches = [f for f in all_files if f.startswith(job_id)]

        if len(matches) == 1:
            matched_path = os.path.join(JOBS_DIR, matches[0])
            matched_id = matches[0][:-5]  # type: ignore
            logger.info(f"[resume] Matched '{job_id}' → full job ID: {matched_id}")
            self.state["job_id"] = matched_id  # patch job_id to the full name
            with open(matched_path, "r", encoding="utf-8") as f:
                return json.load(f)
        elif len(matches) > 1:
            match_list = "\n  ".join(m[:-5] for m in matches)  # type: ignore
            raise FileNotFoundError(
                f"Multiple jobs match '{job_id}':\n  {match_list}\nPlease provide a more specific Job ID."
            )
        else:
            available = "\n  ".join(f[:-5] for f in all_files) if all_files else "  (none)"  # type: ignore
            raise FileNotFoundError(
                f"No saved job found for ID '{job_id}'.\nAvailable jobs:\n  {available}"
            )

    async def _with_retry(self, func, *args, retries=3, delay=5, **kwargs):
        """Helper for simple retry logic that handles both sync and async functions."""
        for i in range(retries):
            try:
                result = func(*args, **kwargs)
                if asyncio.iscoroutine(result):
                    return await result
                return result
            except Exception as e:
                if i == retries - 1:
                    raise e
                logger.warning(f"Retry {i+1}/{retries} failed: {e}. Retrying in {delay}s...")
                await asyncio.sleep(delay)

    async def _generate_scene_assets(self, index: int, scene: dict, job_id: str,
                                       audio_dir: str, images_dir_name: str, topic: str) -> dict | None:
        """
        Generates image + audio for a single scene. Thread-safe via asyncio.Lock.
        Returns an asset dict on success, or None if the scene should be skipped.
        """
        async with self.scene_semaphore:
            # --- Resume: skip if already completed ---
            completed = self.state.get("completed_scenes", [])
            cache_dir = os.path.join(self.base_dir, "assets", "cache", job_id)
        
            if index in completed:
                # Re-load asset paths from saved state
                saved_assets = self.state.get("scene_assets", [])
                for a in saved_assets:
                    if a.get("scene_index") == index:
                        # Double check if the video cache actually exists
                        video_cache = a.get("video_cache")
                        if video_cache and os.path.exists(video_cache):
                            logger.info(f"[resume] skipping scene {index + 1} (assets & cache exist).")
                            return a
                        else:
                            logger.warning(f"[resume] scene {index + 1} missing cache — re-rendering clip.")
                            # Fall through to re-render but skip image/audio gen if they exist
                            break

            narration = scene.get("narration", "").strip()
            image_prompt = scene.get("image_prompt", "").strip()

            if not narration:
                logger.warning(f"Scene {index + 1}: empty narration — skipping.")
                return None

            if not image_prompt:
                image_prompt = f"A professional cinematic visual for: {topic}"

            logger.info(f"[scene {index + 1}] Generating image...")
            image_name = f"scene_{index}"

            # Determine desired image size based on target video format
            video_format = self.state.get("platform", "youtube_short")
            if video_format in ["youtube_short", "tiktok"]:
                img_w, img_h = 720, 1280
            else:
                img_w, img_h = 1280, 720

            async def _run_image_gen():
                return await asyncio.to_thread(
                    self.v_creator.generate_image,
                    image_prompt,
                    image_name,
                    topic_folder=images_dir_name,
                    width=img_w,
                    height=img_h,
                )

            image_path_out = await self._with_retry(_run_image_gen)

            if not image_path_out:
                logger.warning(f"Scene {index + 1}: image failed — skipping audio to preserve TTS quota.")
                return None

            logger.info(f"[scene {index + 1}] Generating audio...")
            audio_path = os.path.join(audio_dir, f"scene_{index}.mp3")
            await self._with_retry(self.v_engine.generate_voice, narration, audio_path)

            asset = {
                "scene_index": index,
                "audio": audio_path,
                "image": image_path_out,
                "narration": narration,
            }

            # --- Incremental Rendering (Plan 1) ---
            os.makedirs(cache_dir, exist_ok=True)
            video_cache_path = os.path.join(cache_dir, f"scene_{index}.mp4")
            
            # Determine video format from state or default
            video_format = self.state.get("platform", "youtube_short")
            if video_format in ["youtube_short", "tiktok"]:
                v_fmt = "9:16"
            else:
                v_fmt = "16:9"

            logger.info(f"[scene {index + 1}] Rendering scene segment...")
            success = await asyncio.to_thread(
                self.v_creator.create_scene_clip, asset, video_cache_path, format=v_fmt
            )
            
            if success:
                asset["video_cache"] = video_cache_path
            else:
                logger.error(f"Scene {index + 1}: Failed to render cached segment.")

            # Thread-safe state update
            async with self._state_lock:
                self.state.setdefault("completed_scenes", []).append(index)
                self.state.setdefault("scene_assets", []).append(asset)
                self._save_state()

            return asset

    async def _run_production(self, topic: str, script: str, job_id: str,
                               music: bool = False, platform: str = "youtube_short") -> str | None:
        """Shared production pipeline (scene gen + video assembly) used by both run_job and resume_job."""
        assets_dir = os.getenv("ASSETS_DIR", "assets")

        # --- Setup job-specific asset dirs ---
        audio_dir = os.path.join(assets_dir, "audio", job_id)
        images_dir_name = job_id  # Passed as topic_folder to VideoCreator
        os.makedirs(audio_dir, exist_ok=True)
        os.makedirs(os.path.join(assets_dir, "images", job_id), exist_ok=True)

        scenes = self.state.get("scenes")
        if not scenes:
            self._notify("Analyzing script to create cinematic scenes...")
            scenes = await self._with_retry(self.generator.generate_scenes, script)
            if not scenes:
                raise Exception("Failed to break script into scenes.")
            self.state["scenes"] = list(scenes)  # type: ignore
            self._save_state()

        scenes_list = list(scenes)  # type: ignore
        total = len(scenes_list)
        self._notify(f"Generating assets sequentially for {total} scenes...")

        # --- Sequential asset generation ---
        scene_assets = []
        for i, scene in enumerate(scenes_list):
            try:
                r = await self._generate_scene_assets(i, scene, job_id, audio_dir, images_dir_name, topic)
                if r is not None:
                    scene_assets.append(r)
            except Exception as e:
                logger.warning(f"Scene {i+1} generation task failed: {e}")

        if not scene_assets:
            logger.warning("No valid scenes were generated, skipping video assembly.")
            return None

        # --- Optional background music ---
        music_path = None
        if music:
            self._notify("Fetching background music track...")
            music_path = self.v_creator.fetch_background_music(topic, job_id)

        # --- Video assembly ---
        self._notify(f"Assembling multi-scene video ({len(scene_assets)} clips) for platform: {platform}...")
        video_name = re.sub(r'[^a-zA-Z0-9]', '_', topic.lower()).strip('_')[:50]  # type: ignore
        
        # Determine format from platform
        video_format = "16:9" if platform == "youtube" else "9:16"
        
        video_file = await asyncio.to_thread(
            self.v_creator.assemble_multi_scene_video, scene_assets, video_name, format=video_format, music_path=music_path
        )

        if not video_file:
            return None

        # --- Outro append ---
        if self.outro is not None:
            self._notify("Appending Maeker Studios outro...")
            outro_path = await asyncio.to_thread(self.outro.build_outro)
            video_file = await asyncio.to_thread(self.v_creator.append_outro, video_file, outro_path)

        return video_file

    async def run_job(self, topic, category, produce=True, voice=None, music=False, upload=False, platform="youtube_short"):
        raw_slug: str = re.sub(r'[^a-zA-Z0-9]', '_', topic.lower()).strip('_')
        topic_slug = raw_slug[:30]  # type: ignore

        # Generate a unique, human-readable job ID
        short_uuid = str(uuid.uuid4()).replace('-', '')[:8]  # type: ignore
        job_id = f"{short_uuid}_{topic_slug}"

        # Add dynamic file handler for this specific run
        log_file = os.path.join(LOG_DIR, f"maker_{topic_slug}.log")
        file_handler = logging.FileHandler(log_file, encoding='utf-8')
        file_handler.setFormatter(logging.Formatter('%(asctime)s - %(levelname)s - %(message)s'))
        logger.addHandler(file_handler)
        self._current_log_handler = file_handler

        self.state = {
            "job_id": job_id,
            "topic": topic,
            "category": category,
            "platform": platform,
            "status": "Started",
            "completed_scenes": [],
            "scene_assets": [],
        }
        if voice:
            self.v_engine.voice_name = voice
            logger.info(f"Using voice: {voice}")

        logger.info(f"[JOB ID] {job_id}")
        self._notify(f"Starting job for topic: {topic}")
        self._save_state()

        try:
            # 1. Script Generation
            self._notify("Generating script...")
            script = await self._with_retry(self.generator.generate_script, topic, category)
            if not isinstance(script, str) or not script.strip():
                raise Exception("Script generation failed after retries.")
            self.state["script"] = script
            self._save_state()

            # 2. Fact Checking
            self._notify("Verifying facts...")
            verification = await self._with_retry(self.checker.verify_script, script, category)
            self.state["verification"] = verification

            # 3. Hooks
            self._notify("Generating viral hooks...")
            hooks = await self._with_retry(self.generator.generate_hooks, script)
            self.state["hooks"] = hooks

            # 4. Compliance
            self._notify("Running compliance check...")
            compliance_result = self.compliance.check_compliance(script, topic)
            self.state["compliance"] = compliance_result

            if compliance_result.get("status") == "Flagged":
                risk_level = compliance_result.get("risk_level", "Medium")
                issues = compliance_result.get("issues", [])
                logger.warning(f"Compliance Alert: {risk_level} risk. Issues: {issues}")

                if risk_level in ["High", "Medium"]:
                    self._notify("Attempting to auto-correct compliance issues...")
                    new_script = self.compliance.rewrite_for_compliance(script, issues)
                    if new_script:
                        self._notify("Script rewritten for compliance. Re-verifying...")
                        script = new_script
                        self.state["script"] = script
                        compliance_result = self.compliance.check_compliance(script, topic)
                        self.state["compliance"] = compliance_result
                        if compliance_result.get("status") == "Flagged" and compliance_result.get("risk_level") == "High":
                            raise Exception(f"Job halted: Second compliance check still High Risk: {compliance_result.get('issues')}")
                        self._notify("Compliance issues resolved via auto-correction.")
                    else:
                        if risk_level == "High":
                            raise Exception("Job halted: High Risk script and auto-correction failed.")

            self._save_state()

            if produce:
                # 5. Scene generation + video assembly + outro
                video_file = await self._run_production(topic, script, job_id, music=music, platform=platform)
                if video_file:
                    self.state["video_file"] = video_file
                    self._notify("Video production complete.")

                    # 6. Upload metadata
                    self._notify("Generating upload titles and descriptions...")
                    hooks = self.state.get("hooks", "")
                    upload_meta = self.generator.generate_upload_metadata(script, topic, category, hooks)
                    self.state["upload_metadata"] = upload_meta
                    self._save_state()
                    logger.info(f"[YouTube Title] {upload_meta.get('youtube_title')}")

                    # 7. Auto-upload
                    if upload:
                        self._notify("Uploading to YouTube...")
                        yt_result = YouTubeUploader().upload_video(
                            video_file,
                            title=upload_meta.get("youtube_title", topic),
                            description=upload_meta.get("youtube_description", ""),
                            tags=upload_meta.get("tiktok_tags", []),
                            category=category,
                        )
                        self.state["youtube_upload"] = yt_result
                        logger.info(f"[YouTube Upload] {yt_result}")

                        self._notify("Uploading to TikTok...")
                        tt_result = TikTokUploader().upload_video(
                            video_file,
                            title=upload_meta.get("tiktok_title", topic),
                            tags=upload_meta.get("tiktok_tags", []),
                        )
                        self.state["tiktok_upload"] = tt_result
                        logger.info(f"[TikTok Upload] {tt_result}")
                else:
                    logger.warning("Video production returned no file.")

            # 6. Finalize
            self.state["status"] = "Complete"
            self._notify("Job finished successfully!", status="Complete")
            self._save_state()
            self.db.save_content_metadata(self.state)
            self._cleanup_log_handler()
            return self.state

        except Exception as e:
            error_msg = f"Fatal error in job: {str(e)}"
            logger.error(error_msg, exc_info=True)
            self._notify(error_msg, status="Error")
            self.state["status"] = "Error"
            self._save_state()
            self._cleanup_log_handler()
            return {"status": "Error", "message": error_msg}

    async def resume_job(self, job_id: str, voice=None, music=False, upload=False, platform="youtube_short"):
        """Loads a saved job state and resumes from the first incomplete scene."""
        logger.info(f"[RESUME] Loading job state for ID: {job_id}")
        self.state = self._load_state(job_id)

        topic = self.state.get("topic", "")
        category = self.state.get("category", "General")
        script = self.state.get("script", "")

        if not topic or not script:
            return {"status": "Error", "message": "Saved state is missing topic or script. Cannot resume."}

        if voice:
            self.v_engine.voice_name = voice
            logger.info(f"Using voice: {voice}")

        raw_slug: str = re.sub(r'[^a-zA-Z0-9]', '_', topic.lower()).strip('_')
        topic_slug = raw_slug[:30]  # type: ignore
        log_file = os.path.join(LOG_DIR, f"maker_{topic_slug}.log")
        file_handler = logging.FileHandler(log_file, encoding='utf-8')
        file_handler.setFormatter(logging.Formatter('%(asctime)s - %(levelname)s - %(message)s'))
        logger.addHandler(file_handler)
        self._current_log_handler = file_handler

        completed = self.state.get("completed_scenes", [])
        self._notify(f"Resuming job '{job_id}' — {len(completed)} scene(s) already completed.")

        try:
            # We can assume if we're resuming, we only need to finish scenes & produce video
            topic = self.state["topic"]
            script = self.state["script"]
            job_id = self.state["job_id"]
            category = self.state.get("category", "General")

            if "platform" not in self.state:
                self.state["platform"] = platform
            video_file = await self._run_production(topic, script, job_id, music=music, platform=self.state.get("platform", platform))
            if video_file:
                self.state["video_file"] = video_file
                self._notify("Video assembly complete.")

                # 6. Upload metadata (if not already there)
                if "upload_metadata" not in self.state:
                    self._notify("Generating upload titles and descriptions...")
                    hooks = self.state.get("hooks", "")
                    upload_meta = self.generator.generate_upload_metadata(script, topic, category, hooks)
                    self.state["upload_metadata"] = upload_meta
                    self._save_state()
                    logger.info(f"[YouTube Title] {upload_meta.get('youtube_title')}")
                else:
                    upload_meta = self.state["upload_metadata"]

                # 7. Auto-upload
                if upload:
                    self._notify("Uploading to YouTube...")
                    yt_result = YouTubeUploader().upload_video(
                        video_file,
                        title=upload_meta.get("youtube_title", topic),
                        description=upload_meta.get("youtube_description", ""),
                        tags=upload_meta.get("tiktok_tags", []),
                        category=category,
                    )
                    self.state["youtube_upload"] = yt_result
                    logger.info(f"[YouTube Upload] {yt_result}")

                    self._notify("Uploading to TikTok...")
                    tt_result = TikTokUploader().upload_video(
                        video_file,
                        title=upload_meta.get("tiktok_title", topic),
                        tags=upload_meta.get("tiktok_tags", []),
                    )
                    self.state["tiktok_upload"] = tt_result
                    logger.info(f"[TikTok Upload] {tt_result}")
            else:
                logger.warning("Video production returned no file.")

            self.state["status"] = "Complete"
            self._notify("Resumed job finished successfully!", status="Complete")
            self._save_state()
            self.db.save_content_metadata(self.state)
            self._cleanup_log_handler()
            return self.state

        except Exception as e:
            error_msg = f"Fatal error while resuming job: {str(e)}"
            logger.error(error_msg, exc_info=True)
            self._notify(error_msg, status="Error")
            self.state["status"] = "Error"
            self._save_state()
            self._cleanup_log_handler()
            return {"status": "Error", "message": error_msg}
