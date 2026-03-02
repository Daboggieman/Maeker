import os
import logging
import requests
import asyncio
from logging.handlers import RotatingFileHandler
from database_manager import DatabaseManager
from script_generator import ScriptGenerator
from fact_checker import FactChecker
from voice_engine import VoiceEngine
from video_creator import VideoCreator
from compliance_engine import ComplianceEngine

# Setup Centralized Rotating Logging
LOG_DIR = "logs"
os.makedirs(LOG_DIR, exist_ok=True)
log_file = os.path.join(LOG_DIR, "maker.log")

# Keep 5 files of 10MB each
handler = RotatingFileHandler(log_file, maxBytes=10*1024*1024, backupCount=5)
handler.setFormatter(logging.Formatter('%(asctime)s - %(levelname)s - %(message)s'))

# Also print to terminal for CLI users
console_handler = logging.StreamHandler()
console_handler.setFormatter(logging.Formatter('%(message)s'))

logger = logging.getLogger("MakerStudio")
logger.setLevel(logging.INFO)
logger.addHandler(handler)
logger.addHandler(console_handler)

class JobManager:
    def __init__(self, webhook_url=None):
        self.db = DatabaseManager()
        self.generator = ScriptGenerator()
        self.checker = FactChecker()
        self.v_engine = VoiceEngine()
        self.v_creator = VideoCreator()
        self.compliance = ComplianceEngine()
        self.webhook_url = webhook_url
        self.state = {}

    def _notify(self, message, status="InProgress"):
        """Sends a pulse to n8n and logs it."""
        logger.info(f"JOB STATUS: {message}")
        if self.webhook_url:
            try:
                requests.post(self.webhook_url, json={
                    "topic": self.state.get("topic"),
                    "status": status,
                    "message": message,
                    "job_id": self.state.get("job_id")
                }, timeout=5)
            except Exception as e:
                logger.warning(f"Webhook notification failed: {e}")

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

    async def run_job(self, topic, category, produce=True, voice=None):
        self.state = {"topic": topic, "category": category, "status": "Started"}
        if voice:
            self.v_engine.voice_name = voice
            logger.info(f"Using voice: {voice}")
        self._notify(f"Starting job for topic: {topic}")

        try:
            # 1. Script Generation
            self._notify("Generating script...")
            script = await self._with_retry(self.generator.generate_script, topic, category)
            # Explicitly check for string type to satisfy IDE type checker
            if not isinstance(script, str) or "Error" in script:
                raise Exception("Script generation failed after retries.")
            self.state["script"] = script

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

            if produce:
                # 5. Scene Generation
                self._notify("Analyzing script to create cinematic scenes...")
                scenes = await self._with_retry(self.generator.generate_scenes, script)
                
                if not scenes:
                    raise Exception("Failed to break script into scenes.")
                    
                self.state["scenes"] = scenes
                scene_assets = []
                assets_dir = os.getenv("ASSETS_DIR", "assets")
                
                # Sanitize topic for folder names (e.g., "The Culture Of Ancient Egypt" -> "the_culture_of_ancient_egypt")
                import re
                topic_slug = re.sub(r'[^a-zA-Z0-9]', '_', topic.lower()).strip('_')
                
                # Create topic-specific subfolders
                topic_audio_dir = os.path.join(assets_dir, "audio", topic_slug)
                topic_images_dir = topic_slug # Passed as parameter to VideoCreator
                os.makedirs(topic_audio_dir, exist_ok=True)
                
                scenes_list = list(scenes)
                for index, scene in enumerate(scenes_list):
                    self._notify(f"Generating assets for scene {index+1} of {len(scenes_list)}...")
                    narration = scene.get("narration", "")
                    image_prompt = scene.get("image_prompt", "")
                    
                    if not narration:
                        continue
                        
                    # Voice (Saved in topic subfolder, narrator is now consistent)
                    audio_name = f"scene_{index}.mp3"
                    audio_path = os.path.join(topic_audio_dir, audio_name)
                    await self._with_retry(self.v_engine.generate_voice, narration, audio_path)
                    
                    # Image (Saved in topic subfolder via VideoCreator)
                    if not image_prompt:
                        image_prompt = f"A professional cinematic visual for: {topic}"
                    image_name = f"scene_{index}"
                    image_path_out = await self._with_retry(self.v_creator.generate_image, image_prompt, image_name, topic_folder=topic_images_dir)
                    
                    scene_assets.append({
                        "audio": audio_path,
                        "image": image_path_out,
                        "narration": narration
                    })

                # 6. Video Assembly
                if scene_assets:
                    self._notify(f"Assembling multi-scene video ({len(scene_assets)} clips) (this may take a few minutes)...")
                    video_name = topic.replace(' ', '_')[:50]
                    video_file = await asyncio.to_thread(self.v_creator.assemble_multi_scene_video, scene_assets, video_name)
                    
                    if video_file:
                        self.state["video_file"] = video_file
                        self._notify("Video assembly complete.")
                    else:
                        logger.warning("Video assembly returned no file.")
                else:
                    logger.warning("No valid scenes were generated, skipping video assembly.")

            # 7. Finalize
            self.state["status"] = "Complete"
            self._notify("Job finished successfully!", status="Complete")
            
            # Save to metadata
            self.db.save_content_metadata(self.state)
            return self.state

        except Exception as e:
            error_msg = f"Fatal error in job: {str(e)}"
            logger.error(error_msg, exc_info=True)
            self._notify(error_msg, status="Error")
            return {"status": "Error", "message": error_msg}
