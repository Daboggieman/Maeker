import os
import sys
import argparse
import asyncio
from dotenv import load_dotenv
from manager import JobManager

def cleanup_old_assets(days_assets=7, days_logs=30):
    import time
    base_dir = os.path.dirname(os.path.abspath(__file__))
    
    # Clean assets
    assets_dir = os.path.join(base_dir, "assets")
    if os.path.exists(assets_dir):
        now = time.time()
        for root, dirs, files in os.walk(assets_dir):
            if "renders" in root or "outro" in root:
                continue
            for name in files:
                filepath = os.path.join(root, name)
                if os.path.isfile(filepath):
                    if os.stat(filepath).st_mtime < now - days_assets * 86400:
                        try:
                            os.remove(filepath)
                            print(f"[cleanup] Removed old asset: {filepath}")
                        except Exception as e:
                            print(f"[cleanup] Failed to remove {filepath}: {e}")
                            
    # Clean logs
    logs_dir = os.path.join(base_dir, "logs")
    if os.path.exists(logs_dir):
        now = time.time()
        for name in os.listdir(logs_dir):
            filepath = os.path.join(logs_dir, name)
            if os.path.isfile(filepath):
                if os.stat(filepath).st_mtime < now - days_logs * 86400:
                    try:
                        os.remove(filepath)
                        print(f"[cleanup] Removed old log: {filepath}")
                    except Exception as e:
                        print(f"[cleanup] Failed to remove {filepath}: {e}")

def main():
    parser = argparse.ArgumentParser(description="Maker Studio Orchestrator")
    parser.add_argument("--topic", help="Topic for the content (not required when using --resume)")
    parser.add_argument("--category", default="General", help="Category of the content")
    parser.add_argument("--voice", default=None, help="ElevenLabs voice name to use for narration")
    parser.add_argument("--produce", action="store_true", help="Enable voice and video production")
    parser.add_argument("--music", action="store_true", help="Fetch and mix royalty-free background music into the video")
    parser.add_argument("--platform", choices=["youtube", "youtube_short", "tiktok"], default="youtube_short", help="Target platform format for aspect ratio cropping")
    parser.add_argument("--upload", action="store_true", help="Auto-upload finished video to YouTube and TikTok")
    parser.add_argument("--no-outro", dest="no_outro", action="store_true", help="Skip the Maeker Studios branded outro clip")
    parser.add_argument("--resume", metavar="JOB_ID", default=None,
                        help="Resume an interrupted job by its Job ID (e.g. 3f9a1b2c_ancient_china)")
    args = parser.parse_args()

    # Load environment variables
    load_dotenv()

    # Initialize JobManager
    manager = JobManager()

    # Fail-Fast Configuration Validation
    active_llms = manager.generator.router.get_active_providers()
    if not active_llms:
        print("\n[CRITICAL ERROR] No LLM providers configured.")
        print("Please set GROQ_API_KEY, OPENROUTER_API_KEY, or ensure Ollama is running.")
        sys.exit(1)
    else:
        print(f"[MAKER STUDIO] Active LLM Providers: {', '.join(active_llms)}")
        
    if not os.getenv("ELEVENLABS_API_KEY") and args.produce:
        print("\n[WARNING] ELEVENLABS_API_KEY is missing. Falling back to free Edge TTS voice engine.")

    try:
        import subprocess
        subprocess.run(["ffmpeg", "-version"], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, check=True)
    except Exception:
        print("\n[CRITICAL ERROR] ffmpeg is not installed or not found in system PATH.")
        print("Please install ffmpeg (https://ffmpeg.org/download.html) before running Maker Studio.")
        sys.exit(1)
        
    # Automated Asset Cleanup
    cleanup_old_assets(days_assets=7, days_logs=30)

    # Pass no_outro flag through to manager
    if args.no_outro:
        manager.outro = None  # disable outro rendering

    # --- Resume mode ---
    if args.resume:
        print(f"\n[MAKER STUDIO] Resuming job: {args.resume}")
        result = asyncio.run(manager.resume_job(
            args.resume, voice=args.voice, music=args.music, upload=args.upload, platform=args.platform
        ))
    else:
        if not args.topic:
            print("Error: --topic is required when not using --resume.")
            sys.exit(1)
        result = asyncio.run(manager.run_job(
            args.topic, args.category,
            produce=args.produce,
            voice=args.voice,
            music=args.music,
            upload=args.upload,
            platform=args.platform
        ))

    # Output results
    if result.get("status") == "Error":
        print(f"\nCRITICAL ERROR: {result.get('message')}")
        sys.exit(1)
    else:
        job_id = result.get("job_id", "N/A")
        topic  = result.get("topic", args.topic or args.resume)
        meta   = result.get("upload_metadata", {})
        print(f"\n--- JOB COMPLETE: {topic} ---")
        print(f"Status  : {result.get('status')}")
        print(f"Job ID  : {job_id}")
        if meta:
            print(f"\nYouTube Title : {meta.get('youtube_title', 'N/A')}")
            print(f"TikTok Caption: {meta.get('tiktok_title', 'N/A')}")
        if result.get("youtube_upload"):
            yt = result["youtube_upload"]
            print(f"YouTube Upload: {yt.get('status')} — {yt.get('url', '')}")
        if result.get("tiktok_upload"):
            tt = result["tiktok_upload"]
            print(f"TikTok Upload : {tt.get('status')}")
        print(f"\n(To resume this job later: --resume {job_id})")

if __name__ == "__main__":
    main()