import os
import sys
import argparse
import requests
import json
import asyncio
import shutil
from datetime import datetime
from dotenv import load_dotenv
from datetime import datetime
from dotenv import load_dotenv

def check_ffmpeg(is_json=False):
    """Checks if FFmpeg is available in the system PATH."""
    if shutil.which("ffmpeg") is None:
        error_msg = "FFmpeg NOT FOUND! Please add the 'ffmpeg/bin' folder of your ffmpeg folder to your Windows System PATH."
        if is_json:
            return False
        else:
            print("\n" + "!"*60)
            print(f"CRITICAL ERROR: {error_msg}")
            print("!"*60 + "\n")
        return False
    return True

def fetch_latest_news(query="Technology", limit=5):
    api_key = os.getenv("GNEWS_API_KEY")
    if not api_key:
        print("WARNING: GNEWS_API_KEY not found. Returning empty list.")
        return []
    
    url = f"https://gnews.io/api/v4/search?q={query}&max={limit}&apikey={api_key}&lang=en"
    try:
        response = requests.get(url, timeout=10)
        if response.status_code == 200:
            return response.json().get("articles", [])
        else:
            print(f"ERROR: GNews API failed with status {response.status_code}")
            return []
    except Exception as e:
        print(f"ERROR: GNews connection failed: {e}")
        return []

def main():
    parser = argparse.ArgumentParser(description="maker Studio Orchestrator")
    parser.add_argument("--topic", help="Topic for the content")
    parser.add_argument("--category", default="General", help="Category of the content")
    parser.add_argument("--fetch-news", action="store_true", help="Fetch latest news as topics")
    parser.add_argument("--produce", action="store_true", help="Enable voice and video production")
    parser.add_argument("--json", action="store_true", help="Output final results as JSON")
    args = parser.parse_args()

    is_produce = args.produce
    is_json = args.json

    try:
        # 0. News Fetch Logic
        if args.fetch_news:
            news_articles = fetch_latest_news(args.topic or "latest news")
            if news_articles:
                args.topic = news_articles[0]['title']
                if not is_json: print(f"Fetched news topic: {args.topic}")

        if not args.topic:
            error_msg = "--topic or --fetch-news is required."
            if is_json:
                print(json.dumps({"status": "Error", "message": error_msg}))
            else:
                print(f"Error: {error_msg}")
            sys.exit(1)

        if not is_json:
            print(f"--- Starting Job: {args.topic} ({args.category}) ---")

        # 0. Check for unresolved n8n variables
        if "{{" in str(args.topic) or "{{" in str(args.category):
            error_msg = "n8n EXPRESSION NOT RESOLVED! FIX: Go to the 'Run Maker Engine' node and click the 'Expression' tab."
            if is_json:
                print(json.dumps({"status": "Error", "message": error_msg}))
                sys.exit(0)
            else:
                print("\n" + "!"*70)
                print(f"CRITICAL ERROR: {error_msg}")
                print("!"*70 + "\n")
            sys.exit(1)
            
        # 1. Initialize Components
        from database_manager import DatabaseManager
        from script_generator import ScriptGenerator
        from fact_checker import FactChecker
        from voice_engine import VoiceEngine
        from video_creator import VideoCreator

        db = DatabaseManager()
        generator = ScriptGenerator()
        checker = FactChecker()

        # 2. Generate Script
        if not is_json: print("Generating script (Primary: Groq)...")
        script = generator.generate_script(args.topic, args.category)
        
        # 3. Fact Check
        if not is_json: print("Fact-checking script...")
        verification = checker.verify_script(script, args.category)

        # 4. Generate Viral Hooks
        if not is_json: print("Generating viral hooks...")
        hooks = generator.generate_hooks(script)

        # 5. Compliance Check
        if not is_json: print("Running compliance check...")
        from compliance_engine import ComplianceEngine
        compliance = ComplianceEngine()
        check_result = compliance.check_compliance(script, args.topic)

        # 6. Production
        audio_file = None
        video_file = None

        if is_produce:
            if not is_json: print("Starting production...")
            v_engine = VoiceEngine()
            audio_name = f"{args.topic.replace(' ', '_')[:50]}.mp3"
            assets_dir = os.getenv("ASSETS_DIR", "assets")
            audio_path = os.path.join(assets_dir, "audio", audio_name)
            
            # Ensure dir exists
            os.makedirs(os.path.dirname(audio_path), exist_ok=True)
            
            # Run async voice generation
            asyncio.run(v_engine.generate_voice(script, audio_path))
            audio_file = audio_path
            if not is_json: print(f"Voiceover generated: {audio_path}")

            # Video assembly with AI-generated image
            v_creator = VideoCreator()
            video_name = args.topic.replace(' ', '_')[:50]
            
            if not is_json: print("Generating visual content (Pollinations)...")
            image_path = v_creator.generate_image(f"A professional cinematic visual for: {args.topic}", video_name)
            
            if image_path and os.path.exists(image_path):
                if not is_json: print(f"Visual generated: {image_path}")
                # FINAL ASSEMBLY
                if not is_json: print(f"\n--- STEP 4: VIDEO ASSEMBLY ---")
                if not check_ffmpeg(is_json=is_json):
                    error_msg = "FFmpeg NOT FOUND! Please add the 'bin' folder (from the ZIP) to your Windows System PATH and RESTART n8n."
                    if is_json:
                        print(json.dumps({"status": "Error", "message": error_msg}))
                        sys.exit(0) # Exit 0 so n8n can show the JSON error
                    else:
                        print(f"Skipping video assembly due to missing FFmpeg.")
                    sys.exit(1)

                video_file = v_creator.assemble_video(audio_path, image_path, video_name)
                if not video_file:
                    if not is_json: print("WARNING: Video assembly failed. Audio only.")
                else:
                    if not is_json: print(f"Video assembled: {video_file}")
            else:
                if not is_json: print("WARNING: Visual generation failed. Skipping video assembly.")

        # 7. Save to Metadata (MongoDB)
        metadata = {
            "topic": args.topic,
            "category": args.category,
            "script": script,
            "verification_notes": verification,
            "suggested_hooks": hooks,
            "compliance": check_result,
            "audio_file": audio_file,
            "video_file": video_file,
            "status": "Production Complete" if video_file else ("Audio Ready" if audio_file else "Awaiting Approval")
        }
        
        db_result = db.save_content_metadata(metadata)
        
        if is_json:
            print(json.dumps(metadata, indent=4, default=str))
        else:
            print("\n--- JOB COMPLETE ---")
            print(f"Status: {check_result['status']}")
            if db_result:
                print(f"Database ID: {db_result.inserted_id}")

    except Exception as e:
        error_msg = f"RUNTIME ERROR: {str(e)}"
        if is_json:
            print(json.dumps({"status": "Error", "message": error_msg}))
            sys.exit(0) # Exit 0 so n8n can show the JSON error
        else:
            print(f"\nCRITICAL {error_msg}")
            sys.exit(1)

if __name__ == "__main__":
    main()